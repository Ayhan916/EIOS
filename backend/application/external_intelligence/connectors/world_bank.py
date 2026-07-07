"""World Bank Governance Indicators Connector — M34.1.

Fetches the six World Governance Indicators (WGI):
  CC  — Control of Corruption   → corruption_score
  GE  — Government Effectiveness
  RQ  — Regulatory Quality
  RL  — Rule of Law
  PS  — Political Stability
  VA  — Voice and Accountability
  (GE + RQ + RL + PS + VA) average → governance_score

WGI raw values range −2.5 (worst) to +2.5 (best).
EIOS risk scores are 0–100 where 100 = highest risk.
Conversion: risk = max(0, min(100, (2.5 − raw) / 5.0 × 100))
"""

from __future__ import annotations

from typing import Any

import structlog

from application.external_intelligence.base_adapter import RawDataset
from domain.enums import ExternalSourceName

from .base import BaseLiveConnector

logger = structlog.get_logger(__name__)

_WGI_INDICATORS = {
    "CC.EST": "corruption",
    "GE.EST": "governance",
    "RQ.EST": "governance",
    "RL.EST": "governance",
    "PS.EST": "governance",
    "VA.EST": "governance",
}

_WB_BASE = "https://api.worldbank.org/v2/country/all/indicator"
_PER_PAGE = 300


class WorldBankConnector(BaseLiveConnector):
    """Fetches World Bank WGI data and maps it to CountryRiskProfile inputs."""

    connector_name = ExternalSourceName.WORLD_BANK.value
    connector_version = "2024"
    refresh_cadence_hours = 24 * 30  # monthly

    async def fetch(self, client: Any) -> list[dict[str, Any]]:
        """Fetch all 6 WGI indicators and aggregate by country."""
        aggregated: dict[str, dict[str, Any]] = {}

        for indicator_id in _WGI_INDICATORS:
            url = f"{_WB_BASE}/WGI.{indicator_id}?format=json&mrv=1&per_page={_PER_PAGE}"
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
            records = payload[1] if len(payload) > 1 else []
            for rec in records:
                country_code = rec.get("countryiso3code", "").strip()
                if not country_code or not rec.get("value"):
                    continue
                if country_code not in aggregated:
                    aggregated[country_code] = {
                        "country_code": country_code,
                        "country_name": rec.get("country", {}).get("value", ""),
                        "date": rec.get("date", ""),
                        "indicators": {},
                    }
                aggregated[country_code]["indicators"][indicator_id] = rec["value"]

        return list(aggregated.values())

    def normalize(self, raw_records: list[dict[str, Any]]) -> RawDataset:
        """Map WGI indicator values to EIOS CountryRiskProfile format."""
        records = []
        for entry in raw_records:
            indicators = entry.get("indicators", {})
            gov_values = [
                indicators[k]
                for k in ["GE.EST", "RQ.EST", "RL.EST", "PS.EST", "VA.EST"]
                if k in indicators
            ]
            governance_raw = sum(gov_values) / len(gov_values) if gov_values else 0.0
            corruption_raw = indicators.get("CC.EST", 0.0)

            def to_risk(raw: float) -> float:
                return max(0.0, min(100.0, (2.5 - raw) / 5.0 * 100))

            records.append(
                {
                    "country_code": entry["country_code"],
                    "country_name": entry["country_name"],
                    "governance_score": round(to_risk(governance_raw), 2),
                    "corruption_score": round(to_risk(corruption_raw), 2),
                    "labour_rights_score": 0.0,
                    "environmental_risk_score": 0.0,
                    "human_rights_score": 0.0,
                    "sanctions_status": "none",
                    "data_date": entry.get("date", ""),
                    "source": ExternalSourceName.WORLD_BANK.value,
                }
            )
        return RawDataset(
            source_name=ExternalSourceName.WORLD_BANK.value,
            source_version=self.connector_version,
            records=records,
            description=f"World Bank WGI Governance Indicators ({self.connector_version})",
        )

    def validate(self, raw: RawDataset) -> list[str]:
        errors = super().validate(raw)
        required = {"country_code", "country_name", "governance_score", "corruption_score"}
        for rec in raw.records[:5]:
            missing = required - set(rec.keys())
            if missing:
                errors.append(f"Record missing required fields: {missing}")
                break
        return errors
