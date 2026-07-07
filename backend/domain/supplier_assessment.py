"""Domain model — Supplier Self-Assessment CSDDD (Art. 10 Abs. 2 lit. a).

Art. 10 Abs. 2 lit. a CSDDD allows using self-assessment questionnaires as a
prevention measure for indirect business partners (Tier 2+).

Security constraints:
  - submitted_by_email NEVER returned in API responses
  - IP address NEVER returned in API responses
  - Token = JWT with assessment_id + supplier_id + expires_at
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AssessmentQuestion:
    """A single question in an assessment template."""

    id: str
    template_id: str | None  # None for seed/library questions
    section: str  # AssessmentSection
    question_text: str
    question_type: str  # QuestionType
    options: list[str]  # choices for multiple_choice
    csddd_article: str  # e.g. "Art. 10 Annex I"
    weight: int  # gap severity weight 1-5
    is_required: bool
    sort_order: int
    is_active: bool


@dataclass
class AssessmentTemplate:
    """A reusable questionnaire template owned by an organization."""

    id: str
    organization_id: str
    title: str
    description: str
    is_default: bool  # True for the system-seeded CSDDD template
    created_by: str
    created_at: datetime
    updated_at: datetime
    question_count: int = 0


@dataclass
class SupplierAssessment:
    """An instance of a template sent to a specific supplier.

    submitted_by_email is stored internally but NEVER returned in API responses.
    """

    id: str
    organization_id: str
    template_id: str
    supplier_id: str
    token_hash: str  # SHA-256 of the JWT; raw token never stored
    token_expires_at: datetime
    status: str  # AssessmentStatus
    reference_code: str  # shown to supplier after submission
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None


@dataclass
class AssessmentResponse:
    """A single answer given by the supplier."""

    id: str
    assessment_id: str
    question_id: str
    answer_value: str  # JSON-encoded for complex types
    answered_at: datetime


@dataclass
class GapItem:
    question_id: str
    section: str
    csddd_article: str
    question_text: str
    answer_given: str
    expected_answer: str
    severity: str  # GapSeverity
    recommendation: str


@dataclass
class SectionScore:
    section: str
    total_questions: int
    answered: int
    gaps: int
    traffic_light: str  # TrafficLight


@dataclass
class GapReport:
    assessment_id: str
    supplier_id: str
    section_scores: list[SectionScore]
    gaps: list[GapItem]
    overall_traffic_light: str  # TrafficLight
    total_gaps: int
    critical_gaps: int
    generated_at: datetime
