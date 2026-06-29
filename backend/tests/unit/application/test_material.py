"""Unit tests — Material Twin (M26 / KAN-91–97)

Uses MagicMock / AsyncMock — no real database or Kafka needed.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from application.material.service import (
    MaterialComplianceService,
    MaterialCompositionService,
    MaterialService,
    MaterialSourcingService,
    MaterialSustainabilityService,
)
from domain.material import (
    ComplianceRegulation,
    ComplianceStatus,
    MaterialStatus,
    MaterialType,
    SourcingRisk,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

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
    kafka.publish_material_event = AsyncMock()
    return kafka


def _make_material_model(org_id: str, material_id: str | None = None):
    m = MagicMock()
    m.id = material_id or _uid()
    m.organization_id = org_id
    m.name = "Lithium"
    m.material_type = MaterialType.RAW_MATERIAL.value
    m.material_status = MaterialStatus.ACTIVE.value
    m.internal_code = "LI-001"
    m.cas_number = "7439-93-2"
    m.ec_number = None
    m.iupac_name = None
    m.molecular_formula = "Li"
    m.hs_code = "2805.19"
    m.un_number = "UN1415"
    m.ghs_hazard_class = "Flammable solids"
    m.unit_of_measure = "kg"
    m.weight_per_unit_kg = None
    m.country_of_origin = "CL"
    m.is_critical_raw_material = True
    m.recycled_content_pct = None
    m.description = "Battery-grade lithium"
    m.notes = None
    m.status = "Draft"
    m.version = 1
    m.created_at = MagicMock()
    m.updated_at = MagicMock()
    return m


# ── MaterialService ───────────────────────────────────────────────────────────

class TestMaterialService:
    @pytest.mark.asyncio
    async def test_create_material(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        with patch(
            "application.material.service.MaterialModel",
            return_value=_make_material_model(org_id),
        ):
            svc = MaterialService(db, kafka)
            result = await svc.create(
                organization_id=org_id,
                name="Lithium",
                material_type=MaterialType.RAW_MATERIAL,
                cas_number="7439-93-2",
                is_critical_raw_material=True,
                actor_id=_uid(),
            )

        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        kafka.publish_material_event.assert_awaited_once()
        assert result.organization_id == org_id

    @pytest.mark.asyncio
    async def test_get_material_returns_none_wrong_org(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        model = _make_material_model(org_id)
        db.get.return_value = model

        svc = MaterialService(db, kafka)
        result = await svc.get("other-org", model.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_material_correct_org(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        model = _make_material_model(org_id)
        db.get.return_value = model

        svc = MaterialService(db, kafka)
        result = await svc.get(org_id, model.id)
        assert result is model

    @pytest.mark.asyncio
    async def test_archive_material(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        model = _make_material_model(org_id)
        db.get.return_value = model

        svc = MaterialService(db, kafka)
        deleted = await svc.archive(org_id, model.id, actor_id=_uid())

        assert deleted is True
        assert model.material_status == MaterialStatus.ARCHIVED.value
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_archive_material_not_found(self):
        db = _make_db()
        kafka = _make_kafka()
        db.get.return_value = None

        svc = MaterialService(db, kafka)
        result = await svc.archive("org", "nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_materials(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        model = _make_material_model(org_id)

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [model]
        db.execute = AsyncMock(side_effect=[count_result, list_result])

        svc = MaterialService(db, kafka)
        items, total = await svc.list_for_org(org_id)

        assert total == 1
        assert len(items) == 1


# ── MaterialCompositionService ────────────────────────────────────────────────

class TestMaterialCompositionService:
    @pytest.mark.asyncio
    async def test_add_composition(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        comp_model = MagicMock()
        comp_model.organization_id = org_id
        comp_model.parent_material_id = _uid()
        comp_model.child_material_id = _uid()
        comp_model.weight_pct = 40.0

        with patch(
            "application.material.service.MaterialCompositionModel",
            return_value=comp_model,
        ):
            svc = MaterialCompositionService(db, kafka)
            result = await svc.add(
                organization_id=org_id,
                parent_material_id=comp_model.parent_material_id,
                child_material_id=comp_model.child_material_id,
                weight_pct=40.0,
            )

        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        assert result.weight_pct == 40.0

    @pytest.mark.asyncio
    async def test_delete_composition_not_found(self):
        db = _make_db()
        kafka = _make_kafka()
        db.get.return_value = None

        svc = MaterialCompositionService(db, kafka)
        result = await svc.delete("org", "missing-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_composition_wrong_org(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        model = MagicMock()
        model.organization_id = org_id
        db.get.return_value = model

        svc = MaterialCompositionService(db, kafka)
        result = await svc.delete("wrong-org", model.id)
        assert result is False


# ── MaterialSourcingService ───────────────────────────────────────────────────

class TestMaterialSourcingService:
    @pytest.mark.asyncio
    async def test_add_sourcing_publishes_kafka(self):
        org_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        sourcing_model = MagicMock()
        sourcing_model.organization_id = org_id
        sourcing_model.material_id = _uid()
        sourcing_model.supplier_id = _uid()
        sourcing_model.country_of_origin = "CL"

        with patch(
            "application.material.service.MaterialSourcingModel",
            return_value=sourcing_model,
        ):
            svc = MaterialSourcingService(db, kafka)
            result = await svc.add(
                organization_id=org_id,
                material_id=sourcing_model.material_id,
                supplier_id=sourcing_model.supplier_id,
                country_of_origin="CL",
                sourcing_risk=SourcingRisk.HIGH,
            )

        kafka.publish_material_event.assert_awaited_once()
        assert result.country_of_origin == "CL"


# ── MaterialComplianceService ─────────────────────────────────────────────────

class TestMaterialComplianceService:
    @pytest.mark.asyncio
    async def test_upsert_creates_new_flag(self):
        org_id = _uid()
        material_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=exec_result)

        svc = MaterialComplianceService(db, kafka)
        result = await svc.upsert(
            organization_id=org_id,
            material_id=material_id,
            regulation=ComplianceRegulation.REACH_SVHC,
            compliance_status=ComplianceStatus.COMPLIANT,
            assessor="Jane Smith",
        )

        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        kafka.publish_material_event.assert_awaited_once()
        assert result.regulation == ComplianceRegulation.REACH_SVHC.value
        assert result.compliance_status == ComplianceStatus.COMPLIANT.value

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_flag(self):
        org_id = _uid()
        material_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        existing = MagicMock()
        existing.organization_id = org_id
        existing.material_id = material_id
        existing.regulation = ComplianceRegulation.ROHS.value

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = existing
        db.execute = AsyncMock(return_value=exec_result)

        svc = MaterialComplianceService(db, kafka)
        result = await svc.upsert(
            organization_id=org_id,
            material_id=material_id,
            regulation=ComplianceRegulation.ROHS,
            compliance_status=ComplianceStatus.NON_COMPLIANT,
        )

        db.add.assert_not_called()
        assert result.compliance_status == ComplianceStatus.NON_COMPLIANT.value


# ── MaterialSustainabilityService ─────────────────────────────────────────────

class TestMaterialSustainabilityService:
    @pytest.mark.asyncio
    async def test_upsert_sustainability_creates(self):
        org_id = _uid()
        material_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=exec_result)

        svc = MaterialSustainabilityService(db, kafka)
        result = await svc.upsert(
            organization_id=org_id,
            material_id=material_id,
            reporting_year=2025,
            carbon_footprint_kg_co2e_per_kg=2.5,
            is_third_party_verified=True,
        )

        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        assert result.reporting_year == 2025
        assert result.carbon_footprint_kg_co2e_per_kg == 2.5

    @pytest.mark.asyncio
    async def test_upsert_sustainability_updates_existing(self):
        org_id = _uid()
        material_id = _uid()
        db = _make_db()
        kafka = _make_kafka()

        existing = MagicMock()
        existing.organization_id = org_id
        existing.reporting_year = 2024
        exec_result = MagicMock()
        exec_result.scalar_one_or_none.return_value = existing
        db.execute = AsyncMock(return_value=exec_result)

        svc = MaterialSustainabilityService(db, kafka)
        result = await svc.upsert(
            organization_id=org_id,
            material_id=material_id,
            reporting_year=2024,
            carbon_footprint_kg_co2e_per_kg=3.1,
        )

        db.add.assert_not_called()
        assert result.carbon_footprint_kg_co2e_per_kg == 3.1
