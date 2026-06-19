"""M33.2 Copilot Enterprise Audit ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class CopilotContradictionModel(BaseModel):
    """Pre-LLM contradiction detected during context assembly."""

    __tablename__ = "copilot_contradictions"
    __table_args__ = (Index("ix_copilot_contradictions_msg", "message_id"),)

    message_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    contradiction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    involved_objects: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CopilotCitationIntegrityModel(BaseModel):
    """Per-citation integrity verification record."""

    __tablename__ = "copilot_citation_integrity"
    __table_args__ = (
        Index("ix_copilot_citation_integrity_msg", "message_id"),
        Index("ix_copilot_citation_integrity_org", "organization_id"),
    )

    message_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    citation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    object_id: Mapped[str] = mapped_column(String(36), nullable=False)
    integrity_status: Mapped[str] = mapped_column(String(20), nullable=False)
    citation_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    citation_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CopilotFeedbackModel(BaseModel):
    """User feedback on a Copilot assistant message."""

    __tablename__ = "copilot_feedback"
    __table_args__ = (
        Index("ix_copilot_feedback_msg", "message_id"),
        Index("ix_copilot_feedback_org", "organization_id"),
    )

    message_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    rating: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CopilotAnswerReviewModel(BaseModel):
    """Executive review decision on a Copilot answer."""

    __tablename__ = "copilot_answer_reviews"
    __table_args__ = (
        Index("ix_copilot_reviews_msg", "message_id"),
        Index("ix_copilot_reviews_org", "organization_id"),
    )

    message_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CopilotAuditPackageModel(BaseModel):
    """Immutable audit package capturing the full Copilot reasoning chain."""

    __tablename__ = "copilot_audit_packages"
    __table_args__ = (
        Index("ix_copilot_audit_packages_msg", "message_id"),
        Index("ix_copilot_audit_packages_org", "organization_id"),
    )

    message_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    package_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    json_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
