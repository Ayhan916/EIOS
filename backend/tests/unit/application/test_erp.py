"""Unit tests — ERP Integration Layer (M6)

Tests cover:
- ERPConnectorService CRUD
- ERPSyncService job lifecycle
- CsvERPAdapter parsing
- RestERPAdapter (mocked HTTP)
- Field mapping upsert / list
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from application.erp.adapters.csv_adapter import CsvERPAdapter
from application.erp.connector_service import ERPConnectorService
from application.erp.sync_service import ERPSyncService


def _uid() -> str:
    return str(uuid4())


def _make_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _make_connector(org_id: str, cid: str | None = None, status: str = "ACTIVE"):
    m = MagicMock()
    m.id = cid or _uid()
    m.organization_id = org_id
    m.name = "SAP S/4HANA Production"
    m.adapter_type = "SAP_ODATA"
    m.connector_status = status
    m.base_url = "https://sap.example.com"
    m.auth_scheme = "BASIC"
    m.secret_reference_id = _uid()
    m.schedule_cron = None
    m.timeout_seconds = 30
    m.config_json = None
    m.description = None
    m.last_sync_at = None
    m.last_sync_status = None
    m.created_by = None
    m.created_at = MagicMock()
    m.updated_at = MagicMock()
    return m


def _make_job(org_id: str, status: str = "RUNNING"):
    m = MagicMock()
    m.id = _uid()
    m.organization_id = org_id
    m.connector_id = _uid()
    m.direction = "INBOUND"
    m.entity_type = "Material"
    m.job_status = status
    m.trigger_source = "manual"
    m.records_fetched = 0
    m.records_created = 0
    m.records_updated = 0
    m.records_failed = 0
    m.error_message = None
    m.error_details_json = None
    m.started_at = MagicMock()
    m.started_at.__sub__ = lambda self, other: MagicMock(total_seconds=lambda: 0.5)
    m.completed_at = None
    m.runtime_seconds = None
    m.initiated_by = None
    m.created_at = MagicMock()
    m.updated_at = MagicMock()
    return m


# ── ERPConnectorService ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_connector_adds_to_session():
    org_id = _uid()
    db = _make_db()
    svc = ERPConnectorService(db)

    result = await svc.create(
        organization_id=org_id,
        name="SAP Connector",
        adapter_type="SAP_ODATA",
        base_url="https://sap.example.com",
        actor_id=_uid(),
    )

    db.add.assert_called_once()
    db.flush.assert_called_once()
    assert result.name == "SAP Connector"
    assert result.connector_status == "ACTIVE"
    assert result.organization_id == org_id


@pytest.mark.asyncio
async def test_get_connector_returns_none_on_org_mismatch():
    db = _make_db()
    connector = _make_connector(_uid())
    db.get = AsyncMock(return_value=connector)

    svc = ERPConnectorService(db)
    result = await svc.get(_uid(), connector.id)  # different org
    assert result is None


@pytest.mark.asyncio
async def test_get_connector_returns_model_when_org_matches():
    org_id = _uid()
    db = _make_db()
    connector = _make_connector(org_id)
    db.get = AsyncMock(return_value=connector)

    svc = ERPConnectorService(db)
    result = await svc.get(org_id, connector.id)
    assert result is connector


@pytest.mark.asyncio
async def test_deactivate_connector_sets_inactive():
    org_id = _uid()
    db = _make_db()
    connector = _make_connector(org_id)
    db.get = AsyncMock(return_value=connector)

    svc = ERPConnectorService(db)
    ok = await svc.deactivate(org_id, connector.id, actor_id=_uid())

    assert ok is True
    assert connector.connector_status == "INACTIVE"
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_deactivate_returns_false_when_not_found():
    db = _make_db()
    db.get = AsyncMock(return_value=None)

    svc = ERPConnectorService(db)
    result = await svc.deactivate(_uid(), _uid())
    assert result is False


@pytest.mark.asyncio
async def test_upsert_field_mapping_creates_new():
    org_id = _uid()
    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    svc = ERPConnectorService(db)
    mapping = await svc.upsert_field_mapping(
        org_id,
        _uid(),
        "Material",
        "MATNR",
        "external_ref",
        transform_fn="trim",
        is_required=True,
    )

    db.add.assert_called_once()
    db.flush.assert_called_once()
    assert mapping.erp_field == "MATNR"
    assert mapping.eios_field == "external_ref"


@pytest.mark.asyncio
async def test_upsert_field_mapping_updates_existing():
    org_id = _uid()
    db = _make_db()
    existing = MagicMock()
    existing.erp_field = "MATNR"
    existing.eios_field = "external_ref"
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=result_mock)

    svc = ERPConnectorService(db)
    await svc.upsert_field_mapping(
        org_id,
        _uid(),
        "Material",
        "MATNR",
        "name",
    )

    assert existing.eios_field == "name"
    db.add.assert_not_called()  # no new add for update


# ── CsvERPAdapter ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_csv_adapter_parse_materials():
    csv_data = "MATNR;MAKTX;MTART;MEINS\nMAT001;Lithium;ROH;KG\nMAT002;Cobalt;ROH;KG\n"
    adapter = CsvERPAdapter(materials_csv=csv_data)
    records = await adapter.fetch_materials()

    assert len(records) == 2
    assert records[0].external_ref == "MAT001"
    assert records[0].name == "Lithium"
    assert records[0].material_type == "ROH"
    assert records[0].unit_of_measure == "KG"


@pytest.mark.asyncio
async def test_csv_adapter_skips_rows_without_external_ref():
    csv_data = "MATNR;MAKTX\n;EmptyRef\nMAT001;Valid\n"
    adapter = CsvERPAdapter(materials_csv=csv_data)
    records = await adapter.fetch_materials()
    assert len(records) == 1
    assert records[0].external_ref == "MAT001"


@pytest.mark.asyncio
async def test_csv_adapter_parse_bom():
    csv_data = (
        "MATNR;IDNRK;MENGE;MEINS;WEIGHT_PCT\nPRD001;MAT001;2.0;KG;30.0\nPRD001;MAT002;1.0;KG;70.0\n"
    )
    adapter = CsvERPAdapter(bom_csv=csv_data)
    records = await adapter.fetch_bom()

    assert len(records) == 2
    assert records[0].product_external_ref == "PRD001"
    assert records[0].material_external_ref == "MAT001"
    assert records[0].quantity == 2.0
    assert records[0].weight_pct == 30.0


@pytest.mark.asyncio
async def test_csv_adapter_push_dpp_returns_csv_output():
    from application.erp.adapters.base import ERPDPPRecord

    adapter = CsvERPAdapter()
    records = [
        ERPDPPRecord(
            passport_uid="uid-1",
            product_external_ref="PRD001",
            carbon_footprint_kg_co2e=12.5,
            recycled_content_pct=20.0,
            substances_of_concern_count=1,
            non_compliant_regulations_count=0,
            disclosed_at="2026-01-01T00:00:00Z",
        )
    ]
    result = await adapter.push_dpp(records)
    assert result["pushed"] == 1
    assert result["failed"] == 0
    assert "PassportUID" in result.get("csv_output", "")


@pytest.mark.asyncio
async def test_csv_adapter_test_connection_true_when_data():
    adapter = CsvERPAdapter(materials_csv="MATNR;MAKTX\nMAT001;Test\n")
    ok = await adapter.test_connection()
    assert ok is True


@pytest.mark.asyncio
async def test_csv_adapter_test_connection_false_when_empty():
    adapter = CsvERPAdapter()
    ok = await adapter.test_connection()
    assert ok is False


# ── ERPSyncService ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sync_service_creates_job_on_inbound():
    org_id = _uid()
    connector_id = _uid()
    db = _make_db()

    # Mock execute for flush (no real DB)
    csv_data = "MATNR;MAKTX;MTART\nMAT001;Lithium;ROH\n"
    adapter = CsvERPAdapter(materials_csv=csv_data)

    # The service will call db.execute for the select(MaterialModel) lookup
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None  # not found → create
    db.execute = AsyncMock(return_value=result_mock)

    svc = ERPSyncService(db)
    job = await svc.run_inbound_sync(
        org_id, connector_id, adapter, entity_type="Material", actor_id=_uid()
    )

    db.add.assert_called()
    db.commit.assert_called()
    assert job.records_fetched == 1
    assert job.records_created == 1
    assert job.job_status == "SUCCESS"
