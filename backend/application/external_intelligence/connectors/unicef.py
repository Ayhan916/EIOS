"""UNICEF Child Welfare Connector — M34.1.

Fetches child welfare, child labour, and education access indicators.
Maps to: CountryRiskProfile.human_rights_score (partial contribution).
"""

from __future__ import annotations

from typing import Any

import structlog

from application.external_intelligence.base_adapter import RawDataset
from domain.enums import ExternalSourceName

from .base import BaseLiveConnector

logger = structlog.get_logger(__name__)

_UNICEF_BASE = "https://data.unicef.org/wp-json/unicef/v1/indicator"

_UNICEF_INDICATORS = {
    "PT_CHLD_5-17_LBR_ECON": "child_labour_pct",
    "EDU_SE_AGP_CPRA_L2": "out_of_school_pct",
}


class UNICEFConnector(BaseLiveConnector):
    """Fetches UNICEF indicators and maps them to human rights risk scores."""

    connector_name = ExternalSourceName.UNICEF.value
    connector_version = "2024"
    refresh_cadence_hours = 24 * 30

    async def fetch(self, client: Any) -> list[dict[str, Any]]:
        """Fetch UNICEF child welfare indicators."""
        aggregated: dict[str, dict[str, Any]] = {}

        for indicator, metric_key in _UNICEF_INDICATORS.items():
            url = f"{_UNICEF_BASE}/{indicator}?format=json"
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                items = resp.json().get("data", resp.json())
                if isinstance(items, list):
                    for item in items:
                        iso3 = item.get("iso3") or item.get("country_iso_code", "")
                        val = item.get("value") or item.get("obs_value")
                        if not iso3 or val is None:
                            continue
                        if iso3 not in aggregated:
                            aggregated[iso3] = {
                                "country_code": iso3,
                                "country_name": item.get("country_name", ""),
                            }
                        try:
                            aggregated[iso3][metric_key] = float(val)
                        except (ValueError, TypeError):
                            pass
            except Exception as exc:
                logger.warning("unicef_indicator_fetch_failed", indicator=indicator, error=str(exc))

        return list(aggregated.values())

    def normalize(self, raw_records: list[dict[str, Any]]) -> RawDataset:
        """Convert UNICEF indicators to human_rights_score (0–100, higher=more risk)."""
        records = []
        for entry in raw_records:
            child_labour = min(float(entry.get("child_labour_pct", 0.0)), 100.0)
            out_of_school = min(float(entry.get("out_of_school_pct", 0.0)), 100.0)
            human_rights_score = round((child_labour * 0.6 + out_of_school * 0.4), 2)
            records.append({
                "country_code": entry["country_code"],
                "country_name": entry.get("country_name", ""),
                "human_rights_score": human_rights_score,
                "child_labour_pct": entry.get("child_labour_pct", 0.0),
                "out_of_school_pct": entry.get("out_of_school_pct", 0.0),
                "source": ExternalSourceName.UNICEF.value,
            })
        return RawDataset(
            source_name=ExternalSourceName.UNICEF.value,
            source_version=self.connector_version,
            records=records,
            description=f"UNICEF Child Welfare Indicators ({self.connector_version})",
        )
