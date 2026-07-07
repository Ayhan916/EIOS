"""UNICEF Child Welfare Connector — M34.1.

Fetches child welfare, child labour, and education access indicators.
Maps to: CountryRiskProfile.human_rights_score (partial contribution).
"""

from __future__ import annotations

import contextlib
from typing import Any

import structlog

from application.external_intelligence.base_adapter import RawDataset
from domain.enums import ExternalSourceName

from .base import BaseLiveConnector

logger = structlog.get_logger(__name__)

_UNICEF_BASE = "https://sdmx.data.unicef.org/ws/public/sdmxapi/rest/data"

_UNICEF_INDICATORS = {
    "UNICEF,PT_CHLD_5-17_LBR_ECON,1.0": "child_labour_pct",
    "UNICEF,EDU_SE_AGP_CPRA_L2,1.0": "out_of_school_pct",
}


class UNICEFConnector(BaseLiveConnector):
    """Fetches UNICEF indicators and maps them to human rights risk scores."""

    connector_name = ExternalSourceName.UNICEF.value
    connector_version = "2024"
    refresh_cadence_hours = 24 * 30

    async def fetch(self, client: Any) -> list[dict[str, Any]]:
        """Fetch UNICEF child welfare indicators via SDMX API."""
        aggregated: dict[str, dict[str, Any]] = {}

        for dataflow, metric_key in _UNICEF_INDICATORS.items():
            url = f"{_UNICEF_BASE}/{dataflow}/all?format=jsondata&lastNObservations=1"
            try:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code not in (200, 206):
                    logger.warning(
                        "unicef_indicator_fetch_failed", indicator=dataflow, status=resp.status_code
                    )
                    continue
                data = resp.json()
                series = data.get("dataSets", [{}])[0].get("series", {})
                dims = data.get("structure", {}).get("dimensions", {}).get("series", [])
                # find country dimension index
                country_dim_idx = next(
                    (i for i, d in enumerate(dims) if d.get("id") in ("REF_AREA", "COUNTRY")), 0
                )
                country_values = dims[country_dim_idx].get("values", []) if dims else []
                for series_key, series_data in series.items():
                    parts = series_key.split(":")
                    if len(parts) <= country_dim_idx:
                        continue
                    country_idx = int(parts[country_dim_idx])
                    if country_idx >= len(country_values):
                        continue
                    iso3 = country_values[country_idx].get("id", "")
                    country_name = country_values[country_idx].get("name", "")
                    obs = series_data.get("observations", {})
                    if not obs:
                        continue
                    val = list(obs.values())[0][0] if obs else None
                    if val is None or not iso3:
                        continue
                    if iso3 not in aggregated:
                        aggregated[iso3] = {"country_code": iso3, "country_name": country_name}
                    with contextlib.suppress(ValueError, TypeError):
                        aggregated[iso3][metric_key] = float(val)
            except Exception as exc:
                logger.warning("unicef_indicator_fetch_failed", indicator=dataflow, error=str(exc))

        return list(aggregated.values())

    def normalize(self, raw_records: list[dict[str, Any]]) -> RawDataset:
        """Convert UNICEF indicators to human_rights_score (0–100, higher=more risk)."""
        records = []
        for entry in raw_records:
            child_labour = min(float(entry.get("child_labour_pct", 0.0)), 100.0)
            out_of_school = min(float(entry.get("out_of_school_pct", 0.0)), 100.0)
            human_rights_score = round((child_labour * 0.6 + out_of_school * 0.4), 2)
            records.append(
                {
                    "country_code": entry["country_code"],
                    "country_name": entry.get("country_name", ""),
                    "human_rights_score": human_rights_score,
                    "child_labour_pct": entry.get("child_labour_pct", 0.0),
                    "out_of_school_pct": entry.get("out_of_school_pct", 0.0),
                    "source": ExternalSourceName.UNICEF.value,
                }
            )
        return RawDataset(
            source_name=ExternalSourceName.UNICEF.value,
            source_version=self.connector_version,
            records=records,
            description=f"UNICEF Child Welfare Indicators ({self.connector_version})",
        )
