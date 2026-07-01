"""Transparency International CPI Connector — M34.1.

Fetches the Corruption Perceptions Index (CPI) from the TI data API.
CPI ranges 0 (highly corrupt) to 100 (very clean).
EIOS corruption_score: 100 - CPI (so higher = more corrupt).
"""

from __future__ import annotations

from typing import Any

import structlog

from application.external_intelligence.base_adapter import RawDataset
from domain.enums import ExternalSourceName

from .base import BaseLiveConnector

logger = structlog.get_logger(__name__)

_TI_URL = "https://www.transparency.org/en/api/latest/country-scores"


class TransparencyInternationalConnector(BaseLiveConnector):
    """Fetches TI CPI data and maps it to CountryRiskProfile corruption_score."""

    connector_name = ExternalSourceName.TRANSPARENCY_INTERNATIONAL.value
    connector_version = "2024"
    refresh_cadence_hours = 24 * 30  # monthly — CPI published annually

    async def fetch(self, client: Any) -> list[dict[str, Any]]:
        """Fetch latest CPI scores from TI data API."""
        resp = await client.get(_TI_URL)
        resp.raise_for_status()
        return resp.json()

    def normalize(self, raw_records: list[dict[str, Any]]) -> RawDataset:
        """Convert CPI scores (0-100) to corruption_score risk (0-100, inverted)."""
        records = []
        for entry in raw_records:
            cpi = entry.get("value") or entry.get("score")
            if cpi is None:
                continue
            corruption_risk = max(0.0, min(100.0, 100.0 - float(cpi)))
            records.append({
                "country_code": entry.get("iso3") or entry.get("country_code", ""),
                "country_name": entry.get("country") or entry.get("name", ""),
                "corruption_score": round(corruption_risk, 2),
                "cpi_score": float(cpi),
                "year": entry.get("year", self.connector_version),
                "source": ExternalSourceName.TRANSPARENCY_INTERNATIONAL.value,
            })
        return RawDataset(
            source_name=ExternalSourceName.TRANSPARENCY_INTERNATIONAL.value,
            source_version=self.connector_version,
            records=records,
            description=f"Transparency International CPI ({self.connector_version})",
        )

    def validate(self, raw: RawDataset) -> list[str]:
        errors = super().validate(raw)
        invalid = [r for r in raw.records if not r.get("country_code")]
        if invalid:
            errors.append(f"{len(invalid)} record(s) missing country_code")
        return errors
