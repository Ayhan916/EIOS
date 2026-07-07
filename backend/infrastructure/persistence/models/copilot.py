from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class CopilotConversationModel(BaseModel):
    """Persistent conversation thread between a user and the Copilot."""

    __tablename__ = "copilot_conversations"
    __table_args__ = (Index("ix_copilot_convs_org_user", "organization_id", "user_id"),)

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    context_type: Mapped[str] = mapped_column(String(30), nullable=False, default="general")
    context_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CopilotMessageModel(BaseModel):
    """Single message within a Copilot conversation.

    Full audit trail: stores the retrieved sources, citations, model used,
    and generation time so every answer is permanently reviewable.
    """

    __tablename__ = "copilot_messages"
    __table_args__ = (
        Index("ix_copilot_messages_conv", "conversation_id"),
        Index("ix_copilot_messages_org", "organization_id"),
    )

    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    citations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    retrieved_sources: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    generation_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # M33.1 — full audit snapshot persisted with each assistant message
    retrieval_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assembled_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    # M33.2 — enterprise hardening: confidence, contradictions, budget, freshness
    confidence_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence_factors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    contradiction_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context_budget_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context_truncated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    freshness_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
