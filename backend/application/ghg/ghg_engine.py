"""M46.2 — GHG Protocol Scope 1/2/3 Calculation Engine (G-030).

Design rules:
  - Deterministic, auditable, explainable — no LLM scoring.
  - Every calculation references a specific emission factor record by ID.
  - result_tco2e = result_kgco2e / 1000 (exact integer division).
  - Factors are looked up from DB; DEFRA 2023 and EPA 2023 seeded in migration 056.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.ghg import GHGCalculationModel, GHGEmissionFactorModel


class GHGFactorNotFound(Exception):
    pass


@dataclass
class GHGResult:
    calculation_id: str
    scope: str
    category: str
    subcategory: str
    amount: float
    unit: str
    factor_id: str
    factor_kgco2e_per_unit: float
    result_kgco2e: float
    result_tco2e: float
    source: str
    region: str
    description: str
    notes: str | None
    reporting_year: int | None
    calculated_at: datetime


async def calculate_emissions(
    *,
    session: AsyncSession,
    organization_id: str,
    created_by: str,
    scope: str,
    category: str,
    subcategory: str,
    amount: float,
    unit: str,
    source: str,
    region: str,
    supplier_id: str | None = None,
    notes: str | None = None,
    reporting_year: int | None = None,
) -> GHGResult:
    """Look up the matching emission factor and persist a calculation record.

    Raises GHGFactorNotFound when no factor matches the (scope, category, subcategory,
    unit, source, region) tuple — the caller decides whether to return 404 or 422.
    """
    factor = await _lookup_factor(
        session=session,
        organization_id=organization_id,
        scope=scope,
        category=category,
        subcategory=subcategory,
        unit=unit,
        source=source,
        region=region,
    )

    result_kgco2e = round(amount * factor.factor_kgco2e_per_unit, 6)
    result_tco2e = round(result_kgco2e / 1000, 9)
    now = datetime.now(UTC)

    record = GHGCalculationModel(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        supplier_id=supplier_id,
        created_by=created_by,
        scope=scope,
        category=category,
        subcategory=subcategory,
        amount=amount,
        unit=unit,
        factor_id=factor.id,
        factor_kgco2e_per_unit=factor.factor_kgco2e_per_unit,
        result_kgco2e=result_kgco2e,
        result_tco2e=result_tco2e,
        source=source,
        region=region,
        notes=notes,
        reporting_year=reporting_year,
        calculated_at=now,
    )
    session.add(record)
    await session.flush()

    return GHGResult(
        calculation_id=record.id,
        scope=scope,
        category=category,
        subcategory=subcategory,
        amount=amount,
        unit=unit,
        factor_id=factor.id,
        factor_kgco2e_per_unit=factor.factor_kgco2e_per_unit,
        result_kgco2e=result_kgco2e,
        result_tco2e=result_tco2e,
        source=source,
        region=region,
        description=factor.description or "",
        notes=notes,
        reporting_year=reporting_year,
        calculated_at=now,
    )


async def _lookup_factor(
    *,
    session: AsyncSession,
    organization_id: str,
    scope: str,
    category: str,
    subcategory: str,
    unit: str,
    source: str,
    region: str,
) -> GHGEmissionFactorModel:
    """Return the most specific factor: org-custom first, then standard."""
    stmt = (
        select(GHGEmissionFactorModel)
        .where(
            GHGEmissionFactorModel.scope == scope,
            GHGEmissionFactorModel.category == category,
            GHGEmissionFactorModel.subcategory == subcategory,
            GHGEmissionFactorModel.unit == unit,
            GHGEmissionFactorModel.source == source,
            GHGEmissionFactorModel.region == region,
        )
        .order_by(
            GHGEmissionFactorModel.is_custom.desc(),  # org custom wins
            GHGEmissionFactorModel.year.desc(),       # latest year wins among same source
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    factor = result.scalar_one_or_none()
    if factor is None:
        raise GHGFactorNotFound(
            f"No emission factor found for {scope}/{category}/{subcategory} "
            f"unit={unit} source={source} region={region}"
        )
    return factor


async def list_factors(
    *,
    session: AsyncSession,
    scope: str | None = None,
    source: str | None = None,
    region: str | None = None,
    organization_id: str | None = None,
) -> list[GHGEmissionFactorModel]:
    stmt = select(GHGEmissionFactorModel).where(
        (GHGEmissionFactorModel.is_custom == False)  # noqa: E712
        | (GHGEmissionFactorModel.organization_id == organization_id)
    )
    if scope:
        stmt = stmt.where(GHGEmissionFactorModel.scope == scope)
    if source:
        stmt = stmt.where(GHGEmissionFactorModel.source == source)
    if region:
        stmt = stmt.where(GHGEmissionFactorModel.region == region)
    stmt = stmt.order_by(
        GHGEmissionFactorModel.scope,
        GHGEmissionFactorModel.category,
        GHGEmissionFactorModel.subcategory,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
