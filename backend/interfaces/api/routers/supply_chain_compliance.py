"""M7 Supply Chain Compliance Extensions API.

Routes:
  POST /compliance/supply-chain/scan/{product_id}   — trigger BOM compliance scan
  GET  /compliance/supply-chain/scan/{product_id}   — list scan results for product
  GET  /compliance/supply-chain/non-compliant        — products with NON_COMPLIANT scans
  GET  /compliance/supply-chain/summary              — org-wide supply chain summary
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.compliance.product_scan import ProductComplianceScanService
from application.compliance.supply_chain_summary import SupplyChainComplianceSummaryService
from domain.user import User
from interfaces.api.deps import get_current_user, get_db, scope_gate
from interfaces.api.schemas.product_compliance import (
    AtRiskRegulationResponse,
    DPPStatsResponse,
    MaterialStatsResponse,
    ProductComplianceScanListResponse,
    ProductComplianceScanResponse,
    ProductStatsResponse,
    ScanTriggerRequest,
    SupplyChainComplianceSummaryResponse,
)

router = APIRouter(
    prefix="/compliance/supply-chain",
    tags=["supply-chain-compliance"],
    dependencies=[
        Depends(get_current_user),
        Depends(scope_gate("compliance:read", "compliance:write")),
    ],
)


@router.post(
    "/scan/{product_id}",
    response_model=ProductComplianceScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger BOM compliance scan for a product",
)
async def trigger_product_scan(
    product_id: str,
    body: ScanTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductComplianceScanResponse:
    svc = ProductComplianceScanService(db)
    scan = await svc.scan_product_bom(
        organization_id=current_user.organization_id,
        product_id=product_id,
        regulation_code=body.regulation_code,
        actor_id=current_user.id,
    )
    await db.commit()
    return ProductComplianceScanResponse.from_model(scan)


@router.get(
    "/scan/{product_id}",
    response_model=ProductComplianceScanListResponse,
    summary="List compliance scan results for a product",
)
async def list_product_scans(
    product_id: str,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductComplianceScanListResponse:
    svc = ProductComplianceScanService(db)
    scans = await svc.list_scans_for_product(
        organization_id=current_user.organization_id,
        product_id=product_id,
        limit=limit,
    )
    return ProductComplianceScanListResponse(
        items=[ProductComplianceScanResponse.from_model(s) for s in scans],
        total=len(scans),
    )


@router.get(
    "/non-compliant",
    response_model=ProductComplianceScanListResponse,
    summary="List products with NON_COMPLIANT scan results",
)
async def list_non_compliant_products(
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductComplianceScanListResponse:
    svc = ProductComplianceScanService(db)
    scans = await svc.list_non_compliant_products(
        organization_id=current_user.organization_id,
        limit=limit,
    )
    return ProductComplianceScanListResponse(
        items=[ProductComplianceScanResponse.from_model(s) for s in scans],
        total=len(scans),
    )


@router.get(
    "/summary",
    response_model=SupplyChainComplianceSummaryResponse,
    summary="Org-wide supply chain compliance summary",
)
async def get_supply_chain_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SupplyChainComplianceSummaryResponse:
    svc = SupplyChainComplianceSummaryService(db)
    data = await svc.compute_summary(organization_id=current_user.organization_id)
    return SupplyChainComplianceSummaryResponse(
        organization_id=data["organization_id"],
        materials=MaterialStatsResponse(**data["materials"]),
        products=ProductStatsResponse(**data["products"]),
        digital_product_passports=DPPStatsResponse(**data["digital_product_passports"]),
        top_at_risk_regulations=[
            AtRiskRegulationResponse(**r) for r in data["top_at_risk_regulations"]
        ],
    )
