"""
M28 — Digital Product Passport Service (KAN-93)

DPPService — CRUD + computed snapshot that pulls live data from the
Product Twin and Material Twin layers.

Session ownership: caller (router) commits; service only flushes.
organization_id is a MANDATORY filter on every DB query.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.dpp import DPPFormat, DPPStatus
from infrastructure.kafka.producer import KafkaEventProducer
from infrastructure.persistence.models.dpp import DigitalProductPassportModel
from infrastructure.persistence.models.material import (
    MaterialComplianceFlagModel,
    MaterialSustainabilityMetricModel,
)
from infrastructure.persistence.models.product import ProductBOMItemModel

logger = structlog.get_logger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _uid() -> str:
    return str(uuid4())


class DPPService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create(
        self,
        organization_id: str,
        product_id: str,
        format: DPPFormat,
        *,
        product_category: str | None = None,
        battery_chemistry: str | None = None,
        capacity_wh: float | None = None,
        nominal_voltage_v: float | None = None,
        declared_capacity_cycles: int | None = None,
        carbon_footprint_kg_co2e: float | None = None,
        carbon_footprint_source: str | None = None,
        recycled_content_pct: float | None = None,
        renewable_content_pct: float | None = None,
        manufacturer_name: str | None = None,
        manufacturer_country: str | None = None,
        manufacturing_date: date | None = None,
        valid_from: date | None = None,
        valid_until: date | None = None,
        evidence_id: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> DigitalProductPassportModel:
        passport_uid = _uid()
        now = _now()
        model = DigitalProductPassportModel(
            id=_uid(),
            organization_id=organization_id,
            product_id=product_id,
            format=format.value,
            dpp_status=DPPStatus.DRAFT.value,
            passport_uid=passport_uid,
            qr_payload=None,
            product_category=product_category,
            battery_chemistry=battery_chemistry,
            capacity_wh=capacity_wh,
            nominal_voltage_v=nominal_voltage_v,
            declared_capacity_cycles=declared_capacity_cycles,
            carbon_footprint_kg_co2e=carbon_footprint_kg_co2e,
            carbon_footprint_source=carbon_footprint_source or "declared",
            recycled_content_pct=recycled_content_pct,
            renewable_content_pct=renewable_content_pct,
            substances_of_concern_count=0,
            non_compliant_regulations_count=0,
            manufacturer_name=manufacturer_name,
            manufacturer_country=manufacturer_country,
            manufacturing_date=manufacturing_date,
            valid_from=valid_from,
            valid_until=valid_until,
            disclosed_at=None,
            evidence_id=evidence_id,
            notes=notes,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
        )
        self._session.add(model)
        await self._session.flush()
        return model

    async def get(self, organization_id: str, dpp_id: str) -> DigitalProductPassportModel | None:
        model = await self._session.get(DigitalProductPassportModel, dpp_id)
        if model is None or model.organization_id != organization_id:
            return None
        return model

    async def get_by_uid(self, passport_uid: str) -> DigitalProductPassportModel | None:
        """Public lookup by stable passport UID (no org filter — public endpoint)."""
        stmt = select(DigitalProductPassportModel).where(
            DigitalProductPassportModel.passport_uid == passport_uid,
            DigitalProductPassportModel.disclosed_at.isnot(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_org(
        self,
        organization_id: str,
        dpp_status: DPPStatus | None = None,
        format: DPPFormat | None = None,
        product_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DigitalProductPassportModel], int]:
        stmt = select(DigitalProductPassportModel).where(
            DigitalProductPassportModel.organization_id == organization_id,
        )
        if dpp_status is not None:
            stmt = stmt.where(DigitalProductPassportModel.dpp_status == dpp_status.value)
        else:
            stmt = stmt.where(DigitalProductPassportModel.dpp_status != DPPStatus.WITHDRAWN.value)
        if format is not None:
            stmt = stmt.where(DigitalProductPassportModel.format == format.value)
        if product_id is not None:
            stmt = stmt.where(DigitalProductPassportModel.product_id == product_id)

        count_result = await self._session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar_one()

        stmt = (
            stmt.order_by(DigitalProductPassportModel.created_at.desc()).offset(offset).limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_for_product(
        self, organization_id: str, product_id: str
    ) -> list[DigitalProductPassportModel]:
        stmt = (
            select(DigitalProductPassportModel)
            .where(
                DigitalProductPassportModel.organization_id == organization_id,
                DigitalProductPassportModel.product_id == product_id,
            )
            .order_by(DigitalProductPassportModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        organization_id: str,
        dpp_id: str,
        *,
        dpp_status: DPPStatus | None = None,
        product_category: str | None = None,
        battery_chemistry: str | None = None,
        capacity_wh: float | None = None,
        nominal_voltage_v: float | None = None,
        declared_capacity_cycles: int | None = None,
        carbon_footprint_kg_co2e: float | None = None,
        carbon_footprint_source: str | None = None,
        recycled_content_pct: float | None = None,
        renewable_content_pct: float | None = None,
        manufacturer_name: str | None = None,
        manufacturer_country: str | None = None,
        manufacturing_date: date | None = None,
        valid_from: date | None = None,
        valid_until: date | None = None,
        evidence_id: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> DigitalProductPassportModel | None:
        model = await self.get(organization_id, dpp_id)
        if model is None:
            return None
        if dpp_status is not None:
            model.dpp_status = dpp_status.value
        if product_category is not None:
            model.product_category = product_category
        if battery_chemistry is not None:
            model.battery_chemistry = battery_chemistry
        if capacity_wh is not None:
            model.capacity_wh = capacity_wh
        if nominal_voltage_v is not None:
            model.nominal_voltage_v = nominal_voltage_v
        if declared_capacity_cycles is not None:
            model.declared_capacity_cycles = declared_capacity_cycles
        if carbon_footprint_kg_co2e is not None:
            model.carbon_footprint_kg_co2e = carbon_footprint_kg_co2e
        if carbon_footprint_source is not None:
            model.carbon_footprint_source = carbon_footprint_source
        if recycled_content_pct is not None:
            model.recycled_content_pct = recycled_content_pct
        if renewable_content_pct is not None:
            model.renewable_content_pct = renewable_content_pct
        if manufacturer_name is not None:
            model.manufacturer_name = manufacturer_name
        if manufacturer_country is not None:
            model.manufacturer_country = manufacturer_country
        if manufacturing_date is not None:
            model.manufacturing_date = manufacturing_date
        if valid_from is not None:
            model.valid_from = valid_from
        if valid_until is not None:
            model.valid_until = valid_until
        if evidence_id is not None:
            model.evidence_id = evidence_id
        if notes is not None:
            model.notes = notes
        model.updated_at = _now()
        model.updated_by = actor_id
        await self._session.flush()
        return model

    async def withdraw(
        self, organization_id: str, dpp_id: str, actor_id: str | None = None
    ) -> bool:
        model = await self.get(organization_id, dpp_id)
        if model is None:
            return False
        model.dpp_status = DPPStatus.WITHDRAWN.value
        model.updated_at = _now()
        model.updated_by = actor_id
        await self._session.flush()
        return True

    # ── Snapshot — pull live data from Product + Material Twins ───────────────

    async def refresh_snapshot(
        self, organization_id: str, dpp_id: str, actor_id: str | None = None
    ) -> DigitalProductPassportModel | None:
        """Recompute substances_of_concern_count and non_compliant_regulations_count
        from the live BOM / compliance data and optionally auto-fill PCF."""
        model = await self.get(organization_id, dpp_id)
        if model is None:
            return None

        product_id = model.product_id

        # 1. Substances of concern from BOM
        concern_stmt = select(func.count()).where(
            ProductBOMItemModel.organization_id == organization_id,
            ProductBOMItemModel.product_id == product_id,
            ProductBOMItemModel.is_substance_of_concern.is_(True),
        )
        concern_result = await self._session.execute(concern_stmt)
        substances_count = concern_result.scalar_one()

        # 2. Non-compliant regulations across all BOM materials
        bom_stmt = select(ProductBOMItemModel.material_id).where(
            ProductBOMItemModel.organization_id == organization_id,
            ProductBOMItemModel.product_id == product_id,
        )
        bom_result = await self._session.execute(bom_stmt)
        material_ids = [row[0] for row in bom_result.all()]

        non_compliant_count = 0
        if material_ids:
            nc_stmt = select(func.count(MaterialComplianceFlagModel.regulation.distinct())).where(
                MaterialComplianceFlagModel.organization_id == organization_id,
                MaterialComplianceFlagModel.material_id.in_(material_ids),
                MaterialComplianceFlagModel.compliance_status == "NON_COMPLIANT",
            )
            nc_result = await self._session.execute(nc_stmt)
            non_compliant_count = nc_result.scalar_one()

        # 3. Auto-fill PCF if not declared and LCA data exists
        if model.carbon_footprint_kg_co2e is None and material_ids:
            await self._auto_fill_pcf(model, organization_id, product_id, material_ids)

        model.substances_of_concern_count = substances_count
        model.non_compliant_regulations_count = non_compliant_count
        model.updated_at = _now()
        model.updated_by = actor_id
        await self._session.flush()
        return model

    async def _auto_fill_pcf(
        self,
        model: DigitalProductPassportModel,
        organization_id: str,
        product_id: str,
        material_ids: list[str],
    ) -> None:
        """Compute weighted PCF from BOM × material LCA. Updates model in place."""
        bom_stmt = select(ProductBOMItemModel.material_id, ProductBOMItemModel.weight_pct).where(
            ProductBOMItemModel.organization_id == organization_id,
            ProductBOMItemModel.product_id == product_id,
            ProductBOMItemModel.weight_pct.isnot(None),
        )
        bom_result = await self._session.execute(bom_stmt)
        bom_rows = {row[0]: row[1] for row in bom_result.all()}  # {material_id: weight_pct}

        if not bom_rows:
            return

        # Latest LCA per material
        subq = (
            select(
                MaterialSustainabilityMetricModel.material_id,
                func.max(MaterialSustainabilityMetricModel.reporting_year).label("max_year"),
            )
            .where(
                MaterialSustainabilityMetricModel.organization_id == organization_id,
                MaterialSustainabilityMetricModel.material_id.in_(list(bom_rows.keys())),
            )
            .group_by(MaterialSustainabilityMetricModel.material_id)
            .subquery()
        )
        lca_stmt = (
            select(
                MaterialSustainabilityMetricModel.material_id,
                MaterialSustainabilityMetricModel.carbon_footprint_kg_co2e_per_kg,
            )
            .join(
                subq,
                (MaterialSustainabilityMetricModel.material_id == subq.c.material_id)
                & (MaterialSustainabilityMetricModel.reporting_year == subq.c.max_year),
            )
            .where(MaterialSustainabilityMetricModel.carbon_footprint_kg_co2e_per_kg.isnot(None))
        )
        lca_result = await self._session.execute(lca_stmt)
        lca_rows = {row[0]: row[1] for row in lca_result.all()}

        contributions = [
            (bom_rows[mid] / 100.0) * co2e for mid, co2e in lca_rows.items() if mid in bom_rows
        ]
        if contributions:
            model.carbon_footprint_kg_co2e = round(sum(contributions), 4)
            model.carbon_footprint_source = "computed"

    # ── Publish (make active + disclose) ─────────────────────────────────────

    async def publish(
        self, organization_id: str, dpp_id: str, actor_id: str | None = None
    ) -> DigitalProductPassportModel | None:
        """Refresh snapshot, set status=ACTIVE, stamp disclosed_at."""
        model = await self.refresh_snapshot(organization_id, dpp_id, actor_id=actor_id)
        if model is None:
            return None
        model.dpp_status = DPPStatus.ACTIVE.value
        if model.disclosed_at is None:
            model.disclosed_at = _now()
        await self._session.flush()
        return model
