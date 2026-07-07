"""UN Security Council Sanctions Connector — M34.1.

Fetches the UNSC consolidated sanctions list.
Maps each sanctioned country/entity to an ExternalRiskSignal with
signal_type=sanctions and severity=critical.

Source: https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list
XML download: https://scsanctions.un.org/resources/xml/en/consolidated.xml
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog

from application.external_intelligence.base_adapter import RawDataset
from domain.enums import ExternalSourceName

from .base import BaseLiveConnector

logger = structlog.get_logger(__name__)

_UN_SANCTIONS_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"


class UNSanctionsConnector(BaseLiveConnector):
    """Fetches UN consolidated sanctions list and creates ExternalRiskSignals."""

    connector_name = ExternalSourceName.UN_SANCTIONS.value
    connector_version = "live"
    refresh_cadence_hours = 24  # daily

    async def fetch(self, client: Any) -> list[dict[str, Any]]:
        """Download UN consolidated sanctions XML and parse to records."""
        resp = await client.get(_UN_SANCTIONS_URL)
        resp.raise_for_status()
        return _parse_sanctions_xml(resp.text)

    def normalize(self, raw_records: list[dict[str, Any]]) -> RawDataset:
        """Map each sanctions entry to a signal record."""
        records = []
        today = datetime.now(UTC).date().isoformat()
        for entry in raw_records:
            records.append(
                {
                    "signal_type": "sanctions",
                    "severity": "critical",
                    "description": (
                        f"UN Security Council sanction: {entry.get('name', 'Unknown')}. "
                        f"Listed: {entry.get('listed_on', 'Unknown')}. "
                        f"Committee: {entry.get('committee', 'Unknown')}."
                    ),
                    "country_code": entry.get("country_code", ""),
                    "entity_type": entry.get("entity_type", "individual"),
                    "entity_name": entry.get("name", ""),
                    "listed_on": entry.get("listed_on", today),
                    "source": ExternalSourceName.UN_SANCTIONS.value,
                    "observed_at": today,
                }
            )
        return RawDataset(
            source_name=ExternalSourceName.UN_SANCTIONS.value,
            source_version=today,
            records=records,
            description=f"UN Security Council Consolidated Sanctions List ({today})",
        )

    async def ingest(self, session: Any, client: Any | None = None) -> tuple[Any, list[str]]:
        """Ingest sanctions list and create ExternalRiskSignals."""
        from application.external_intelligence.metrics import ext_counters

        dataset, errors = await super().ingest(session, client)

        # Additionally create ExternalRiskSignal records for each sanction
        if not errors:
            await _create_sanctions_signals(dataset, session)
            ext_counters.record_sanctions_update()

        return dataset, errors


def _parse_sanctions_xml(xml_text: str) -> list[dict[str, Any]]:
    """Parse UN sanctions XML into a list of entity dicts."""
    import xml.etree.ElementTree as ET

    records = []
    try:
        root = ET.fromstring(xml_text)

        # Fallback: handle namespace-free XML
        for individual in root.iter("INDIVIDUAL"):
            name_parts = [
                individual.findtext("FIRST_NAME", ""),
                individual.findtext("SECOND_NAME", ""),
                individual.findtext("THIRD_NAME", ""),
            ]
            name = " ".join(p for p in name_parts if p).strip()
            records.append(
                {
                    "name": name or "Unknown",
                    "entity_type": "individual",
                    "country_code": individual.findtext("NATIONALITY/VALUE", "")[:3].upper(),
                    "listed_on": individual.findtext("LISTED_ON", ""),
                    "committee": individual.findtext("UN_LIST_TYPE", ""),
                }
            )

        for entity in root.iter("ENTITY"):
            records.append(
                {
                    "name": entity.findtext(
                        "FIRST_NAME", entity.findtext("ENTITY_NAME", "Unknown")
                    ),
                    "entity_type": "entity",
                    "country_code": entity.findtext("NATIONALITY/VALUE", "")[:3].upper(),
                    "listed_on": entity.findtext("LISTED_ON", ""),
                    "committee": entity.findtext("UN_LIST_TYPE", ""),
                }
            )
    except ET.ParseError as exc:
        logger.warning("un_sanctions_xml_parse_failed", error=str(exc))
    return records


async def _create_sanctions_signals(dataset, session: Any) -> None:
    """Create ExternalRiskSignal records for each UN sanctions entry."""
    from datetime import UTC, datetime

    from application.external_intelligence.signal_service import create_signal
    from domain.enums import RiskSignalType, SignalSeverity
    from domain.external_intelligence import ExternalRiskSignal

    for record in dataset.records if hasattr(dataset, "records") else []:
        signal = ExternalRiskSignal(
            signal_type=RiskSignalType.SANCTIONS,
            severity=SignalSeverity.CRITICAL,
            description=record.get("description", "UN sanction"),
            source_name=ExternalSourceName.UN_SANCTIONS.value,
            source_version=dataset.source_version if hasattr(dataset, "source_version") else "live",
            observed_at=datetime.now(UTC),
            dataset_id=dataset.id if hasattr(dataset, "id") else "",
            country_code=record.get("country_code", ""),
            supplier_id="",
            organization_id="",
            is_active=True,
        )
        try:
            await create_signal(signal, session)
        except Exception as exc:
            logger.warning(
                "sanctions_signal_creation_failed",
                error=str(exc),
                entity=record.get("entity_name", ""),
            )
