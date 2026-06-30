"""Unit tests — M8 Scope 3 Supply Chain Carbon Inventory.

Tests cover:
- PCFCalculationService: formula correctness, weight coverage, empty BOM, no LCA data
- PCFCalculationService: partial LCA coverage (some materials missing LCA)
- PCFCalculationService: list methods
- Scope3InventoryService: aggregate, upsert idempotency, zero-products case
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from application.scope3.inventory_service import Scope3InventoryService
from application.scope3.pcf_service import PCFCalculationService


def _uid() -> str:
    return str(uuid4())


def _make_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


def _scalars_result(items: list):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=items)
    result.scalars = MagicMock(return_value=scalars)
    return result


def _rows_result(rows: list):
    result = MagicMock()
    result.all = MagicMock(return_value=rows)
    return result


def _scalar_one_or_none(value):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=value)
    return result


def _make_bom_row(material_id: str, weight_pct: float):
    r = MagicMock()
    r.material_id = material_id
    r.weight_pct = weight_pct
    return r


def _make_lca_row(material_id: str, co2e: float):
    r = MagicMock()
    r.material_id = material_id
    r.carbon_footprint_kg_co2e_per_kg = co2e
    return r


def _make_name_row(id_: str, name: str):
    r = MagicMock()
    r.id = id_
    r.name = name
    return r


def _make_pcf_model(org_id: str, product_id: str, year: int, pcf: float | None, cov: float | None = None):
    m = MagicMock()
    m.organization_id = org_id
    m.product_id = product_id
    m.reporting_year = year
    m.pcf_kg_co2e_per_unit = pcf
    m.weight_coverage_pct = cov
    return m


# ── PCF formula tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pcf_correct_weighted_sum():
    """PCF = Σ (weight_pct/100) × co2e_per_kg  for each material with LCA."""
    org_id, product_id = _uid(), _uid()
    mat_a, mat_b = _uid(), _uid()

    # BOM: mat_a=60%, mat_b=40%
    # LCA: mat_a=10 kg CO2e/kg, mat_b=5 kg CO2e/kg
    # PCF = (60/100)*10 + (40/100)*5 = 6 + 2 = 8 kg CO2e/unit

    db = _make_db()
    db.execute = AsyncMock(side_effect=[
        _rows_result([_make_bom_row(mat_a, 60.0), _make_bom_row(mat_b, 40.0)]),
        _rows_result([_make_lca_row(mat_a, 10.0), _make_lca_row(mat_b, 5.0)]),
        _rows_result([_make_name_row(mat_a, "Steel"), _make_name_row(mat_b, "Plastic")]),
    ])

    svc = PCFCalculationService(db)
    record = await svc.calculate(org_id, product_id, 2024)

    assert record.pcf_kg_co2e_per_unit == pytest.approx(8.0, abs=1e-4)
    assert record.bom_materials_total == 2
    assert record.bom_materials_with_lca == 2
    assert record.weight_coverage_pct == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_pcf_partial_lca_coverage():
    """When only one material has LCA, coverage < 100% and PCF reflects partial data."""
    org_id, product_id = _uid(), _uid()
    mat_a, mat_b = _uid(), _uid()

    # BOM: mat_a=70%, mat_b=30%
    # LCA: mat_a=8 kg CO2e/kg, mat_b has no LCA
    # PCF = (70/100)*8 = 5.6, coverage = 70/100 = 70%

    db = _make_db()
    db.execute = AsyncMock(side_effect=[
        _rows_result([_make_bom_row(mat_a, 70.0), _make_bom_row(mat_b, 30.0)]),
        _rows_result([_make_lca_row(mat_a, 8.0)]),  # only mat_a has LCA
        _rows_result([_make_name_row(mat_a, "Aluminum"), _make_name_row(mat_b, "Rubber")]),
    ])

    svc = PCFCalculationService(db)
    record = await svc.calculate(org_id, product_id, 2024)

    assert record.pcf_kg_co2e_per_unit == pytest.approx(5.6, abs=1e-4)
    assert record.bom_materials_with_lca == 1
    assert record.weight_coverage_pct == pytest.approx(70.0)


@pytest.mark.asyncio
async def test_pcf_no_lca_data_returns_none():
    """When no material has LCA data, PCF is None and source is no_lca_data."""
    org_id, product_id = _uid(), _uid()
    mat_a = _uid()

    db = _make_db()
    db.execute = AsyncMock(side_effect=[
        _rows_result([_make_bom_row(mat_a, 100.0)]),
        _rows_result([]),  # no LCA rows
        _rows_result([_make_name_row(mat_a, "Unknown Material")]),
    ])

    svc = PCFCalculationService(db)
    record = await svc.calculate(org_id, product_id, 2024)

    assert record.pcf_kg_co2e_per_unit is None
    assert record.pcf_source == "no_lca_data"
    assert record.bom_materials_with_lca == 0


@pytest.mark.asyncio
async def test_pcf_empty_bom():
    """Empty BOM yields unknown PCF with zero material counts."""
    org_id, product_id = _uid(), _uid()

    db = _make_db()
    db.execute = AsyncMock(return_value=_rows_result([]))

    svc = PCFCalculationService(db)
    record = await svc.calculate(org_id, product_id, 2024)

    assert record.pcf_kg_co2e_per_unit is None
    assert record.bom_materials_total == 0
    assert record.material_breakdown == []


@pytest.mark.asyncio
async def test_pcf_persists_to_session():
    """PCFCalculationService always calls db.add + db.flush."""
    org_id, product_id = _uid(), _uid()

    db = _make_db()
    db.execute = AsyncMock(return_value=_rows_result([]))

    svc = PCFCalculationService(db)
    await svc.calculate(org_id, product_id, 2024)

    db.add.assert_called_once()
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_pcf_records_actor_and_year():
    """Calculated_by and reporting_year are set from parameters."""
    org_id, product_id, actor = _uid(), _uid(), _uid()

    db = _make_db()
    db.execute = AsyncMock(return_value=_rows_result([]))

    svc = PCFCalculationService(db)
    record = await svc.calculate(org_id, product_id, 2023, actor_id=actor)

    assert record.calculated_by == actor
    assert record.reporting_year == 2023


@pytest.mark.asyncio
async def test_pcf_material_breakdown_has_entry_per_material():
    """breakdown list has one entry per BOM material regardless of LCA."""
    org_id, product_id = _uid(), _uid()
    mat_a, mat_b = _uid(), _uid()

    db = _make_db()
    db.execute = AsyncMock(side_effect=[
        _rows_result([_make_bom_row(mat_a, 50.0), _make_bom_row(mat_b, 50.0)]),
        _rows_result([_make_lca_row(mat_a, 4.0)]),
        _rows_result([_make_name_row(mat_a, "Steel"), _make_name_row(mat_b, "Glass")]),
    ])

    svc = PCFCalculationService(db)
    record = await svc.calculate(org_id, product_id, 2024)

    assert len(record.material_breakdown) == 2
    mat_b_entry = next(e for e in record.material_breakdown if e["material_id"] == mat_b)
    assert mat_b_entry["co2e_per_kg"] is None
    assert mat_b_entry["contribution_kg_co2e"] is None


@pytest.mark.asyncio
async def test_list_for_product_returns_results():
    org_id, product_id = _uid(), _uid()
    mock_rec = MagicMock()

    db = _make_db()
    db.execute = AsyncMock(return_value=_scalars_result([mock_rec]))

    svc = PCFCalculationService(db)
    result = await svc.list_for_product(org_id, product_id)
    assert result == [mock_rec]


@pytest.mark.asyncio
async def test_list_for_org_filters_by_year():
    org_id = _uid()
    mock_rec = MagicMock()

    db = _make_db()
    db.execute = AsyncMock(return_value=_scalars_result([mock_rec]))

    svc = PCFCalculationService(db)
    result = await svc.list_for_org(org_id, reporting_year=2024)
    assert result == [mock_rec]


# ── Scope3InventoryService tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_inventory_aggregates_pcfs():
    org_id = _uid()
    p1, p2 = _uid(), _uid()

    pcf1 = _make_pcf_model(org_id, p1, 2024, pcf=10.0, cov=100.0)
    pcf2 = _make_pcf_model(org_id, p2, 2024, pcf=6.0, cov=80.0)

    db = _make_db()
    db.execute = AsyncMock(side_effect=[
        _scalars_result([pcf1, pcf2]),  # load PCFs
        _scalar_one_or_none(None),       # no existing inventory
    ])

    svc = Scope3InventoryService(db)
    inv = await svc.compute_inventory(org_id, 2024)

    assert inv.total_pcf_kg_co2e == pytest.approx(16.0)
    assert inv.total_pcf_tco2e == pytest.approx(0.016, abs=1e-5)
    assert inv.products_included == 2


@pytest.mark.asyncio
async def test_inventory_full_lca_requires_95pct_coverage():
    """Products with weight_coverage_pct >= 95 count as full LCA."""
    org_id = _uid()
    p1, p2, p3 = _uid(), _uid(), _uid()

    pcf_full = _make_pcf_model(org_id, p1, 2024, pcf=5.0, cov=100.0)
    pcf_partial = _make_pcf_model(org_id, p2, 2024, pcf=3.0, cov=70.0)
    pcf_none = _make_pcf_model(org_id, p3, 2024, pcf=None, cov=None)

    db = _make_db()
    db.execute = AsyncMock(side_effect=[
        _scalars_result([pcf_full, pcf_partial, pcf_none]),
        _scalar_one_or_none(None),
    ])

    svc = Scope3InventoryService(db)
    inv = await svc.compute_inventory(org_id, 2024)

    assert inv.products_with_full_lca == 1
    assert inv.products_with_partial_lca == 1
    assert inv.products_without_lca == 1


@pytest.mark.asyncio
async def test_inventory_upsert_overwrites_existing():
    """If an inventory for the year already exists, it is updated in-place."""
    org_id = _uid()

    existing = MagicMock()
    existing.total_pcf_kg_co2e = 5.0

    db = _make_db()
    db.execute = AsyncMock(side_effect=[
        _scalars_result([]),          # no PCFs → total 0
        _scalar_one_or_none(existing),  # existing inventory
    ])

    svc = Scope3InventoryService(db)
    inv = await svc.compute_inventory(org_id, 2024)

    assert inv is existing
    assert existing.total_pcf_kg_co2e == 0.0
    db.add.assert_not_called()
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_inventory_zero_products_returns_zero_totals():
    org_id = _uid()

    db = _make_db()
    db.execute = AsyncMock(side_effect=[
        _scalars_result([]),
        _scalar_one_or_none(None),
    ])

    svc = Scope3InventoryService(db)
    inv = await svc.compute_inventory(org_id, 2024)

    assert inv.total_pcf_kg_co2e == 0.0
    assert inv.products_included == 0
    assert inv.top_contributors == []


@pytest.mark.asyncio
async def test_inventory_top_contributors_sorted_descending():
    org_id = _uid()
    p1, p2, p3 = _uid(), _uid(), _uid()

    pcf_low = _make_pcf_model(org_id, p1, 2024, pcf=1.0, cov=100.0)
    pcf_high = _make_pcf_model(org_id, p2, 2024, pcf=9.0, cov=100.0)
    pcf_mid = _make_pcf_model(org_id, p3, 2024, pcf=4.0, cov=100.0)

    db = _make_db()
    db.execute = AsyncMock(side_effect=[
        _scalars_result([pcf_low, pcf_high, pcf_mid]),
        _scalar_one_or_none(None),
    ])

    svc = Scope3InventoryService(db)
    inv = await svc.compute_inventory(org_id, 2024)

    top = inv.top_contributors
    assert len(top) == 3
    assert top[0]["pcf_kg_co2e"] == 9.0
    assert top[1]["pcf_kg_co2e"] == 4.0
    assert top[2]["pcf_kg_co2e"] == 1.0


@pytest.mark.asyncio
async def test_list_inventories_returns_results():
    org_id = _uid()
    mock_inv = MagicMock()

    db = _make_db()
    db.execute = AsyncMock(return_value=_scalars_result([mock_inv]))

    svc = Scope3InventoryService(db)
    result = await svc.list_inventories(org_id)
    assert result == [mock_inv]


@pytest.mark.asyncio
async def test_get_inventory_returns_none_when_not_found():
    org_id = _uid()

    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_one_or_none(None))

    svc = Scope3InventoryService(db)
    result = await svc.get_inventory(org_id, 2024)
    assert result is None
