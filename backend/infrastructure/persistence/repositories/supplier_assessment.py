"""Repositories — Supplier Self-Assessment CSDDD (CSDDD-015)."""

from __future__ import annotations

import hashlib
import json
import random
import string
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.enums import AssessmentStatus
from domain.supplier_assessment import (
    AssessmentQuestion,
    AssessmentResponse,
    AssessmentTemplate,
    SupplierAssessment,
)
from infrastructure.persistence.models.supplier_assessment import (
    AssessmentQuestionModel,
    AssessmentResponseModel,
    AssessmentTemplateModel,
    SupplierAssessmentModel,
)

SEED_QUESTIONS: list[dict] = [
    # ── Section A: Company Structure (Art. 7) ────────────────────────────────
    {
        "section": "company_structure",
        "question_text": "Does your company have a documented ownership and governance structure?",
        "question_type": "yes_no",
        "csddd_article": "Art. 7",
        "weight": 3,
        "sort_order": 1,
    },
    {
        "section": "company_structure",
        "question_text": "Is your company registered and operating legally in its country of domicile?",
        "question_type": "yes_no",
        "csddd_article": "Art. 7",
        "weight": 4,
        "sort_order": 2,
    },
    {
        "section": "company_structure",
        "question_text": "Does your company have an appointed compliance or ESG responsible person?",
        "question_type": "yes_no",
        "csddd_article": "Art. 7",
        "weight": 3,
        "sort_order": 3,
    },
    {
        "section": "company_structure",
        "question_text": "How many direct employees does your company have?",
        "question_type": "text",
        "csddd_article": "Art. 7",
        "weight": 1,
        "sort_order": 4,
        "is_required": False,
    },
    {
        "section": "company_structure",
        "question_text": "Does your company publish an annual sustainability or ESG report?",
        "question_type": "yes_no",
        "csddd_article": "Art. 7",
        "weight": 2,
        "sort_order": 5,
    },
    # ── Section B: HR Policies (Art. 10 + Annex I) ───────────────────────────
    {
        "section": "hr_policies",
        "question_text": "Does your company have a written Human Rights Policy?",
        "question_type": "yes_no",
        "csddd_article": "Art. 10 Annex I",
        "weight": 5,
        "sort_order": 6,
    },
    {
        "section": "hr_policies",
        "question_text": "Does your company prohibit child labour in all operations and supply chain?",
        "question_type": "yes_no",
        "csddd_article": "Art. 10 Annex I Item 1",
        "weight": 5,
        "sort_order": 7,
    },
    {
        "section": "hr_policies",
        "question_text": "Does your company prohibit forced or compulsory labour?",
        "question_type": "yes_no",
        "csddd_article": "Art. 10 Annex I Item 2",
        "weight": 5,
        "sort_order": 8,
    },
    {
        "section": "hr_policies",
        "question_text": "Does your company ensure freedom of association and right to collective bargaining?",
        "question_type": "yes_no",
        "csddd_article": "Art. 10 Annex I Item 3",
        "weight": 4,
        "sort_order": 9,
    },
    {
        "section": "hr_policies",
        "question_text": "Does your company ensure equal pay and non-discrimination in employment?",
        "question_type": "yes_no",
        "csddd_article": "Art. 10 Annex I Item 6",
        "weight": 4,
        "sort_order": 10,
    },
    {
        "section": "hr_policies",
        "question_text": "Does your company conduct regular worker health and safety assessments?",
        "question_type": "yes_no",
        "csddd_article": "Art. 10 Annex I Item 5",
        "weight": 4,
        "sort_order": 11,
    },
    {
        "section": "hr_policies",
        "question_text": "Rate your company's maturity in human rights due diligence (1=none, 5=advanced)",
        "question_type": "scale_1_5",
        "csddd_article": "Art. 10 Annex I",
        "weight": 4,
        "sort_order": 12,
    },
    # ── Section C: Environmental Measures (Art. 10 + Annex II) ───────────────
    {
        "section": "environment",
        "question_text": "Does your company have a documented environmental management system (e.g. ISO 14001)?",
        "question_type": "yes_no",
        "csddd_article": "Art. 10 Annex II",
        "weight": 4,
        "sort_order": 13,
    },
    {
        "section": "environment",
        "question_text": "Does your company measure and report greenhouse gas emissions (Scope 1 and 2)?",
        "question_type": "yes_no",
        "csddd_article": "Art. 10 Annex II",
        "weight": 3,
        "sort_order": 14,
    },
    {
        "section": "environment",
        "question_text": "Does your company have policies to prevent or minimise adverse environmental impacts?",
        "question_type": "yes_no",
        "csddd_article": "Art. 10 Annex II",
        "weight": 4,
        "sort_order": 15,
    },
    {
        "section": "environment",
        "question_text": "Does your company comply with applicable regulations on hazardous substances and waste disposal?",
        "question_type": "yes_no",
        "csddd_article": "Art. 10 Annex II Item 3",
        "weight": 5,
        "sort_order": 16,
    },
    {
        "section": "environment",
        "question_text": "Rate your company's maturity in environmental due diligence (1=none, 5=advanced)",
        "question_type": "scale_1_5",
        "csddd_article": "Art. 10 Annex II",
        "weight": 3,
        "sort_order": 17,
    },
    # ── Section D: Grievance Mechanism (Art. 14) ─────────────────────────────
    {
        "section": "grievance",
        "question_text": "Does your company provide a grievance or complaints mechanism for workers and affected communities?",
        "question_type": "yes_no",
        "csddd_article": "Art. 14",
        "weight": 5,
        "sort_order": 18,
    },
    {
        "section": "grievance",
        "question_text": "Is the grievance mechanism accessible to all workers including migrant and agency workers?",
        "question_type": "yes_no",
        "csddd_article": "Art. 14",
        "weight": 4,
        "sort_order": 19,
    },
    {
        "section": "grievance",
        "question_text": "Does your company track and report on grievance resolution outcomes?",
        "question_type": "yes_no",
        "csddd_article": "Art. 14",
        "weight": 3,
        "sort_order": 20,
    },
    {
        "section": "grievance",
        "question_text": "Describe how grievances are investigated and remediated at your company.",
        "question_type": "text",
        "csddd_article": "Art. 14",
        "weight": 3,
        "sort_order": 21,
        "is_required": False,
    },
    # ── Section E: Sub-suppliers / Cascade (Art. 10 Abs. 2 lit. b) ───────────
    {
        "section": "sub_suppliers",
        "question_text": "Does your company require direct sub-suppliers to comply with equivalent human rights and environmental standards?",
        "question_type": "yes_no",
        "csddd_article": "Art. 10 Abs. 2 lit. b",
        "weight": 5,
        "sort_order": 22,
    },
    {
        "section": "sub_suppliers",
        "question_text": "Are cascade due diligence obligations contractually included in supplier agreements?",
        "question_type": "yes_no",
        "csddd_article": "Art. 10 Abs. 2 lit. b",
        "weight": 5,
        "sort_order": 23,
    },
    {
        "section": "sub_suppliers",
        "question_text": "Does your company monitor or audit sub-supplier compliance?",
        "question_type": "yes_no",
        "csddd_article": "Art. 10 Abs. 2 lit. b",
        "weight": 4,
        "sort_order": 24,
    },
    {
        "section": "sub_suppliers",
        "question_text": "Approximately how many direct sub-suppliers does your company work with?",
        "question_type": "text",
        "csddd_article": "Art. 10 Abs. 2 lit. b",
        "weight": 1,
        "sort_order": 25,
        "is_required": False,
    },
]


def _now() -> datetime:
    return datetime.now(UTC)


def _ref_code() -> str:
    return "SA-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _template_to_domain(m: AssessmentTemplateModel) -> AssessmentTemplate:
    return AssessmentTemplate(
        id=m.id,
        organization_id=m.organization_id,
        title=m.title,
        description=m.description,
        is_default=m.is_default,
        created_by=m.created_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
        question_count=len(m.questions) if m.questions else 0,
    )


def _question_to_domain(m: AssessmentQuestionModel) -> AssessmentQuestion:
    try:
        options = json.loads(m.options_json)
    except (ValueError, TypeError):
        options = []
    return AssessmentQuestion(
        id=m.id,
        template_id=m.template_id,
        section=m.section,
        question_text=m.question_text,
        question_type=m.question_type,
        options=options,
        csddd_article=m.csddd_article,
        weight=m.weight,
        is_required=m.is_required,
        sort_order=m.sort_order,
        is_active=m.is_active,
    )


def _assessment_to_domain(m: SupplierAssessmentModel) -> SupplierAssessment:
    return SupplierAssessment(
        id=m.id,
        organization_id=m.organization_id,
        template_id=m.template_id,
        supplier_id=m.supplier_id,
        token_hash=m.token_hash,
        token_expires_at=m.token_expires_at,
        status=m.status,
        reference_code=m.reference_code,
        created_at=m.created_at,
        updated_at=m.updated_at,
        submitted_at=m.submitted_at,
        # submitted_by_email intentionally NOT included
    )


def _response_to_domain(m: AssessmentResponseModel) -> AssessmentResponse:
    return AssessmentResponse(
        id=m.id,
        assessment_id=m.assessment_id,
        question_id=m.question_id,
        answer_value=m.answer_value,
        answered_at=m.answered_at,
    )


class SQLAssessmentTemplateRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def seed_default(self, organization_id: str, created_by: str) -> AssessmentTemplate:
        """Create the 25-question CSDDD default template for an organization if it does not exist."""
        stmt = select(AssessmentTemplateModel).where(
            AssessmentTemplateModel.organization_id == organization_id,
            AssessmentTemplateModel.is_default,
        )
        existing = self._s.execute(stmt).scalar_one_or_none()
        if existing:
            return _template_to_domain(existing)

        tmpl = AssessmentTemplateModel(
            id=str(uuid4()),
            organization_id=organization_id,
            title="CSDDD Standard Self-Assessment (Art. 10 Abs. 2 lit. a)",
            description="Pre-defined 25-question CSDDD compliance questionnaire covering Art. 7, Art. 10 Annex I/II, Art. 14, and cascade obligations.",
            is_default=True,
            created_by=created_by,
            created_at=_now(),
            updated_at=_now(),
        )
        self._s.add(tmpl)
        self._s.flush()

        for seed in SEED_QUESTIONS:
            self._s.add(
                AssessmentQuestionModel(
                    id=str(uuid4()),
                    template_id=tmpl.id,
                    section=seed["section"],
                    question_text=seed["question_text"],
                    question_type=seed["question_type"],
                    options_json="[]",
                    csddd_article=seed["csddd_article"],
                    weight=seed["weight"],
                    is_required=seed.get("is_required", True),
                    sort_order=seed["sort_order"],
                    is_active=True,
                )
            )
        self._s.flush()
        self._s.refresh(tmpl)
        return _template_to_domain(tmpl)

    def list_org(self, organization_id: str) -> list[AssessmentTemplate]:
        stmt = (
            select(AssessmentTemplateModel)
            .where(AssessmentTemplateModel.organization_id == organization_id)
            .order_by(AssessmentTemplateModel.created_at.desc())
        )
        return [_template_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def get(self, template_id: str, organization_id: str) -> AssessmentTemplate | None:
        m = self._s.get(AssessmentTemplateModel, template_id)
        if not m or m.organization_id != organization_id:
            return None
        return _template_to_domain(m)

    def get_questions(self, template_id: str) -> list[AssessmentQuestion]:
        stmt = (
            select(AssessmentQuestionModel)
            .where(AssessmentQuestionModel.template_id == template_id)
            .order_by(AssessmentQuestionModel.sort_order)
        )
        return [_question_to_domain(m) for m in self._s.execute(stmt).scalars().all()]


class SQLSupplierAssessmentRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def create(
        self,
        organization_id: str,
        template_id: str,
        supplier_id: str,
        token: str,
        token_expires_at: datetime,
    ) -> SupplierAssessment:
        m = SupplierAssessmentModel(
            id=str(uuid4()),
            organization_id=organization_id,
            template_id=template_id,
            supplier_id=supplier_id,
            token_hash=_hash_token(token),
            token_expires_at=token_expires_at,
            status=AssessmentStatus.SENT.value,
            reference_code=_ref_code(),
            created_at=_now(),
            updated_at=_now(),
            submitted_at=None,
        )
        self._s.add(m)
        self._s.flush()
        return _assessment_to_domain(m)

    def get_by_token_hash(self, token_hash: str) -> SupplierAssessmentModel | None:
        stmt = select(SupplierAssessmentModel).where(
            SupplierAssessmentModel.token_hash == token_hash
        )
        return self._s.execute(stmt).scalar_one_or_none()

    def get(self, assessment_id: str, organization_id: str) -> SupplierAssessment | None:
        m = self._s.get(SupplierAssessmentModel, assessment_id)
        if not m or m.organization_id != organization_id:
            return None
        return _assessment_to_domain(m)

    def list_org(self, organization_id: str, status: str | None = None) -> list[SupplierAssessment]:
        stmt = select(SupplierAssessmentModel).where(
            SupplierAssessmentModel.organization_id == organization_id
        )
        if status:
            stmt = stmt.where(SupplierAssessmentModel.status == status)
        stmt = stmt.order_by(SupplierAssessmentModel.created_at.desc())
        return [_assessment_to_domain(m) for m in self._s.execute(stmt).scalars().all()]

    def mark_in_progress(self, token_hash: str) -> None:
        m = self.get_by_token_hash(token_hash)
        if m and m.status == AssessmentStatus.SENT.value:
            m.status = AssessmentStatus.IN_PROGRESS.value
            m.updated_at = _now()
            self._s.flush()

    def save_responses(self, assessment_id: str, answers: dict[str, str]) -> None:
        """Upsert answers: replace existing responses for the assessment."""
        existing_stmt = select(AssessmentResponseModel).where(
            AssessmentResponseModel.assessment_id == assessment_id
        )
        existing = {r.question_id: r for r in self._s.execute(existing_stmt).scalars().all()}
        for qid, value in answers.items():
            if qid in existing:
                existing[qid].answer_value = value
                existing[qid].answered_at = _now()
            else:
                self._s.add(
                    AssessmentResponseModel(
                        id=str(uuid4()),
                        assessment_id=assessment_id,
                        question_id=qid,
                        answer_value=value,
                        answered_at=_now(),
                    )
                )
        self._s.flush()

    def submit(
        self,
        token_hash: str,
        answers: dict[str, str],
        submitted_by_email: str,
    ) -> tuple[SupplierAssessment, str]:
        """Mark assessment as submitted. Returns (domain, reference_code).

        submitted_by_email stored internally — NEVER returned in API response.
        """
        m = self.get_by_token_hash(token_hash)
        if not m:
            return None, ""
        self.save_responses(m.id, answers)
        m.status = AssessmentStatus.SUBMITTED.value
        m._submitted_by_email = submitted_by_email
        m.submitted_at = _now()
        m.updated_at = _now()
        self._s.flush()
        return _assessment_to_domain(m), m.reference_code

    def get_responses(self, assessment_id: str) -> list[AssessmentResponse]:
        stmt = select(AssessmentResponseModel).where(
            AssessmentResponseModel.assessment_id == assessment_id
        )
        return [_response_to_domain(r) for r in self._s.execute(stmt).scalars().all()]
