"""Scope 3 Inventory Service — M8.

Aggregates all ProductCarbonFootprintModel records for (org, year) into a
Scope3InventoryModel representing GHG Protocol Scope 3 Category 1
(Purchased Goods & Services).

Recalculation is idempotent: existing record for (org, year) is overwritten.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.scope3 import (
    ProductCarbonFootprintModel,
    Scope3InventoryModel,
)

_CALC_VERSION = "1.0"
_TOP_N = 10


class Scope3InventoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def compute_inventory(
        self,
        organization_id: str,
        reporting_year: int,
        actor_id: str | None = None,
    ) -> Scope3InventoryModel:
        pcfs_result = await self._db.execute(
            select(ProductCarbonFootprintModel).where(
                ProductCarbonFootprintModel.organization_id == organization_id,
                ProductCarbonFootprintModel.reporting_year == reporting_year,
            )
        )
        pcfs = list(pcfs_result.scalars().all())

        if not pcfs:
            return await self._upsert(
                organization_id=organization_id,
                reporting_year=reporting_year,
                total_kg=0.0,
                products_included=0,
                full_lca=0,
                partial_lca=0,
                without_lca=0,
                top=[],
                actor_id=actor_id,
            )

        total_kg = 0.0
        full_lca = 0
        partial_lca = 0
        without_lca = 0
        contributors = []

        for pcf in pcfs:
            cov = pcf.weight_coverage_pct
            val = pcf.pcf_kg_co2e_per_unit

            if val is not None:
                total_kg += val
                contributors.append(
                    {
                        "product_id": pcf.product_id,
                        "pcf_kg_co2e": val,
                        "weight_coverage_pct": cov,
                    }
                )
                if cov is not None and cov >= 95.0:
                    full_lca += 1
                else:
                    partial_lca += 1
            else:
                without_lca += 1

        contributors.sort(key=lambda c: c["pcf_kg_co2e"], reverse=True)
        top = contributors[:_TOP_N]

        return await self._upsert(
            organization_id=organization_id,
            reporting_year=reporting_year,
            total_kg=round(total_kg, 4),
            products_included=len(pcfs),
            full_lca=full_lca,
            partial_lca=partial_lca,
            without_lca=without_lca,
            top=top,
            actor_id=actor_id,
        )

    async def _upsert(
        self,
        organization_id: str,
        reporting_year: int,
        total_kg: float,
        products_included: int,
        full_lca: int,
        partial_lca: int,
        without_lca: int,
        top: list,
        actor_id: str | None,
    ) -> Scope3InventoryModel:
        existing_result = await self._db.execute(
            select(Scope3InventoryModel).where(
                Scope3InventoryModel.organization_id == organization_id,
                Scope3InventoryModel.reporting_year == reporting_year,
            )
        )
        existing = existing_result.scalar_one_or_none()
        now = datetime.now(UTC)

        if existing is not None:
            existing.total_pcf_kg_co2e = total_kg
            existing.total_pcf_tco2e = round(total_kg / 1000.0, 6)
            existing.products_included = products_included
            existing.products_with_full_lca = full_lca
            existing.products_with_partial_lca = partial_lca
            existing.products_without_lca = without_lca
            existing.top_contributors = top
            existing.calc_version = _CALC_VERSION
            existing.calculated_at = now
            existing.calculated_by = actor_id
            existing.updated_by = actor_id
            existing.updated_at = now
            await self._db.flush()
            return existing

        record = Scope3InventoryModel(
            id=str(uuid4()),
            organization_id=organization_id,
            reporting_year=reporting_year,
            total_pcf_kg_co2e=total_kg,
            total_pcf_tco2e=round(total_kg / 1000.0, 6),
            products_included=products_included,
            products_with_full_lca=full_lca,
            products_with_partial_lca=partial_lca,
            products_without_lca=without_lca,
            top_contributors=top,
            calc_version=_CALC_VERSION,
            calculated_at=now,
            calculated_by=actor_id,
            created_by=actor_id,
            updated_by=actor_id,
            created_at=now,
            updated_at=now,
        )
        self._db.add(record)
        await self._db.flush()
        return record

    async def list_inventories(
        self,
        organization_id: str,
    ) -> list[Scope3InventoryModel]:
        result = await self._db.execute(
            select(Scope3InventoryModel)
            .where(Scope3InventoryModel.organization_id == organization_id)
            .order_by(Scope3InventoryModel.reporting_year.desc())
        )
        return list(result.scalars().all())

    async def get_inventory(
        self,
        organization_id: str,
        reporting_year: int,
    ) -> Scope3InventoryModel | None:
        result = await self._db.execute(
            select(Scope3InventoryModel).where(
                Scope3InventoryModel.organization_id == organization_id,
                Scope3InventoryModel.reporting_year == reporting_year,
            )
        )
        return result.scalar_one_or_none()
