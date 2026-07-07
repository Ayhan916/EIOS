"""CSDDD-013 — Board Sign-off Trail API (Art. 22).

Endpoints (authenticated):
  GET    /board-signoff/dashboard             KPI summary
  GET    /board-signoff/                      list sign-off requests
  POST   /board-signoff/                      create sign-off request
  GET    /board-signoff/{id}                  get request
  POST   /board-signoff/{id}/approve          HUMAN BOARD MEMBER/ADMIN ONLY
  POST   /board-signoff/{id}/reject           HUMAN BOARD MEMBER/ADMIN ONLY
  POST   /board-signoff/{id}/withdraw         withdraw pending request
  GET    /board-signoff/{id}/decisions        audit trail of decisions

Security:
  - organization_id MANDATORY
  - approve / reject → require_analyst (board member or admin role)
  - KI-Agenten DÜRFEN approve/reject NIEMALS aufrufen (Art. 22 explizit menschliche Verantwortung)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from domain.user import User
from infrastructure.persistence.repositories.board_signoff import SQLBoardSignoffRepository
from interfaces.api.deps import get_current_user, get_sync_db, require_analyst

router = APIRouter(prefix="/board-signoff", tags=["board-signoff"])

VALID_TYPES = {
    "dd_policy",
    "dd_strategy",
    "annual_report",
    "scoping_study",
    "cap_plan",
    "remedy_settlement",
    "other",
}
VALID_ROLES = {
    "ceo",
    "cfo",
    "cso",
    "board_member",
    "supervisory_board",
    "compliance_officer",
    "other",
}


# ── Schemas ───────────────────────────────────────────────────────────────────


class SignoffRequestCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    signoff_type: str = Field(default="other")
    description: str = Field(default="", max_length=10000)
    entity_type: str | None = Field(default=None, max_length=30)
    entity_id: UUID | None = None
    due_date: datetime | None = None
    document_ref: str | None = Field(default=None, max_length=500)


class ApproveBody(BaseModel):
    approved_by: str = Field(min_length=1, max_length=255)
    approved_by_role: str = Field(default="board_member")
    comment: str | None = Field(default=None, max_length=2000)


class RejectBody(BaseModel):
    rejected_by: str = Field(min_length=1, max_length=255)
    rejected_by_role: str = Field(default="board_member")
    reason: str = Field(min_length=5, max_length=2000)


class SignoffRequestResponse(BaseModel):
    id: UUID
    organization_id: UUID
    title: str
    signoff_type: str
    entity_type: str | None
    entity_id: UUID | None
    description: str
    status: str
    requested_by: str
    requested_at: Any
    due_date: Any | None
    approved_at: Any | None
    approved_by: str | None
    approved_by_role: str | None
    rejection_reason: str | None
    document_ref: str | None
    created_at: Any
    updated_at: Any

    model_config = ConfigDict(from_attributes=True)


class DecisionResponse(BaseModel):
    id: UUID
    request_id: UUID
    decision: str
    decided_by: str
    decided_by_role: str
    comment: str | None
    decided_at: Any

    model_config = ConfigDict(from_attributes=True)


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLBoardSignoffRepository(db)
    return repo.dashboard(user.organization_id)


@router.get("/", response_model=list[SignoffRequestResponse])
def list_requests(
    status: str | None = Query(default=None),
    signoff_type: str | None = Query(default=None),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLBoardSignoffRepository(db)
    return repo.list_org(user.organization_id, status=status, signoff_type=signoff_type)


@router.post("/", response_model=SignoffRequestResponse, status_code=status.HTTP_201_CREATED)
def create_request(
    body: SignoffRequestCreate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    if body.signoff_type not in VALID_TYPES:
        raise HTTPException(status_code=422, detail=f"signoff_type must be one of {VALID_TYPES}")
    repo = SQLBoardSignoffRepository(db)
    req = repo.create(
        organization_id=user.organization_id,
        title=body.title,
        signoff_type=body.signoff_type,
        description=body.description,
        entity_type=body.entity_type,
        entity_id=str(body.entity_id) if body.entity_id else None,
        requested_by=str(user.email or user.id),
        due_date=body.due_date,
        document_ref=body.document_ref,
    )
    db.commit()
    return req


@router.get("/{request_id}", response_model=SignoffRequestResponse)
def get_request(
    request_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLBoardSignoffRepository(db)
    r = repo.get(str(request_id), user.organization_id)
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    return r


@router.post("/{request_id}/approve", response_model=SignoffRequestResponse)
def approve_request(
    request_id: UUID,
    body: ApproveBody,
    db: Session = Depends(get_sync_db),
    user: User = Depends(require_analyst),
):
    """HUMAN BOARD MEMBER / ADMIN ONLY — KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen.
    Records formal board approval per CSDDD Art. 22 Abs. 1 lit. a."""
    if body.approved_by_role not in VALID_ROLES:
        raise HTTPException(
            status_code=422, detail=f"approved_by_role must be one of {VALID_ROLES}"
        )
    repo = SQLBoardSignoffRepository(db)
    r = repo.approve(
        str(request_id),
        user.organization_id,
        approved_by=body.approved_by,
        approved_by_role=body.approved_by_role,
        comment=body.comment,
    )
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    db.commit()
    return r


@router.post("/{request_id}/reject", response_model=SignoffRequestResponse)
def reject_request(
    request_id: UUID,
    body: RejectBody,
    db: Session = Depends(get_sync_db),
    user: User = Depends(require_analyst),
):
    """HUMAN BOARD MEMBER / ADMIN ONLY — KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen."""
    if body.rejected_by_role not in VALID_ROLES:
        raise HTTPException(
            status_code=422, detail=f"rejected_by_role must be one of {VALID_ROLES}"
        )
    repo = SQLBoardSignoffRepository(db)
    r = repo.reject(
        str(request_id),
        user.organization_id,
        rejected_by=body.rejected_by,
        rejected_by_role=body.rejected_by_role,
        reason=body.reason,
    )
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    db.commit()
    return r


@router.post("/{request_id}/withdraw", response_model=SignoffRequestResponse)
def withdraw_request(
    request_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLBoardSignoffRepository(db)
    r = repo.withdraw(str(request_id), user.organization_id)
    if not r:
        raise HTTPException(status_code=404, detail="Request not found")
    db.commit()
    return r


@router.get("/{request_id}/decisions", response_model=list[DecisionResponse])
def get_decisions(
    request_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLBoardSignoffRepository(db)
    return repo.decisions(str(request_id), user.organization_id)
