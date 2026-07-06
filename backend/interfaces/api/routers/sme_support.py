"""CSDDD-007 — SME Support Tracker API (Art. 10 Abs. 2 lit. b).

Endpoints (authenticated):
  GET    /sme-support/profiles/                     list SME profiles
  POST   /sme-support/profiles/                     create/update SME profile
  GET    /sme-support/profiles/{supplier_id}        get profile by supplier
  POST   /sme-support/profiles/{supplier_id}/confirm   HUMAN ANALYST/ADMIN ONLY
  GET    /sme-support/profiles/summary              SME classification summary

  GET    /sme-support/programs/                     list support programs
  POST   /sme-support/programs/                     create program
  GET    /sme-support/programs/{id}                 get program with measures
  PATCH  /sme-support/programs/{id}                 update program
  POST   /sme-support/programs/{id}/activate        HUMAN ANALYST/ADMIN ONLY
  POST   /sme-support/programs/{id}/complete        HUMAN ANALYST/ADMIN ONLY

  GET    /sme-support/programs/{id}/measures/       list measures
  POST   /sme-support/programs/{id}/measures/       add measure
  POST   /sme-support/measures/{id}/complete        HUMAN ANALYST/ADMIN ONLY
  PATCH  /sme-support/measures/{id}/status          HUMAN ANALYST/ADMIN ONLY

  GET    /sme-support/annual-report?year=           CSDDD annual report data

Security:
  - organization_id MANDATORY on all queries
  - confirm / activate / complete → analyst/admin only; KI-Agenten DÜRFEN diese
    Endpunkte NICHT aufrufen
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from domain.user import User
from infrastructure.persistence.repositories.sme_support import (
    SQLSMEProfileRepository,
    SQLSupportMeasureRepository,
    SQLSupportProgramRepository,
)
from interfaces.api.deps import get_current_user, get_sync_db, require_analyst

router = APIRouter(prefix="/sme-support", tags=["sme-support"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class SMEProfileUpsert(BaseModel):
    supplier_id: UUID
    employee_count: Optional[int] = Field(default=None, ge=0)
    annual_revenue_eur: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = Field(default=None, max_length=2000)


class SMEProfileResponse(BaseModel):
    id: UUID
    organization_id: UUID
    supplier_id: UUID
    classification: str
    employee_count: Optional[int]
    annual_revenue_eur: Optional[float]
    is_confirmed: bool
    confirmed_by: Optional[str]
    confirmed_at: Optional[Any]
    notes: Optional[str]
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


class ProgramCreate(BaseModel):
    supplier_id: UUID
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(default="", max_length=5000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    responsible_user: Optional[str] = Field(default=None, max_length=255)
    total_budget_eur: Optional[float] = Field(default=None, ge=0)


class ProgramUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    responsible_user: Optional[str] = Field(default=None, max_length=255)
    total_budget_eur: Optional[float] = Field(default=None, ge=0)


class ProgramResponse(BaseModel):
    id: UUID
    organization_id: UUID
    supplier_id: UUID
    title: str
    description: str
    status: str
    start_date: Optional[Any]
    end_date: Optional[Any]
    responsible_user: Optional[str]
    total_budget_eur: Optional[float]
    spent_budget_eur: float
    created_by: str
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


class MeasureCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    support_type: str = Field(default="training")
    description: Optional[str] = Field(default=None, max_length=5000)
    due_date: Optional[datetime] = None
    cost_eur: Optional[float] = Field(default=None, ge=0)


class MeasureCompleteBody(BaseModel):
    impact_notes: Optional[str] = Field(default=None, max_length=2000)


class MeasureStatusUpdate(BaseModel):
    status: str = Field(description="planned | in_progress | completed | cancelled")


class MeasureResponse(BaseModel):
    id: UUID
    organization_id: UUID
    program_id: UUID
    title: str
    support_type: str
    status: str
    description: Optional[str]
    due_date: Optional[Any]
    completed_at: Optional[Any]
    cost_eur: Optional[float]
    impact_notes: Optional[str]
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


# ── SME Profile endpoints ─────────────────────────────────────────────────────


@router.get("/profiles/summary")
def profile_summary(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLSMEProfileRepository(db)
    return repo.summary(user.organization_id)


@router.get("/profiles/", response_model=list[SMEProfileResponse])
def list_profiles(
    sme_only: bool = Query(default=True),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLSMEProfileRepository(db)
    return repo.list_org(user.organization_id, sme_only=sme_only)


@router.post("/profiles/", response_model=SMEProfileResponse, status_code=status.HTTP_201_CREATED)
def upsert_profile(
    body: SMEProfileUpsert,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLSMEProfileRepository(db)
    profile = repo.upsert(
        organization_id=user.organization_id,
        supplier_id=str(body.supplier_id),
        employee_count=body.employee_count,
        annual_revenue_eur=body.annual_revenue_eur,
        notes=body.notes,
        created_by=str(user.id),
    )
    db.commit()
    return profile


@router.get("/profiles/{supplier_id}", response_model=SMEProfileResponse)
def get_profile(
    supplier_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLSMEProfileRepository(db)
    p = repo.get_by_supplier(user.organization_id, str(supplier_id))
    if not p:
        raise HTTPException(status_code=404, detail="SME profile not found")
    return p


@router.post("/profiles/{supplier_id}/confirm", response_model=SMEProfileResponse)
def confirm_profile(
    supplier_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(require_analyst),
):
    """HUMAN ANALYST/ADMIN ONLY — KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen.
    Confirms the SME classification as officially verified."""
    repo = SQLSMEProfileRepository(db)
    p = repo.confirm(
        user.organization_id,
        str(supplier_id),
        confirmed_by=str(user.email or user.id),
    )
    if not p:
        raise HTTPException(status_code=404, detail="SME profile not found")
    db.commit()
    return p


# ── Program endpoints ─────────────────────────────────────────────────────────


@router.get("/programs/", response_model=list[ProgramResponse])
def list_programs(
    supplier_id: Optional[UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLSupportProgramRepository(db)
    return repo.list_org(
        user.organization_id,
        supplier_id=str(supplier_id) if supplier_id else None,
        status=status,
    )


@router.post("/programs/", response_model=ProgramResponse, status_code=status.HTTP_201_CREATED)
def create_program(
    body: ProgramCreate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLSupportProgramRepository(db)
    prog = repo.create(
        organization_id=user.organization_id,
        supplier_id=str(body.supplier_id),
        title=body.title,
        description=body.description,
        start_date=body.start_date,
        end_date=body.end_date,
        responsible_user=body.responsible_user,
        total_budget_eur=body.total_budget_eur,
        created_by=str(user.id),
    )
    db.commit()
    return prog


@router.get("/programs/{program_id}", response_model=ProgramResponse)
def get_program(
    program_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLSupportProgramRepository(db)
    prog = repo.get(str(program_id), user.organization_id)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")
    return prog


@router.patch("/programs/{program_id}", response_model=ProgramResponse)
def update_program(
    program_id: UUID,
    body: ProgramUpdate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLSupportProgramRepository(db)
    prog = repo.update(str(program_id), user.organization_id, **body.model_dump(exclude_none=True))
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")
    db.commit()
    return prog


@router.post("/programs/{program_id}/activate", response_model=ProgramResponse)
def activate_program(
    program_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(require_analyst),
):
    """HUMAN ANALYST/ADMIN ONLY — KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen."""
    repo = SQLSupportProgramRepository(db)
    prog = repo.activate(str(program_id), user.organization_id)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")
    db.commit()
    return prog


@router.post("/programs/{program_id}/complete", response_model=ProgramResponse)
def complete_program(
    program_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(require_analyst),
):
    """HUMAN ANALYST/ADMIN ONLY — KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen."""
    repo = SQLSupportProgramRepository(db)
    prog = repo.complete(str(program_id), user.organization_id)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")
    db.commit()
    return prog


# ── Measure endpoints ─────────────────────────────────────────────────────────


@router.get("/programs/{program_id}/measures/", response_model=list[MeasureResponse])
def list_measures(
    program_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLSupportMeasureRepository(db)
    return repo.list_program(str(program_id), user.organization_id)


@router.post(
    "/programs/{program_id}/measures/",
    response_model=MeasureResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_measure(
    program_id: UUID,
    body: MeasureCreate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    prog_repo = SQLSupportProgramRepository(db)
    if not prog_repo.get(str(program_id), user.organization_id):
        raise HTTPException(status_code=404, detail="Program not found")
    repo = SQLSupportMeasureRepository(db)
    measure = repo.create(
        organization_id=user.organization_id,
        program_id=str(program_id),
        title=body.title,
        support_type=body.support_type,
        description=body.description,
        due_date=body.due_date,
        cost_eur=body.cost_eur,
    )
    db.commit()
    return measure


@router.post("/measures/{measure_id}/complete", response_model=MeasureResponse)
def complete_measure(
    measure_id: UUID,
    body: MeasureCompleteBody,
    db: Session = Depends(get_sync_db),
    user: User = Depends(require_analyst),
):
    """HUMAN ANALYST/ADMIN ONLY — KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen."""
    repo = SQLSupportMeasureRepository(db)
    m = repo.complete(str(measure_id), user.organization_id, body.impact_notes)
    if not m:
        raise HTTPException(status_code=404, detail="Measure not found")
    db.commit()
    return m


@router.patch("/measures/{measure_id}/status", response_model=MeasureResponse)
def update_measure_status(
    measure_id: UUID,
    body: MeasureStatusUpdate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(require_analyst),
):
    """HUMAN ANALYST/ADMIN ONLY — KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen."""
    allowed = {"planned", "in_progress", "completed", "cancelled"}
    if body.status not in allowed:
        raise HTTPException(status_code=422, detail=f"status must be one of {allowed}")
    repo = SQLSupportMeasureRepository(db)
    m = repo.update_status(str(measure_id), user.organization_id, body.status)
    if not m:
        raise HTTPException(status_code=404, detail="Measure not found")
    db.commit()
    return m


# ── Annual report ─────────────────────────────────────────────────────────────


@router.get("/annual-report")
def annual_report(
    year: int = Query(ge=2020, le=2100),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLSupportProgramRepository(db)
    return repo.annual_report(user.organization_id, year)
