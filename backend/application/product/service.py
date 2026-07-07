"""
M27 — Product Twin Service (KAN-100)

Two service classes:
  ProductService     — CRUD for the Product aggregate
  ProductBOMService  — manage BOM items + aggregate compliance/sustainability

Session ownership: caller (router) commits; service only flushes.
organization_id is a MANDATORY filter on every DB query.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.product import ProductStatus, ProductType, TargetMarket
from infrastructure.kafka.events import DomainEvent
from infrastructure.kafka.producer import KafkaEventProducer
from infrastructure.persistence.models.material import (
    MaterialComplianceFlagModel,
    MaterialSustainabilityMetricModel,
)
from infrastructure.persistence.models.product import ProductBOMItemModel, ProductModel

logger = structlog.get_logger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _uid() -> str:
    return str(uuid4())


# ── Product CRUD ──────────────────────────────────────────────────────────────


class ProductService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def create(
        self,
        organization_id: str,
        name: str,
        product_type: ProductType,
        *,
        sku: str | None = None,
        internal_code: str | None = None,
        gtin: str | None = None,
        category: str | None = None,
        brand: str | None = None,
        unit_of_measure: str = "pcs",
        weight_kg: float | None = None,
        country_of_manufacture: str | None = None,
        is_regulated_product: bool = False,
        target_market: TargetMarket | None = None,
        description: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> ProductModel:
        now = _now()
        model = ProductModel(
            id=_uid(),
            organization_id=organization_id,
            name=name,
            product_type=product_type.value,
            product_status=ProductStatus.DRAFT.value,
            sku=sku,
            internal_code=internal_code,
            gtin=gtin,
            category=category,
            brand=brand,
            unit_of_measure=unit_of_measure,
            weight_kg=weight_kg,
            country_of_manufacture=country_of_manufacture,
            is_regulated_product=is_regulated_product,
            target_market=target_market.value if target_market else None,
            description=description,
            notes=notes,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
        )
        self._session.add(model)
        await self._session.flush()

        await self._kafka.publish_product_event(
            DomainEvent.product_created(
                organization_id=organization_id,
                product_id=model.id,
                product_type=product_type.value,
                name=name,
                actor_id=actor_id,
            )
        )
        return model

    async def list_for_org(
        self,
        organization_id: str,
        product_type: ProductType | None = None,
        product_status: ProductStatus | None = None,
        search: str | None = None,
        category: str | None = None,
        regulated_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ProductModel], int]:
        stmt = select(ProductModel).where(
            ProductModel.organization_id == organization_id,
        )
        if product_type is not None:
            stmt = stmt.where(ProductModel.product_type == product_type.value)
        if product_status is not None:
            stmt = stmt.where(ProductModel.product_status == product_status.value)
        else:
            stmt = stmt.where(ProductModel.product_status != ProductStatus.ARCHIVED.value)
        if category:
            stmt = stmt.where(ProductModel.category.ilike(f"%{category}%"))
        if regulated_only:
            stmt = stmt.where(ProductModel.is_regulated_product.is_(True))
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                ProductModel.name.ilike(like)
                | ProductModel.sku.ilike(like)
                | ProductModel.gtin.ilike(like)
                | ProductModel.internal_code.ilike(like)
            )

        count_result = await self._session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar_one()

        stmt = stmt.order_by(ProductModel.name).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get(self, organization_id: str, product_id: str) -> ProductModel | None:
        model = await self._session.get(ProductModel, product_id)
        if model is None or model.organization_id != organization_id:
            return None
        return model

    async def update(
        self,
        organization_id: str,
        product_id: str,
        *,
        name: str | None = None,
        product_type: ProductType | None = None,
        product_status: ProductStatus | None = None,
        sku: str | None = None,
        internal_code: str | None = None,
        gtin: str | None = None,
        category: str | None = None,
        brand: str | None = None,
        unit_of_measure: str | None = None,
        weight_kg: float | None = None,
        country_of_manufacture: str | None = None,
        is_regulated_product: bool | None = None,
        target_market: TargetMarket | None = None,
        description: str | None = None,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> ProductModel | None:
        model = await self.get(organization_id, product_id)
        if model is None:
            return None
        if name is not None:
            model.name = name
        if product_type is not None:
            model.product_type = product_type.value
        if product_status is not None:
            model.product_status = product_status.value
        if sku is not None:
            model.sku = sku
        if internal_code is not None:
            model.internal_code = internal_code
        if gtin is not None:
            model.gtin = gtin
        if category is not None:
            model.category = category
        if brand is not None:
            model.brand = brand
        if unit_of_measure is not None:
            model.unit_of_measure = unit_of_measure
        if weight_kg is not None:
            model.weight_kg = weight_kg
        if country_of_manufacture is not None:
            model.country_of_manufacture = country_of_manufacture
        if is_regulated_product is not None:
            model.is_regulated_product = is_regulated_product
        if target_market is not None:
            model.target_market = target_market.value
        if description is not None:
            model.description = description
        if notes is not None:
            model.notes = notes
        model.updated_at = _now()
        model.updated_by = actor_id
        await self._session.flush()
        return model

    async def archive(
        self, organization_id: str, product_id: str, actor_id: str | None = None
    ) -> bool:
        model = await self.get(organization_id, product_id)
        if model is None:
            return False
        model.product_status = ProductStatus.ARCHIVED.value
        model.updated_at = _now()
        model.updated_by = actor_id
        await self._session.flush()
        return True


# ── Product BOM ───────────────────────────────────────────────────────────────


class ProductBOMService:
    def __init__(self, session: AsyncSession, kafka: KafkaEventProducer) -> None:
        self._session = session
        self._kafka = kafka

    async def add_item(
        self,
        organization_id: str,
        product_id: str,
        material_id: str,
        *,
        weight_pct: float | None = None,
        quantity: float | None = None,
        unit: str | None = None,
        is_substance_of_concern: bool = False,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> ProductBOMItemModel:
        now = _now()
        model = ProductBOMItemModel(
            id=_uid(),
            organization_id=organization_id,
            product_id=product_id,
            material_id=material_id,
            weight_pct=weight_pct,
            quantity=quantity,
            unit=unit,
            is_substance_of_concern=is_substance_of_concern,
            notes=notes,
            created_at=now,
            updated_at=now,
            created_by=actor_id,
        )
        self._session.add(model)
        await self._session.flush()

        await self._kafka.publish_product_event(
            DomainEvent.product_bom_item_added(
                organization_id=organization_id,
                product_id=product_id,
                material_id=material_id,
                weight_pct=weight_pct,
                actor_id=actor_id,
            )
        )
        return model

    async def list_bom(self, organization_id: str, product_id: str) -> list[ProductBOMItemModel]:
        stmt = (
            select(ProductBOMItemModel)
            .where(
                ProductBOMItemModel.organization_id == organization_id,
                ProductBOMItemModel.product_id == product_id,
            )
            .order_by(ProductBOMItemModel.weight_pct.desc().nullslast())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_item(self, organization_id: str, bom_item_id: str) -> bool:
        model = await self._session.get(ProductBOMItemModel, bom_item_id)
        if model is None or model.organization_id != organization_id:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def aggregate_compliance(self, organization_id: str, product_id: str) -> list[dict]:
        """Return compliance flags for all materials in the BOM, grouped by regulation."""
        bom = await self.list_bom(organization_id, product_id)
        if not bom:
            return []

        material_ids = [item.material_id for item in bom]
        stmt = (
            select(MaterialComplianceFlagModel)
            .where(
                MaterialComplianceFlagModel.organization_id == organization_id,
                MaterialComplianceFlagModel.material_id.in_(material_ids),
            )
            .order_by(
                MaterialComplianceFlagModel.regulation,
                MaterialComplianceFlagModel.compliance_status,
            )
        )
        result = await self._session.execute(stmt)
        flags = list(result.scalars().all())

        # Group by regulation, keep worst status
        STATUS_PRIORITY = {
            "NON_COMPLIANT": 0,
            "PARTIALLY_COMPLIANT": 1,
            "UNDER_ASSESSMENT": 2,
            "UNKNOWN": 3,
            "EXEMPT": 4,
            "COMPLIANT": 5,
        }
        by_reg: dict[str, dict] = {}
        for flag in flags:
            reg = flag.regulation
            prio = STATUS_PRIORITY.get(flag.compliance_status, 99)
            if reg not in by_reg or prio < STATUS_PRIORITY.get(by_reg[reg]["worst_status"], 99):
                by_reg[reg] = {
                    "regulation": reg,
                    "worst_status": flag.compliance_status,
                    "material_count": 0,
                    "non_compliant_material_ids": [],
                }
            by_reg[reg]["material_count"] += 1
            if flag.compliance_status == "NON_COMPLIANT":
                by_reg[reg]["non_compliant_material_ids"].append(flag.material_id)

        return list(by_reg.values())

    async def aggregate_sustainability(
        self, organization_id: str, product_id: str, reporting_year: int | None = None
    ) -> dict:
        """Compute weighted PCF and other sustainability KPIs from BOM materials."""
        bom = await self.list_bom(organization_id, product_id)
        if not bom:
            return {"has_data": False}

        material_ids = [item.material_id for item in bom]
        stmt = select(MaterialSustainabilityMetricModel).where(
            MaterialSustainabilityMetricModel.organization_id == organization_id,
            MaterialSustainabilityMetricModel.material_id.in_(material_ids),
        )
        if reporting_year is not None:
            stmt = stmt.where(MaterialSustainabilityMetricModel.reporting_year == reporting_year)
        else:
            # Use the most recent year for each material
            subq = (
                select(
                    MaterialSustainabilityMetricModel.material_id,
                    func.max(MaterialSustainabilityMetricModel.reporting_year).label("max_year"),
                )
                .where(
                    MaterialSustainabilityMetricModel.organization_id == organization_id,
                    MaterialSustainabilityMetricModel.material_id.in_(material_ids),
                )
                .group_by(MaterialSustainabilityMetricModel.material_id)
                .subquery()
            )
            stmt = stmt.join(
                subq,
                (MaterialSustainabilityMetricModel.material_id == subq.c.material_id)
                & (MaterialSustainabilityMetricModel.reporting_year == subq.c.max_year),
            )

        result = await self._session.execute(stmt)
        metrics = {m.material_id: m for m in result.scalars().all()}

        # Build BOM weight lookup
        bom_by_material = {item.material_id: item for item in bom}

        sum((item.weight_pct or 0) for item in bom if item.weight_pct is not None)

        pcf_contributions: list[tuple[float, float]] = []  # (weight_pct, co2e_per_kg)
        water_contributions: list[tuple[float, float]] = []
        covered_pct = 0.0

        for mat_id, item in bom_by_material.items():
            if mat_id not in metrics or item.weight_pct is None:
                continue
            m = metrics[mat_id]
            pct = item.weight_pct / 100.0  # fraction
            covered_pct += item.weight_pct
            if m.carbon_footprint_kg_co2e_per_kg is not None:
                pcf_contributions.append((pct, m.carbon_footprint_kg_co2e_per_kg))
            if m.water_footprint_l_per_kg is not None:
                water_contributions.append((pct, m.water_footprint_l_per_kg))

        pcf = round(sum(p * v for p, v in pcf_contributions), 4) if pcf_contributions else None
        water = (
            round(sum(p * v for p, v in water_contributions), 4) if water_contributions else None
        )

        return {
            "has_data": bool(metrics),
            "bom_materials_total": len(bom),
            "bom_materials_with_lca": len(metrics),
            "weight_coverage_pct": round(covered_pct, 2),
            "product_carbon_footprint_kg_co2e_per_kg": pcf,
            "product_water_footprint_l_per_kg": water,
            "materials_with_concern": sum(1 for item in bom if item.is_substance_of_concern),
        }
