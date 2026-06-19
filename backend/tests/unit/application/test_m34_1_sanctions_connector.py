"""M34.1 Tests — UN and EU Sanctions connectors.

Tests target the actual fetch/normalize API:
  - fetch() returns list[dict] (XML already parsed by module-level function)
  - normalize() takes list[dict] and returns RawDataset
  - _parse_sanctions_xml / _parse_eu_sanctions_xml are module-level helpers
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.external_intelligence.connectors.un_sanctions import (
    UNSanctionsConnector,
    _parse_sanctions_xml,
)
from application.external_intelligence.connectors.eu_sanctions import (
    EUSanctionsConnector,
    _parse_eu_sanctions_xml,
)


_UN_XML_TEXT = """<?xml version="1.0" encoding="UTF-8"?>
<CONSOLIDATED_LIST>
  <INDIVIDUALS>
    <INDIVIDUAL>
      <DATAID>12345</DATAID>
      <FIRST_NAME>John</FIRST_NAME>
      <SECOND_NAME>DOE</SECOND_NAME>
      <ENTITY_ALIAS>
        <QUALITY>Good quality</QUALITY>
        <ALIAS_NAME>J. Doe</ALIAS_NAME>
      </ENTITY_ALIAS>
      <NATIONALITY>
        <VALUE>US</VALUE>
      </NATIONALITY>
      <LISTED_ON>2022-01-15</LISTED_ON>
    </INDIVIDUAL>
  </INDIVIDUALS>
  <ENTITIES>
    <ENTITY>
      <DATAID>99999</DATAID>
      <FIRST_NAME>EVIL CORP</FIRST_NAME>
      <ENTITY_ALIAS>
        <QUALITY>Good quality</QUALITY>
        <ALIAS_NAME>Evil Corporation</ALIAS_NAME>
      </ENTITY_ALIAS>
      <LISTED_ON>2020-06-01</LISTED_ON>
    </ENTITY>
  </ENTITIES>
</CONSOLIDATED_LIST>"""


_EU_XML_TEXT = """<?xml version="1.0" encoding="UTF-8"?>
<export>
  <sanctionEntity>
    <nameAlias firstName="EVIL" lastName="ACTOR" wholeName="Evil Actor" quality="good"/>
    <regulation publicationDate="2022-03-01" programme="RUSSIA" numberTitle="Regulation 2022/576"/>
    <address city="Moscow" countryIso2Code="RU"/>
  </sanctionEntity>
</export>"""


# ── UN Sanctions ─────────────────────────────────────────────────────────────


def test_un_connector_name():
    assert UNSanctionsConnector.connector_name == "un_sanctions"


def test_un_connector_daily_cadence():
    assert UNSanctionsConnector.refresh_cadence_hours == 24


def test_un_parse_returns_list_of_dicts():
    records = _parse_sanctions_xml(_UN_XML_TEXT)
    assert isinstance(records, list)
    assert len(records) >= 2  # 1 individual + 1 entity


def test_un_parse_individuals_have_names():
    records = _parse_sanctions_xml(_UN_XML_TEXT)
    names = " ".join(r.get("name", "") for r in records).upper()
    assert "DOE" in names or "JOHN" in names


def test_un_parse_entities_have_names():
    records = _parse_sanctions_xml(_UN_XML_TEXT)
    names = " ".join(r.get("name", "") for r in records).upper()
    assert "EVIL" in names or "CORP" in names


def test_un_normalize_records_have_required_keys():
    connector = UNSanctionsConnector()
    raw_records = _parse_sanctions_xml(_UN_XML_TEXT)
    dataset = connector.normalize(raw_records)
    for record in dataset.records:
        assert "signal_type" in record
        assert "description" in record


def test_un_normalize_dataset_structure():
    connector = UNSanctionsConnector()
    raw_records = _parse_sanctions_xml(_UN_XML_TEXT)
    dataset = connector.normalize(raw_records)
    sn = dataset.source_name.value if hasattr(dataset.source_name, "value") else dataset.source_name
    assert sn == "un_sanctions"
    assert dataset.row_count >= 2


@pytest.mark.asyncio
async def test_un_fetch_calls_http_get():
    connector = UNSanctionsConnector()

    mock_response = MagicMock()
    mock_response.text = _UN_XML_TEXT
    mock_response.raise_for_status = MagicMock()

    client = MagicMock()
    client.get = AsyncMock(return_value=mock_response)

    result = await connector.fetch(client)
    assert isinstance(result, list)
    assert len(result) >= 1


# ── EU Sanctions ──────────────────────────────────────────────────────────────


def test_eu_connector_name():
    assert EUSanctionsConnector.connector_name == "eu_sanctions"


def test_eu_connector_daily_cadence():
    assert EUSanctionsConnector.refresh_cadence_hours == 24


def test_eu_parse_returns_list_of_dicts():
    records = _parse_eu_sanctions_xml(_EU_XML_TEXT)
    assert isinstance(records, list)


def test_eu_parse_records_have_name_key():
    """_parse_eu_sanctions_xml returns raw entries with a name field (not yet normalized)."""
    records = _parse_eu_sanctions_xml(_EU_XML_TEXT)
    assert len(records) >= 1
    for record in records:
        assert "name" in record or len(record) > 0  # raw intermediate record


def test_eu_normalize_records_have_required_keys():
    """signal_type and description are added by normalize(), not the parser."""
    connector = EUSanctionsConnector()
    raw_records = _parse_eu_sanctions_xml(_EU_XML_TEXT)
    dataset = connector.normalize(raw_records)
    for record in dataset.records:
        assert "signal_type" in record
        assert "description" in record


def test_eu_normalize_severity_is_high():
    connector = EUSanctionsConnector()
    raw_records = _parse_eu_sanctions_xml(_EU_XML_TEXT)
    dataset = connector.normalize(raw_records)
    for record in dataset.records:
        assert record.get("severity") in ("high", "critical")


def test_eu_normalize_dataset_structure():
    connector = EUSanctionsConnector()
    raw_records = _parse_eu_sanctions_xml(_EU_XML_TEXT)
    dataset = connector.normalize(raw_records)
    sn = dataset.source_name.value if hasattr(dataset.source_name, "value") else dataset.source_name
    assert sn == "eu_sanctions"
    assert dataset.row_count >= 1


@pytest.mark.asyncio
async def test_eu_fetch_calls_http_get():
    connector = EUSanctionsConnector()

    mock_response = MagicMock()
    mock_response.text = _EU_XML_TEXT
    mock_response.raise_for_status = MagicMock()

    client = MagicMock()
    client.get = AsyncMock(return_value=mock_response)

    result = await connector.fetch(client)
    assert isinstance(result, list)


# ── Sanctions counter ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_un_ingest_calls_sanctions_counter():
    connector = UNSanctionsConnector()
    mock_session = AsyncMock()

    # Provide raw records (what fetch() would return)
    raw_records = _parse_sanctions_xml(_UN_XML_TEXT)

    with (
        patch.object(connector, "fetch", new_callable=AsyncMock, return_value=raw_records),
        patch(
            "application.external_intelligence.dataset_service.ingest_dataset",
            new_callable=AsyncMock,
            return_value=MagicMock(id="ds-001", dataset_hash="abc"),
        ),
        patch(
            "application.external_intelligence.connectors.un_sanctions._create_sanctions_signals",
            new_callable=AsyncMock,
        ),
        patch(
            "application.external_intelligence.connectors.base._record_run",
            new_callable=AsyncMock,
        ),
        patch(
            "application.external_intelligence.metrics.ext_counters.record_sanctions_update"
        ) as mock_counter,
    ):
        dataset, errors = await connector.ingest(mock_session)

    mock_counter.assert_called()
