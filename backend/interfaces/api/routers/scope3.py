"""M8 Scope 3 Supply Chain Carbon Inventory API.

Routes:
  POST /scope3/pcf/{product_id}          — calculate + persist PCF for a product
  GET  /scope3/pcf/{product_id}          — list PCF history for a product
  GET  /scope3/pcf                       — list all PCFs for the org (optional year filter)
  POST /scope3/inventory/{year}          — compute/refresh Scope 3 inventory for a year
  GET  /scope3/inventory                 — list inventory records across years
  GET  /scope3/inventory/{year}          — get inventory for a specific year
  GET  /scope3/summary                   — org-level Scope 3 summary (latest year)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.scope3.inventory_service import Scope3InventoryService
from application.scope3.pcf_service import PCFCalculationService
from domain.user import User
from interfaces.api.deps import get_current_user, get_db, scope_gate
from interfaces.api.schemas.scope3 import (
    PCFCalculateRequest,
    ProductCarbonFootprintListResponse,
    ProductCarbonFootprintResponse,
    Scope3InventoryListResponse,
    Scope3InventoryResponse,
    Scope3OrgSummaryResponse,
)

router = APIRouter(
    prefix="/scope3",
    tags=["scope3"],
    dependencies=[
        Depends(get_current_user),
        Depends(scope_gate("ghg:read", "ghg:write")),
    ],
)


@router.post(
    "/pcf/{product_id}",
    response_model=ProductCarbonFootprintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calculate and persist PCF for a product",
)
async def calculate_pcf(
    product_id: str,
    body: PCFCalculateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductCarbonFootprintResponse:
    svc = PCFCalculationService(db)
    record = await svc.calculate(
        organization_id=current_user.organization_id,
        product_id=product_id,
        reporting_year=body.reporting_year,
        actor_id=current_user.id,
        notes=body.notes,
    )
    await db.commit()
    return ProductCarbonFootprintResponse.from_model(record)


@router.get(
    "/pcf/{product_id}",
    response_model=ProductCarbonFootprintListResponse,
    summary="List PCF calculation history for a product",
)
async def list_product_pcfs(
    product_id: str,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductCarbonFootprintListResponse:
    svc = PCFCalculationService(db)
    records = await svc.list_for_product(
        organization_id=current_user.organization_id,
        product_id=product_id,
        limit=limit,
    )
    return ProductCarbonFootprintListResponse(
        items=[ProductCarbonFootprintResponse.from_model(r) for r in records],
        total=len(records),
    )


@router.get(
    "/pcf",
    response_model=ProductCarbonFootprintListResponse,
    summary="List all PCFs for the organisation",
)
async def list_org_pcfs(
    reporting_year: int | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductCarbonFootprintListResponse:
    svc = PCFCalculationService(db)
    records = await svc.list_for_org(
        organization_id=current_user.organization_id,
        reporting_year=reporting_year,
        limit=limit,
    )
    return ProductCarbonFootprintListResponse(
        items=[ProductCarbonFootprintResponse.from_model(r) for r in records],
        total=len(records),
    )


@router.post(
    "/inventory/{year}",
    response_model=Scope3InventoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute or refresh Scope 3 Category 1 inventory for a reporting year",
)
async def compute_inventory(
    year: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Scope3InventoryResponse:
    svc = Scope3InventoryService(db)
    inventory = await svc.compute_inventory(
        organization_id=current_user.organization_id,
        reporting_year=year,
        actor_id=current_user.id,
    )
    await db.commit()
    return Scope3InventoryResponse.from_model(inventory)


@router.get(
    "/inventory",
    response_model=Scope3InventoryListResponse,
    summary="List Scope 3 inventories across reporting years",
)
async def list_inventories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Scope3InventoryListResponse:
    svc = Scope3InventoryService(db)
    items = await svc.list_inventories(
        organization_id=current_user.organization_id,
    )
    return Scope3InventoryListResponse(
        items=[Scope3InventoryResponse.from_model(i) for i in items],
        total=len(items),
    )


@router.get(
    "/inventory/{year}",
    response_model=Scope3InventoryResponse,
    summary="Get Scope 3 inventory for a specific reporting year",
)
async def get_inventory(
    year: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Scope3InventoryResponse:
    svc = Scope3InventoryService(db)
    inventory = await svc.get_inventory(
        organization_id=current_user.organization_id,
        reporting_year=year,
    )
    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Scope 3 inventory for year {year}.",
        )
    return Scope3InventoryResponse.from_model(inventory)


@router.get(
    "/summary",
    response_model=Scope3OrgSummaryResponse,
    summary="Org-level Scope 3 summary aggregated from latest PCF records",
)
async def get_scope3_summary(
    reporting_year: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Scope3OrgSummaryResponse:
    svc = PCFCalculationService(db)
    records = await svc.list_for_org(
        organization_id=current_user.organization_id,
        reporting_year=reporting_year,
        limit=500,
    )

    if not records:
        return Scope3OrgSummaryResponse(
            organization_id=current_user.organization_id,
            reporting_year=reporting_year,
            total_products_with_pcf=0,
            total_pcf_kg_co2e=0.0,
            total_pcf_tco2e=0.0,
            avg_pcf_kg_co2e_per_product=None,
            lca_coverage_pct=None,
        )

    valid = [r for r in records if r.pcf_kg_co2e_per_unit is not None]
    total_kg = sum(r.pcf_kg_co2e_per_unit for r in valid)
    avg = round(total_kg / len(valid), 4) if valid else None
    coverages = [r.weight_coverage_pct for r in valid if r.weight_coverage_pct is not None]
    avg_cov = round(sum(coverages) / len(coverages), 2) if coverages else None

    return Scope3OrgSummaryResponse(
        organization_id=current_user.organization_id,
        reporting_year=reporting_year,
        total_products_with_pcf=len(valid),
        total_pcf_kg_co2e=round(total_kg, 4),
        total_pcf_tco2e=round(total_kg / 1000.0, 6),
        avg_pcf_kg_co2e_per_product=avg,
        lca_coverage_pct=avg_cov,
    )
