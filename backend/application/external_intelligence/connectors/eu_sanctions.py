"""EU Sanctions Connector — M34.1.

Fetches the EU consolidated sanctions list (CFSP).
Maps each sanctioned entry to an ExternalRiskSignal with signal_type=sanctions.

Source: EU Financial Sanctions Files (FSF)
https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog

from application.external_intelligence.base_adapter import RawDataset
from domain.enums import ExternalSourceName

from .base import BaseLiveConnector

logger = structlog.get_logger(__name__)

_EU_SANCTIONS_URL = (
    "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content"
)


class EUSanctionsConnector(BaseLiveConnector):
    """Fetches EU financial sanctions list and creates ExternalRiskSignals."""

    connector_name = ExternalSourceName.EU_SANCTIONS.value
    connector_version = "live"
    refresh_cadence_hours = 24  # daily

    async def fetch(self, client: Any) -> list[dict[str, Any]]:
        """Download EU sanctions XML and parse to records."""
        resp = await client.get(_EU_SANCTIONS_URL)
        resp.raise_for_status()
        return _parse_eu_sanctions_xml(resp.text)

    def normalize(self, raw_records: list[dict[str, Any]]) -> RawDataset:
        """Map each EU sanction to a signal record."""
        today = datetime.now(UTC).date().isoformat()
        records = []
        for entry in raw_records:
            records.append({
                "signal_type": "sanctions",
                "severity": "high",
                "description": (
                    f"EU sanctions designation: {entry.get('name', 'Unknown')}. "
                    f"Regulation: {entry.get('regulation', 'Unknown')}."
                ),
                "country_code": entry.get("country_code", ""),
                "entity_name": entry.get("name", ""),
                "entity_type": entry.get("entity_type", "individual"),
                "regulation": entry.get("regulation", ""),
                "source": ExternalSourceName.EU_SANCTIONS.value,
                "observed_at": today,
            })
        return RawDataset(
            source_name=ExternalSourceName.EU_SANCTIONS.value,
            source_version=today,
            records=records,
            description=f"EU Consolidated Financial Sanctions List ({today})",
        )

    async def ingest(self, session: Any, client: Any | None = None) -> tuple[Any, list[str]]:
        """Ingest EU sanctions and create ExternalRiskSignal records."""
        from application.external_intelligence.metrics import ext_counters

        dataset, errors = await super().ingest(session, client)

        if not errors:
            await _create_eu_signals(dataset, session)
            ext_counters.record_sanctions_update()

        return dataset, errors


def _parse_eu_sanctions_xml(xml_text: str) -> list[dict[str, Any]]:
    """Parse EU Financial Sanctions XML."""
    import xml.etree.ElementTree as ET
    records = []
    try:
        root = ET.fromstring(xml_text)
        for subject in root.iter("sanctionEntity"):
            name_node = subject.find(".//nameAlias")
            name = name_node.get("wholeName", "Unknown") if name_node is not None else "Unknown"
            country = ""
            addr = subject.find(".//address")
            if addr is not None:
                country = addr.get("countryIso2Code", "")
            regulation = ""
            reg_node = subject.find(".//regulation")
            if reg_node is not None:
                regulation = reg_node.get("numberTitle", "")
            records.append({
                "name": name,
                "entity_type": subject.get("subjectType", "individual").lower(),
                "country_code": country,
                "regulation": regulation,
            })
    except ET.ParseError as exc:
        logger.warning("eu_sanctions_xml_parse_failed", error=str(exc))
    return records


async def _create_eu_signals(dataset, session: Any) -> None:
    """Create ExternalRiskSignal records for EU sanctions entries."""
    from domain.enums import RiskSignalType, SignalSeverity
    from domain.external_intelligence import ExternalRiskSignal
    from application.external_intelligence.signal_service import create_signal

    source_version = dataset.source_version if hasattr(dataset, "source_version") else "live"
    dataset_id = dataset.id if hasattr(dataset, "id") else ""

    for record in (dataset.records if hasattr(dataset, "records") else []):
        signal = ExternalRiskSignal(
            signal_type=RiskSignalType.SANCTIONS,
            severity=SignalSeverity.HIGH,
            description=record.get("description", "EU sanction"),
            source_name=ExternalSourceName.EU_SANCTIONS.value,
            source_version=source_version,
            observed_at=datetime.now(UTC),
            dataset_id=dataset_id,
            country_code=record.get("country_code", ""),
            supplier_id="",
            organization_id="",
            is_active=True,
        )
        try:
            await create_signal(signal, session)
        except Exception:
            pass
