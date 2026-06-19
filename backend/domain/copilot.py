from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class CopilotConversation(BaseEntity):
    """A persistent conversation thread between a user and the Copilot."""

    organization_id: str
    user_id: str
    title: str = ""
    context_type: str = "general"
    context_id: str | None = None
    message_count: int = 0
    is_archived: bool = False


@dataclass(slots=True, kw_only=True)
class CopilotMessage(BaseEntity):
    """A single message exchange within a Copilot conversation.

    Full audit trail: stores the prompt, retrieved sources, citations, model
    used, and generation time so every answer is permanently reviewable.
    """

    conversation_id: str
    organization_id: str
    user_id: str
    role: str  # CopilotMessageRole value
    content: str
    intent: str = ""
    citations: list = field(default_factory=list)
    retrieved_sources: dict = field(default_factory=dict)
    model_used: str = ""
    generation_ms: int | None = None
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    # M33.1 — full audit snapshot so historical answers are reproducible
    retrieval_snapshot: dict = field(default_factory=dict)
    assembled_context: str = ""
    system_prompt_snapshot: str = ""
    # M33.2 — enterprise hardening fields
    confidence_level: str = ""
    confidence_factors: dict = field(default_factory=dict)
    contradiction_count: int = 0
    context_budget_used: int = 0
    context_truncated: bool = False
    freshness_summary: dict = field(default_factory=dict)
