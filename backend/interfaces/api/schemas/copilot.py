"""Pydantic schemas for M33 AI Sustainability Copilot API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .copilot_audit import ContradictionSchema


class CitationSchema(BaseModel):
    citation_type: str
    object_id: str
    relevance: str = "retrieved"


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    conversation_id: str | None = None
    context_type: str = "general"
    context_id: str | None = None


class CopilotAnswerResponse(BaseModel):
    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    intent: str
    answer: str
    citations: list[CitationSchema]
    model_used: str
    generation_ms: int | None
    retrieved_sources: dict[str, Any]
    # M33.2 explainability fields
    confidence_level: str = ""
    confidence_factors: dict[str, Any] = {}
    contradictions: list[ContradictionSchema] = []
    freshness_summary: dict[str, Any] = {}
    context_truncated: bool = False


class CopilotConversationSummary(BaseModel):
    id: str
    title: str
    context_type: str
    message_count: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New Conversation", max_length=255)
    context_type: str = "general"
    context_id: str | None = None


class CopilotMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    intent: str
    citations: list[CitationSchema]
    model_used: str
    generation_ms: int | None
    generated_at: datetime


class SuggestedQuestionsResponse(BaseModel):
    context_type: str
    questions: list[str]


class ExecutiveBriefResponse(BaseModel):
    answer: str
    supplier_overview: dict[str, Any]
    key_risks: list[dict[str, Any]]
    compliance_concerns: list[dict[str, Any]]
    reporting_blockers: list[dict[str, Any]]
    recommended_actions: list[dict[str, Any]]
    open_recommendations_total: int
    citations: list[CitationSchema]
    model_used: str
    generated_at: datetime


class ActionAdvisorResponse(BaseModel):
    answer: str
    highest_impact_actions: list[dict[str, Any]]
    fastest_remediations: list[dict[str, Any]]
    risk_reduction_priorities: list[dict[str, Any]]
    top_compliance_gaps: list[dict[str, Any]]
    finding_hotspots: list[dict[str, Any]]
    open_action_count: int
    citations: list[CitationSchema]
    model_used: str
    generated_at: datetime
