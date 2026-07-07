"""Corrective Action Plan (CAP) API (GAP-20).

Endpoints:
  POST   /corrective-action-plans/                     create CAP for a finding
  GET    /corrective-action-plans/                     list CAPs for org
  GET    /corrective-action-plans/kpis                 KPI summary
  GET    /corrective-action-plans/by-finding/{fid}     CAP for a specific finding
  GET    /corrective-action-plans/{id}                 single CAP
  PATCH  /corrective-action-plans/{id}                 update editable fields
  PATCH  /corrective-action-plans/{id}/commit          → COMMITTED
  PATCH  /corrective-action-plans/{id}/start           → IN_PROGRESS
  PATCH  /corrective-action-plans/{id}/submit-evidence → EVIDENCE_SUBMITTED
  PATCH  /corrective-action-plans/{id}/verify          → VERIFIED (analyst only)
  PATCH  /corrective-action-plans/{id}/mark-insufficient → back to IN_PROGRESS
  PATCH  /corrective-action-plans/{id}/close           → CLOSED (analyst only)

Security:
  - organization_id MANDATORY on every DB query
  - Agents MUST NOT call /verify, /close, /mark-insufficient
  - Human analyst/admin required for status progression
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from domain.corrective_action_plan import CorrectiveActionPlan
from domain.enums import EntityStatus
from domain.user import User
from infrastructure.persistence.repositories.corrective_action_plan import SQLCAPRepository
from interfaces.api.deps import get_current_user, get_db, require_analyst

router = APIRouter(prefix="/corrective-action-plans", tags=["corrective-action-plans"])

# ── Schemas ───────────────────────────────────────────────────────────────────


class CAPResponse(BaseModel):
    id: str
    finding_id: str
    organization_id: str
    title: str
    description: str
    responsible_party: str
    deadline: date | None
    cap_status: str
    evidence_note: str
    evidence_file_url: str | None
    evidence_submitted_at: datetime | None
    verification_note: str
    verified_by_user_id: str | None
    verified_at: datetime | None
    insufficient_reason: str
    closed_at: datetime | None
    closed_by_user_id: str | None
    is_overdue: bool
    overdue_days: int
    created_at: datetime
    updated_at: datetime


class CreateCAPRequest(BaseModel):
    finding_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=5)
    responsible_party: str = Field(default="", max_length=255)
    deadline: date | None = None


class UpdateCAPRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=500)
    description: str | None = None
    responsible_party: str | None = Field(default=None, max_length=255)
    deadline: date | None = None


class SubmitEvidenceRequest(BaseModel):
    evidence_note: str = Field(..., min_length=10)
    evidence_file_url: str | None = None


class VerifyRequest(BaseModel):
    verification_note: str = Field(..., min_length=5)


class InsufficientRequest(BaseModel):
    insufficient_reason: str = Field(..., min_length=10)


class KPIResponse(BaseModel):
    total: int
    open: int
    overdue: int
    verified: int
    closed: int
    completion_rate: float


# ── Helper ────────────────────────────────────────────────────────────────────


def _to_response(cap: CorrectiveActionPlan) -> CAPResponse:
    return CAPResponse(
        id=cap.id,
        finding_id=cap.finding_id,
        organization_id=cap.organization_id,
        title=cap.title,
        description=cap.description,
        responsible_party=cap.responsible_party,
        deadline=cap.deadline,
        cap_status=cap.cap_status,
        evidence_note=cap.evidence_note,
        evidence_file_url=cap.evidence_file_url,
        evidence_submitted_at=cap.evidence_submitted_at,
        verification_note=cap.verification_note,
        verified_by_user_id=cap.verified_by_user_id,
        verified_at=cap.verified_at,
        insufficient_reason=cap.insufficient_reason,
        closed_at=cap.closed_at,
        closed_by_user_id=cap.closed_by_user_id,
        is_overdue=cap.is_overdue,
        overdue_days=cap.overdue_days,
        created_at=cap.created_at,
        updated_at=cap.updated_at,
    )


def _require_status(cap: CorrectiveActionPlan, allowed: list[str], action: str) -> None:
    if cap.cap_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot '{action}' CAP with status '{cap.cap_status}'. "
            f"Allowed: {', '.join(allowed)}",
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=CAPResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_analyst)],
)
async def create_cap(
    body: CreateCAPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CAPResponse:
    """Create a CAP for a finding. At most one CAP per finding."""
    org_id = str(current_user.organization_id)
    repo = SQLCAPRepository(db)

    # Enforce one-CAP-per-finding
    existing = await repo.get_by_finding(body.finding_id, org_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A CAP already exists for finding {body.finding_id} (id: {existing.id})",
        )

    now = datetime.now(UTC)
    cap = CorrectiveActionPlan(
        finding_id=body.finding_id,
        organization_id=org_id,
        title=body.title,
        description=body.description,
        responsible_party=body.responsible_party,
        deadline=body.deadline,
        cap_status="DRAFT",
        status=EntityStatus.ACTIVE,
        created_by=str(current_user.id),
        created_at=now,
        updated_at=now,
    )
    saved = await repo.save(cap)
    await db.commit()
    return _to_response(saved)


@router.get(
    "/kpis",
    response_model=KPIResponse,
    dependencies=[Depends(require_analyst)],
)
async def get_kpis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KPIResponse:
    repo = SQLCAPRepository(db)
    data = await repo.kpis(str(current_user.organization_id))
    return KPIResponse(**data)


@router.get(
    "/by-finding/{finding_id}",
    response_model=CAPResponse | None,
    dependencies=[Depends(require_analyst)],
)
async def get_cap_by_finding(
    finding_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CAPResponse | None:
    repo = SQLCAPRepository(db)
    cap = await repo.get_by_finding(finding_id, str(current_user.organization_id))
    return _to_response(cap) if cap else None


@router.get(
    "/",
    response_model=list[CAPResponse],
    dependencies=[Depends(require_analyst)],
)
async def list_caps(
    cap_status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CAPResponse]:
    repo = SQLCAPRepository(db)
    caps = await repo.list_for_org(
        str(current_user.organization_id),
        cap_status=cap_status,
        limit=limit,
    )
    return [_to_response(c) for c in caps]


@router.get(
    "/{cap_id}",
    response_model=CAPResponse,
    dependencies=[Depends(require_analyst)],
)
async def get_cap(
    cap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CAPResponse:
    repo = SQLCAPRepository(db)
    cap = await repo.get_by_id(cap_id, str(current_user.organization_id))
    if cap is None:
        raise HTTPException(status_code=404, detail="CAP not found")
    return _to_response(cap)


@router.patch(
    "/{cap_id}",
    response_model=CAPResponse,
    dependencies=[Depends(require_analyst)],
)
async def update_cap(
    cap_id: str,
    body: UpdateCAPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CAPResponse:
    repo = SQLCAPRepository(db)
    cap = await repo.get_by_id(cap_id, str(current_user.organization_id))
    if cap is None:
        raise HTTPException(status_code=404, detail="CAP not found")
    if cap.cap_status == "CLOSED":
        raise HTTPException(status_code=400, detail="Cannot edit a CLOSED CAP")

    if body.title is not None:
        cap.title = body.title
    if body.description is not None:
        cap.description = body.description
    if body.responsible_party is not None:
        cap.responsible_party = body.responsible_party
    if body.deadline is not None:
        cap.deadline = body.deadline
    cap.updated_at = datetime.now(UTC)
    saved = await repo.save(cap)
    await db.commit()
    return _to_response(saved)


@router.patch(
    "/{cap_id}/commit", response_model=CAPResponse, dependencies=[Depends(require_analyst)]
)
async def commit_cap(
    cap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CAPResponse:
    """Supplier/analyst commits to the CAP plan → COMMITTED."""
    repo = SQLCAPRepository(db)
    cap = await repo.get_by_id(cap_id, str(current_user.organization_id))
    if cap is None:
        raise HTTPException(status_code=404, detail="CAP not found")
    _require_status(cap, ["DRAFT"], "commit")
    cap.cap_status = "COMMITTED"
    cap.updated_at = datetime.now(UTC)
    saved = await repo.save(cap)
    await db.commit()
    return _to_response(saved)


@router.patch(
    "/{cap_id}/start", response_model=CAPResponse, dependencies=[Depends(require_analyst)]
)
async def start_cap(
    cap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CAPResponse:
    """Mark work as started → IN_PROGRESS."""
    repo = SQLCAPRepository(db)
    cap = await repo.get_by_id(cap_id, str(current_user.organization_id))
    if cap is None:
        raise HTTPException(status_code=404, detail="CAP not found")
    _require_status(cap, ["COMMITTED"], "start")
    cap.cap_status = "IN_PROGRESS"
    cap.updated_at = datetime.now(UTC)
    saved = await repo.save(cap)
    await db.commit()
    return _to_response(saved)


@router.patch(
    "/{cap_id}/submit-evidence", response_model=CAPResponse, dependencies=[Depends(require_analyst)]
)
async def submit_evidence(
    cap_id: str,
    body: SubmitEvidenceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CAPResponse:
    """Supplier submits evidence → EVIDENCE_SUBMITTED."""
    repo = SQLCAPRepository(db)
    cap = await repo.get_by_id(cap_id, str(current_user.organization_id))
    if cap is None:
        raise HTTPException(status_code=404, detail="CAP not found")
    _require_status(cap, ["COMMITTED", "IN_PROGRESS"], "submit-evidence")
    now = datetime.now(UTC)
    cap.cap_status = "EVIDENCE_SUBMITTED"
    cap.evidence_note = body.evidence_note
    cap.evidence_file_url = body.evidence_file_url
    cap.evidence_submitted_at = now
    cap.insufficient_reason = ""
    cap.updated_at = now
    saved = await repo.save(cap)
    await db.commit()
    return _to_response(saved)


@router.patch(
    "/{cap_id}/verify", response_model=CAPResponse, dependencies=[Depends(require_analyst)]
)
async def verify_cap(
    cap_id: str,
    body: VerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CAPResponse:
    """Human analyst verifies evidence → VERIFIED.

    AI agents MUST NOT call this endpoint.
    """
    repo = SQLCAPRepository(db)
    cap = await repo.get_by_id(cap_id, str(current_user.organization_id))
    if cap is None:
        raise HTTPException(status_code=404, detail="CAP not found")
    _require_status(cap, ["EVIDENCE_SUBMITTED"], "verify")
    now = datetime.now(UTC)
    cap.cap_status = "VERIFIED"
    cap.verification_note = body.verification_note
    cap.verified_by_user_id = str(current_user.id)
    cap.verified_at = now
    cap.updated_at = now
    saved = await repo.save(cap)
    await db.commit()
    return _to_response(saved)


@router.patch(
    "/{cap_id}/mark-insufficient",
    response_model=CAPResponse,
    dependencies=[Depends(require_analyst)],
)
async def mark_insufficient(
    cap_id: str,
    body: InsufficientRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CAPResponse:
    """Analyst marks submitted evidence as insufficient → back to IN_PROGRESS.

    AI agents MUST NOT call this endpoint.
    """
    repo = SQLCAPRepository(db)
    cap = await repo.get_by_id(cap_id, str(current_user.organization_id))
    if cap is None:
        raise HTTPException(status_code=404, detail="CAP not found")
    _require_status(cap, ["EVIDENCE_SUBMITTED"], "mark-insufficient")
    now = datetime.now(UTC)
    cap.cap_status = "IN_PROGRESS"
    cap.insufficient_reason = body.insufficient_reason
    cap.evidence_submitted_at = None
    cap.updated_at = now
    saved = await repo.save(cap)
    await db.commit()
    return _to_response(saved)


@router.patch(
    "/{cap_id}/close", response_model=CAPResponse, dependencies=[Depends(require_analyst)]
)
async def close_cap(
    cap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CAPResponse:
    """Human analyst closes a verified (or overdue) CAP → CLOSED.

    AI agents MUST NOT call this endpoint.
    """
    repo = SQLCAPRepository(db)
    cap = await repo.get_by_id(cap_id, str(current_user.organization_id))
    if cap is None:
        raise HTTPException(status_code=404, detail="CAP not found")
    _require_status(cap, ["VERIFIED", "IN_PROGRESS", "COMMITTED"], "close")
    now = datetime.now(UTC)
    cap.cap_status = "CLOSED"
    cap.closed_at = now
    cap.closed_by_user_id = str(current_user.id)
    cap.updated_at = now
    saved = await repo.save(cap)
    await db.commit()
    return _to_response(saved)
