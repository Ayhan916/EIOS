"""M34 signal service tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.external_intelligence.signal_service import (
    create_signal,
    list_active_signals,
    list_signals_for_country,
    list_signals_for_supplier,
)
from domain.enums import ExternalSourceName, RiskSignalType, SignalSeverity
from domain.external_intelligence import ExternalRiskSignal


def _now():
    return datetime.now(UTC)


def _make_signal(**kwargs):
    defaults = dict(
        signal_type=RiskSignalType.SANCTIONS,
        severity=SignalSeverity.CRITICAL,
        description="OFAC SDN match",
        source_name=ExternalSourceName.OFAC,
        source_version="2025-06",
        observed_at=_now(),
        supplier_id="sup-001",
        organization_id="org-001",
        country_code="RU",
        is_active=True,
    )
    defaults.update(kwargs)
    return ExternalRiskSignal(**defaults)


def _make_signal_model(**kwargs):
    m = MagicMock()
    m.id = "sig-001"
    m.status = "Active"
    m.version = 1
    m.owner = None
    m.created_by = None
    m.updated_by = None
    m.created_at = _now()
    m.updated_at = _now()
    m.signal_type = "sanctions"
    m.severity = "critical"
    m.description = "OFAC match"
    m.source_name = "ofac"
    m.source_version = "2025-06"
    m.observed_at = _now()
    m.dataset_id = None
    m.country_code = "RU"
    m.sector_code = ""
    m.supplier_id = "sup-001"
    m.organization_id = "org-001"
    m.is_active = True
    for k, v in kwargs.items():
        setattr(m, k, v)
    return m


def _make_list_session(rows):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_create_signal_persists():
    session = AsyncMock()
    session.flush = AsyncMock()

    signal = _make_signal()
    returned = await create_signal(signal, session)
    assert returned is not None
    assert returned.signal_type == RiskSignalType.SANCTIONS
    assert returned.is_active is True
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_signal_stores_org_id():
    session = AsyncMock()
    session.flush = AsyncMock()

    signal = _make_signal(
        signal_type=RiskSignalType.CORRUPTION,
        severity=SignalSeverity.HIGH,
        description="Corruption allegation",
        source_name=ExternalSourceName.TRANSPARENCY_INTERNATIONAL,
        source_version="2025",
        organization_id="org-abc",
    )
    returned = await create_signal(signal, session)
    assert returned.organization_id == "org-abc"


@pytest.mark.asyncio
async def test_list_signals_for_supplier_tenant_scoped():
    models = [_make_signal_model(supplier_id="sup-001", organization_id="org-001")]
    session = _make_list_session(models)

    signals = await list_signals_for_supplier("sup-001", "org-001", session)
    assert len(signals) == 1
    assert signals[0].supplier_id == "sup-001"
    assert signals[0].organization_id == "org-001"


@pytest.mark.asyncio
async def test_list_signals_for_supplier_returns_empty_for_wrong_org():
    session = _make_list_session([])
    signals = await list_signals_for_supplier("sup-001", "org-other", session)
    assert len(signals) == 0


@pytest.mark.asyncio
async def test_list_signals_for_country_global():
    models = [_make_signal_model(country_code="RU", organization_id="")]
    session = _make_list_session(models)

    signals = await list_signals_for_country("RU", session)
    assert len(signals) == 1
    assert signals[0].country_code == "RU"


@pytest.mark.asyncio
async def test_list_active_signals_filters_active():
    active = _make_signal_model(is_active=True)
    session = _make_list_session([active])

    signals = await list_active_signals(session, organization_id="org-001")
    assert len(signals) == 1
    assert signals[0].is_active is True


@pytest.mark.asyncio
async def test_list_active_signals_empty_when_none():
    session = _make_list_session([])
    signals = await list_active_signals(session, organization_id="org-001")
    assert signals == []


@pytest.mark.asyncio
async def test_create_signal_defaults_is_active_true():
    session = AsyncMock()
    session.flush = AsyncMock()

    signal = _make_signal(
        signal_type=RiskSignalType.ENVIRONMENTAL,
        severity=SignalSeverity.MEDIUM,
        description="Climate risk elevated",
        source_name=ExternalSourceName.CLIMATE_VULNERABILITY,
        source_version="2025",
    )
    returned = await create_signal(signal, session)
    assert returned.is_active is True
