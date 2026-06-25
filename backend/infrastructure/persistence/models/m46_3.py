"""M46.3 — ORM models: remediation milestones, assessment schedules,
supplier certificates, risk drafts.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RemediationMilestoneModel(Base):
    __tablename__ = "remediation_milestones"
    __table_args__ = (
        Index("ix_rem_milestones_plan", "plan_id"),
        Index("ix_rem_milestones_status", "milestone_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("remediation_plans.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    milestone_status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AssessmentScheduleModel(Base):
    __tablename__ = "assessment_schedules"
    __table_args__ = (
        UniqueConstraint("organization_id", "supplier_id", name="uq_assessment_schedule_org_supplier"),
        Index("ix_assessment_schedules_org", "organization_id"),
        Index("ix_assessment_schedules_supplier", "supplier_id"),
        Index("ix_assessment_schedules_next_due", "next_due_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    supplier_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("suppliers.id"), nullable=False
    )
    frequency_days: Mapped[int] = mapped_column(Integer, nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    template_assessment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assessments.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SupplierCertificateModel(Base):
    __tablename__ = "supplier_certificates"
    __table_args__ = (
        Index("ix_supplier_certs_supplier", "supplier_id"),
        Index("ix_supplier_certs_org", "organization_id"),
        Index("ix_supplier_certs_expires", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("suppliers.id"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    cert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    alert_days_before: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    last_alert_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    issuer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    certificate_number: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskDraftModel(Base):
    """AI-drafted risk description awaiting human review.

    INVARIANT: this record is NEVER automatically promoted to a Risk.
    A human reviewer must call /risks/drafts/{id}/accept to create the real Risk.
    Agents may only create RiskDraft records (RECOMMEND), never Risk records (APPROVE).
    """

    __tablename__ = "risk_drafts"
    __table_args__ = (
        Index("ix_risk_drafts_org", "organization_id"),
        Index("ix_risk_drafts_status", "review_status"),
        Index("ix_risk_drafts_supplier", "supplier_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    supplier_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("suppliers.id"), nullable=True
    )
    signal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    draft_title: Mapped[str] = mapped_column(String(500), nullable=False)
    draft_description: Mapped[str] = mapped_column(Text, nullable=False)
    draft_severity: Mapped[str] = mapped_column(String(20), nullable=False)
    draft_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    draft_likelihood: Mapped[str | None] = mapped_column(String(20), nullable=True)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    llm_prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_risk_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
