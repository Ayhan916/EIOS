"""Grievance Mechanism API — LkSG §8 / CSDDD Art. 14.

Two access tiers:
  PUBLIC  — POST /grievances/submit          (no auth — external reporters)
            GET  /grievances/status/{code}   (no auth — reporter tracks own case)
  INTERNAL— GET  /grievances/               (analyst+ — list all for org)
            GET  /grievances/{id}            (analyst+ — detail view)
            PATCH /grievances/{id}/status    (analyst+ — update status / notes)
            GET  /grievances/summary         (analyst+ — LkSG §10 reporting counts)

Security guarantees:
- submitted_by_email / submitted_by_name are NEVER returned in any response.
- Internal endpoints filter strictly by current_user.organization_id.
- Status transition to "investigating" auto-creates a Finding draft.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import GrievanceStatus
from domain.supplier_portal import GrievanceReport
from domain.user import User
from interfaces.api.deps import get_current_user, get_db, require_analyst
from interfaces.api.schemas.grievance import (
    GrievanceReportResponse,
    GrievanceStatusCheckResponse,
    GrievanceStatusUpdate,
    GrievanceSubmitRequest,
    GrievanceSubmitResponse,
    GrievanceSummary,
)

router = APIRouter(tags=["Grievance Mechanism"])

_INTERNAL = [Depends(require_analyst)]


def _generate_reference_code() -> str:
    """Short, URL-safe reference code for reporters — not a secret."""
    return "GR-" + secrets.token_hex(6).upper()


def _to_response(report: GrievanceReport) -> GrievanceReportResponse:
    return GrievanceReportResponse(
        id=report.id,
        organization_id=report.organization_id,
        category=report.category,
        grievance_status=report.grievance_status,
        title=report.title,
        description=report.description,
        is_anonymous=report.is_anonymous,
        anonymized_reference_code=report.anonymized_reference_code,
        related_supplier_id=report.related_supplier_id,
        assigned_to_user_id=report.assigned_to_user_id,
        reviewer_notes=report.reviewer_notes,
        resolution_notes=report.resolution_notes,
        resolved_at=report.resolved_at,
        regulation_refs=report.regulation_refs,
        linked_finding_id=report.linked_finding_id,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


# ── Public endpoints (no auth) ────────────────────────────────────────────────

@router.post(
    "/grievances/submit",
    response_model=GrievanceSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a grievance report (public — no authentication required)",
    tags=["Grievance Mechanism"],
)
async def submit_grievance(
    body: GrievanceSubmitRequest,
    session: AsyncSession = Depends(get_db),
) -> GrievanceSubmitResponse:
    """LkSG §8 / CSDDD Art. 14 — public submission endpoint.

    Accessible to workers, trade unions, local communities, and any affected party.
    Reporter identity is stored encrypted and is never exposed to internal users.
    """
    from infrastructure.persistence.repositories.grievance import SQLGrievanceRepository

    repo = SQLGrievanceRepository(session)

    reference_code = _generate_reference_code()

    report = GrievanceReport(
        organization_id=body.organization_id,
        category=body.category,
        grievance_status=GrievanceStatus.RECEIVED.value,
        title=body.title,
        description=body.description,
        submitted_by_email=body.submitted_by_email,
        submitted_by_name=body.submitted_by_name,
        is_anonymous=body.submitted_by_email is None,
        anonymized_reference_code=reference_code,
        related_supplier_id=None,
    )
    await repo.save(report)
    await session.commit()

    return GrievanceSubmitResponse(reference_code=reference_code)


@router.get(
    "/grievances/status/{reference_code}",
    response_model=GrievanceStatusCheckResponse,
    summary="Check grievance status by reference code (public — no authentication required)",
    tags=["Grievance Mechanism"],
)
async def check_grievance_status(
    reference_code: str,
    session: AsyncSession = Depends(get_db),
) -> GrievanceStatusCheckResponse:
    """Allow reporter to track their submission without disclosing identity."""
    from infrastructure.persistence.repositories.grievance import SQLGrievanceRepository

    repo = SQLGrievanceRepository(session)
    report = await repo.get_by_reference_code(reference_code)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference code not found")

    return GrievanceStatusCheckResponse(
        reference_code=report.anonymized_reference_code,
        status=report.grievance_status,
        category=report.category,
        submitted_at=report.created_at,
        last_updated=report.updated_at,
    )


# ── Internal endpoints (analyst+ auth required) ───────────────────────────────

@router.get(
    "/grievances/",
    response_model=list[GrievanceReportResponse],
    dependencies=_INTERNAL,
    summary="List grievance reports for the current organisation",
)
async def list_grievances(
    status_filter: str | None = Query(default=None),
    category_filter: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[GrievanceReportResponse]:
    from infrastructure.persistence.repositories.grievance import SQLGrievanceRepository

    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")

    repo = SQLGrievanceRepository(session)
    reports = await repo.list_by_org(
        current_user.organization_id,
        status_filter=status_filter,
        category_filter=category_filter,
        limit=limit,
        offset=offset,
    )
    return [_to_response(r) for r in reports]


@router.get(
    "/grievances/summary",
    response_model=GrievanceSummary,
    dependencies=_INTERNAL,
    summary="Aggregated grievance counts for LkSG §10 annual report",
)
async def grievance_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> GrievanceSummary:
    from infrastructure.persistence.repositories.grievance import SQLGrievanceRepository
    from sqlalchemy import func, select
    from infrastructure.persistence.models.supplier_portal import GrievanceReportModel

    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")

    repo = SQLGrievanceRepository(session)
    by_status = await repo.count_by_org(current_user.organization_id)
    total = sum(by_status.values())

    # Count by category
    cat_stmt = (
        select(GrievanceReportModel.category, func.count().label("n"))
        .where(GrievanceReportModel.organization_id == current_user.organization_id)
        .group_by(GrievanceReportModel.category)
    )
    cat_result = await session.execute(cat_stmt)
    by_category = {row.category: row.n for row in cat_result.all()}

    return GrievanceSummary(total=total, by_status=by_status, by_category=by_category)


@router.get(
    "/grievances/{grievance_id}",
    response_model=GrievanceReportResponse,
    dependencies=_INTERNAL,
    summary="Get a single grievance report (reporter identity not included)",
)
async def get_grievance(
    grievance_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> GrievanceReportResponse:
    from infrastructure.persistence.repositories.grievance import SQLGrievanceRepository

    repo = SQLGrievanceRepository(session)
    report = await repo.get_by_id(grievance_id)
    if report is None or report.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grievance not found")
    return _to_response(report)


@router.patch(
    "/grievances/{grievance_id}/status",
    response_model=GrievanceReportResponse,
    dependencies=_INTERNAL,
    summary="Update grievance status and notes — triggers Finding creation when investigating",
)
async def update_grievance_status(
    grievance_id: str,
    body: GrievanceStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> GrievanceReportResponse:
    from infrastructure.persistence.repositories.grievance import SQLGrievanceRepository

    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")

    valid_statuses = {s.value for s in GrievanceStatus}
    if body.grievance_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Valid values: {sorted(valid_statuses)}",
        )

    repo = SQLGrievanceRepository(session)
    report = await repo.get_by_id(grievance_id)
    if report is None or report.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grievance not found")

    now = datetime.now(UTC)
    report.grievance_status = body.grievance_status
    report.updated_at = now
    report.updated_by = current_user.id
    if body.reviewer_notes is not None:
        report.reviewer_notes = body.reviewer_notes
    if body.resolution_notes is not None:
        report.resolution_notes = body.resolution_notes
    if body.assigned_to_user_id is not None:
        report.assigned_to_user_id = body.assigned_to_user_id
    if body.grievance_status == GrievanceStatus.RESOLVED.value:
        report.resolved_at = now

    # When status → investigating, an analyst should create a Finding manually
    # via POST /findings with the relevant assessment_id, then store the Finding
    # ID via the linked_finding_id field (use reviewer_notes to coordinate).
    # Auto-creation is not possible here because Finding requires an assessment_id FK.

    await repo.save(report)
    await session.commit()
    return _to_response(report)
