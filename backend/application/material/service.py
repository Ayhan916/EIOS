"""
M26 — Material Twin Service (KAN-91–97)

Business logic for the Material aggregate:
  MaterialService             — core CRUD
  MaterialCompositionService  — BOM management
  MaterialSourcingService     — supplier sourcing links
  MaterialComplianceService   — compliance flags per regulation
  MaterialSustainabilityService — LCA / sustainability KPIs

Session ownership: caller (router) commits; service only flushes.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.material import (
    ComplianceRegulation,
    ComplianceStatus,
    MaterialStatus,
    MaterialType,
    SourcingRisk,
)
from infrastructure.kafka.events import DomainEvent, MaterialEventType
from infrastructure.kafka.producer import KafkaEventProducer
from infrastructure.persistence.models.material import (
    MaterialComplianceFlagModel,
    MaterialCompositionModel,
    MaterialModel,
    MaterialSourcingModel,
    MaterialSustainabilityMetricModel,
)

logger = structlog.get_logger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _uid() -> str:
    return str(uuid4())


# ── Material Core (KAN-91) ────────────────────────────────────────────────────

class MaterialService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def create(
        self,
        organization_id: str,
        name: str,
        material_type: MaterialType,
        *,
        internal_code: str | None = None,
        cas_number: str | None = None,
        ec_number: str | None = None,
        iupac_name: str | None = None,
        molecular_formula: str | None = None,
        hs_code: str | None = None,
        un_number: str | None = None,
        ghs_hazard_class: str | None = None,
        unit_of_measure: str = "kg",
        weight_per_unit_kg: float | None = None,
        country_of_origin: str | None = None,
        is_critical_raw_material: bool = False,
        recycled_content_pct: float | None = None,
        description: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> MaterialModel:
        now = _now()
        model = MaterialModel(
            id=_uid(),
            organization_id=organization_id,
            name=name,
            material_type=material_type.value,
            material_status=MaterialStatus.ACTIVE.value,
            internal_code=internal_code,
            cas_number=cas_number,
            ec_number=ec_number,
            iupac_name=iupac_name,
            molecular_formula=molecular_formula,
            hs_code=hs_code,
            un_number=un_number,
            ghs_hazard_class=ghs_hazard_class,
            unit_of_measure=unit_of_measure,
            weight_per_unit_kg=weight_per_unit_kg,
            country_of_origin=country_of_origin,
            is_critical_raw_material=is_critical_raw_material,
            recycled_content_pct=recycled_content_pct,
            description=description,
            notes=notes,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
        )
        self._session.add(model)
        await self._session.flush()

        await self._kafka.publish_material_event(
            DomainEvent.material_created(
                organization_id=organization_id,
                material_id=model.id,
                material_type=material_type.value,
                name=name,
                actor_id=actor_id,
            )
        )
        return model

    async def list_for_org(
        self,
        organization_id: str,
        material_type: MaterialType | None = None,
        material_status: MaterialStatus | None = None,
        search: str | None = None,
        crm_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MaterialModel], int]:
        stmt = select(MaterialModel).where(
            MaterialModel.organization_id == organization_id,
        )
        if material_type is not None:
            stmt = stmt.where(MaterialModel.material_type == material_type.value)
        if material_status is not None:
            stmt = stmt.where(MaterialModel.material_status == material_status.value)
        else:
            stmt = stmt.where(MaterialModel.material_status != MaterialStatus.ARCHIVED.value)
        if crm_only:
            stmt = stmt.where(MaterialModel.is_critical_raw_material.is_(True))
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                MaterialModel.name.ilike(like)
                | MaterialModel.internal_code.ilike(like)
                | MaterialModel.cas_number.ilike(like)
                | MaterialModel.hs_code.ilike(like)
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = stmt.order_by(MaterialModel.name).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get(self, organization_id: str, material_id: str) -> MaterialModel | None:
        model = await self._session.get(MaterialModel, material_id)
        if model is None or model.organization_id != organization_id:
            return None
        return model

    async def update(
        self,
        organization_id: str,
        material_id: str,
        *,
        name: str | None = None,
        material_type: MaterialType | None = None,
        material_status: MaterialStatus | None = None,
        internal_code: str | None = None,
        cas_number: str | None = None,
        ec_number: str | None = None,
        iupac_name: str | None = None,
        hs_code: str | None = None,
        unit_of_measure: str | None = None,
        weight_per_unit_kg: float | None = None,
        country_of_origin: str | None = None,
        is_critical_raw_material: bool | None = None,
        recycled_content_pct: float | None = None,
        description: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> MaterialModel | None:
        model = await self.get(organization_id, material_id)
        if model is None:
            return None
        if name is not None:
            model.name = name
        if material_type is not None:
            model.material_type = material_type.value
        if material_status is not None:
            model.material_status = material_status.value
        if internal_code is not None:
            model.internal_code = internal_code
        if cas_number is not None:
            model.cas_number = cas_number
        if ec_number is not None:
            model.ec_number = ec_number
        if iupac_name is not None:
            model.iupac_name = iupac_name
        if hs_code is not None:
            model.hs_code = hs_code
        if unit_of_measure is not None:
            model.unit_of_measure = unit_of_measure
        if weight_per_unit_kg is not None:
            model.weight_per_unit_kg = weight_per_unit_kg
        if country_of_origin is not None:
            model.country_of_origin = country_of_origin
        if is_critical_raw_material is not None:
            model.is_critical_raw_material = is_critical_raw_material
        if recycled_content_pct is not None:
            model.recycled_content_pct = recycled_content_pct
        if description is not None:
            model.description = description
        if notes is not None:
            model.notes = notes
        model.updated_at = _now()
        model.updated_by = actor_id
        await self._session.flush()
        return model

    async def archive(self, organization_id: str, material_id: str, actor_id: str | None = None) -> bool:
        model = await self.get(organization_id, material_id)
        if model is None:
            return False
        model.material_status = MaterialStatus.ARCHIVED.value
        model.updated_at = _now()
        model.updated_by = actor_id
        await self._session.flush()
        return True


# ── Composition / BOM (KAN-92) ────────────────────────────────────────────────

class MaterialCompositionService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def add(
        self,
        organization_id: str,
        parent_material_id: str,
        child_material_id: str,
        *,
        weight_pct: float | None = None,
        quantity: float | None = None,
        unit: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> MaterialCompositionModel:
        now = _now()
        model = MaterialCompositionModel(
            id=_uid(),
            organization_id=organization_id,
            parent_material_id=parent_material_id,
            child_material_id=child_material_id,
            weight_pct=weight_pct,
            quantity=quantity,
            unit=unit,
            notes=notes,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def list_for_material(
        self, organization_id: str, parent_material_id: str
    ) -> list[MaterialCompositionModel]:
        stmt = (
            select(MaterialCompositionModel)
            .where(
                MaterialCompositionModel.organization_id == organization_id,
                MaterialCompositionModel.parent_material_id == parent_material_id,
            )
            .order_by(MaterialCompositionModel.weight_pct.desc().nullslast())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, organization_id: str, composition_id: str) -> bool:
        model = await self._session.get(MaterialCompositionModel, composition_id)
        if model is None or model.organization_id != organization_id:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True


# ── Sourcing (KAN-93) ─────────────────────────────────────────────────────────

class MaterialSourcingService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def add(
        self,
        organization_id: str,
        material_id: str,
        supplier_id: str,
        *,
        country_of_origin: str | None = None,
        annual_volume: float | None = None,
        unit: str | None = None,
        price_per_unit_eur: float | None = None,
        is_primary: bool = False,
        lead_time_days: int | None = None,
        sourcing_risk: SourcingRisk = SourcingRisk.MEDIUM,
        certification_required: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> MaterialSourcingModel:
        now = _now()
        model = MaterialSourcingModel(
            id=_uid(),
            organization_id=organization_id,
            material_id=material_id,
            supplier_id=supplier_id,
            country_of_origin=country_of_origin,
            annual_volume=annual_volume,
            unit=unit,
            price_per_unit_eur=price_per_unit_eur,
            is_primary=is_primary,
            lead_time_days=lead_time_days,
            sourcing_risk=sourcing_risk.value,
            certification_required=certification_required,
            notes=notes,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
        )
        self._session.add(model)
        await self._session.flush()

        await self._kafka.publish_material_event(
            DomainEvent.material_sourcing_added(
                organization_id=organization_id,
                material_id=material_id,
                supplier_id=supplier_id,
                country_of_origin=country_of_origin,
                actor_id=actor_id,
            )
        )
        return model

    async def list_for_material(
        self, organization_id: str, material_id: str
    ) -> list[MaterialSourcingModel]:
        stmt = (
            select(MaterialSourcingModel)
            .where(
                MaterialSourcingModel.organization_id == organization_id,
                MaterialSourcingModel.material_id == material_id,
            )
            .order_by(MaterialSourcingModel.is_primary.desc(), MaterialSourcingModel.supplier_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, organization_id: str, sourcing_id: str) -> bool:
        model = await self._session.get(MaterialSourcingModel, sourcing_id)
        if model is None or model.organization_id != organization_id:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True


# ── Compliance Flags (KAN-94) ─────────────────────────────────────────────────

class MaterialComplianceService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def upsert(
        self,
        organization_id: str,
        material_id: str,
        regulation: ComplianceRegulation,
        compliance_status: ComplianceStatus,
        *,
        custom_regulation_name: str | None = None,
        assessed_at: date | None = None,
        valid_until: date | None = None,
        assessor: str | None = None,
        evidence_id: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> MaterialComplianceFlagModel:
        # Try existing record first (upsert semantics)
        stmt = select(MaterialComplianceFlagModel).where(
            MaterialComplianceFlagModel.organization_id == organization_id,
            MaterialComplianceFlagModel.material_id == material_id,
            MaterialComplianceFlagModel.regulation == regulation.value,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        now = _now()

        if existing is None:
            model = MaterialComplianceFlagModel(
                id=_uid(),
                organization_id=organization_id,
                material_id=material_id,
                regulation=regulation.value,
                created_at=now,
                created_by=actor_id,
            )
            self._session.add(model)
        else:
            model = existing

        model.compliance_status = compliance_status.value
        model.custom_regulation_name = custom_regulation_name
        model.assessed_at = assessed_at
        model.valid_until = valid_until
        model.assessor = assessor
        model.evidence_id = evidence_id
        model.notes = notes
        model.updated_at = now
        model.updated_by = actor_id
        await self._session.flush()

        await self._kafka.publish_material_event(
            DomainEvent.material_compliance_flag_set(
                organization_id=organization_id,
                material_id=material_id,
                regulation=regulation.value,
                compliance_status=compliance_status.value,
                actor_id=actor_id,
            )
        )
        return model

    async def list_for_material(
        self, organization_id: str, material_id: str
    ) -> list[MaterialComplianceFlagModel]:
        stmt = (
            select(MaterialComplianceFlagModel)
            .where(
                MaterialComplianceFlagModel.organization_id == organization_id,
                MaterialComplianceFlagModel.material_id == material_id,
            )
            .order_by(MaterialComplianceFlagModel.regulation)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, organization_id: str, flag_id: str) -> bool:
        model = await self._session.get(MaterialComplianceFlagModel, flag_id)
        if model is None or model.organization_id != organization_id:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True


# ── Sustainability Metrics (KAN-95) ───────────────────────────────────────────

class MaterialSustainabilityService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def upsert(
        self,
        organization_id: str,
        material_id: str,
        reporting_year: int,
        *,
        carbon_footprint_kg_co2e_per_kg: float | None = None,
        carbon_scope: str = "cradle_to_gate",
        water_footprint_l_per_kg: float | None = None,
        energy_mj_per_kg: float | None = None,
        energy_renewable_pct: float | None = None,
        recycled_content_pct: float | None = None,
        recyclability_pct: float | None = None,
        biodegradable: bool | None = None,
        data_source: str | None = None,
        is_third_party_verified: bool = False,
        verification_standard: str | None = None,
        evidence_id: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> MaterialSustainabilityMetricModel:
        stmt = select(MaterialSustainabilityMetricModel).where(
            MaterialSustainabilityMetricModel.organization_id == organization_id,
            MaterialSustainabilityMetricModel.material_id == material_id,
            MaterialSustainabilityMetricModel.reporting_year == reporting_year,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        now = _now()

        if existing is None:
            model = MaterialSustainabilityMetricModel(
                id=_uid(),
                organization_id=organization_id,
                material_id=material_id,
                reporting_year=reporting_year,
                created_at=now,
                created_by=actor_id,
            )
            self._session.add(model)
        else:
            model = existing

        model.carbon_footprint_kg_co2e_per_kg = carbon_footprint_kg_co2e_per_kg
        model.carbon_scope = carbon_scope
        model.water_footprint_l_per_kg = water_footprint_l_per_kg
        model.energy_mj_per_kg = energy_mj_per_kg
        model.energy_renewable_pct = energy_renewable_pct
        model.recycled_content_pct = recycled_content_pct
        model.recyclability_pct = recyclability_pct
        model.biodegradable = biodegradable
        model.data_source = data_source
        model.is_third_party_verified = is_third_party_verified
        model.verification_standard = verification_standard
        model.evidence_id = evidence_id
        model.notes = notes
        model.updated_at = now
        model.updated_by = actor_id
        await self._session.flush()
        return model

    async def list_for_material(
        self, organization_id: str, material_id: str
    ) -> list[MaterialSustainabilityMetricModel]:
        stmt = (
            select(MaterialSustainabilityMetricModel)
            .where(
                MaterialSustainabilityMetricModel.organization_id == organization_id,
                MaterialSustainabilityMetricModel.material_id == material_id,
            )
            .order_by(MaterialSustainabilityMetricModel.reporting_year.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
