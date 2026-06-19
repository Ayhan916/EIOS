"""Pydantic schemas for M33.2 Copilot Audit & Governance API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ContradictionSchema(BaseModel):
    contradiction_type: str
    description: str
    involved_objects: list[dict[str, str]] = []
    severity: str = "warning"
    detected_at: str = ""


class ConfidenceFactorsSchema(BaseModel):
    retrieval_coverage: float
    citation_count: int
    source_diversity: int
    average_data_age_days: float
    contradiction_count: int
    raw_score: float
    level: str


class FreshnessReportSchema(BaseModel):
    oldest_age_days: float = 0.0
    newest_age_days: float = 0.0
    average_age_days: float = 0.0
    has_stale_data: bool = False
    stale_retrievers: list[str] = []
    freshness_by_retriever: dict[str, float] = {}


class ContextBudgetSchema(BaseModel):
    max_chars: int
    used_chars: int
    truncated: bool
    retrievers_included: list[str] = []
    retrievers_omitted: list[str] = []
    retrievers_empty: list[str] = []


class CitationIntegritySchema(BaseModel):
    citation_type: str
    object_id: str
    integrity_status: str
    citation_hash: str
    verified_at: datetime


class AuditPackageResponse(BaseModel):
    package_id: str
    message_id: str
    package_hash: str
    generated_at: datetime
    verification_status: str
    json_payload: dict[str, Any]


class VerificationCheckSchema(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class VerificationResultResponse(BaseModel):
    package_id: str
    message_id: str
    overall: str  # PASS or FAIL
    checks: list[VerificationCheckSchema]
    verified_at: str


class FeedbackRequest(BaseModel):
    rating: str = Field(..., pattern="^(helpful|not_helpful|incorrect|outdated)$")
    reason: str = Field(default="", max_length=1000)


class FeedbackResponse(BaseModel):
    id: str
    message_id: str
    rating: str
    reason: str
    submitted_at: datetime


class ReviewRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|misleading|investigate)$")
    notes: str = Field(default="", max_length=2000)


class ReviewResponse(BaseModel):
    id: str
    message_id: str
    reviewer_id: str
    decision: str
    notes: str
    reviewed_at: datetime


class AnalyticsResponse(BaseModel):
    organization_id: str
    total_questions: int
    total_conversations: int
    questions_by_intent: dict[str, int]
    average_confidence_score: float
    confidence_distribution: dict[str, int]
    average_citations_per_answer: float
    empty_context_count: int
    empty_context_rate: float
    contradiction_rate: float
    average_contradiction_count: float
    feedback_helpful_count: int
    feedback_not_helpful_count: int
    feedback_incorrect_count: int
    feedback_outdated_count: int
    feedback_total: int
