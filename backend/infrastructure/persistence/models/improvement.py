"""SQLAlchemy model for ImprovementProposal (GAP-05)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.models.base import BaseModel


class ImprovementProposalModel(BaseModel):
    __tablename__ = "improvement_proposals"

    weakness_type: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    affected_module: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    current_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    target_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_impact: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False, default="")

    approval_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    approved_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    before_evaluation_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    after_evaluation_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    verified_improvement: Mapped[float | None] = mapped_column(Float, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_improv_status", "approval_status"),
        Index("ix_improv_module", "affected_module"),
        Index("ix_improv_priority", "priority_score"),
    )
