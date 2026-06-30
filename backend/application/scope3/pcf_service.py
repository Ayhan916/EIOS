"""PCF Calculation Service — M8 Scope 3 Supply Chain Carbon Inventory.

Computes Product Carbon Footprint (PCF) from BOM × material LCA data.

Formula: PCF = Σ (weight_pct_i / 100) × co2e_per_kg_i  for each BOM material i
  - weight_pct_i: share of material i in the product BOM (from ProductBOMItemModel)
  - co2e_per_kg_i: latest LCA carbon intensity of material i (MaterialSustainabilityMetricModel)

Weight coverage:  Σ weight_pct of materials that have LCA data  /  Σ weight_pct of all BOM items
This tracks how representative the PCF is — a 40% coverage PCF is incomplete.

Deterministic, auditable, no LLM involvement.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.material import (
    MaterialModel,
    MaterialSustainabilityMetricModel,
)
from infrastructure.persistence.models.product import ProductBOMItemModel
from infrastructure.persistence.models.scope3 import ProductCarbonFootprintModel

_CALC_VERSION = "1.0"


class PCFCalculationService:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def calculate(
        self,
        organization_id: str,
        product_id: str,
        reporting_year: int,
        actor_id: str | None = None,
        notes: str | None = None,
    ) -> ProductCarbonFootprintModel:
        bom_result = await self._db.execute(
            select(
                ProductBOMItemModel.material_id,
                ProductBOMItemModel.weight_pct,
            ).where(
                ProductBOMItemModel.organization_id == organization_id,
                ProductBOMItemModel.product_id == product_id,
            )
        )
        bom_rows = {row.material_id: row.weight_pct for row in bom_result.all()}
        total_bom = len(bom_rows)

        if not bom_rows:
            return await self._persist(
                organization_id=organization_id,
                product_id=product_id,
                reporting_year=reporting_year,
                pcf=None,
                total=0,
                with_lca=0,
                weight_coverage=None,
                breakdown=[],
                actor_id=actor_id,
                notes=notes,
            )

        # Latest LCA year ≤ reporting_year per material
        subq = (
            select(
                MaterialSustainabilityMetricModel.material_id,
                func.max(MaterialSustainabilityMetricModel.reporting_year).label("max_year"),
            )
            .where(
                MaterialSustainabilityMetricModel.organization_id == organization_id,
                MaterialSustainabilityMetricModel.material_id.in_(list(bom_rows.keys())),
                MaterialSustainabilityMetricModel.reporting_year <= reporting_year,
            )
            .group_by(MaterialSustainabilityMetricModel.material_id)
            .subquery()
        )
        lca_result = await self._db.execute(
            select(
                MaterialSustainabilityMetricModel.material_id,
                MaterialSustainabilityMetricModel.carbon_footprint_kg_co2e_per_kg,
            ).join(
                subq,
                (MaterialSustainabilityMetricModel.material_id == subq.c.material_id)
                & (MaterialSustainabilityMetricModel.reporting_year == subq.c.max_year),
            ).where(
                MaterialSustainabilityMetricModel.carbon_footprint_kg_co2e_per_kg.isnot(None)
            )
        )
        lca_rows = {row.material_id: row.carbon_footprint_kg_co2e_per_kg for row in lca_result.all()}

        # Lookup material names for breakdown
        name_result = await self._db.execute(
            select(MaterialModel.id, MaterialModel.name).where(
                MaterialModel.organization_id == organization_id,
                MaterialModel.id.in_(list(bom_rows.keys())),
            )
        )
        name_map = {row.id: row.name for row in name_result.all()}

        breakdown = []
        total_weight_with_lca = 0.0
        total_weight_all = 0.0
        pcf_sum = 0.0

        for mid, weight_pct in bom_rows.items():
            w = weight_pct if weight_pct is not None else 0.0
            total_weight_all += w
            co2e_per_kg = lca_rows.get(mid)
            if co2e_per_kg is not None:
                contribution = (w / 100.0) * co2e_per_kg
                pcf_sum += contribution
                total_weight_with_lca += w
                breakdown.append({
                    "material_id": mid,
                    "material_name": name_map.get(mid, ""),
                    "weight_pct": w,
                    "co2e_per_kg": co2e_per_kg,
                    "contribution_kg_co2e": round(contribution, 6),
                })
            else:
                breakdown.append({
                    "material_id": mid,
                    "material_name": name_map.get(mid, ""),
                    "weight_pct": w,
                    "co2e_per_kg": None,
                    "contribution_kg_co2e": None,
                })

        weight_coverage = (
            round((total_weight_with_lca / total_weight_all) * 100, 2)
            if total_weight_all > 0 else None
        )
        pcf_value = round(pcf_sum, 6) if lca_rows else None

        return await self._persist(
            organization_id=organization_id,
            product_id=product_id,
            reporting_year=reporting_year,
            pcf=pcf_value,
            total=total_bom,
            with_lca=len(lca_rows),
            weight_coverage=weight_coverage,
            breakdown=breakdown,
            actor_id=actor_id,
            notes=notes,
        )

    async def _persist(
        self,
        organization_id: str,
        product_id: str,
        reporting_year: int,
        pcf: float | None,
        total: int,
        with_lca: int,
        weight_coverage: float | None,
        breakdown: list,
        actor_id: str | None,
        notes: str | None,
    ) -> ProductCarbonFootprintModel:
        now = datetime.now(UTC)
        record = ProductCarbonFootprintModel(
            id=str(uuid4()),
            organization_id=organization_id,
            product_id=product_id,
            reporting_year=reporting_year,
            pcf_kg_co2e_per_unit=pcf,
            pcf_source="computed" if pcf is not None else "no_lca_data",
            bom_materials_total=total,
            bom_materials_with_lca=with_lca,
            weight_coverage_pct=weight_coverage,
            material_breakdown=breakdown,
            calc_version=_CALC_VERSION,
            calculated_at=now,
            calculated_by=actor_id,
            notes=notes,
            created_by=actor_id,
            updated_by=actor_id,
            created_at=now,
            updated_at=now,
        )
        self._db.add(record)
        await self._db.flush()
        return record

    async def list_for_product(
        self,
        organization_id: str,
        product_id: str,
        limit: int = 20,
    ) -> list[ProductCarbonFootprintModel]:
        result = await self._db.execute(
            select(ProductCarbonFootprintModel)
            .where(
                ProductCarbonFootprintModel.organization_id == organization_id,
                ProductCarbonFootprintModel.product_id == product_id,
            )
            .order_by(
                ProductCarbonFootprintModel.reporting_year.desc(),
                ProductCarbonFootprintModel.calculated_at.desc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_for_org(
        self,
        organization_id: str,
        reporting_year: int | None = None,
        limit: int = 100,
    ) -> list[ProductCarbonFootprintModel]:
        stmt = select(ProductCarbonFootprintModel).where(
            ProductCarbonFootprintModel.organization_id == organization_id,
        )
        if reporting_year is not None:
            stmt = stmt.where(ProductCarbonFootprintModel.reporting_year == reporting_year)
        stmt = stmt.order_by(
            ProductCarbonFootprintModel.reporting_year.desc(),
            ProductCarbonFootprintModel.pcf_kg_co2e_per_unit.desc(),
        ).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
