"""CSDDD-002 — DD-Governance & Policy Review API (Art. 7).

Endpoints (authenticated):
  GET    /governance/policies/                     list all policy versions
  POST   /governance/policies/                     create draft
  GET    /governance/policies/active               current active policy
  GET    /governance/policies/{id}                 single policy
  PATCH  /governance/policies/{id}                 update draft
  POST   /governance/policies/{id}/activate        → ACTIVE (analyst only)
  POST   /governance/policies/{id}/clone           clone as new draft for review
  POST   /governance/policies/{id}/archive         → ARCHIVED (analyst only)

  GET    /governance/codes-of-conduct/             list CoC versions
  POST   /governance/codes-of-conduct/             create CoC
  GET    /governance/codes-of-conduct/active       current active CoC
  POST   /governance/suppliers/{sid}/coc-acceptance  supplier accepts CoC
  GET    /governance/coc/{coc_id}/acceptances      list acceptances (analyst only)

  GET    /governance/calendar                      aggregated governance deadlines
  GET    /governance/review-status                 policy review status summary

Public (no auth):
  GET    /governance/public/{token}                publicly accessible policy

Security:
  - organization_id MANDATORY on all queries
  - ip_hash stored, never raw IP (DSGVO)
  - Activate/Archive require analyst role
"""

from __future__ import annotations

import secrets
from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from domain.dd_policy import CoCAcceptance, CodeOfConduct, DDPolicy
from domain.enums import DDPolicyStatus
from infrastructure.persistence.repositories.dd_policy import (
    SQLCoCAcceptanceRepository,
    SQLCodeOfConductRepository,
    SQLDDPolicyRepository,
)
from interfaces.api.deps import get_current_user, get_db, require_analyst
from domain.user import User

# ── Schemas ───────────────────────────────────────────────────────────────────


class PolicyCreate(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    content_text: str = Field(default="", max_length=50_000)
    approved_by: str = Field(default="", max_length=255)
    approved_role: str = Field(default="", max_length=255)
    valid_from: date | None = None
    is_public: bool = False


class PolicyUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    content_text: str | None = Field(default=None, max_length=50_000)
    approved_by: str | None = Field(default=None, max_length=255)
    approved_role: str | None = Field(default=None, max_length=255)
    valid_from: date | None = None
    is_public: bool | None = None


class PolicyResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    policy_status: str
    content_text: str
    file_url: str | None
    approved_by: str
    approved_role: str
    valid_from: date | None
    published_at: datetime | None
    next_review_due: date | None
    is_public: bool
    public_token: str | None
    policy_version: int
    parent_policy_id: str | None
    review_status: str
    created_at: datetime
    updated_at: datetime


class CoCCreate(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    content_text: str = Field(default="", max_length=50_000)
    valid_from: date | None = None
    acceptance_validity_months: int = Field(default=24, ge=6, le=48)
    linked_policy_id: str | None = None


class CoCResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    content_text: str
    coc_version: int
    valid_from: date | None
    acceptance_validity_months: int
    is_active: bool
    linked_policy_id: str | None
    created_at: datetime
    updated_at: datetime


class CoCAcceptanceCreate(BaseModel):
    accepted_by_name: str = Field(min_length=2, max_length=500)
    coc_version: int


class CoCAcceptanceResponse(BaseModel):
    id: str
    supplier_id: str
    coc_id: str
    coc_version: int
    accepted_at: datetime | None
    accepted_by_name: str
    expires_at: date | None


class GovernanceEvent(BaseModel):
    event_type: str
    title: str
    due_date: date | None
    status: str
    detail: str
    reference_id: str


class GovernanceCalendarResponse(BaseModel):
    events: list[GovernanceEvent]


class ReviewStatusResponse(BaseModel):
    has_active_policy: bool
    review_status: str
    next_review_due: date | None
    days_until_review: int | None
    policy_version: int | None
    policy_title: str | None


# ── Dependency helpers ────────────────────────────────────────────────────────


async def get_policy_repo(session: AsyncSession = Depends(get_db)) -> SQLDDPolicyRepository:
    return SQLDDPolicyRepository(session)


async def get_coc_repo(session: AsyncSession = Depends(get_db)) -> SQLCodeOfConductRepository:
    return SQLCodeOfConductRepository(session)


async def get_acceptance_repo(session: AsyncSession = Depends(get_db)) -> SQLCoCAcceptanceRepository:
    return SQLCoCAcceptanceRepository(session)


def _policy_response(p: DDPolicy) -> PolicyResponse:
    return PolicyResponse(
        id=p.id,
        organization_id=p.organization_id,
        title=p.title,
        policy_status=p.policy_status.value if hasattr(p.policy_status, "value") else p.policy_status,
        content_text=p.content_text,
        file_url=p.file_url,
        approved_by=p.approved_by,
        approved_role=p.approved_role,
        valid_from=p.valid_from,
        published_at=p.published_at,
        next_review_due=p.next_review_due,
        is_public=p.is_public,
        public_token=p.public_token if p.is_public else None,
        policy_version=p.policy_version,
        parent_policy_id=p.parent_policy_id,
        review_status=p.review_status,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _coc_response(c: CodeOfConduct) -> CoCResponse:
    return CoCResponse(
        id=c.id,
        organization_id=c.organization_id,
        title=c.title,
        content_text=c.content_text,
        coc_version=c.coc_version,
        valid_from=c.valid_from,
        acceptance_validity_months=c.acceptance_validity_months,
        is_active=c.is_active,
        linked_policy_id=c.linked_policy_id,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


# ── Routers ───────────────────────────────────────────────────────────────────

router = APIRouter(
    prefix="/governance",
    tags=["governance"],
    dependencies=[Depends(get_current_user)],
)

public_router = APIRouter(prefix="/governance", tags=["governance-public"])

# ── DD-Policy ─────────────────────────────────────────────────────────────────


@router.get("/policies/", response_model=list[PolicyResponse])
async def list_policies(
    current_user: User = Depends(get_current_user),
    repo: SQLDDPolicyRepository = Depends(get_policy_repo),
) -> list[PolicyResponse]:
    if not current_user.organization_id:
        return []
    items = await repo.list_by_org(current_user.organization_id)
    return [_policy_response(p) for p in items]


@router.get("/policies/active", response_model=PolicyResponse | None)
async def get_active_policy(
    current_user: User = Depends(get_current_user),
    repo: SQLDDPolicyRepository = Depends(get_policy_repo),
) -> PolicyResponse | None:
    if not current_user.organization_id:
        return None
    p = await repo.get_active(current_user.organization_id)
    return _policy_response(p) if p else None


@router.post("/policies/", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    body: PolicyCreate,
    current_user: User = Depends(get_current_user),
    repo: SQLDDPolicyRepository = Depends(get_policy_repo),
) -> PolicyResponse:
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organisation")
    # Auto-increment version
    existing = await repo.list_by_org(current_user.organization_id)
    next_version = max((p.policy_version for p in existing), default=0) + 1
    token = secrets.token_urlsafe(32) if body.is_public else None
    p = DDPolicy(
        organization_id=current_user.organization_id,
        title=body.title,
        content_text=body.content_text,
        approved_by=body.approved_by,
        approved_role=body.approved_role,
        valid_from=body.valid_from,
        is_public=body.is_public,
        public_token=token,
        policy_version=next_version,
        created_by=current_user.id,
    )
    saved = await repo.save(p)
    return _policy_response(saved)


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLDDPolicyRepository = Depends(get_policy_repo),
) -> PolicyResponse:
    p = await repo.get_by_id(policy_id)
    if not p or p.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    return _policy_response(p)


@router.patch("/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: str,
    body: PolicyUpdate,
    current_user: User = Depends(get_current_user),
    repo: SQLDDPolicyRepository = Depends(get_policy_repo),
) -> PolicyResponse:
    p = await repo.get_by_id(policy_id)
    if not p or p.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    if p.policy_status == DDPolicyStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Cannot edit an archived policy")
    if body.title is not None:
        p.title = body.title
    if body.content_text is not None:
        p.content_text = body.content_text
    if body.approved_by is not None:
        p.approved_by = body.approved_by
    if body.approved_role is not None:
        p.approved_role = body.approved_role
    if body.valid_from is not None:
        p.valid_from = body.valid_from
    if body.is_public is not None:
        p.is_public = body.is_public
        if body.is_public and not p.public_token:
            p.public_token = secrets.token_urlsafe(32)
    p.updated_by = current_user.id
    p.updated_at = datetime.now(UTC)
    saved = await repo.save(p)
    return _policy_response(saved)


@router.post(
    "/policies/{policy_id}/activate",
    response_model=PolicyResponse,
    dependencies=[Depends(require_analyst)],
)
async def activate_policy(
    policy_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLDDPolicyRepository = Depends(get_policy_repo),
) -> PolicyResponse:
    p = await repo.get_by_id(policy_id)
    if not p or p.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    if p.policy_status == DDPolicyStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Policy is already active")

    # Archive currently active policy
    current = await repo.get_active(current_user.organization_id)
    if current:
        current.policy_status = DDPolicyStatus.ARCHIVED
        current.updated_by = current_user.id
        current.updated_at = datetime.now(UTC)
        await repo.save(current)

    p.activate()
    p.published_at = datetime.now(UTC)
    p.updated_by = current_user.id
    p.updated_at = datetime.now(UTC)
    saved = await repo.save(p)
    return _policy_response(saved)


@router.post(
    "/policies/{policy_id}/clone",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def clone_policy_for_review(
    policy_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLDDPolicyRepository = Depends(get_policy_repo),
) -> PolicyResponse:
    """Clone an active policy as a new draft for the 24-month review cycle."""
    p = await repo.get_by_id(policy_id)
    if not p or p.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    existing = await repo.list_by_org(current_user.organization_id)
    next_version = max((x.policy_version for x in existing), default=0) + 1
    clone = DDPolicy(
        organization_id=p.organization_id,
        title=f"{p.title} (Review v{next_version})",
        content_text=p.content_text,
        approved_by="",
        approved_role="",
        is_public=False,
        policy_version=next_version,
        parent_policy_id=p.id,
        created_by=current_user.id,
    )
    saved = await repo.save(clone)
    return _policy_response(saved)


@router.post(
    "/policies/{policy_id}/archive",
    response_model=PolicyResponse,
    dependencies=[Depends(require_analyst)],
)
async def archive_policy(
    policy_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLDDPolicyRepository = Depends(get_policy_repo),
) -> PolicyResponse:
    p = await repo.get_by_id(policy_id)
    if not p or p.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    p.policy_status = DDPolicyStatus.ARCHIVED
    p.updated_by = current_user.id
    p.updated_at = datetime.now(UTC)
    saved = await repo.save(p)
    return _policy_response(saved)


# ── Code of Conduct ───────────────────────────────────────────────────────────


@router.get("/codes-of-conduct/", response_model=list[CoCResponse])
async def list_cocs(
    current_user: User = Depends(get_current_user),
    repo: SQLCodeOfConductRepository = Depends(get_coc_repo),
) -> list[CoCResponse]:
    if not current_user.organization_id:
        return []
    items = await repo.list_by_org(current_user.organization_id)
    return [_coc_response(c) for c in items]


@router.get("/codes-of-conduct/active", response_model=CoCResponse | None)
async def get_active_coc(
    current_user: User = Depends(get_current_user),
    repo: SQLCodeOfConductRepository = Depends(get_coc_repo),
) -> CoCResponse | None:
    if not current_user.organization_id:
        return None
    c = await repo.get_active(current_user.organization_id)
    return _coc_response(c) if c else None


@router.post("/codes-of-conduct/", response_model=CoCResponse, status_code=status.HTTP_201_CREATED)
async def create_coc(
    body: CoCCreate,
    current_user: User = Depends(get_current_user),
    repo: SQLCodeOfConductRepository = Depends(get_coc_repo),
) -> CoCResponse:
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organisation")
    existing = await repo.list_by_org(current_user.organization_id)
    next_version = max((c.coc_version for c in existing), default=0) + 1
    # deactivate current
    for old in existing:
        if old.is_active:
            old.is_active = False
            old.updated_at = datetime.now(UTC)
            await repo.save(old)
    c = CodeOfConduct(
        organization_id=current_user.organization_id,
        title=body.title,
        content_text=body.content_text,
        valid_from=body.valid_from,
        acceptance_validity_months=body.acceptance_validity_months,
        linked_policy_id=body.linked_policy_id,
        coc_version=next_version,
        is_active=True,
        created_by=current_user.id,
    )
    saved = await repo.save(c)
    return _coc_response(saved)


@router.post("/suppliers/{supplier_id}/coc-acceptance", status_code=status.HTTP_201_CREATED)
async def supplier_accept_coc(
    supplier_id: str,
    body: CoCAcceptanceCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    coc_repo: SQLCodeOfConductRepository = Depends(get_coc_repo),
    acceptance_repo: SQLCoCAcceptanceRepository = Depends(get_acceptance_repo),
) -> dict[str, str]:
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organisation")
    coc = await coc_repo.get_active(current_user.organization_id)
    if not coc:
        raise HTTPException(status_code=404, detail="No active Code of Conduct found")
    client_ip = request.client.host if request.client else "unknown"
    now = datetime.now(UTC)
    from dateutil.relativedelta import relativedelta
    expires = (now + relativedelta(months=coc.acceptance_validity_months)).date()
    acc = CoCAcceptance(
        organization_id=current_user.organization_id,
        coc_id=coc.id,
        supplier_id=supplier_id,
        coc_version=body.coc_version,
        accepted_at=now,
        accepted_by_name=body.accepted_by_name,
        ip_hash=CoCAcceptance.hash_ip(client_ip),
        expires_at=expires,
        created_by=current_user.id,
    )
    saved = await acceptance_repo.save(acc)
    return {"acceptance_id": saved.id, "expires_at": expires.isoformat()}


@router.get(
    "/coc/{coc_id}/acceptances",
    response_model=list[CoCAcceptanceResponse],
    dependencies=[Depends(require_analyst)],
)
async def list_coc_acceptances(
    coc_id: str,
    current_user: User = Depends(get_current_user),
    acceptance_repo: SQLCoCAcceptanceRepository = Depends(get_acceptance_repo),
) -> list[CoCAcceptanceResponse]:
    if not current_user.organization_id:
        return []
    items = await acceptance_repo.list_by_coc(coc_id, current_user.organization_id)
    return [
        CoCAcceptanceResponse(
            id=a.id,
            supplier_id=a.supplier_id,
            coc_id=a.coc_id,
            coc_version=a.coc_version,
            accepted_at=a.accepted_at,
            accepted_by_name=a.accepted_by_name,
            expires_at=a.expires_at,
        )
        for a in items
    ]


# ── Governance Calendar & Review Status ───────────────────────────────────────


@router.get("/review-status", response_model=ReviewStatusResponse)
async def get_review_status(
    current_user: User = Depends(get_current_user),
    repo: SQLDDPolicyRepository = Depends(get_policy_repo),
) -> ReviewStatusResponse:
    if not current_user.organization_id:
        return ReviewStatusResponse(
            has_active_policy=False, review_status="no_policy",
            next_review_due=None, days_until_review=None,
            policy_version=None, policy_title=None,
        )
    p = await repo.get_active(current_user.organization_id)
    if not p:
        return ReviewStatusResponse(
            has_active_policy=False, review_status="no_policy",
            next_review_due=None, days_until_review=None,
            policy_version=None, policy_title=None,
        )
    days = None
    if p.next_review_due:
        days = (p.next_review_due - datetime.now(UTC).date()).days
    return ReviewStatusResponse(
        has_active_policy=True,
        review_status=p.review_status,
        next_review_due=p.next_review_due,
        days_until_review=days,
        policy_version=p.policy_version,
        policy_title=p.title,
    )


@router.get("/calendar", response_model=GovernanceCalendarResponse)
async def governance_calendar(
    current_user: User = Depends(get_current_user),
    policy_repo: SQLDDPolicyRepository = Depends(get_policy_repo),
    coc_repo: SQLCodeOfConductRepository = Depends(get_coc_repo),
) -> GovernanceCalendarResponse:
    if not current_user.organization_id:
        return GovernanceCalendarResponse(events=[])

    events: list[GovernanceEvent] = []
    today = datetime.now(UTC).date()

    # Policy review deadlines
    policies = await policy_repo.list_by_org(current_user.organization_id)
    for p in policies:
        if p.policy_status == DDPolicyStatus.ACTIVE and p.next_review_due:
            days = (p.next_review_due - today).days
            evt_status = "overdue" if days < 0 else ("due_soon" if days <= 60 else "upcoming")
            events.append(GovernanceEvent(
                event_type="policy_review",
                title=f"DD-Politik Review: {p.title}",
                due_date=p.next_review_due,
                status=evt_status,
                detail=f"Version {p.policy_version} — fällig in {days} Tagen" if days >= 0 else f"Überfällig seit {abs(days)} Tagen",
                reference_id=p.id,
            ))

    # Sort by due_date
    events.sort(key=lambda e: e.due_date or date.max)
    return GovernanceCalendarResponse(events=events)


# ── Public policy endpoint (no auth) ─────────────────────────────────────────


@public_router.get("/public/{token}")
async def get_public_policy(
    token: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    repo = SQLDDPolicyRepository(session)
    p = await repo.get_by_public_token(token)
    if not p:
        raise HTTPException(status_code=404, detail="Policy not found or not publicly available")
    return {
        "title": p.title,
        "content_text": p.content_text,
        "valid_from": p.valid_from.isoformat() if p.valid_from else None,
        "published_at": p.published_at.isoformat() if p.published_at else None,
        "policy_version": p.policy_version,
        "approved_by": p.approved_by,
        "approved_role": p.approved_role,
    }
