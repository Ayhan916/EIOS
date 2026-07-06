"""CSDDD-003 — Effectiveness Monitoring API (Art. 15).

Endpoints (authenticated):
  GET    /effectiveness/indicators/                 list indicator library (global + org)
  POST   /effectiveness/indicators/                 add custom indicator
  GET    /effectiveness/indicators/{id}             get single indicator

  POST   /effectiveness/reviews/                    create review (draft)
  GET    /effectiveness/reviews/                    list reviews
  GET    /effectiveness/reviews/{id}                get review with lines
  PATCH  /effectiveness/reviews/{id}                update draft
  POST   /effectiveness/reviews/{id}/lines          upsert measurement line
  POST   /effectiveness/reviews/{id}/submit         submit for approval
  POST   /effectiveness/reviews/{id}/close          HUMAN MANAGER/ADMIN ONLY

  GET    /effectiveness/cap/{cap_id}/snapshot       pre/post risk-score snapshot
  POST   /effectiveness/cap/{cap_id}/baseline       record baseline score
  POST   /effectiveness/cap/{cap_id}/closed-score   record post-closure score

  GET    /effectiveness/dashboard                   live 6-metric monitoring dashboard

Security:
  - organization_id MANDATORY on all queries
  - POST /effectiveness/reviews/{id}/close → manager/admin only, AI agents MUST NOT call
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from domain.user import User
from infrastructure.persistence.repositories.effectiveness import (
    SQLCAPSnapshotRepository,
    SQLEffectivenessDashboardRepository,
    SQLEffectivenessIndicatorRepository,
    SQLEffectivenessReviewRepository,
)
from interfaces.api.deps import get_current_user, get_sync_db, require_analyst

router = APIRouter(prefix="/effectiveness", tags=["effectiveness"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class IndicatorCreate(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    indicator_type: str = "qualitative"
    unit: str = Field(default="", max_length=100)
    data_source: str = "manual"
    csddd_article: str = Field(default="", max_length=50)
    risk_category: Optional[str] = Field(default=None, max_length=100)


class IndicatorResponse(BaseModel):
    id: UUID
    organization_id: Optional[UUID]
    name: str
    description: Optional[str]
    indicator_type: str
    unit: str
    data_source: str
    csddd_article: str
    risk_category: Optional[str]
    is_active: bool
    created_at: Any

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    period_start: Any
    period_end: Any
    overall_rating: Optional[int] = Field(default=None, ge=1, le=5)
    key_findings: Optional[str] = Field(default=None, max_length=10000)
    improvement_actions: Optional[str] = Field(default=None, max_length=10000)


class ReviewUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    period_start: Optional[Any] = None
    period_end: Optional[Any] = None
    overall_rating: Optional[int] = Field(default=None, ge=1, le=5)
    key_findings: Optional[str] = Field(default=None, max_length=10000)
    improvement_actions: Optional[str] = Field(default=None, max_length=10000)


class ReviewLineUpsert(BaseModel):
    indicator_id: UUID
    indicator_name: str = Field(default="", max_length=255)
    measured_value: Optional[float] = None
    measured_text: Optional[str] = Field(default=None, max_length=2000)
    comment: Optional[str] = Field(default=None, max_length=2000)
    auto_populated: bool = False


class ReviewLineResponse(BaseModel):
    id: UUID
    review_id: UUID
    indicator_id: UUID
    indicator_name: str
    measured_value: Optional[float]
    measured_text: Optional[str]
    comment: Optional[str]
    auto_populated: bool

    class Config:
        from_attributes = True


class ReviewResponse(BaseModel):
    id: UUID
    organization_id: UUID
    title: str
    period_start: Any
    period_end: Any
    overall_rating: Optional[int]
    key_findings: Optional[str]
    improvement_actions: Optional[str]
    status: str
    submitted_at: Optional[Any]
    submitted_by: Optional[str]
    approved_at: Optional[Any]
    approved_by: Optional[str]
    lines: list[ReviewLineResponse]
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


class ScoreInput(BaseModel):
    score: float = Field(ge=0.0, le=10.0)


# ── Indicator Library ─────────────────────────────────────────────────────────

def _ind_repo(db: Session = Depends(get_sync_db)) -> SQLEffectivenessIndicatorRepository:
    repo = SQLEffectivenessIndicatorRepository(db)
    repo.seed_if_empty()
    return repo


def _rev_repo(db: Session = Depends(get_sync_db)) -> SQLEffectivenessReviewRepository:
    return SQLEffectivenessReviewRepository(db)


@router.get("/indicators/", response_model=list[IndicatorResponse])
def list_indicators(
    risk_category: Optional[str] = None,
    user: User = Depends(get_current_user),
    repo: SQLEffectivenessIndicatorRepository = Depends(_ind_repo),
):
    return [_ind(i) for i in repo.list(user.organization_id, risk_category=risk_category)]


@router.post("/indicators/", response_model=IndicatorResponse, status_code=201)
def create_indicator(
    body: IndicatorCreate,
    user: User = Depends(get_current_user),
    repo: SQLEffectivenessIndicatorRepository = Depends(_ind_repo),
    db: Session = Depends(get_sync_db),
):
    ind = repo.create(user.organization_id, body.model_dump())
    db.commit()
    return _ind(ind)


@router.get("/indicators/{indicator_id}", response_model=IndicatorResponse)
def get_indicator(
    indicator_id: UUID,
    user: User = Depends(get_current_user),
    repo: SQLEffectivenessIndicatorRepository = Depends(_ind_repo),
):
    ind = repo.get(indicator_id)
    if not ind:
        raise HTTPException(status_code=404, detail="Indicator not found")
    return _ind(ind)


# ── Reviews ───────────────────────────────────────────────────────────────────

@router.post("/reviews/", response_model=ReviewResponse, status_code=201)
def create_review(
    body: ReviewCreate,
    user: User = Depends(get_current_user),
    repo: SQLEffectivenessReviewRepository = Depends(_rev_repo),
    db: Session = Depends(get_sync_db),
):
    review = repo.create(user.organization_id, body.model_dump())
    db.commit()
    return _rev(review)


@router.get("/reviews/", response_model=list[ReviewResponse])
def list_reviews(
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    repo: SQLEffectivenessReviewRepository = Depends(_rev_repo),
):
    return [_rev(r) for r in repo.list_by_org(user.organization_id, skip=skip, limit=limit)]


@router.get("/reviews/{review_id}", response_model=ReviewResponse)
def get_review(
    review_id: UUID,
    user: User = Depends(get_current_user),
    repo: SQLEffectivenessReviewRepository = Depends(_rev_repo),
):
    review = repo.get(review_id, user.organization_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return _rev(review)


@router.patch("/reviews/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: UUID,
    body: ReviewUpdate,
    user: User = Depends(get_current_user),
    repo: SQLEffectivenessReviewRepository = Depends(_rev_repo),
    db: Session = Depends(get_sync_db),
):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    review = repo.update(review_id, user.organization_id, data)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    db.commit()
    return _rev(review)


@router.post("/reviews/{review_id}/lines", response_model=ReviewLineResponse)
def upsert_line(
    review_id: UUID,
    body: ReviewLineUpsert,
    user: User = Depends(get_current_user),
    repo: SQLEffectivenessReviewRepository = Depends(_rev_repo),
    db: Session = Depends(get_sync_db),
):
    review = repo.get(review_id, user.organization_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.status not in ("draft",):
        raise HTTPException(status_code=400, detail="Can only edit lines on draft reviews")
    data = body.model_dump()
    data["indicator_id"] = str(data["indicator_id"])
    line = repo.upsert_line(review_id, data)
    db.commit()
    return _line(line)


@router.post("/reviews/{review_id}/submit", response_model=ReviewResponse)
def submit_review(
    review_id: UUID,
    user: User = Depends(get_current_user),
    repo: SQLEffectivenessReviewRepository = Depends(_rev_repo),
    db: Session = Depends(get_sync_db),
):
    review = repo.submit(review_id, user.organization_id, user.email)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    db.commit()
    return _rev(review)


@router.post(
    "/reviews/{review_id}/close",
    response_model=ReviewResponse,
    summary="Close Effectiveness Review — HUMAN MANAGER/ADMIN ONLY. AI agents MUST NOT call this endpoint.",
)
def close_review(
    review_id: UUID,
    user: User = Depends(require_analyst),
    repo: SQLEffectivenessReviewRepository = Depends(_rev_repo),
    db: Session = Depends(get_sync_db),
):
    """Close and approve an Effectiveness Review. Restricted to human managers and admins.
    KI-Agenten DÜRFEN diesen Endpunkt NICHT aufrufen."""
    review = repo.close(review_id, user.organization_id, user.email)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    db.commit()
    return _rev(review)


# ── CAP Snapshots ─────────────────────────────────────────────────────────────

@router.get("/cap/{cap_id}/snapshot")
def get_cap_snapshot(
    cap_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> dict:
    repo = SQLCAPSnapshotRepository(db)
    snapshot = repo.get_snapshot(cap_id, user.organization_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="CAP not found")
    return {
        "cap_id": snapshot.cap_id,
        "baseline_score": snapshot.baseline_score,
        "closed_score": snapshot.closed_score,
        "risk_delta": snapshot.risk_delta,
        "snapshot_taken_at": snapshot.snapshot_taken_at,
    }


@router.post("/cap/{cap_id}/baseline", status_code=204)
def set_cap_baseline(
    cap_id: str,
    body: ScoreInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
):
    SQLCAPSnapshotRepository(db).set_baseline(cap_id, user.organization_id, body.score)
    db.commit()


@router.post("/cap/{cap_id}/closed-score", status_code=204)
def set_cap_closed_score(
    cap_id: str,
    body: ScoreInput,
    user: User = Depends(require_analyst),
    db: Session = Depends(get_sync_db),
):
    SQLCAPSnapshotRepository(db).set_closed_score(cap_id, user.organization_id, body.score)
    db.commit()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def effectiveness_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> dict[str, Any]:
    return SQLEffectivenessDashboardRepository(db).get_dashboard(user.organization_id)


# ── Serialization helpers ─────────────────────────────────────────────────────

def _ind(i: Any) -> dict:
    return {
        "id": i.id,
        "organization_id": i.organization_id,
        "name": i.name,
        "description": i.description,
        "indicator_type": i.indicator_type,
        "unit": i.unit,
        "data_source": i.data_source,
        "csddd_article": i.csddd_article,
        "risk_category": i.risk_category,
        "is_active": i.is_active,
        "created_at": i.created_at,
    }


def _line(l: Any) -> dict:
    return {
        "id": l.id,
        "review_id": l.review_id,
        "indicator_id": l.indicator_id,
        "indicator_name": l.indicator_name,
        "measured_value": l.measured_value,
        "measured_text": l.measured_text,
        "comment": l.comment,
        "auto_populated": l.auto_populated,
    }


def _rev(r: Any) -> dict:
    return {
        "id": r.id,
        "organization_id": r.organization_id,
        "title": r.title,
        "period_start": r.period_start,
        "period_end": r.period_end,
        "overall_rating": r.overall_rating,
        "key_findings": r.key_findings,
        "improvement_actions": r.improvement_actions,
        "status": r.status,
        "submitted_at": r.submitted_at,
        "submitted_by": r.submitted_by,
        "approved_at": r.approved_at,
        "approved_by": r.approved_by,
        "lines": [_line(l) for l in r.lines],
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }
