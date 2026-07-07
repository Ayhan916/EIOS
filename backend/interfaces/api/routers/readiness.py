"""CSDDD-011 — CSDDD Readiness Score API.

Endpoints (authenticated):
  POST   /readiness/compute             compute & save a fresh snapshot
  GET    /readiness/latest              get the most recent snapshot
  GET    /readiness/history             list last N snapshots (default 12)

Security:
  - organization_id MANDATORY on all queries
  - Scoring is deterministic, auditable, no LLM (M43/M44 constraint)
  - All scores are saved for audit trail
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from application.csddd.readiness_calculator import compute
from domain.user import User
from infrastructure.persistence.repositories.readiness import SQLReadinessRepository
from interfaces.api.deps import get_current_user, get_sync_db

router = APIRouter(prefix="/readiness", tags=["readiness"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class ArticleScoreResponse(BaseModel):
    article: str
    title: str
    earned_points: int
    max_points: int
    score_pct: float
    level: str
    gaps: list[str]

    model_config = ConfigDict(from_attributes=True)


class ReadinessSnapshotResponse(BaseModel):
    id: UUID
    organization_id: UUID
    overall_score_pct: float
    overall_level: str
    article_scores: list[ArticleScoreResponse]
    computed_at: Any
    computed_by: str | None

    model_config = ConfigDict(from_attributes=True)


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/compute", response_model=ReadinessSnapshotResponse)
def compute_score(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    """Compute a fresh CSDDD readiness score and persist it as an audit snapshot.

    Fully deterministic — no LLM. Score is reproducible for audit purposes.
    """
    snapshot = compute(db, user.organization_id, computed_by=str(user.email or user.id))
    repo = SQLReadinessRepository(db)
    repo.save(snapshot)
    db.commit()
    return snapshot


@router.get("/latest", response_model=ReadinessSnapshotResponse)
def get_latest(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLReadinessRepository(db)
    snap = repo.latest(user.organization_id)
    if not snap:
        raise HTTPException(
            status_code=404, detail="No snapshot yet — POST /readiness/compute first"
        )
    return snap


@router.get("/history")
def get_history(
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLReadinessRepository(db)
    history = repo.history(user.organization_id, limit=limit)
    return [
        {
            "id": str(s.id),
            "overall_score_pct": s.overall_score_pct,
            "overall_level": s.overall_level,
            "computed_at": s.computed_at.isoformat() if s.computed_at else None,
            "computed_by": s.computed_by,
        }
        for s in history
    ]
