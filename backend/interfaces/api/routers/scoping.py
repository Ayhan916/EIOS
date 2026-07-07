"""CSDDD-008 — Scoping Study Workflow API (Art. 8 Abs. 3).

Endpoints (authenticated):
  GET    /scoping/config/                       get latest scoping config
  GET    /scoping/config/history                all config versions
  POST   /scoping/config/                       create new config version
  POST   /scoping/config/default                create best-practice default config

  POST   /scoping/analyze                       run deterministic prioritization analysis
  POST   /scoping/studies/                      create scoping study (saves snapshot)
  GET    /scoping/studies/                      list all studies
  GET    /scoping/studies/{id}                  get single study
  PATCH  /scoping/studies/{id}/notes            update methodology notes (draft only)
  POST   /scoping/studies/{id}/submit           submit for approval
  POST   /scoping/studies/{id}/approve          HUMAN MANAGER/ADMIN ONLY
  POST   /scoping/studies/{id}/clone            clone as new draft

  GET    /scoping/review-status                 annual review status indicator

Security:
  - organization_id MANDATORY on all queries
  - POST /scoping/studies/{id}/approve → analyst/admin only, AI agents MUST NOT call
  - Approved studies are immutable (locked)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from application.scoping.scoping_analyzer import SupplierInput, analyze
from domain.user import User
from infrastructure.persistence.repositories.scoping import (
    SQLScopingConfigRepository,
    SQLScopingStudyRepository,
    SQLScopingSupplierLoader,
)
from interfaces.api.deps import get_current_user, get_sync_db, require_analyst

router = APIRouter(prefix="/scoping", tags=["scoping"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class ScopingConfigCreate(BaseModel):
    risk_score_threshold_p1: float = Field(default=7.0, ge=0.0, le=10.0)
    risk_score_threshold_p2: float = Field(default=4.0, ge=0.0, le=10.0)
    high_risk_countries: list[str] = Field(default_factory=list)
    high_risk_sectors: list[str] = Field(default_factory=list)
    revenue_threshold_pct: float = Field(default=5.0, ge=0.0, le=100.0)
    notes: str = Field(default="", max_length=5000)


class ScopingConfigResponse(BaseModel):
    id: UUID
    organization_id: UUID
    version: int
    risk_score_threshold_p1: float
    risk_score_threshold_p2: float
    high_risk_countries: list[str]
    high_risk_sectors: list[str]
    revenue_threshold_pct: float
    notes: str
    created_by: str
    created_at: Any

    class Config:
        from_attributes = True


class ScopingStudyCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    report_year: int = Field(ge=2020, le=2100)
    config_id: UUID
    methodology_notes: str = Field(default="", max_length=10000)
    results: list[dict] = Field(default_factory=list)


class NotesUpdate(BaseModel):
    methodology_notes: str = Field(max_length=10000)


class ScopingStudyResponse(BaseModel):
    id: UUID
    organization_id: UUID
    title: str
    report_year: int
    config_id: UUID
    status: str
    results_snapshot: list[dict]
    methodology_notes: str
    submitted_at: Any | None
    submitted_by: str | None
    approved_at: Any | None
    approved_by: str | None
    next_review_due: Any | None
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cfg_repo(db: Session = Depends(get_sync_db)) -> SQLScopingConfigRepository:
    return SQLScopingConfigRepository(db)


def _study_repo(db: Session = Depends(get_sync_db)) -> SQLScopingStudyRepository:
    return SQLScopingStudyRepository(db)


def _cfg(c: Any) -> dict:
    return {
        "id": c.id,
        "organization_id": c.organization_id,
        "version": c.version,
        "risk_score_threshold_p1": c.risk_score_threshold_p1,
        "risk_score_threshold_p2": c.risk_score_threshold_p2,
        "high_risk_countries": c.high_risk_countries,
        "high_risk_sectors": c.high_risk_sectors,
        "revenue_threshold_pct": c.revenue_threshold_pct,
        "notes": c.notes,
        "created_by": c.created_by,
        "created_at": c.created_at,
    }


def _study(s: Any) -> dict:
    return {
        "id": s.id,
        "organization_id": s.organization_id,
        "title": s.title,
        "report_year": s.report_year,
        "config_id": s.config_id,
        "status": s.status,
        "results_snapshot": s.results_snapshot,
        "methodology_notes": s.methodology_notes,
        "submitted_at": s.submitted_at,
        "submitted_by": s.submitted_by,
        "approved_at": s.approved_at,
        "approved_by": s.approved_by,
        "next_review_due": s.next_review_due,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


# ── Config Endpoints ──────────────────────────────────────────────────────────


@router.get("/config/", response_model=ScopingConfigResponse)
def get_latest_config(
    user: User = Depends(get_current_user),
    repo: SQLScopingConfigRepository = Depends(_cfg_repo),
):
    cfg = repo.get_latest(user.organization_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="No scoping config found — create one first")
    return _cfg(cfg)


@router.get("/config/history", response_model=list[ScopingConfigResponse])
def list_config_history(
    user: User = Depends(get_current_user),
    repo: SQLScopingConfigRepository = Depends(_cfg_repo),
):
    return [_cfg(c) for c in repo.list(user.organization_id)]


@router.post("/config/", response_model=ScopingConfigResponse, status_code=201)
def create_config(
    body: ScopingConfigCreate,
    user: User = Depends(get_current_user),
    repo: SQLScopingConfigRepository = Depends(_cfg_repo),
    db: Session = Depends(get_sync_db),
):
    cfg = repo.create(user.organization_id, body.model_dump(), created_by=user.email)
    db.commit()
    return _cfg(cfg)


@router.post("/config/default", response_model=ScopingConfigResponse, status_code=201)
def create_default_config(
    user: User = Depends(get_current_user),
    repo: SQLScopingConfigRepository = Depends(_cfg_repo),
    db: Session = Depends(get_sync_db),
):
    cfg = repo.create_default(user.organization_id, created_by=user.email)
    db.commit()
    return _cfg(cfg)


# ── Analyze ───────────────────────────────────────────────────────────────────


@router.post("/analyze")
def run_analysis(
    config_id: UUID,
    user: User = Depends(get_current_user),
    cfg_repo: SQLScopingConfigRepository = Depends(_cfg_repo),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    """Run deterministic scoping analysis. Does NOT write to database."""
    cfg = cfg_repo.get_latest(user.organization_id)
    if not cfg:
        raise HTTPException(status_code=400, detail="No scoping config found")

    loader = SQLScopingSupplierLoader(db)
    supplier_data = loader.load(user.organization_id)

    if not supplier_data:
        return {
            "results": [],
            "summary": {"total": 0, "priority_1": 0, "priority_2": 0, "priority_3": 0},
        }

    inputs = [SupplierInput(**s) for s in supplier_data]
    results = analyze(cfg, inputs)

    result_dicts = [
        {
            "supplier_id": r.supplier_id,
            "supplier_name": r.supplier_name,
            "country": r.country,
            "industry": r.industry,
            "risk_score": r.risk_score,
            "risk_band": r.risk_band,
            "priority": r.priority.value,
            "reasons": r.reasons,
            "manually_overridden": r.manually_overridden,
            "override_reason": r.override_reason,
        }
        for r in results
    ]

    return {
        "results": result_dicts,
        "summary": {
            "total": len(results),
            "priority_1": sum(1 for r in results if r.priority.value == "priority_1"),
            "priority_2": sum(1 for r in results if r.priority.value == "priority_2"),
            "priority_3": sum(1 for r in results if r.priority.value == "priority_3"),
        },
        "config_version": cfg.version,
    }


# ── Studies ───────────────────────────────────────────────────────────────────


@router.post("/studies/", response_model=ScopingStudyResponse, status_code=201)
def create_study(
    body: ScopingStudyCreate,
    user: User = Depends(get_current_user),
    repo: SQLScopingStudyRepository = Depends(_study_repo),
    db: Session = Depends(get_sync_db),
):
    study = repo.create(
        user.organization_id, body.model_dump(exclude={"results"}), results=body.results
    )
    db.commit()
    return _study(study)


@router.get("/studies/", response_model=list[ScopingStudyResponse])
def list_studies(
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    repo: SQLScopingStudyRepository = Depends(_study_repo),
):
    return [_study(s) for s in repo.list_by_org(user.organization_id, skip=skip, limit=limit)]


@router.get("/studies/{study_id}", response_model=ScopingStudyResponse)
def get_study(
    study_id: UUID,
    user: User = Depends(get_current_user),
    repo: SQLScopingStudyRepository = Depends(_study_repo),
):
    s = repo.get(study_id, user.organization_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scoping study not found")
    return _study(s)


@router.patch("/studies/{study_id}/notes", response_model=ScopingStudyResponse)
def update_study_notes(
    study_id: UUID,
    body: NotesUpdate,
    user: User = Depends(get_current_user),
    repo: SQLScopingStudyRepository = Depends(_study_repo),
    db: Session = Depends(get_sync_db),
):
    s = repo.update_notes(study_id, user.organization_id, body.methodology_notes)
    if not s:
        raise HTTPException(status_code=404, detail="Study not found or not in draft status")
    db.commit()
    return _study(s)


@router.post("/studies/{study_id}/submit", response_model=ScopingStudyResponse)
def submit_study(
    study_id: UUID,
    user: User = Depends(get_current_user),
    repo: SQLScopingStudyRepository = Depends(_study_repo),
    db: Session = Depends(get_sync_db),
):
    s = repo.submit(study_id, user.organization_id, user.email)
    if not s:
        raise HTTPException(status_code=404, detail="Study not found")
    db.commit()
    return _study(s)


@router.post(
    "/studies/{study_id}/approve",
    response_model=ScopingStudyResponse,
    summary="Approve Scoping Study — HUMAN MANAGER/ADMIN ONLY. AI agents MUST NOT call this endpoint.",
)
def approve_study(
    study_id: UUID,
    user: User = Depends(require_analyst),
    repo: SQLScopingStudyRepository = Depends(_study_repo),
    db: Session = Depends(get_sync_db),
):
    """Approve and lock a Scoping Study. Restricted to human managers and admins.
    KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen. Dokument wird nach Genehmigung gesperrt."""
    s = repo.approve(study_id, user.organization_id, user.email)
    if not s:
        raise HTTPException(status_code=404, detail="Study not found")
    db.commit()
    return _study(s)


@router.post("/studies/{study_id}/clone", response_model=ScopingStudyResponse, status_code=201)
def clone_study(
    study_id: UUID,
    user: User = Depends(get_current_user),
    repo: SQLScopingStudyRepository = Depends(_study_repo),
    db: Session = Depends(get_sync_db),
):
    source = repo.get(study_id, user.organization_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source study not found")
    new_study = repo.create(
        user.organization_id,
        {
            "title": f"{source.title} (Kopie)",
            "report_year": source.report_year + 1,
            "config_id": source.config_id,
            "methodology_notes": source.methodology_notes,
        },
        results=source.results_snapshot,
    )
    db.commit()
    return _study(new_study)


@router.get("/review-status")
def get_review_status(
    user: User = Depends(get_current_user),
    repo: SQLScopingStudyRepository = Depends(_study_repo),
) -> dict[str, Any]:
    return repo.review_status(user.organization_id)
