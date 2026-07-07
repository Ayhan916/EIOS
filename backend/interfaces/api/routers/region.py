"""M47 — Data Residency endpoints.

GET /api/v1/organizations/{org_id}/data-residency        — org region info
GET /api/v1/organizations/{org_id}/data-residency/audit  — audit log (admin only)
GET /api/v1/region/info                                  — this instance's region
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.user import User
from infrastructure.routing.region_router import VALID_REGIONS, region_router
from interfaces.api.deps import get_current_user, get_db, require_admin
from shared.config import settings

router = APIRouter(tags=["M47 — Data Residency"])

_ADMIN = Depends(require_admin)


# ── Schemas ───────────────────────────────────────────────────────────────────


class InstanceRegionResponse(BaseModel):
    instance_region: str
    valid_regions: list[str]
    enforcement_strict: bool


class OrgResidencyResponse(BaseModel):
    organization_id: str
    declared_region: str | None
    canonical_region: str
    is_local_region: bool
    celery_queue: str
    s3_bucket: str


class AuditLogEntry(BaseModel):
    id: str
    organization_id: str | None
    user_id: str | None
    request_path: str
    request_method: str
    org_region: str | None
    instance_region: str
    event_type: str
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/region/info", response_model=InstanceRegionResponse)
async def get_instance_region_info(
    _current_user: User = Depends(get_current_user),
) -> InstanceRegionResponse:
    """Return the region this EIOS instance is deployed in."""
    return InstanceRegionResponse(
        instance_region=settings.instance_region.upper(),
        valid_regions=sorted(VALID_REGIONS),
        enforcement_strict=settings.region_enforcement_strict,
    )


@router.get(
    "/organizations/{org_id}/data-residency",
    response_model=OrgResidencyResponse,
)
async def get_org_residency(
    org_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> OrgResidencyResponse:
    """Return the data residency configuration for an organization."""
    from infrastructure.persistence.models.organization import OrganizationModel  # noqa: PLC0415

    if current_user.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    org = (
        await session.execute(select(OrganizationModel).where(OrganizationModel.id == org_id))
    ).scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    declared = getattr(org, "data_residency", None)
    canonical = region_router.canonical(declared)
    return OrgResidencyResponse(
        organization_id=org_id,
        declared_region=declared,
        canonical_region=canonical,
        is_local_region=region_router.is_local_region(declared),
        celery_queue=region_router.get_celery_queue(declared),
        s3_bucket=region_router.get_s3_bucket(declared),
    )


@router.get(
    "/organizations/{org_id}/data-residency/audit",
    response_model=list[AuditLogEntry],
    dependencies=[_ADMIN],
)
async def list_residency_audit_log(
    org_id: str,
    event_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[AuditLogEntry]:
    """List data residency access audit entries for an organization (admin only)."""
    from infrastructure.persistence.models.region import DataResidencyAuditLogModel  # noqa: PLC0415

    if current_user.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    stmt = select(DataResidencyAuditLogModel).where(
        DataResidencyAuditLogModel.organization_id == org_id
    )
    if event_type:
        stmt = stmt.where(DataResidencyAuditLogModel.event_type == event_type)
    stmt = stmt.order_by(DataResidencyAuditLogModel.created_at.desc()).limit(limit)

    result = await session.execute(stmt)
    return [AuditLogEntry.model_validate(e) for e in result.scalars().all()]
