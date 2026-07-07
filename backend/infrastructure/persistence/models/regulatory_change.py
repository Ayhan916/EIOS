"""ORM models for regulatory_changes + regulatory_change_impacts (GAP-19)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class RegulatoryChangeModel(BaseModel):
    __tablename__ = "regulatory_changes"

    __table_args__ = (
        Index("ix_regchg_framework", "framework_code"),
        Index("ix_regchg_org", "organization_id"),
        Index("ix_regchg_status", "change_status"),
    )

    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    framework_code: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    change_title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    change_description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    affected_article: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="moderate")
    change_status: Mapped[str] = mapped_column(String(30), nullable=False, default="new")

    source_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    source_url: Mapped[str] = mapped_column(String(2000), nullable=False, default="")

    affected_sectors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    affected_frameworks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    impact_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    impacted_assessment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impacted_gap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    regulation_refs: Mapped[str] = mapped_column(String(500), nullable=False, default="")


class RegulatoryChangeImpactModel(BaseModel):
    __tablename__ = "regulatory_change_impacts"

    __table_args__ = (
        Index("ix_regchgimp_org", "organization_id"),
        Index("ix_regchgimp_change", "change_id"),
        Index("ix_regchgimp_assessment", "assessment_id"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    change_id: Mapped[str] = mapped_column(String(36), nullable=False)

    assessment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    compliance_gap_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    impact_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="assessment_re_review"
    )
    re_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notification_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    acknowledged_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
