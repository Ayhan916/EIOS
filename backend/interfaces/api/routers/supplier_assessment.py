"""CSDDD-015 — Supplier Self-Assessment API (Art. 10 Abs. 2 lit. a).

Internal endpoints (authenticated):
  GET    /supplier-assessments/templates               list templates
  POST   /supplier-assessments/templates/seed          seed default 25-question template
  GET    /supplier-assessments/templates/{tid}         get template with questions
  POST   /supplier-assessments/                        create & send assessment (JWT link)
  GET    /supplier-assessments/                        list assessments
  GET    /supplier-assessments/{id}                    get assessment
  GET    /supplier-assessments/{id}/gap-report         gap analysis (deterministic)

Public endpoints (no auth — supplier portal):
  GET    /supplier-portal/assessment/{token}           get questionnaire
  POST   /supplier-portal/assessment/{token}/save      save progress (partial)
  POST   /supplier-portal/assessment/{token}/submit    submit final answers

Security:
  - submitted_by_email NEVER in any API response
  - IP address NEVER in any API response
  - Token = JWT signed with SECRET_KEY, 30-day TTL
  - Rate limit on public /submit enforced via RateLimiterMiddleware config
  - organization_id MANDATORY on all internal queries
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from application.supplier_assessment.gap_analyzer import analyze
from domain.enums import AssessmentStatus
from domain.user import User
from infrastructure.persistence.repositories.supplier_assessment import (
    SQLAssessmentTemplateRepository,
    SQLSupplierAssessmentRepository,
)
from interfaces.api.deps import get_current_user, get_sync_db
from shared.config import settings

router = APIRouter(prefix="/supplier-assessments", tags=["supplier-assessments"])
public_router = APIRouter(prefix="/supplier-portal", tags=["supplier-portal-public"])

_ALGORITHM = "HS256"
_TOKEN_TYPE = "csddd_assessment"
_TOKEN_TTL_DAYS = 30


def _make_token(assessment_id: str, supplier_id: str, expires_at: datetime) -> str:
    payload = {
        "type": _TOKEN_TYPE,
        "assessment_id": assessment_id,
        "supplier_id": supplier_id,
        "exp": int(expires_at.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


def _decode_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
    if payload.get("type") != _TOKEN_TYPE:
        raise jwt.InvalidTokenError("Wrong token type")
    return payload


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ── Schemas ────────────────────────────────────────────────────────────────────


class TemplateOut(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str
    is_default: bool
    created_by: str
    created_at: Any
    question_count: int

    model_config = ConfigDict(from_attributes=True)


class QuestionOut(BaseModel):
    id: str
    section: str
    question_text: str
    question_type: str
    options: list[str]
    csddd_article: str
    weight: int
    is_required: bool
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class TemplateDetailOut(TemplateOut):
    questions: list[QuestionOut] = []


class CreateAssessmentBody(BaseModel):
    template_id: str
    supplier_id: str


class AssessmentOut(BaseModel):
    id: str
    organization_id: str
    template_id: str
    supplier_id: str
    status: str
    reference_code: str
    token_expires_at: Any
    created_at: Any
    submitted_at: Any | None
    portal_link: str | None = None  # only on creation

    model_config = ConfigDict(from_attributes=True)


class GapItemOut(BaseModel):
    question_id: str
    section: str
    csddd_article: str
    question_text: str
    answer_given: str
    expected_answer: str
    severity: str
    recommendation: str


class SectionScoreOut(BaseModel):
    section: str
    total_questions: int
    answered: int
    gaps: int
    traffic_light: str


class GapReportOut(BaseModel):
    assessment_id: str
    supplier_id: str
    section_scores: list[SectionScoreOut]
    gaps: list[GapItemOut]
    overall_traffic_light: str
    total_gaps: int
    critical_gaps: int
    generated_at: Any


class PortalAnswers(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    submitter_email: str = Field(default="", max_length=255)
    confirm_accuracy: bool = Field(default=False)


# ── Internal endpoints ─────────────────────────────────────────────────────────


@router.post("/templates/seed", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def seed_template(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLAssessmentTemplateRepository(db)
    tmpl = repo.seed_default(user.organization_id, str(user.email or user.id))
    db.commit()
    return tmpl


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    repo = SQLAssessmentTemplateRepository(db)
    return repo.list_org(user.organization_id)


@router.get("/templates/{template_id}")
def get_template(
    template_id: str,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    trepo = SQLAssessmentTemplateRepository(db)
    tmpl = trepo.get(template_id, user.organization_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    questions = trepo.get_questions(template_id)
    return {
        **tmpl.__dict__,
        "questions": [q.__dict__ for q in questions],
    }


@router.post("/", response_model=AssessmentOut, status_code=status.HTTP_201_CREATED)
def create_assessment(
    body: CreateAssessmentBody,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    trepo = SQLAssessmentTemplateRepository(db)
    tmpl = trepo.get(body.template_id, user.organization_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    expires_at = datetime.now(UTC) + timedelta(days=_TOKEN_TTL_DAYS)
    arepo = SQLSupplierAssessmentRepository(db)

    # Create with a placeholder — real token needs the ID
    temp_token = _make_token("TEMP", body.supplier_id, expires_at)
    assessment = arepo.create(
        organization_id=user.organization_id,
        template_id=body.template_id,
        supplier_id=body.supplier_id,
        token=temp_token,
        token_expires_at=expires_at,
    )
    # Re-create token with real assessment ID and update hash
    real_token = _make_token(assessment.id, body.supplier_id, expires_at)
    # update token_hash in DB
    from infrastructure.persistence.models.supplier_assessment import SupplierAssessmentModel

    m = db.get(SupplierAssessmentModel, assessment.id)
    m.token_hash = _hash(real_token)
    db.commit()

    portal_link = f"/supplier/assessment/{real_token}"
    return {**assessment.__dict__, "portal_link": portal_link}


@router.get("/", response_model=list[AssessmentOut])
def list_assessments(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    arepo = SQLSupplierAssessmentRepository(db)
    return arepo.list_org(user.organization_id, status=status_filter)


@router.get("/{assessment_id}", response_model=AssessmentOut)
def get_assessment(
    assessment_id: str,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    arepo = SQLSupplierAssessmentRepository(db)
    a = arepo.get(assessment_id, user.organization_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return a


@router.get("/{assessment_id}/gap-report", response_model=GapReportOut)
def get_gap_report(
    assessment_id: str,
    db: Session = Depends(get_sync_db),
    user: User = Depends(get_current_user),
):
    arepo = SQLSupplierAssessmentRepository(db)
    a = arepo.get(assessment_id, user.organization_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if a.status not in (AssessmentStatus.SUBMITTED.value, AssessmentStatus.IN_PROGRESS.value):
        raise HTTPException(status_code=422, detail="No responses yet — assessment not started")

    trepo = SQLAssessmentTemplateRepository(db)
    questions = trepo.get_questions(a.template_id)
    responses = arepo.get_responses(assessment_id)

    report = analyze(questions, responses, assessment_id, a.supplier_id)
    return {
        "assessment_id": report.assessment_id,
        "supplier_id": report.supplier_id,
        "section_scores": [s.__dict__ for s in report.section_scores],
        "gaps": [g.__dict__ for g in report.gaps],
        "overall_traffic_light": report.overall_traffic_light,
        "total_gaps": report.total_gaps,
        "critical_gaps": report.critical_gaps,
        "generated_at": report.generated_at,
    }


# ── Public endpoints (no auth — supplier portal) ───────────────────────────────


def _resolve_token(token: str, db: Session):
    """Decode JWT and load the assessment model. Raises 401/404 on failure."""
    try:
        payload = _decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, detail="Assessment link has expired. Please request a new one."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid assessment link.")

    arepo = SQLSupplierAssessmentRepository(db)
    token_hash = _hash(token)
    m = arepo.get_by_token_hash(token_hash)
    if not m:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    if m.status in (AssessmentStatus.SUBMITTED.value, AssessmentStatus.ARCHIVED.value):
        raise HTTPException(status_code=410, detail="Assessment already submitted or archived.")
    return m, arepo, payload


@public_router.get("/assessment/{token}")
def portal_get_assessment(
    token: str,
    db: Session = Depends(get_sync_db),
):
    """Public — supplier reads the questionnaire. No authentication required."""
    m, arepo, _ = _resolve_token(token, db)
    arepo.mark_in_progress(m.token_hash)
    db.commit()

    trepo = SQLAssessmentTemplateRepository(db)
    questions = trepo.get_questions(m.template_id)
    tmpl = db.get(
        __import__(
            "infrastructure.persistence.models.supplier_assessment",
            fromlist=["AssessmentTemplateModel"],
        ).AssessmentTemplateModel,
        m.template_id,
    )
    existing_responses = arepo.get_responses(m.id)
    saved = {r.question_id: r.answer_value for r in existing_responses}

    return {
        "assessment_id": m.id,
        "template_title": tmpl.title if tmpl else "",
        "status": m.status,
        "reference_code": m.reference_code,
        "expires_at": m.token_expires_at,
        "questions": [
            {
                "id": q.id,
                "section": q.section,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": q.options,
                "csddd_article": q.csddd_article,
                "is_required": q.is_required,
                "sort_order": q.sort_order,
                "saved_answer": saved.get(q.id, ""),
            }
            for q in questions
            if q.is_active
        ],
    }


@public_router.post("/assessment/{token}/save")
def portal_save_progress(
    token: str,
    body: PortalAnswers,
    db: Session = Depends(get_sync_db),
):
    """Public — save partial progress. No authentication required."""
    m, arepo, _ = _resolve_token(token, db)
    arepo.save_responses(m.id, body.answers)
    db.commit()
    return {"saved": True, "answered_count": len(body.answers)}


@public_router.post("/assessment/{token}/submit")
def portal_submit(
    token: str,
    body: PortalAnswers,
    request: Request,
    db: Session = Depends(get_sync_db),
):
    """Public — final submission.

    submitted_by_email stored internally only — NEVER returned in response.
    IP address NEVER returned in response.
    """
    if not body.confirm_accuracy:
        raise HTTPException(
            status_code=422, detail="You must confirm the accuracy of your answers."
        )

    m, arepo, _ = _resolve_token(token, db)
    assessment, ref_code = arepo.submit(
        token_hash=_hash(token),
        answers=body.answers,
        submitted_by_email=body.submitter_email,  # stored internally, not echoed back
    )
    db.commit()
    # Return only safe fields — no email, no IP
    return {
        "submitted": True,
        "reference_code": ref_code,
        "message": "Your self-assessment has been submitted. Please save your reference code.",
    }
