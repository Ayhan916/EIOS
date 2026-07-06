"""CSDDD-014 — Regulatory Change Radar API (Art. 7 Abs. 4).

GET  /regulatory-radar/dashboard         KPI summary
GET  /regulatory-radar/sources           list sources (global + org)
POST /regulatory-radar/sources/seed      seed global library (10 sources)
GET  /regulatory-radar/changes           list changes
POST /regulatory-radar/changes           create manual change
GET  /regulatory-radar/changes/{id}      get change
PATCH /regulatory-radar/changes/{id}     update status / impact analysis
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from domain.user import User
from infrastructure.persistence.repositories.regulatory_radar import (
    SQLRegulatoryChangeRepository,
    SQLRegulatorySourceRepository,
)
from interfaces.api.deps import get_current_user, get_sync_db

router = APIRouter(prefix="/regulatory-radar", tags=["regulatory-radar"])

VALID_STATUSES = {"new", "analysed", "implemented", "not_relevant"}
VALID_ACTIONS = {"yes", "no", "pending"}
EIOS_MODULES = ["risks", "supply_chain", "compliance", "assessments", "findings", "board_signoff", "grievance", "remediation", "effectiveness", "scoping", "reporting"]


class ChangeCreate(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    source_name: str = Field(default="Manual Entry", max_length=255)
    summary: str = Field(default="", max_length=10000)
    url: Optional[str] = Field(default=None, max_length=500)
    effective_date: Optional[datetime] = None
    affected_articles: list[str] = Field(default_factory=list)
    action_required: str = Field(default="pending")
    action_description: str = Field(default="", max_length=5000)
    impact_modules: list[str] = Field(default_factory=list)
    estimated_effort_days: int = Field(default=0, ge=0)
    due_date: Optional[datetime] = None
    source_id: Optional[str] = None


class ChangeUpdate(BaseModel):
    status: Optional[str] = None
    action_required: Optional[str] = None
    action_description: Optional[str] = None
    impact_modules: Optional[list[str]] = None
    estimated_effort_days: Optional[int] = None
    due_date: Optional[datetime] = None


class ChangeOut(BaseModel):
    id: str
    organization_id: str
    title: str
    source_name: str
    url: Optional[str]
    effective_date: Optional[Any]
    summary: str
    affected_articles: list[str]
    status: str
    action_required: str
    action_description: str
    impact_modules: list[str]
    estimated_effort_days: int
    due_date: Optional[Any]
    created_by: str
    created_at: Any
    updated_at: Any

    model_config = ConfigDict(from_attributes=True)


class SourceOut(BaseModel):
    id: str
    organization_id: Optional[str]
    name: str
    url: str
    description: str
    relevance_score: int
    country_code: Optional[str]
    rss_feed_url: Optional[str]
    is_active: bool
    last_fetched_at: Optional[Any]

    model_config = ConfigDict(from_attributes=True)


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLRegulatoryChangeRepository(db)
    return repo.dashboard(user.organization_id)


@router.get("/sources", response_model=list[SourceOut])
def list_sources(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    return SQLRegulatorySourceRepository(db).list_for_org(user.organization_id)


@router.post("/sources/seed")
def seed_sources(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    created = SQLRegulatorySourceRepository(db).seed_global()
    db.commit()
    return {"seeded": len(created), "message": f"{len(created)} global regulatory sources seeded."}


@router.get("/changes", response_model=list[ChangeOut])
def list_changes(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    action_required: Optional[str] = Query(default=None),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLRegulatoryChangeRepository(db)
    return repo.list_org(user.organization_id, status=status_filter, action_required=action_required)


@router.post("/changes", response_model=ChangeOut, status_code=status.HTTP_201_CREATED)
def create_change(
    body: ChangeCreate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    if body.action_required not in VALID_ACTIONS:
        raise HTTPException(status_code=422, detail=f"action_required must be one of {VALID_ACTIONS}")
    repo = SQLRegulatoryChangeRepository(db)
    change = repo.create(
        organization_id=user.organization_id,
        title=body.title,
        source_name=body.source_name,
        summary=body.summary,
        affected_articles=body.affected_articles,
        created_by=str(user.email or user.id),
        url=body.url,
        effective_date=body.effective_date,
        action_required=body.action_required,
        action_description=body.action_description,
        impact_modules=body.impact_modules,
        estimated_effort_days=body.estimated_effort_days,
        due_date=body.due_date,
        source_id=body.source_id,
    )
    db.commit()
    return change


@router.get("/changes/{change_id}", response_model=ChangeOut)
def get_change(
    change_id: str,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    c = SQLRegulatoryChangeRepository(db).get(change_id, user.organization_id)
    if not c:
        raise HTTPException(status_code=404, detail="Change not found")
    return c


@router.patch("/changes/{change_id}", response_model=ChangeOut)
def update_change(
    change_id: str,
    body: ChangeUpdate,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {VALID_STATUSES}")
    if body.action_required and body.action_required not in VALID_ACTIONS:
        raise HTTPException(status_code=422, detail=f"action_required must be one of {VALID_ACTIONS}")
    repo = SQLRegulatoryChangeRepository(db)
    c = repo.update_status(
        change_id,
        user.organization_id,
        status=body.status or "new",
        action_required=body.action_required,
        action_description=body.action_description,
        impact_modules=body.impact_modules,
        estimated_effort_days=body.estimated_effort_days,
        due_date=body.due_date,
    )
    if not c:
        raise HTTPException(status_code=404, detail="Change not found")
    db.commit()
    return c
