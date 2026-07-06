"""CSDDD-006 — Contractual Assurance Module API (Art. 10).

Endpoints (authenticated):
  GET    /contractual-assurance/clauses/             list clause library
  POST   /contractual-assurance/clauses/             create new clause
  POST   /contractual-assurance/clauses/seed         seed 10 best-practice clauses
  GET    /contractual-assurance/clauses/{id}         get clause
  PATCH  /contractual-assurance/clauses/{id}         update clause
  GET    /contractual-assurance/clauses/summary       clause library stats

  GET    /contractual-assurance/assurances/           list assurances (filter by supplier/clause/status)
  POST   /contractual-assurance/assurances/           create assurance record
  GET    /contractual-assurance/assurances/{id}       get assurance
  POST   /contractual-assurance/assurances/{id}/accept       HUMAN ANALYST/ADMIN ONLY
  PATCH  /contractual-assurance/assurances/{id}/status       HUMAN ANALYST/ADMIN ONLY
  POST   /contractual-assurance/assurances/{id}/confirm-cascade  HUMAN ANALYST/ADMIN ONLY
  GET    /contractual-assurance/assurances/{id}/audit-log     audit trail

  GET    /contractual-assurance/dashboard             compliance KPI summary
  GET    /contractual-assurance/supplier-coverage     per-supplier assurance overview

Security:
  - organization_id MANDATORY on all queries
  - accept / update_status / confirm_cascade → analyst/admin only; KI-Agenten DÜRFEN diese
    Endpunkte NICHT aufrufen (Art. 10 requires human accountability)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from domain.user import User
from infrastructure.persistence.repositories.contractual_assurance import (
    SQLContractAssuranceRepository,
    SQLContractClauseRepository,
)
from interfaces.api.deps import get_current_user, get_sync_db, require_analyst

router = APIRouter(prefix="/contractual-assurance", tags=["contractual-assurance"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class ClauseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    clause_text: str = Field(min_length=10, max_length=10000)
    category: str = Field(default="other")
    cascade_required: bool = False
    is_mandatory: bool = True
    version: str = Field(default="1.0", max_length=20)


class ClauseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    clause_text: Optional[str] = Field(default=None, max_length=10000)
    category: Optional[str] = None
    cascade_required: Optional[bool] = None
    is_mandatory: Optional[bool] = None
    version: Optional[str] = Field(default=None, max_length=20)
    is_active: Optional[bool] = None


class ClauseResponse(BaseModel):
    id: UUID
    organization_id: UUID
    title: str
    clause_text: str
    category: str
    cascade_required: bool
    is_mandatory: bool
    version: str
    is_active: bool
    created_by: str
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


class AssuranceCreate(BaseModel):
    supplier_id: UUID
    clause_id: UUID
    document_ref: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=5000)
    valid_until: Optional[datetime] = None


class AssuranceAccept(BaseModel):
    document_ref: Optional[str] = Field(default=None, max_length=500)


class AssuranceStatusUpdate(BaseModel):
    status: str = Field(description="pending | accepted | rejected | expired | waived")
    note: Optional[str] = Field(default=None, max_length=1000)


class AssuranceResponse(BaseModel):
    id: UUID
    organization_id: UUID
    supplier_id: UUID
    clause_id: UUID
    status: str
    accepted_at: Optional[Any]
    accepted_by: Optional[str]
    document_ref: Optional[str]
    notes: Optional[str]
    cascade_confirmed: bool
    cascade_confirmed_at: Optional[Any]
    valid_until: Optional[Any]
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: UUID
    assurance_id: UUID
    changed_by: str
    from_status: Optional[str]
    to_status: str
    note: Optional[str]
    created_at: Any

    class Config:
        from_attributes = True


# ── Clause endpoints ──────────────────────────────────────────────────────────


@router.get("/clauses/summary")
def clause_summary(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLContractClauseRepository(db)
    return repo.summary(user.organization_id)


@router.post("/clauses/seed")
def seed_clauses(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLContractClauseRepository(db)
    count = repo.seed_defaults(user.organization_id, str(user.id))
    db.commit()
    return {"seeded": count}


@router.get("/clauses/", response_model=list[ClauseResponse])
def list_clauses(
    active_only: bool = Query(default=True),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLContractClauseRepository(db)
    return repo.list_org(user.organization_id, active_only=active_only)


@router.post("/clauses/", response_model=ClauseResponse, status_code=status.HTTP_201_CREATED)
def create_clause(
    body: ClauseCreate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLContractClauseRepository(db)
    clause = repo.create(
        organization_id=user.organization_id,
        title=body.title,
        clause_text=body.clause_text,
        category=body.category,
        cascade_required=body.cascade_required,
        is_mandatory=body.is_mandatory,
        version=body.version,
        created_by=str(user.id),
    )
    db.commit()
    return clause


@router.get("/clauses/{clause_id}", response_model=ClauseResponse)
def get_clause(
    clause_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLContractClauseRepository(db)
    c = repo.get(str(clause_id), user.organization_id)
    if not c:
        raise HTTPException(status_code=404, detail="Clause not found")
    return c


@router.patch("/clauses/{clause_id}", response_model=ClauseResponse)
def update_clause(
    clause_id: UUID,
    body: ClauseUpdate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLContractClauseRepository(db)
    updated = repo.update(str(clause_id), user.organization_id, **body.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Clause not found")
    db.commit()
    return updated


# ── Assurance endpoints ───────────────────────────────────────────────────────


@router.get("/assurances/", response_model=list[AssuranceResponse])
def list_assurances(
    supplier_id: Optional[UUID] = Query(default=None),
    clause_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLContractAssuranceRepository(db)
    return repo.list_org(
        user.organization_id,
        supplier_id=str(supplier_id) if supplier_id else None,
        clause_id=str(clause_id) if clause_id else None,
        status=status,
    )


@router.post("/assurances/", response_model=AssuranceResponse, status_code=status.HTTP_201_CREATED)
def create_assurance(
    body: AssuranceCreate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLContractAssuranceRepository(db)
    a = repo.create(
        organization_id=user.organization_id,
        supplier_id=str(body.supplier_id),
        clause_id=str(body.clause_id),
        document_ref=body.document_ref,
        notes=body.notes,
        valid_until=body.valid_until,
    )
    db.commit()
    return a


@router.get("/assurances/{assurance_id}", response_model=AssuranceResponse)
def get_assurance(
    assurance_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLContractAssuranceRepository(db)
    a = repo.get(str(assurance_id), user.organization_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assurance not found")
    return a


@router.post("/assurances/{assurance_id}/accept", response_model=AssuranceResponse)
def accept_assurance(
    assurance_id: UUID,
    body: AssuranceAccept,
    db: Session = Depends(get_sync_db),
    user: User = Depends(require_analyst),
):
    """HUMAN ANALYST/ADMIN ONLY — KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen.
    Records that a supplier has formally accepted a contractual clause (Art. 10 Abs. 2)."""
    repo = SQLContractAssuranceRepository(db)
    a = repo.accept(
        str(assurance_id),
        user.organization_id,
        accepted_by=str(user.email or user.id),
        document_ref=body.document_ref,
    )
    if not a:
        raise HTTPException(status_code=404, detail="Assurance not found")
    db.commit()
    return a


@router.patch("/assurances/{assurance_id}/status", response_model=AssuranceResponse)
def update_assurance_status(
    assurance_id: UUID,
    body: AssuranceStatusUpdate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(require_analyst),
):
    """HUMAN ANALYST/ADMIN ONLY — KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen."""
    allowed = {"pending", "accepted", "rejected", "expired", "waived"}
    if body.status not in allowed:
        raise HTTPException(status_code=422, detail=f"status must be one of {allowed}")
    repo = SQLContractAssuranceRepository(db)
    a = repo.update_status(
        str(assurance_id),
        user.organization_id,
        new_status=body.status,
        changed_by=str(user.email or user.id),
        note=body.note,
    )
    if not a:
        raise HTTPException(status_code=404, detail="Assurance not found")
    db.commit()
    return a


@router.post("/assurances/{assurance_id}/confirm-cascade", response_model=AssuranceResponse)
def confirm_cascade(
    assurance_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(require_analyst),
):
    """HUMAN ANALYST/ADMIN ONLY — KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen.
    Records that the supplier has confirmed they have cascaded this clause to their own suppliers."""
    repo = SQLContractAssuranceRepository(db)
    a = repo.confirm_cascade(
        str(assurance_id),
        user.organization_id,
        confirmed_by=str(user.email or user.id),
    )
    if not a:
        raise HTTPException(status_code=404, detail="Assurance not found")
    db.commit()
    return a


@router.get("/assurances/{assurance_id}/audit-log", response_model=list[AuditLogResponse])
def get_audit_log(
    assurance_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLContractAssuranceRepository(db)
    return repo.audit_logs(str(assurance_id), user.organization_id)


# ── Dashboard endpoints ───────────────────────────────────────────────────────


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLContractAssuranceRepository(db)
    return repo.dashboard(user.organization_id)


@router.get("/supplier-coverage")
def supplier_coverage(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLContractAssuranceRepository(db)
    return repo.supplier_coverage(user.organization_id)
