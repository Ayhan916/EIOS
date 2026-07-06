"""CSDDD-004 — Remedy Case Manager API (Art. 12).

Endpoints (authenticated):
  POST   /remedy-cases/                              create new remedy case
  GET    /remedy-cases/                              list remedy cases (org-scoped)
  GET    /remedy-cases/{id}                          get single case
  PATCH  /remedy-cases/{id}                          update case metadata
  PATCH  /remedy-cases/{id}/close                    HUMAN ANALYST/ADMIN ONLY
  POST   /grievances/{grievance_id}/create-remedy-case  create case from grievance

  POST   /remedy-cases/{id}/beneficiaries            add beneficiary
  GET    /remedy-cases/{id}/beneficiaries            list beneficiaries
  PATCH  /remedy-cases/{id}/beneficiaries/{ben_id}   update beneficiary

  POST   /remedy-cases/{id}/actions                  add action
  GET    /remedy-cases/{id}/actions                  list actions
  PATCH  /remedy-cases/{id}/actions/{action_id}      update action status

  GET    /remedy-cases/{id}/audit-log                full audit trail
  GET    /reports/remedy-summary                     annual CSDDD summary report

Security:
  - organization_id MANDATORY on all queries
  - PATCH /remedy-cases/{id}/close → analyst role only, AI agents MUST NOT call
  - closed_by recorded from authenticated user
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from domain.user import User
from infrastructure.persistence.repositories.remedy_case import (
    SQLRemedyActionRepository,
    SQLRemedyAuditLogRepository,
    SQLRemedyBeneficiaryRepository,
    SQLRemedyCaseRepository,
)
from interfaces.api.deps import get_current_user, get_sync_db, require_analyst

# ── Schemas ───────────────────────────────────────────────────────────────────


class RemedyCaseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    incident_date: datetime
    affected_count: int = Field(default=0, ge=0)
    affected_type: str
    rights: list[str] = Field(default_factory=list)
    remedy_types: list[str] = Field(default_factory=list)
    severity_score: float = Field(default=0.0, ge=0.0, le=10.0)
    impact_causation: str
    source_grievance_id: Optional[UUID] = None
    co_responsible_parties: list[str] = Field(default_factory=list)


class RemedyCaseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    incident_date: Optional[datetime] = None
    affected_count: Optional[int] = Field(default=None, ge=0)
    affected_type: Optional[str] = None
    rights: Optional[list[str]] = None
    remedy_types: Optional[list[str]] = None
    severity_score: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    impact_causation: Optional[str] = None
    co_responsible_parties: Optional[list[str]] = None


class RemedyCaseClose(BaseModel):
    closure_notes: Optional[str] = Field(default=None, max_length=5000)


class RemedyCaseResponse(BaseModel):
    id: UUID
    organization_id: UUID
    title: str
    description: Optional[str]
    incident_date: datetime
    affected_count: int
    affected_type: str
    rights: list[str]
    remedy_types: list[str]
    severity_score: float
    impact_causation: str
    status: str
    source_grievance_id: Optional[UUID]
    co_responsible_parties: list[str]
    closed_at: Optional[datetime]
    closed_by: Optional[str]
    closure_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BeneficiaryCreate(BaseModel):
    reference: str = Field(min_length=1, max_length=255)
    affected_type: str
    promised_compensation: Optional[float] = Field(default=None, ge=0)
    received_compensation: Optional[float] = Field(default=None, ge=0)
    confirmation_date: Optional[datetime] = None


class BeneficiaryUpdate(BaseModel):
    reference: Optional[str] = Field(default=None, max_length=255)
    promised_compensation: Optional[float] = Field(default=None, ge=0)
    received_compensation: Optional[float] = Field(default=None, ge=0)
    confirmation_date: Optional[datetime] = None


class BeneficiaryResponse(BaseModel):
    id: UUID
    remedy_case_id: UUID
    reference: str
    affected_type: str
    promised_compensation: Optional[float]
    received_compensation: Optional[float]
    confirmation_date: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class RemedyActionCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=3000)
    responsible_party: Optional[str] = Field(default=None, max_length=255)
    due_date: Optional[datetime] = None


class RemedyActionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=3000)
    status: Optional[str] = None
    responsible_party: Optional[str] = Field(default=None, max_length=255)
    due_date: Optional[datetime] = None


class RemedyActionResponse(BaseModel):
    id: UUID
    remedy_case_id: UUID
    title: str
    description: Optional[str]
    status: str
    responsible_party: Optional[str]
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: UUID
    remedy_case_id: UUID
    action: str
    performed_by: str
    details: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/remedy-cases", tags=["remedy-cases"])
grievance_router = APIRouter(prefix="/grievances", tags=["remedy-cases"])
report_router = APIRouter(prefix="/reports", tags=["remedy-cases"])


def _case_repo(db: Session = Depends(get_sync_db)) -> SQLRemedyCaseRepository:
    return SQLRemedyCaseRepository(db)


def _ben_repo(db: Session = Depends(get_sync_db)) -> SQLRemedyBeneficiaryRepository:
    return SQLRemedyBeneficiaryRepository(db)


def _action_repo(db: Session = Depends(get_sync_db)) -> SQLRemedyActionRepository:
    return SQLRemedyActionRepository(db)


def _log_repo(db: Session = Depends(get_sync_db)) -> SQLRemedyAuditLogRepository:
    return SQLRemedyAuditLogRepository(db)


# ── Remedy Cases ──────────────────────────────────────────────────────────────

@router.post("/", response_model=RemedyCaseResponse, status_code=status.HTTP_201_CREATED)
def create_remedy_case(
    body: RemedyCaseCreate,
    user: User = Depends(get_current_user),
    repo: SQLRemedyCaseRepository = Depends(_case_repo),
    log_repo: SQLRemedyAuditLogRepository = Depends(_log_repo),
    db: Session = Depends(get_sync_db),
):
    case = repo.create(user.organization_id, body.model_dump())
    log_repo.log(case.id, "created", user.email)
    db.commit()
    return _case_to_response(case)


@router.get("/", response_model=list[RemedyCaseResponse])
def list_remedy_cases(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    repo: SQLRemedyCaseRepository = Depends(_case_repo),
):
    cases = repo.list_by_org(user.organization_id, status=status_filter, skip=skip, limit=limit)
    return [_case_to_response(c) for c in cases]


@router.get("/{case_id}", response_model=RemedyCaseResponse)
def get_remedy_case(
    case_id: UUID,
    user: User = Depends(get_current_user),
    repo: SQLRemedyCaseRepository = Depends(_case_repo),
):
    case = repo.get(case_id, user.organization_id)
    if not case:
        raise HTTPException(status_code=404, detail="Remedy case not found")
    return _case_to_response(case)


@router.patch("/{case_id}", response_model=RemedyCaseResponse)
def update_remedy_case(
    case_id: UUID,
    body: RemedyCaseUpdate,
    user: User = Depends(get_current_user),
    repo: SQLRemedyCaseRepository = Depends(_case_repo),
    log_repo: SQLRemedyAuditLogRepository = Depends(_log_repo),
    db: Session = Depends(get_sync_db),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    case = repo.update(case_id, user.organization_id, data)
    if not case:
        raise HTTPException(status_code=404, detail="Remedy case not found")
    log_repo.log(case_id, "updated", user.email, f"fields: {list(data.keys())}")
    db.commit()
    return _case_to_response(case)


@router.patch(
    "/{case_id}/close",
    response_model=RemedyCaseResponse,
    summary="Close Remedy Case — HUMAN ANALYST/ADMIN ONLY. AI agents MUST NOT call this endpoint.",
)
def close_remedy_case(
    case_id: UUID,
    body: RemedyCaseClose,
    user: User = Depends(require_analyst),  # analyst/admin only
    repo: SQLRemedyCaseRepository = Depends(_case_repo),
    log_repo: SQLRemedyAuditLogRepository = Depends(_log_repo),
    db: Session = Depends(get_sync_db),
):
    """Close a Remedy Case. Restricted to human analysts and admins.
    KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen."""
    case = repo.close(case_id, user.organization_id, user.email, body.closure_notes)
    if not case:
        raise HTTPException(status_code=404, detail="Remedy case not found")
    log_repo.log(case_id, "closed", user.email, body.closure_notes)
    db.commit()
    return _case_to_response(case)


# ── Create Case from Grievance ────────────────────────────────────────────────

@grievance_router.post("/{grievance_id}/create-remedy-case", response_model=RemedyCaseResponse, status_code=201)
def create_remedy_case_from_grievance(
    grievance_id: UUID,
    body: RemedyCaseCreate,
    user: User = Depends(get_current_user),
    repo: SQLRemedyCaseRepository = Depends(_case_repo),
    log_repo: SQLRemedyAuditLogRepository = Depends(_log_repo),
    db: Session = Depends(get_sync_db),
):
    data = body.model_dump()
    data["source_grievance_id"] = grievance_id
    case = repo.create(user.organization_id, data)
    log_repo.log(case.id, "created_from_grievance", user.email, f"grievance_id={grievance_id}")
    db.commit()
    return _case_to_response(case)


# ── Beneficiaries ─────────────────────────────────────────────────────────────

@router.post("/{case_id}/beneficiaries", response_model=BeneficiaryResponse, status_code=201)
def add_beneficiary(
    case_id: UUID,
    body: BeneficiaryCreate,
    user: User = Depends(get_current_user),
    case_repo: SQLRemedyCaseRepository = Depends(_case_repo),
    ben_repo: SQLRemedyBeneficiaryRepository = Depends(_ben_repo),
    log_repo: SQLRemedyAuditLogRepository = Depends(_log_repo),
    db: Session = Depends(get_sync_db),
):
    if not case_repo.get(case_id, user.organization_id):
        raise HTTPException(status_code=404, detail="Remedy case not found")
    ben = ben_repo.create(case_id, body.model_dump())
    log_repo.log(case_id, "beneficiary_added", user.email, body.reference)
    db.commit()
    return _ben_to_response(ben)


@router.get("/{case_id}/beneficiaries", response_model=list[BeneficiaryResponse])
def list_beneficiaries(
    case_id: UUID,
    user: User = Depends(get_current_user),
    case_repo: SQLRemedyCaseRepository = Depends(_case_repo),
    ben_repo: SQLRemedyBeneficiaryRepository = Depends(_ben_repo),
):
    if not case_repo.get(case_id, user.organization_id):
        raise HTTPException(status_code=404, detail="Remedy case not found")
    return [_ben_to_response(b) for b in ben_repo.list_by_case(case_id)]


@router.patch("/{case_id}/beneficiaries/{ben_id}", response_model=BeneficiaryResponse)
def update_beneficiary(
    case_id: UUID,
    ben_id: UUID,
    body: BeneficiaryUpdate,
    user: User = Depends(get_current_user),
    case_repo: SQLRemedyCaseRepository = Depends(_case_repo),
    ben_repo: SQLRemedyBeneficiaryRepository = Depends(_ben_repo),
    db: Session = Depends(get_sync_db),
):
    if not case_repo.get(case_id, user.organization_id):
        raise HTTPException(status_code=404, detail="Remedy case not found")
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    ben = ben_repo.update(ben_id, data)
    if not ben:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    db.commit()
    return _ben_to_response(ben)


# ── Actions ───────────────────────────────────────────────────────────────────

@router.post("/{case_id}/actions", response_model=RemedyActionResponse, status_code=201)
def add_action(
    case_id: UUID,
    body: RemedyActionCreate,
    user: User = Depends(get_current_user),
    case_repo: SQLRemedyCaseRepository = Depends(_case_repo),
    action_repo: SQLRemedyActionRepository = Depends(_action_repo),
    log_repo: SQLRemedyAuditLogRepository = Depends(_log_repo),
    db: Session = Depends(get_sync_db),
):
    if not case_repo.get(case_id, user.organization_id):
        raise HTTPException(status_code=404, detail="Remedy case not found")
    action = action_repo.create(case_id, body.model_dump(), created_by=user.email)
    log_repo.log(case_id, "action_added", user.email, body.title)
    db.commit()
    return _action_to_response(action)


@router.get("/{case_id}/actions", response_model=list[RemedyActionResponse])
def list_actions(
    case_id: UUID,
    user: User = Depends(get_current_user),
    case_repo: SQLRemedyCaseRepository = Depends(_case_repo),
    action_repo: SQLRemedyActionRepository = Depends(_action_repo),
):
    if not case_repo.get(case_id, user.organization_id):
        raise HTTPException(status_code=404, detail="Remedy case not found")
    return [_action_to_response(a) for a in action_repo.list_by_case(case_id)]


@router.patch("/{case_id}/actions/{action_id}", response_model=RemedyActionResponse)
def update_action(
    case_id: UUID,
    action_id: UUID,
    body: RemedyActionUpdate,
    user: User = Depends(get_current_user),
    case_repo: SQLRemedyCaseRepository = Depends(_case_repo),
    action_repo: SQLRemedyActionRepository = Depends(_action_repo),
    log_repo: SQLRemedyAuditLogRepository = Depends(_log_repo),
    db: Session = Depends(get_sync_db),
):
    if not case_repo.get(case_id, user.organization_id):
        raise HTTPException(status_code=404, detail="Remedy case not found")
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    action = action_repo.update(action_id, data)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    log_repo.log(case_id, "action_updated", user.email, f"action_id={action_id}")
    db.commit()
    return _action_to_response(action)


# ── Audit Log ─────────────────────────────────────────────────────────────────

@router.get("/{case_id}/audit-log", response_model=list[AuditLogResponse])
def get_audit_log(
    case_id: UUID,
    user: User = Depends(require_analyst),
    case_repo: SQLRemedyCaseRepository = Depends(_case_repo),
    log_repo: SQLRemedyAuditLogRepository = Depends(_log_repo),
):
    if not case_repo.get(case_id, user.organization_id):
        raise HTTPException(status_code=404, detail="Remedy case not found")
    return [_log_to_response(l) for l in log_repo.list_by_case(case_id)]


# ── Annual Report ─────────────────────────────────────────────────────────────

@report_router.get("/remedy-summary")
def remedy_summary_report(
    year: int,
    user: User = Depends(get_current_user),
    repo: SQLRemedyCaseRepository = Depends(_case_repo),
) -> dict[str, Any]:
    return repo.remedy_summary(user.organization_id, year)


# ── Serialization helpers ─────────────────────────────────────────────────────

def _case_to_response(c: Any) -> dict:
    return {
        "id": c.id,
        "organization_id": c.organization_id,
        "title": c.title,
        "description": c.description,
        "incident_date": c.incident_date,
        "affected_count": c.affected_count,
        "affected_type": c.affected_type,
        "rights": c.rights,
        "remedy_types": c.remedy_types,
        "severity_score": c.severity_score,
        "impact_causation": c.impact_causation,
        "status": c.status,
        "source_grievance_id": c.source_grievance_id,
        "co_responsible_parties": c.co_responsible_parties,
        "closed_at": c.closed_at,
        "closed_by": c.closed_by,
        "closure_notes": c.closure_notes,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


def _ben_to_response(b: Any) -> dict:
    return {
        "id": b.id,
        "remedy_case_id": b.remedy_case_id,
        "reference": b.reference,
        "affected_type": b.affected_type,
        "promised_compensation": b.promised_compensation,
        "received_compensation": b.received_compensation,
        "confirmation_date": b.confirmation_date,
        "created_at": b.created_at,
    }


def _action_to_response(a: Any) -> dict:
    return {
        "id": a.id,
        "remedy_case_id": a.remedy_case_id,
        "title": a.title,
        "description": a.description,
        "status": a.status,
        "responsible_party": a.responsible_party,
        "due_date": a.due_date,
        "completed_at": a.completed_at,
        "created_by": a.created_by,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


def _log_to_response(l: Any) -> dict:
    return {
        "id": l.id,
        "remedy_case_id": l.remedy_case_id,
        "action": l.action,
        "performed_by": l.performed_by,
        "details": l.details,
        "created_at": l.created_at,
    }
