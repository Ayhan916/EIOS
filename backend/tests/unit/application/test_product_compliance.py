"""Unit tests — M7 Supply Chain Compliance Extensions.

Tests cover:
- ProductComplianceScanService: scan logic for COMPLIANT / NON_COMPLIANT / PARTIAL / UNKNOWN
- ProductComplianceScanService: list scans, list non-compliant
- SupplyChainComplianceSummaryService: summary aggregation
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from application.compliance.product_scan import ProductComplianceScanService
from application.compliance.supply_chain_summary import SupplyChainComplianceSummaryService


def _uid() -> str:
    return str(uuid4())


def _make_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


def _make_bom_items(org_id: str, product_id: str, material_ids: list[str]):
    items = []
    for mid in material_ids:
        m = MagicMock()
        m.organization_id = org_id
        m.product_id = product_id
        m.material_id = mid
        m.is_substance_of_concern = False
        items.append(m)
    return items


def _make_flag(org_id: str, material_id: str, regulation: str, status: str):
    m = MagicMock()
    m.organization_id = org_id
    m.material_id = material_id
    m.regulation = regulation
    m.compliance_status = status
    return m


def _scalars_result(items: list):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=items)
    result.scalars = MagicMock(return_value=scalars)
    return result


def _scalar_one(value):
    result = MagicMock()
    result.scalar_one = MagicMock(return_value=value)
    return result


# ── scan_result logic ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scan_result_compliant_when_all_materials_compliant():
    org_id = _uid()
    product_id = _uid()
    mat_ids = [_uid(), _uid()]

    db = _make_db()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result(_make_bom_items(org_id, product_id, mat_ids)),
            _scalars_result(
                [
                    _make_flag(org_id, mat_ids[0], "REACH", "COMPLIANT"),
                    _make_flag(org_id, mat_ids[1], "REACH", "COMPLIANT"),
                ]
            ),
        ]
    )

    svc = ProductComplianceScanService(db)
    scan = await svc.scan_product_bom(org_id, product_id, "REACH")

    assert scan.scan_result == "COMPLIANT"
    assert scan.compliant_count == 2
    assert scan.non_compliant_count == 0
    assert scan.unknown_count == 0
    assert scan.flagged_material_ids == []


@pytest.mark.asyncio
async def test_scan_result_non_compliant_when_any_material_non_compliant():
    org_id = _uid()
    product_id = _uid()
    mat_ids = [_uid(), _uid()]

    db = _make_db()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result(_make_bom_items(org_id, product_id, mat_ids)),
            _scalars_result(
                [
                    _make_flag(org_id, mat_ids[0], "REACH", "COMPLIANT"),
                    _make_flag(org_id, mat_ids[1], "REACH", "NON_COMPLIANT"),
                ]
            ),
        ]
    )

    svc = ProductComplianceScanService(db)
    scan = await svc.scan_product_bom(org_id, product_id, "REACH")

    assert scan.scan_result == "NON_COMPLIANT"
    assert scan.non_compliant_count == 1
    assert mat_ids[1] in scan.flagged_material_ids


@pytest.mark.asyncio
async def test_scan_result_partial_when_mix_of_compliant_and_unknown():
    org_id = _uid()
    product_id = _uid()
    mat_ids = [_uid(), _uid()]

    db = _make_db()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result(_make_bom_items(org_id, product_id, mat_ids)),
            _scalars_result(
                [
                    _make_flag(org_id, mat_ids[0], "REACH", "COMPLIANT"),
                    # mat_ids[1] has no flag → unknown
                ]
            ),
        ]
    )

    svc = ProductComplianceScanService(db)
    scan = await svc.scan_product_bom(org_id, product_id, "REACH")

    assert scan.scan_result == "PARTIAL"
    assert scan.compliant_count == 1
    assert scan.unknown_count == 1


@pytest.mark.asyncio
async def test_scan_result_unknown_when_no_flags_exist():
    org_id = _uid()
    product_id = _uid()
    mat_ids = [_uid()]

    db = _make_db()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result(_make_bom_items(org_id, product_id, mat_ids)),
            _scalars_result([]),  # no flags at all
        ]
    )

    svc = ProductComplianceScanService(db)
    scan = await svc.scan_product_bom(org_id, product_id, "REACH")

    assert scan.scan_result == "UNKNOWN"
    assert scan.unknown_count == 1


@pytest.mark.asyncio
async def test_scan_result_unknown_when_empty_bom():
    org_id = _uid()
    product_id = _uid()

    db = _make_db()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([]),  # no BOM items
        ]
    )

    svc = ProductComplianceScanService(db)
    scan = await svc.scan_product_bom(org_id, product_id, "REACH")

    assert scan.scan_result == "UNKNOWN"
    assert scan.total_materials == 0


@pytest.mark.asyncio
async def test_scan_writes_to_session_and_flushes():
    org_id = _uid()
    product_id = _uid()

    db = _make_db()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([]),  # empty BOM
        ]
    )

    svc = ProductComplianceScanService(db)
    await svc.scan_product_bom(org_id, product_id, "EU_BATTERY")

    db.add.assert_called_once()
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_scan_records_actor_id():
    org_id = _uid()
    product_id = _uid()
    actor_id = _uid()

    db = _make_db()
    db.execute = AsyncMock(
        side_effect=[
            _scalars_result([]),
        ]
    )

    svc = ProductComplianceScanService(db)
    scan = await svc.scan_product_bom(org_id, product_id, "REACH", actor_id=actor_id)

    assert scan.scanned_by == actor_id


@pytest.mark.asyncio
async def test_list_scans_for_product_returns_results():
    org_id = _uid()
    product_id = _uid()
    scan_mock = MagicMock()

    db = _make_db()
    db.execute = AsyncMock(return_value=_scalars_result([scan_mock]))

    svc = ProductComplianceScanService(db)
    result = await svc.list_scans_for_product(org_id, product_id)

    assert result == [scan_mock]


@pytest.mark.asyncio
async def test_list_non_compliant_products_returns_results():
    org_id = _uid()
    scan_mock = MagicMock()

    db = _make_db()
    db.execute = AsyncMock(return_value=_scalars_result([scan_mock]))

    svc = ProductComplianceScanService(db)
    result = await svc.list_non_compliant_products(org_id)

    assert result == [scan_mock]


# ── SupplyChainComplianceSummaryService ────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_returns_expected_structure():
    org_id = _uid()
    db = _make_db()

    reg_row = MagicMock()
    reg_row.regulation = "REACH"
    reg_row.count = 3

    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        if call_count <= 7:
            return _scalar_one(call_count * 10)
        result = MagicMock()
        result.all = MagicMock(return_value=[reg_row])
        return result

    db.execute = mock_execute

    svc = SupplyChainComplianceSummaryService(db)
    summary = await svc.compute_summary(org_id)

    assert summary["organization_id"] == org_id
    assert "materials" in summary
    assert "products" in summary
    assert "digital_product_passports" in summary
    assert "top_at_risk_regulations" in summary
    assert isinstance(summary["top_at_risk_regulations"], list)


@pytest.mark.asyncio
async def test_summary_top_regulations_contains_regulation_code():
    org_id = _uid()
    db = _make_db()

    reg_row = MagicMock()
    reg_row.regulation = "EU_BATTERY"
    reg_row.count = 5

    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        if call_count <= 7:
            return _scalar_one(0)
        result = MagicMock()
        result.all = MagicMock(return_value=[reg_row])
        return result

    db.execute = mock_execute

    svc = SupplyChainComplianceSummaryService(db)
    summary = await svc.compute_summary(org_id)

    regs = summary["top_at_risk_regulations"]
    assert len(regs) == 1
    assert regs[0]["regulation_code"] == "EU_BATTERY"
    assert regs[0]["non_compliant_materials"] == 5


@pytest.mark.asyncio
async def test_summary_handles_zero_counts_gracefully():
    org_id = _uid()
    db = _make_db()

    async def mock_execute(stmt):
        result = MagicMock()
        result.scalar_one = MagicMock(return_value=0)
        result.all = MagicMock(return_value=[])
        return result

    db.execute = mock_execute

    svc = SupplyChainComplianceSummaryService(db)
    summary = await svc.compute_summary(org_id)

    assert summary["materials"]["total_active"] == 0
    assert summary["materials"]["non_compliant"] == 0
    assert summary["products"]["total_active"] == 0
    assert summary["digital_product_passports"]["total"] == 0
    assert summary["top_at_risk_regulations"] == []
