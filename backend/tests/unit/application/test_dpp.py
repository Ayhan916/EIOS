"""Unit tests — Digital Product Passport (M28 / KAN-95)

Uses MagicMock / AsyncMock — no real database or Kafka.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from application.dpp.service import DPPService
from domain.dpp import DPPFormat, DPPStatus


def _uid() -> str:
    return str(uuid4())


def _make_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    return db


def _make_kafka():
    kafka = MagicMock()
    return kafka


def _make_dpp_model(org_id: str, dpp_id: str | None = None, *, disclosed: bool = False):
    m = MagicMock()
    m.id = dpp_id or _uid()
    m.organization_id = org_id
    m.product_id = _uid()
    m.format = DPPFormat.BATTERY_REGULATION.value
    m.dpp_status = DPPStatus.DRAFT.value
    m.passport_uid = _uid()
    m.qr_payload = None
    m.product_category = "Energy Storage"
    m.battery_chemistry = "NMC"
    m.capacity_wh = 100.0
    m.nominal_voltage_v = 3.7
    m.declared_capacity_cycles = 500
    m.carbon_footprint_kg_co2e = None
    m.carbon_footprint_source = None
    m.recycled_content_pct = 15.0
    m.renewable_content_pct = None
    m.substances_of_concern_count = 0
    m.non_compliant_regulations_count = 0
    m.manufacturer_name = "ACME GmbH"
    m.manufacturer_country = "DE"
    m.manufacturing_date = date(2024, 1, 15)
    m.valid_from = date(2024, 2, 1)
    m.valid_until = None
    m.disclosed_at = datetime.now(timezone.utc) if disclosed else None
    m.evidence_id = None
    m.notes = None
    m.status = "Draft"
    m.version = 1
    m.created_at = MagicMock()
    m.updated_at = MagicMock()
    m.updated_by = None
    m.created_by = None
    return m


# ── create ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_dpp_adds_to_session():
    org_id = _uid()
    product_id = _uid()
    db = _make_db()
    kafka = _make_kafka()

    svc = DPPService(db, kafka)
    result = await svc.create(
        organization_id=org_id,
        product_id=product_id,
        format=DPPFormat.BATTERY_REGULATION,
        battery_chemistry="NMC",
        capacity_wh=100.0,
        actor_id=_uid(),
    )

    db.add.assert_called_once()
    db.flush.assert_called_once()
    assert result.organization_id == org_id
    assert result.product_id == product_id
    assert result.dpp_status == DPPStatus.DRAFT.value
    assert result.format == DPPFormat.BATTERY_REGULATION.value


@pytest.mark.asyncio
async def test_create_dpp_generates_passport_uid():
    org_id = _uid()
    db = _make_db()
    kafka = _make_kafka()

    svc = DPPService(db, kafka)
    result = await svc.create(
        organization_id=org_id,
        product_id=_uid(),
        format=DPPFormat.ESPR_GENERAL,
        actor_id=None,
    )
    assert result.passport_uid is not None
    assert len(result.passport_uid) == 36  # UUID string


@pytest.mark.asyncio
async def test_create_dpp_disclosed_at_is_none_by_default():
    db = _make_db()
    kafka = _make_kafka()
    svc = DPPService(db, kafka)
    result = await svc.create(
        organization_id=_uid(),
        product_id=_uid(),
        format=DPPFormat.TEXTILE,
    )
    assert result.disclosed_at is None


# ── get ────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_returns_model_when_org_matches():
    org_id = _uid()
    dpp_id = _uid()
    db = _make_db()
    model = _make_dpp_model(org_id, dpp_id)
    db.get = AsyncMock(return_value=model)

    svc = DPPService(db, _make_kafka())
    result = await svc.get(org_id, dpp_id)
    assert result is model


@pytest.mark.asyncio
async def test_get_returns_none_when_org_mismatch():
    org_id = _uid()
    dpp_id = _uid()
    db = _make_db()
    model = _make_dpp_model(_uid(), dpp_id)  # different org
    db.get = AsyncMock(return_value=model)

    svc = DPPService(db, _make_kafka())
    result = await svc.get(org_id, dpp_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_returns_none_when_not_found():
    db = _make_db()
    db.get = AsyncMock(return_value=None)

    svc = DPPService(db, _make_kafka())
    result = await svc.get(_uid(), _uid())
    assert result is None


# ── get_by_uid (public — no org filter) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_uid_returns_disclosed_dpp():
    model = _make_dpp_model(_uid(), disclosed=True)
    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = model
    db.execute = AsyncMock(return_value=result_mock)

    svc = DPPService(db, _make_kafka())
    result = await svc.get_by_uid("some-uid")
    assert result is model


@pytest.mark.asyncio
async def test_get_by_uid_returns_none_when_not_disclosed():
    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    svc = DPPService(db, _make_kafka())
    result = await svc.get_by_uid("nonexistent-uid")
    assert result is None


# ── update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_returns_none_when_not_found():
    db = _make_db()
    db.get = AsyncMock(return_value=None)

    svc = DPPService(db, _make_kafka())
    result = await svc.update(_uid(), _uid(), notes="test")
    assert result is None


@pytest.mark.asyncio
async def test_update_modifies_fields():
    org_id = _uid()
    dpp_id = _uid()
    model = _make_dpp_model(org_id, dpp_id)
    db = _make_db()
    db.get = AsyncMock(return_value=model)

    svc = DPPService(db, _make_kafka())
    result = await svc.update(
        org_id, dpp_id,
        notes="Updated note",
        recycled_content_pct=25.0,
        actor_id=_uid(),
    )
    assert result is not None
    assert model.notes == "Updated note"
    assert model.recycled_content_pct == 25.0
    db.flush.assert_called_once()


# ── withdraw ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_withdraw_sets_withdrawn_status():
    org_id = _uid()
    dpp_id = _uid()
    model = _make_dpp_model(org_id, dpp_id)
    db = _make_db()
    db.get = AsyncMock(return_value=model)

    svc = DPPService(db, _make_kafka())
    success = await svc.withdraw(org_id, dpp_id, actor_id=_uid())
    assert success is True
    assert model.dpp_status == DPPStatus.WITHDRAWN.value


@pytest.mark.asyncio
async def test_withdraw_returns_false_when_not_found():
    db = _make_db()
    db.get = AsyncMock(return_value=None)

    svc = DPPService(db, _make_kafka())
    result = await svc.withdraw(_uid(), _uid())
    assert result is False


# ── publish ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_publish_sets_active_and_discloses():
    org_id = _uid()
    dpp_id = _uid()
    model = _make_dpp_model(org_id, dpp_id, disclosed=False)
    model.carbon_footprint_kg_co2e = 12.5  # already set — no auto-fill needed
    db = _make_db()
    db.get = AsyncMock(return_value=model)

    execute_results = []
    for _ in range(4):
        r = MagicMock()
        r.scalar_one.return_value = 0
        r.all.return_value = []
        execute_results.append(r)
    db.execute = AsyncMock(side_effect=execute_results)

    svc = DPPService(db, _make_kafka())
    result = await svc.publish(org_id, dpp_id, actor_id=_uid())
    assert result is not None
    assert model.dpp_status == DPPStatus.ACTIVE.value
    assert model.disclosed_at is not None


@pytest.mark.asyncio
async def test_publish_returns_none_when_not_found():
    db = _make_db()
    db.get = AsyncMock(return_value=None)

    svc = DPPService(db, _make_kafka())
    result = await svc.publish(_uid(), _uid())
    assert result is None


# ── list_for_product ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_for_product_org_filter_applied():
    org_id = _uid()
    product_id = _uid()
    db = _make_db()
    model = _make_dpp_model(org_id)

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [model]
    db.execute = AsyncMock(return_value=result_mock)

    svc = DPPService(db, _make_kafka())
    items = await svc.list_for_product(org_id, product_id)
    assert len(items) == 1
    assert items[0] is model
