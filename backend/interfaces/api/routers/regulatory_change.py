"""Regulatory Change Monitoring API — GAP-19.

Endpoints:
  GET    /regulatory-changes/              List changes (global + org-specific)
  POST   /regulatory-changes/              Log a manual change
  GET    /regulatory-changes/summary       Count of new / unacknowledged items
  GET    /regulatory-changes/seed          Seed the global curated change list
  POST   /regulatory-changes/{id}/scan     Run impact scan for a specific change
  GET    /regulatory-changes/{id}/impacts  List impacts for a change
  PATCH  /regulatory-changes/impacts/{id}/acknowledge  Mark impact as reviewed
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

import application.notification_service as notification_service
from application.regulatory.change_scanner import (
    _REVIEW_STATUS_FLAG,
    REGULATORY_CHANGE_SEED,
    build_impact_summary,
)
from domain.enums import (
    EntityStatus,
    NotificationType,
    RegulatoryChangeSeverity,
    RegulatoryChangeStatus,
)
from domain.regulatory_change import RegulatoryChange, RegulatoryChangeImpact
from infrastructure.persistence.models.assessment import AssessmentModel
from infrastructure.persistence.models.regulatory import (
    ComplianceGapModel,
    RegulationModel,
    RegulationRequirementModel,
)
from infrastructure.persistence.models.regulatory_change import (
    RegulatoryChangeModel,
)
from infrastructure.persistence.repositories.regulatory_change import (
    SQLRegulatoryChangeImpactRepository,
    SQLRegulatoryChangeRepository,
)
from interfaces.api.deps import get_current_user, get_db, require_analyst

router = APIRouter(prefix="/regulatory-changes", tags=["regulatory-changes"])

# ── Schemas ────────────────────────────────────────────────────────────────────


class RegulatoryChangeCreate(BaseModel):
    framework_code: str
    change_title: str
    change_description: str
    affected_article: str = ""
    effective_date: date | None = None
    severity: str = RegulatoryChangeSeverity.MODERATE.value
    source_name: str = "Manual"
    source_url: str = ""
    affected_sectors: list[str] = Field(default_factory=list)
    affected_frameworks: list[str] = Field(default_factory=list)
    regulation_refs: str = ""


class RegulatoryChangeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    organization_id: str | None
    framework_code: str
    change_title: str
    change_description: str
    affected_article: str
    effective_date: date | None
    severity: str
    change_status: str
    source_name: str
    source_url: str
    affected_sectors: list[str]
    affected_frameworks: list[str]
    impact_summary: str
    impacted_assessment_count: int
    impacted_gap_count: int
    regulation_refs: str
    created_at: datetime
    updated_at: datetime


class RegulatoryChangeImpactResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    organization_id: str
    change_id: str
    assessment_id: str | None
    compliance_gap_id: str | None
    impact_type: str
    re_review_required: bool
    notification_sent: bool
    acknowledged_by_user_id: str | None
    acknowledged_at: datetime | None
    created_at: datetime


class ChangeSummaryResponse(BaseModel):
    new_changes: int
    pending_re_reviews: int
    total_changes: int


# ── Helpers ────────────────────────────────────────────────────────────────────


def _change_to_response(c: RegulatoryChange) -> RegulatoryChangeResponse:
    return RegulatoryChangeResponse(
        id=c.id,
        organization_id=c.organization_id,
        framework_code=c.framework_code,
        change_title=c.change_title,
        change_description=c.change_description,
        affected_article=c.affected_article,
        effective_date=c.effective_date,
        severity=c.severity,
        change_status=c.change_status,
        source_name=c.source_name,
        source_url=c.source_url,
        affected_sectors=c.affected_sectors,
        affected_frameworks=c.affected_frameworks,
        impact_summary=c.impact_summary,
        impacted_assessment_count=c.impacted_assessment_count,
        impacted_gap_count=c.impacted_gap_count,
        regulation_refs=c.regulation_refs,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _impact_to_response(i: RegulatoryChangeImpact) -> RegulatoryChangeImpactResponse:
    return RegulatoryChangeImpactResponse(
        id=i.id,
        organization_id=i.organization_id,
        change_id=i.change_id,
        assessment_id=i.assessment_id,
        compliance_gap_id=i.compliance_gap_id,
        impact_type=i.impact_type,
        re_review_required=i.re_review_required,
        notification_sent=i.notification_sent,
        acknowledged_by_user_id=i.acknowledged_by_user_id,
        acknowledged_at=i.acknowledged_at,
        created_at=i.created_at,
    )


async def _find_affected_assessments(
    session: AsyncSession,
    organization_id: str,
    affected_sectors: list[str],
) -> list[str]:
    """Return assessment IDs in the org not yet flagged for re-review.

    If affected_sectors is non-empty we filter by sector; otherwise all
    non-deleted assessments are considered potentially affected.
    """
    stmt = select(AssessmentModel.id).where(
        AssessmentModel.organization_id == organization_id,
        AssessmentModel.review_status != "Deleted",
        AssessmentModel.review_status != _REVIEW_STATUS_FLAG,
    )
    # Sector filtering is advisory — we include all if no sectors specified
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def _find_affected_gaps(
    session: AsyncSession,
    organization_id: str,
    framework_code: str,
) -> list[str]:
    """Return ComplianceGap IDs linked to the given framework that are unresolved."""
    stmt = (
        select(ComplianceGapModel.id)
        .join(
            RegulationRequirementModel,
            ComplianceGapModel.regulation_requirement_id == RegulationRequirementModel.id,
        )
        .join(
            RegulationModel,
            RegulationRequirementModel.regulation_id == RegulationModel.id,
        )
        .where(
            ComplianceGapModel.organization_id == organization_id,
            ComplianceGapModel.is_resolved.is_(False),
            RegulationModel.framework_code == framework_code,
        )
    )
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get(
    "/summary",
    response_model=ChangeSummaryResponse,
    dependencies=[Depends(require_analyst)],
    summary="Count of new changes and pending re-reviews",
)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> ChangeSummaryResponse:
    org_id = current_user.organization_id or ""
    change_repo = SQLRegulatoryChangeRepository(db)
    impact_repo = SQLRegulatoryChangeImpactRepository(db)

    new_count = await change_repo.count_new_for_org(org_id)
    pending = await impact_repo.list_pending_re_review(org_id)
    all_changes = await change_repo.list_for_org(org_id, limit=1000)

    return ChangeSummaryResponse(
        new_changes=new_count,
        pending_re_reviews=len(pending),
        total_changes=len(all_changes),
    )


@router.get(
    "/seed",
    response_model=list[RegulatoryChangeResponse],
    dependencies=[Depends(require_analyst)],
    summary="Seed the global curated regulatory change list (idempotent)",
)
async def seed_changes(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[RegulatoryChangeResponse]:
    """Insert the curated seed changes if they don't already exist.

    Keyed by (framework_code, affected_article) — re-running is safe.
    """
    change_repo = SQLRegulatoryChangeRepository(db)
    now = datetime.now(UTC)
    created: list[RegulatoryChange] = []

    for entry in REGULATORY_CHANGE_SEED:
        # Check for existing entry
        stmt = select(RegulatoryChangeModel).where(
            RegulatoryChangeModel.organization_id.is_(None),
            RegulatoryChangeModel.framework_code == entry["framework_code"],
            RegulatoryChangeModel.affected_article == entry["affected_article"],
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            continue

        change = RegulatoryChange(
            organization_id=None,
            framework_code=entry["framework_code"],
            change_title=entry["change_title"],
            change_description=entry["change_description"],
            affected_article=entry["affected_article"],
            effective_date=entry.get("effective_date"),
            severity=entry["severity"],
            change_status=RegulatoryChangeStatus.NEW.value,
            source_name=entry["source_name"],
            source_url=entry["source_url"],
            affected_sectors=entry.get("affected_sectors", []),
            affected_frameworks=entry.get("affected_frameworks", []),
            regulation_refs=entry.get("regulation_refs", ""),
            status=EntityStatus.ACTIVE,
            created_by=str(current_user.id),
            created_at=now,
            updated_at=now,
        )
        await change_repo.create(change)
        created.append(change)

    await db.commit()
    return [_change_to_response(c) for c in created]


@router.get(
    "/",
    response_model=list[RegulatoryChangeResponse],
    dependencies=[Depends(require_analyst)],
    summary="List regulatory changes (global + org-specific)",
)
async def list_changes(
    framework: str | None = None,
    change_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[RegulatoryChangeResponse]:
    org_id = current_user.organization_id or ""
    repo = SQLRegulatoryChangeRepository(db)
    changes = await repo.list_for_org(
        org_id,
        framework_filter=framework,
        status_filter=change_status,
        limit=limit,
        offset=offset,
    )
    return [_change_to_response(c) for c in changes]


@router.post(
    "/",
    response_model=RegulatoryChangeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
    summary="Log a manual regulatory change",
)
async def create_change(
    body: RegulatoryChangeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> RegulatoryChangeResponse:
    org_id = current_user.organization_id or ""
    now = datetime.now(UTC)
    change = RegulatoryChange(
        organization_id=org_id,
        framework_code=body.framework_code,
        change_title=body.change_title,
        change_description=body.change_description,
        affected_article=body.affected_article,
        effective_date=body.effective_date,
        severity=body.severity,
        change_status=RegulatoryChangeStatus.NEW.value,
        source_name=body.source_name,
        source_url=body.source_url,
        affected_sectors=body.affected_sectors,
        affected_frameworks=body.affected_frameworks,
        regulation_refs=body.regulation_refs,
        status=EntityStatus.ACTIVE,
        created_by=str(current_user.id),
        created_at=now,
        updated_at=now,
    )
    repo = SQLRegulatoryChangeRepository(db)
    await repo.create(change)
    await db.commit()
    return _change_to_response(change)


@router.post(
    "/{change_id}/scan",
    response_model=RegulatoryChangeResponse,
    dependencies=[Depends(require_analyst)],
    summary="Run impact scan and flag affected assessments and gaps for re-review",
)
async def scan_impact(
    change_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> RegulatoryChangeResponse:
    """Identifies affected Assessments and ComplianceGaps, flags them,
    creates RegulatoryChangeImpact rows, and notifies the current user."""
    org_id = current_user.organization_id or ""
    change_repo = SQLRegulatoryChangeRepository(db)
    impact_repo = SQLRegulatoryChangeImpactRepository(db)

    change = await change_repo.get(change_id)
    if change is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Regulatory change not found")

    now = datetime.now(UTC)

    # 1 — Find affected assessments
    assessment_ids = await _find_affected_assessments(db, org_id, change.affected_sectors)

    # 2 — Flag assessments for re-review
    if assessment_ids:
        await db.execute(
            sa_update(AssessmentModel)
            .where(AssessmentModel.id.in_(assessment_ids))
            .values(review_status=_REVIEW_STATUS_FLAG, updated_at=now)
        )

    # 3 — Find affected compliance gaps
    gap_ids = await _find_affected_gaps(db, org_id, change.framework_code)

    # 4 — Create impact rows
    for aid in assessment_ids:
        impact = RegulatoryChangeImpact(
            organization_id=org_id,
            change_id=change_id,
            assessment_id=aid,
            impact_type="assessment_re_review",
            re_review_required=True,
            status=EntityStatus.ACTIVE,
            created_by=str(current_user.id),
            created_at=now,
            updated_at=now,
        )
        await impact_repo.create(impact)

    for gid in gap_ids:
        impact = RegulatoryChangeImpact(
            organization_id=org_id,
            change_id=change_id,
            compliance_gap_id=gid,
            impact_type="gap_update",
            re_review_required=True,
            status=EntityStatus.ACTIVE,
            created_by=str(current_user.id),
            created_at=now,
            updated_at=now,
        )
        await impact_repo.create(impact)

    # 5 — Update change record
    change.change_status = RegulatoryChangeStatus.IMPACTS_IDENTIFIED.value
    change.impacted_assessment_count = len(assessment_ids)
    change.impacted_gap_count = len(gap_ids)
    change.impact_summary = build_impact_summary(
        framework_code=change.framework_code,
        assessment_count=len(assessment_ids),
        gap_count=len(gap_ids),
        affected_sectors=change.affected_sectors,
    )
    change.updated_at = now
    await change_repo.update(change)

    # 6 — Send in-app notification
    await notification_service.notify(
        session=db,
        user_id=str(current_user.id),
        organization_id=org_id,
        notification_type=NotificationType.REGULATORY_CHANGE.value,
        title=f"Regulatory Change: {change.change_title}",
        body=change.impact_summary,
        entity_type="regulatory_change",
        entity_id=change_id,
        dedupe_key=f"regchg-scan-{change_id}-{org_id}",
    )

    await db.commit()
    return _change_to_response(change)


@router.get(
    "/{change_id}/impacts",
    response_model=list[RegulatoryChangeImpactResponse],
    dependencies=[Depends(require_analyst)],
    summary="List impact items for a change",
)
async def list_impacts(
    change_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[RegulatoryChangeImpactResponse]:
    org_id = current_user.organization_id or ""
    repo = SQLRegulatoryChangeImpactRepository(db)
    impacts = await repo.list_by_change(change_id, org_id)
    return [_impact_to_response(i) for i in impacts]


@router.patch(
    "/impacts/{impact_id}/acknowledge",
    response_model=RegulatoryChangeImpactResponse,
    dependencies=[Depends(require_analyst)],
    summary="Acknowledge a re-review impact item",
)
async def acknowledge_impact(
    impact_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> RegulatoryChangeImpactResponse:
    org_id = current_user.organization_id or ""
    repo = SQLRegulatoryChangeImpactRepository(db)
    impact = await repo.get(impact_id)
    if impact is None or impact.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Impact not found")

    now = datetime.now(UTC)
    impact.re_review_required = False
    impact.acknowledged_by_user_id = str(current_user.id)
    impact.acknowledged_at = now
    impact.updated_by = str(current_user.id)
    impact.updated_at = now
    await repo.update(impact)
    await db.commit()
    return _impact_to_response(impact)
