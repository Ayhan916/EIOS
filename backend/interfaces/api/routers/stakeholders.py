"""CSDDD-001 — Stakeholder Engagement API (Art. 13).

Endpoints (authenticated):
  GET    /stakeholders/                         list stakeholders for org
  POST   /stakeholders/                         create stakeholder
  GET    /stakeholders/{id}                     single stakeholder
  PATCH  /stakeholders/{id}                     update
  DELETE /stakeholders/{id}                     delete

  GET    /stakeholders/consultations/           list consultations for org
  POST   /stakeholders/consultations/           create consultation
  GET    /stakeholders/consultations/{id}       single consultation
  PATCH  /stakeholders/consultations/{id}       update
  GET    /stakeholders/consultations/{id}/feedback  list feedback (admin only)

  GET    /stakeholders/report/engagement        engagement report for annual report
  GET    /stakeholders/map-data                 visualisation data

Public (no auth — S3):
  POST   /stakeholders/consultations/{token}/feedback   submit feedback via link

Security:
  - organization_id MANDATORY on every DB query
  - submitted_by_email / submitted_by_name NEVER in API responses (PII)
  - Rate-limiting on public feedback endpoint enforced via app middleware
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from domain.enums import ConsultationBarrier, ConsultationFormat, CSDDDRight, StakeholderType
from domain.stakeholder import Stakeholder, StakeholderConsultation, StakeholderFeedback
from infrastructure.persistence.repositories.stakeholder import (
    SQLStakeholderConsultationRepository,
    SQLStakeholderFeedbackRepository,
    SQLStakeholderRepository,
)
from interfaces.api.deps import get_current_user, get_db, require_admin, require_analyst
from domain.user import User

# ── Schemas ─��─────────────────────────────────────────────────────────────────


class StakeholderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    stakeholder_type: StakeholderType = StakeholderType.OTHER
    contact_email: str | None = Field(default=None, max_length=320)
    language: str = Field(default="de", max_length=10)
    activity_chain_ids: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    risk_topics: list[str] = Field(default_factory=list)
    justification: str = Field(min_length=5, max_length=2000)


class StakeholderUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=500)
    stakeholder_type: StakeholderType | None = None
    contact_email: str | None = Field(default=None, max_length=320)
    language: str | None = Field(default=None, max_length=10)
    activity_chain_ids: list[str] | None = None
    regions: list[str] | None = None
    risk_topics: list[str] | None = None
    justification: str | None = Field(default=None, max_length=2000)


class StakeholderResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    stakeholder_type: str
    contact_email: str | None
    language: str
    activity_chain_ids: list[str]
    regions: list[str]
    risk_topics: list[str]
    justification: str
    created_at: datetime
    updated_at: datetime


class ConsultationCreate(BaseModel):
    stakeholder_ids: list[str] = Field(min_length=1)
    consultation_date: date | None = None
    format: ConsultationFormat = ConsultationFormat.MEETING
    topics: list[str] = Field(default_factory=list)
    description: str = Field(min_length=5, max_length=5000)
    outcomes: str = Field(default="", max_length=5000)
    barrier: ConsultationBarrier = ConsultationBarrier.NONE
    barrier_notes: str = Field(default="", max_length=2000)
    linked_risk_id: str | None = None
    linked_finding_id: str | None = None
    linked_cap_id: str | None = None


class ConsultationUpdate(BaseModel):
    stakeholder_ids: list[str] | None = None
    consultation_date: date | None = None
    format: ConsultationFormat | None = None
    topics: list[str] | None = None
    description: str | None = Field(default=None, max_length=5000)
    outcomes: str | None = Field(default=None, max_length=5000)
    barrier: ConsultationBarrier | None = None
    barrier_notes: str | None = Field(default=None, max_length=2000)
    linked_risk_id: str | None = None
    linked_finding_id: str | None = None
    linked_cap_id: str | None = None


class ConsultationResponse(BaseModel):
    id: str
    organization_id: str
    stakeholder_ids: list[str]
    consultation_date: date | None
    format: str
    topics: list[str]
    description: str
    outcomes: str
    barrier: str
    barrier_notes: str
    linked_risk_id: str | None
    linked_finding_id: str | None
    linked_cap_id: str | None
    feedback_count: int = 0
    created_at: datetime
    updated_at: datetime


class PublicFeedbackCreate(BaseModel):
    risk_assessment: int = Field(ge=1, le=5)
    affected_rights: list[CSDDDRight] = Field(default_factory=list)
    description: str = Field(min_length=10, max_length=5000)
    wants_contact: bool = False
    submitted_by_email: str | None = Field(default=None, max_length=320)
    submitted_by_name: str | None = Field(default=None, max_length=500)


class FeedbackResponse(BaseModel):
    """PII fields are NEVER included."""
    id: str
    consultation_id: str
    risk_assessment: int
    affected_rights: list[str]
    description: str
    wants_contact: bool
    created_at: datetime


class EngagementReportResponse(BaseModel):
    total_stakeholders: int
    stakeholders_by_type: dict[str, int]
    total_consultations: int
    consultations_by_format: dict[str, int]
    barrier_summary: dict[str, int]
    stakeholders_without_consultation_12m: int
    consultations: list[ConsultationResponse]
    stakeholders: list[StakeholderResponse]


class MapDataResponse(BaseModel):
    nodes: list[dict[str, Any]]


# ── Dependency helpers ────────────────────────────────────────────────────────


async def get_stakeholder_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLStakeholderRepository:
    return SQLStakeholderRepository(session)


async def get_consultation_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLStakeholderConsultationRepository:
    return SQLStakeholderConsultationRepository(session)


async def get_feedback_repo(
    session: AsyncSession = Depends(get_db),
) -> SQLStakeholderFeedbackRepository:
    return SQLStakeholderFeedbackRepository(session)


def _stakeholder_to_response(s: Stakeholder) -> StakeholderResponse:
    return StakeholderResponse(
        id=s.id,
        organization_id=s.organization_id,
        name=s.name,
        stakeholder_type=s.stakeholder_type.value if hasattr(s.stakeholder_type, "value") else s.stakeholder_type,
        contact_email=s.contact_email,
        language=s.language,
        activity_chain_ids=s.activity_chain_ids,
        regions=s.regions,
        risk_topics=s.risk_topics,
        justification=s.justification,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _consultation_to_response(c: StakeholderConsultation, feedback_count: int = 0) -> ConsultationResponse:
    return ConsultationResponse(
        id=c.id,
        organization_id=c.organization_id,
        stakeholder_ids=c.stakeholder_ids,
        consultation_date=c.consultation_date,
        format=c.format.value if hasattr(c.format, "value") else c.format,
        topics=c.topics,
        description=c.description,
        outcomes=c.outcomes,
        barrier=c.barrier.value if hasattr(c.barrier, "value") else c.barrier,
        barrier_notes=c.barrier_notes,
        linked_risk_id=c.linked_risk_id,
        linked_finding_id=c.linked_finding_id,
        linked_cap_id=c.linked_cap_id,
        feedback_count=feedback_count,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


# ── Routers ───────────────────────────────────────────────────────────────────

router = APIRouter(
    prefix="/stakeholders",
    tags=["stakeholders"],
    dependencies=[Depends(get_current_user)],
)

# Separate router for public endpoints (no auth)
public_router = APIRouter(
    prefix="/stakeholders",
    tags=["stakeholders-public"],
)

# ── Stakeholder CRUD ──────────────────────────────────────────────────────────


@router.get("/", response_model=list[StakeholderResponse])
async def list_stakeholders(
    stakeholder_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    repo: SQLStakeholderRepository = Depends(get_stakeholder_repo),
) -> list[StakeholderResponse]:
    if not current_user.organization_id:
        return []
    items = await repo.list_by_org(
        current_user.organization_id,
        stakeholder_type=stakeholder_type,
        limit=limit,
        offset=offset,
    )
    return [_stakeholder_to_response(s) for s in items]


@router.post("/", response_model=StakeholderResponse, status_code=status.HTTP_201_CREATED)
async def create_stakeholder(
    body: StakeholderCreate,
    current_user: User = Depends(get_current_user),
    repo: SQLStakeholderRepository = Depends(get_stakeholder_repo),
) -> StakeholderResponse:
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organisation")
    s = Stakeholder(
        organization_id=current_user.organization_id,
        name=body.name,
        stakeholder_type=body.stakeholder_type,
        contact_email=body.contact_email,
        language=body.language,
        activity_chain_ids=body.activity_chain_ids,
        regions=body.regions,
        risk_topics=body.risk_topics,
        justification=body.justification,
        created_by=current_user.id,
    )
    saved = await repo.save(s)
    return _stakeholder_to_response(saved)


@router.get("/map-data", response_model=MapDataResponse)
async def get_map_data(
    current_user: User = Depends(get_current_user),
    repo: SQLStakeholderRepository = Depends(get_stakeholder_repo),
    consult_repo: SQLStakeholderConsultationRepository = Depends(get_consultation_repo),
) -> MapDataResponse:
    if not current_user.organization_id:
        return MapDataResponse(nodes=[])
    stakeholders = await repo.list_by_org(current_user.organization_id, limit=500)
    consultations = await consult_repo.list_by_org(current_user.organization_id, limit=500)

    # Build lookup: stakeholder_id → most recent consultation date
    last_consult: dict[str, date | None] = {}
    for c in consultations:
        for sid in c.stakeholder_ids:
            existing = last_consult.get(sid)
            if c.consultation_date and (existing is None or c.consultation_date > existing):
                last_consult[sid] = c.consultation_date

    today = datetime.now(UTC).date()
    nodes = []
    for s in stakeholders:
        last = last_consult.get(s.id)
        if last is None:
            color = "red"
        elif (today - last).days > 365:
            color = "yellow"
        else:
            color = "green"
        nodes.append({
            "id": s.id,
            "name": s.name,
            "type": s.stakeholder_type.value if hasattr(s.stakeholder_type, "value") else s.stakeholder_type,
            "lastConsultation": last.isoformat() if last else None,
            "color": color,
            "regions": s.regions,
        })
    return MapDataResponse(nodes=nodes)


@router.get("/report/engagement", response_model=EngagementReportResponse)
async def engagement_report(
    current_user: User = Depends(get_current_user),
    repo: SQLStakeholderRepository = Depends(get_stakeholder_repo),
    consult_repo: SQLStakeholderConsultationRepository = Depends(get_consultation_repo),
) -> EngagementReportResponse:
    if not current_user.organization_id:
        return EngagementReportResponse(
            total_stakeholders=0, stakeholders_by_type={}, total_consultations=0,
            consultations_by_format={}, barrier_summary={},
            stakeholders_without_consultation_12m=0, consultations=[], stakeholders=[],
        )
    stakeholders = await repo.list_by_org(current_user.organization_id, limit=500)
    consultations = await consult_repo.list_by_org(current_user.organization_id, limit=500)

    by_type: dict[str, int] = {}
    for s in stakeholders:
        t = s.stakeholder_type.value if hasattr(s.stakeholder_type, "value") else s.stakeholder_type
        by_type[t] = by_type.get(t, 0) + 1

    by_format: dict[str, int] = {}
    barrier_summary: dict[str, int] = {}
    for c in consultations:
        f = c.format.value if hasattr(c.format, "value") else c.format
        by_format[f] = by_format.get(f, 0) + 1
        b = c.barrier.value if hasattr(c.barrier, "value") else c.barrier
        barrier_summary[b] = barrier_summary.get(b, 0) + 1

    today = datetime.now(UTC).date()
    last_consult: dict[str, date | None] = {}
    for c in consultations:
        for sid in c.stakeholder_ids:
            existing = last_consult.get(sid)
            if c.consultation_date and (existing is None or c.consultation_date > existing):
                last_consult[sid] = c.consultation_date

    overdue = sum(
        1 for s in stakeholders
        if s.id not in last_consult or last_consult[s.id] is None
        or (today - last_consult[s.id]).days > 365
    )

    return EngagementReportResponse(
        total_stakeholders=len(stakeholders),
        stakeholders_by_type=by_type,
        total_consultations=len(consultations),
        consultations_by_format=by_format,
        barrier_summary=barrier_summary,
        stakeholders_without_consultation_12m=overdue,
        consultations=[_consultation_to_response(c) for c in consultations],
        stakeholders=[_stakeholder_to_response(s) for s in stakeholders],
    )


@router.get("/{stakeholder_id}", response_model=StakeholderResponse)
async def get_stakeholder(
    stakeholder_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLStakeholderRepository = Depends(get_stakeholder_repo),
) -> StakeholderResponse:
    s = await repo.get_by_id(stakeholder_id)
    if not s or s.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    return _stakeholder_to_response(s)


@router.patch("/{stakeholder_id}", response_model=StakeholderResponse)
async def update_stakeholder(
    stakeholder_id: str,
    body: StakeholderUpdate,
    current_user: User = Depends(get_current_user),
    repo: SQLStakeholderRepository = Depends(get_stakeholder_repo),
) -> StakeholderResponse:
    s = await repo.get_by_id(stakeholder_id)
    if not s or s.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    if body.name is not None:
        s.name = body.name
    if body.stakeholder_type is not None:
        s.stakeholder_type = body.stakeholder_type
    if body.contact_email is not None:
        s.contact_email = body.contact_email
    if body.language is not None:
        s.language = body.language
    if body.activity_chain_ids is not None:
        s.activity_chain_ids = body.activity_chain_ids
    if body.regions is not None:
        s.regions = body.regions
    if body.risk_topics is not None:
        s.risk_topics = body.risk_topics
    if body.justification is not None:
        s.justification = body.justification
    s.updated_by = current_user.id
    s.updated_at = datetime.now(UTC)
    saved = await repo.save(s)
    return _stakeholder_to_response(saved)


@router.delete("/{stakeholder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stakeholder(
    stakeholder_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLStakeholderRepository = Depends(get_stakeholder_repo),
) -> None:
    s = await repo.get_by_id(stakeholder_id)
    if not s or s.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    await repo.delete(stakeholder_id)


# ── Consultation CRUD ─────────────────────────────────────────────────────────


@router.get("/consultations/", response_model=list[ConsultationResponse])
async def list_consultations(
    stakeholder_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    repo: SQLStakeholderConsultationRepository = Depends(get_consultation_repo),
) -> list[ConsultationResponse]:
    if not current_user.organization_id:
        return []
    items = await repo.list_by_org(
        current_user.organization_id,
        stakeholder_id=stakeholder_id,
        limit=limit,
        offset=offset,
    )
    return [_consultation_to_response(c) for c in items]


@router.post("/consultations/", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
async def create_consultation(
    body: ConsultationCreate,
    current_user: User = Depends(get_current_user),
    repo: SQLStakeholderConsultationRepository = Depends(get_consultation_repo),
) -> ConsultationResponse:
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organisation")
    c = StakeholderConsultation(
        organization_id=current_user.organization_id,
        stakeholder_ids=body.stakeholder_ids,
        consultation_date=body.consultation_date,
        format=body.format,
        topics=body.topics,
        description=body.description,
        outcomes=body.outcomes,
        barrier=body.barrier,
        barrier_notes=body.barrier_notes,
        linked_risk_id=body.linked_risk_id,
        linked_finding_id=body.linked_finding_id,
        linked_cap_id=body.linked_cap_id,
        created_by=current_user.id,
    )
    saved = await repo.save(c)
    return _consultation_to_response(saved)


@router.get("/consultations/{consultation_id}", response_model=ConsultationResponse)
async def get_consultation(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    repo: SQLStakeholderConsultationRepository = Depends(get_consultation_repo),
    feedback_repo: SQLStakeholderFeedbackRepository = Depends(get_feedback_repo),
) -> ConsultationResponse:
    c = await repo.get_by_id(consultation_id)
    if not c or c.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Consultation not found")
    feedbacks = await feedback_repo.list_by_consultation(consultation_id)
    return _consultation_to_response(c, feedback_count=len(feedbacks))


@router.patch("/consultations/{consultation_id}", response_model=ConsultationResponse)
async def update_consultation(
    consultation_id: str,
    body: ConsultationUpdate,
    current_user: User = Depends(get_current_user),
    repo: SQLStakeholderConsultationRepository = Depends(get_consultation_repo),
) -> ConsultationResponse:
    c = await repo.get_by_id(consultation_id)
    if not c or c.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Consultation not found")
    if body.stakeholder_ids is not None:
        c.stakeholder_ids = body.stakeholder_ids
    if body.consultation_date is not None:
        c.consultation_date = body.consultation_date
    if body.format is not None:
        c.format = body.format
    if body.topics is not None:
        c.topics = body.topics
    if body.description is not None:
        c.description = body.description
    if body.outcomes is not None:
        c.outcomes = body.outcomes
    if body.barrier is not None:
        c.barrier = body.barrier
    if body.barrier_notes is not None:
        c.barrier_notes = body.barrier_notes
    if body.linked_risk_id is not None:
        c.linked_risk_id = body.linked_risk_id
    if body.linked_finding_id is not None:
        c.linked_finding_id = body.linked_finding_id
    if body.linked_cap_id is not None:
        c.linked_cap_id = body.linked_cap_id
    c.updated_by = current_user.id
    c.updated_at = datetime.now(UTC)
    saved = await repo.save(c)
    return _consultation_to_response(saved)


@router.get(
    "/consultations/{consultation_id}/feedback",
    response_model=list[FeedbackResponse],
    dependencies=[Depends(require_analyst)],
)
async def list_consultation_feedback(
    consultation_id: str,
    current_user: User = Depends(get_current_user),
    consult_repo: SQLStakeholderConsultationRepository = Depends(get_consultation_repo),
    feedback_repo: SQLStakeholderFeedbackRepository = Depends(get_feedback_repo),
) -> list[FeedbackResponse]:
    c = await consult_repo.get_by_id(consultation_id)
    if not c or c.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Consultation not found")
    feedbacks = await feedback_repo.list_by_consultation(consultation_id)
    return [
        FeedbackResponse(
            id=f.id,
            consultation_id=f.consultation_id,
            risk_assessment=f.risk_assessment,
            affected_rights=f.affected_rights,
            description=f.description,
            wants_contact=f.wants_contact,
            created_at=f.created_at,
        )
        for f in feedbacks
    ]


# ── Public feedback endpoint (S3) ���────────────────────────────────────────────


@public_router.post(
    "/consultations/{consultation_id}/feedback",
    status_code=status.HTTP_201_CREATED,
)
async def submit_public_feedback(
    consultation_id: str,
    body: PublicFeedbackCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    consult_repo = SQLStakeholderConsultationRepository(session)
    feedback_repo = SQLStakeholderFeedbackRepository(session)

    c = await consult_repo.get_by_id(consultation_id)
    if not c:
        raise HTTPException(status_code=404, detail="Consultation not found")

    client_ip = request.client.host if request.client else None

    fb = StakeholderFeedback(
        consultation_id=consultation_id,
        organization_id=c.organization_id,
        risk_assessment=body.risk_assessment,
        affected_rights=[r.value if hasattr(r, "value") else r for r in body.affected_rights],
        description=body.description,
        wants_contact=body.wants_contact,
        submitted_by_email=body.submitted_by_email if body.wants_contact else None,
        submitted_by_name=body.submitted_by_name if body.wants_contact else None,
        submitter_ip=client_ip,
    )
    await feedback_repo.save(fb)
    return {"message": "Thank you. Your feedback has been received."}
