"""SQLAlchemy model for CorrectiveActionPlan (GAP-20)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.models.base import BaseModel


class CorrectiveActionPlanModel(BaseModel):
    __tablename__ = "corrective_action_plans"

    finding_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    responsible_party: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)

    cap_status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")

    evidence_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    verification_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    verified_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    insufficient_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    __table_args__ = (
        Index("ix_cap_org_status", "organization_id", "cap_status"),
        Index("ix_cap_org_deadline", "organization_id", "deadline"),
        Index("ix_cap_finding", "finding_id"),
    )
