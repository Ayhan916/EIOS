"""M46.2 — GHG Protocol Scope 1/2/3 Calculation API (G-030).

All results are deterministic and auditable — every calculation record
references the exact emission factor ID used.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.ghg.ghg_engine import (
    GHGFactorNotFound,
    calculate_emissions,
    list_factors,
)
from domain.user import User
from interfaces.api.deps import get_current_user, get_db, require_analyst
from interfaces.api.schemas.ghg import (
    GHGBulkCalculateRequest,
    GHGBulkCalculateResponse,
    GHGCalculateRequest,
    GHGCalculationResponse,
    GHGEmissionFactorResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/ghg", tags=["ghg"])


@router.get("/factors", response_model=list[GHGEmissionFactorResponse])
async def get_emission_factors(
    scope: str | None = Query(default=None),
    source: str | None = Query(default=None),
    region: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[GHGEmissionFactorResponse]:
    """List available emission factors (DEFRA 2023, EPA 2023 + any org-custom factors)."""
    factors = await list_factors(
        session=session,
        scope=scope,
        source=source,
        region=region,
        organization_id=current_user.organization_id,
    )
    return [GHGEmissionFactorResponse.model_validate(f) for f in factors]


@router.post(
    "/calculate",
    response_model=GHGCalculationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def calculate_ghg(
    body: GHGCalculateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> GHGCalculationResponse:
    """Calculate GHG emissions for a single activity and persist the audit record."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )
    try:
        result = await calculate_emissions(
            session=session,
            organization_id=current_user.organization_id,
            created_by=current_user.id,
            scope=body.scope,
            category=body.category,
            subcategory=body.subcategory,
            amount=body.amount,
            unit=body.unit,
            source=body.source,
            region=body.region,
            supplier_id=body.supplier_id,
            notes=body.notes,
            reporting_year=body.reporting_year,
        )
    except GHGFactorNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    logger.info(
        "ghg_calculated",
        organization_id=current_user.organization_id,
        scope=body.scope,
        result_tco2e=result.result_tco2e,
    )
    return GHGCalculationResponse(
        calculation_id=result.calculation_id,
        scope=result.scope,
        category=result.category,
        subcategory=result.subcategory,
        amount=result.amount,
        unit=result.unit,
        factor_id=result.factor_id,
        factor_kgco2e_per_unit=result.factor_kgco2e_per_unit,
        result_kgco2e=result.result_kgco2e,
        result_tco2e=result.result_tco2e,
        source=result.source,
        region=result.region,
        description=result.description,
        notes=result.notes,
        reporting_year=result.reporting_year,
        calculated_at=result.calculated_at,
    )


@router.post(
    "/calculate/bulk",
    response_model=GHGBulkCalculateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def calculate_ghg_bulk(
    body: GHGBulkCalculateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> GHGBulkCalculateResponse:
    """Calculate GHG emissions for multiple activities in one request.

    Each activity is attempted independently; failures collect into `errors`.
    Successful calculations are persisted and returned in `results`.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to an organization"
        )

    results = []
    errors = []

    for idx, item in enumerate(body.activities):
        try:
            result = await calculate_emissions(
                session=session,
                organization_id=current_user.organization_id,
                created_by=current_user.id,
                scope=item.scope,
                category=item.category,
                subcategory=item.subcategory,
                amount=item.amount,
                unit=item.unit,
                source=item.source,
                region=item.region,
                supplier_id=item.supplier_id,
                notes=item.notes,
                reporting_year=item.reporting_year,
            )
            results.append(
                GHGCalculationResponse(
                    calculation_id=result.calculation_id,
                    scope=result.scope,
                    category=result.category,
                    subcategory=result.subcategory,
                    amount=result.amount,
                    unit=result.unit,
                    factor_id=result.factor_id,
                    factor_kgco2e_per_unit=result.factor_kgco2e_per_unit,
                    result_kgco2e=result.result_kgco2e,
                    result_tco2e=result.result_tco2e,
                    source=result.source,
                    region=result.region,
                    description=result.description,
                    notes=result.notes,
                    reporting_year=result.reporting_year,
                    calculated_at=result.calculated_at,
                )
            )
        except GHGFactorNotFound as exc:
            errors.append({"index": idx, "error": str(exc)})

    total_kgco2e = round(sum(r.result_kgco2e for r in results), 6)
    total_tco2e = round(total_kgco2e / 1000, 9)

    logger.info(
        "ghg_bulk_calculated",
        organization_id=current_user.organization_id,
        count=len(results),
        errors=len(errors),
        total_tco2e=total_tco2e,
    )
    return GHGBulkCalculateResponse(
        results=results,
        errors=errors,
        total_kgco2e=total_kgco2e,
        total_tco2e=total_tco2e,
    )
