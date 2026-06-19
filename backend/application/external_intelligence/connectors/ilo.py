"""ILO Labour Rights Connector — M34.1.

Fetches labour rights, child labour, forced labour, and workplace safety
indicators from the ILO Statistics API (ILOSTAT).

Maps to: CountryRiskProfile.labour_rights_score
"""

from __future__ import annotations

from typing import Any

import structlog

from application.external_intelligence.base_adapter import RawDataset
from domain.enums import ExternalSourceName

from .base import BaseLiveConnector

logger = structlog.get_logger(__name__)

_ILO_BASE = "https://sdmx.ilo.org/rest/data/ILO"

_ILO_DATASETS = {
    "SDG_0882_NOC_RT": "child_labour_rate",
    "SDG_T881_NOC_RT": "forced_labour_rate",
    "SDG_0971_NOC_RT": "workplace_fatal_rate",
}


class ILOConnector(BaseLiveConnector):
    """Fetches ILO labour indicators and maps them to labour_rights_score."""

    connector_name = ExternalSourceName.ILO.value
    connector_version = "2024"
    refresh_cadence_hours = 24 * 30

    async def fetch(self, client: Any) -> list[dict[str, Any]]:
        """Fetch multiple ILO indicator datasets and aggregate by country."""
        aggregated: dict[str, dict[str, Any]] = {}

        for dataset_id, metric_key in _ILO_DATASETS.items():
            url = f"{_ILO_BASE},{dataset_id}/all?format=jsondata&lastNObservations=1"
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                observations = data.get("dataSets", [{}])[0].get("observations", {})
                dimension_map = _extract_ilo_dimensions(data)
                for obs_key, obs_vals in observations.items():
                    parts = obs_key.split(":")
                    country_code = dimension_map.get(("0", parts[0]), "") if parts else ""
                    if not country_code:
                        continue
                    value = obs_vals[0] if obs_vals else None
                    if value is None:
                        continue
                    if country_code not in aggregated:
                        aggregated[country_code] = {"country_code": country_code}
                    aggregated[country_code][metric_key] = float(value)
            except Exception as exc:
                logger.warning("ilo_dataset_fetch_failed", dataset=dataset_id, error=str(exc))

        return list(aggregated.values())

    def normalize(self, raw_records: list[dict[str, Any]]) -> RawDataset:
        """Map ILO indicators to a 0–100 labour rights risk score."""
        records = []
        for entry in raw_records:
            # Weight: child labour 40%, forced labour 40%, fatal rate 20%
            child = min(entry.get("child_labour_rate", 0.0), 100.0) * 0.4
            forced = min(entry.get("forced_labour_rate", 0.0) * 10.0, 100.0) * 0.4
            fatal = min(entry.get("workplace_fatal_rate", 0.0) * 5.0, 100.0) * 0.2
            labour_rights_score = round(min(100.0, child + forced + fatal), 2)
            records.append({
                "country_code": entry["country_code"],
                "labour_rights_score": labour_rights_score,
                "child_labour_rate": entry.get("child_labour_rate", 0.0),
                "forced_labour_rate": entry.get("forced_labour_rate", 0.0),
                "workplace_fatal_rate": entry.get("workplace_fatal_rate", 0.0),
                "source": ExternalSourceName.ILO.value,
            })
        return RawDataset(
            source_name=ExternalSourceName.ILO.value,
            source_version=self.connector_version,
            records=records,
            description=f"ILO Labour Rights Indicators ({self.connector_version})",
        )


def _extract_ilo_dimensions(data: dict) -> dict[tuple[str, str], str]:
    """Extract dimension-to-value mappings from ILO SDMX JSON structure."""
    result: dict[tuple[str, str], str] = {}
    structures = data.get("structure", {}).get("dimensions", {}).get("observation", [])
    for dim_idx, dim in enumerate(structures):
        values = dim.get("values", [])
        for val_idx, val in enumerate(values):
            result[(str(dim_idx), str(val_idx))] = val.get("id", "")
    return result
