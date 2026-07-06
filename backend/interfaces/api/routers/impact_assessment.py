"""CSDDD-012 — Impact Severity Calculator API (Art. 3/6).

Endpoints (authenticated):
  POST   /impact/preview             compute score without saving (live calculator)
  GET    /impact/dashboard           KPI overview
  GET    /impact/                    list assessments
  POST   /impact/                    create assessment
  GET    /impact/{id}                get assessment
  PUT    /impact/{id}                update (recomputes score deterministically)
  DELETE /impact/{id}                delete

Security:
  - organization_id MANDATORY
  - Scoring fully deterministic, no LLM (M43/M44)
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from domain.user import User
from infrastructure.persistence.repositories.impact_assessment import SQLImpactAssessmentRepository
from interfaces.api.deps import get_current_user, get_sync_db

router = APIRouter(prefix="/impact", tags=["impact"])

VALID_IMPACT_TYPES = {"human_rights", "labor_rights", "environment", "health_safety", "anti_corruption", "other"}
VALID_ENTITY_TYPES = {"finding", "risk", "supplier", "assessment", "standalone"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class DimensionScore(BaseModel):
    gravity: int = Field(ge=1, le=5, description="1=minor, 5=catastrophic")
    scope: int = Field(ge=1, le=5, description="1=individual, 5=widespread")
    remediability: int = Field(ge=1, le=5, description="1=easily reversible, 5=irremediable")
    likelihood: int = Field(ge=1, le=5, description="1=very unlikely, 5=certain/ongoing")


class AssessmentCreate(DimensionScore):
    title: str = Field(min_length=3, max_length=255)
    impact_type: str = Field(default="other")
    entity_type: str = Field(default="standalone")
    entity_id: Optional[UUID] = None
    justification: Optional[str] = Field(default=None, max_length=5000)


class AssessmentUpdate(DimensionScore):
    title: Optional[str] = Field(default=None, max_length=255)
    justification: Optional[str] = Field(default=None, max_length=5000)


class AssessmentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    title: str
    impact_type: str
    entity_type: str
    entity_id: Optional[UUID]
    gravity: int
    scope: int
    remediability: int
    likelihood: int
    severity_score: float
    priority_score: float
    severity_level: str
    justification: Optional[str]
    created_by: str
    created_at: Any
    updated_at: Any

    model_config = ConfigDict(from_attributes=True)


class PreviewResponse(BaseModel):
    severity_score: float
    priority_score: float
    severity_level: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/preview", response_model=PreviewResponse)
def preview_score(
    body: DimensionScore,
    user: User = Depends(get_current_user),
):
    """Compute severity score in real-time without saving. Used by the live calculator UI."""
    from application.csddd.severity_calculator import assess
    return assess(body.gravity, body.scope, body.remediability, body.likelihood)


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLImpactAssessmentRepository(db)
    return repo.dashboard(user.organization_id)


@router.get("/", response_model=list[AssessmentResponse])
def list_assessments(
    severity_level: Optional[str] = Query(default=None),
    impact_type: Optional[str] = Query(default=None),
    entity_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLImpactAssessmentRepository(db)
    return repo.list_org(
        user.organization_id,
        severity_level=severity_level,
        impact_type=impact_type,
        entity_id=str(entity_id) if entity_id else None,
    )


@router.post("/", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_assessment(
    body: AssessmentCreate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    if body.impact_type not in VALID_IMPACT_TYPES:
        raise HTTPException(status_code=422, detail=f"impact_type must be one of {VALID_IMPACT_TYPES}")
    if body.entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=422, detail=f"entity_type must be one of {VALID_ENTITY_TYPES}")

    repo = SQLImpactAssessmentRepository(db)
    a = repo.create(
        organization_id=user.organization_id,
        title=body.title,
        impact_type=body.impact_type,
        entity_type=body.entity_type,
        entity_id=str(body.entity_id) if body.entity_id else None,
        gravity=body.gravity,
        scope=body.scope,
        remediability=body.remediability,
        likelihood=body.likelihood,
        justification=body.justification,
        created_by=str(user.id),
    )
    db.commit()
    return a


@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLImpactAssessmentRepository(db)
    a = repo.get(str(assessment_id), user.organization_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return a


@router.put("/{assessment_id}", response_model=AssessmentResponse)
def update_assessment(
    assessment_id: UUID,
    body: AssessmentUpdate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLImpactAssessmentRepository(db)
    a = repo.update(
        str(assessment_id),
        user.organization_id,
        gravity=body.gravity,
        scope=body.scope,
        remediability=body.remediability,
        likelihood=body.likelihood,
        title=body.title,
        justification=body.justification,
    )
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    db.commit()
    return a


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment(
    assessment_id: UUID,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLImpactAssessmentRepository(db)
    if not repo.delete(str(assessment_id), user.organization_id):
        raise HTTPException(status_code=404, detail="Assessment not found")
    db.commit()
