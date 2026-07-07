"""SQLAlchemy models for CSDDD-001 Stakeholder Engagement (Art. 13)."""

from __future__ import annotations

from sqlalchemy import Boolean, Date, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class StakeholderModel(BaseModel):
    __tablename__ = "stakeholders"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    stakeholder_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="de")
    # JSON arrays stored as text (PostgreSQL supports JSON natively; serialised client-side)
    activity_chain_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    regions: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    risk_topics: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    justification: Mapped[str] = mapped_column(Text, nullable=False, default="")


class StakeholderConsultationModel(BaseModel):
    __tablename__ = "stakeholder_consultations"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    stakeholder_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    consultation_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    format: Mapped[str] = mapped_column(String(50), nullable=False, default="meeting")
    topics: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outcomes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    barrier: Mapped[str] = mapped_column(String(50), nullable=False, default="none")
    barrier_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    linked_risk_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    linked_finding_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    linked_cap_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class StakeholderFeedbackModel(BaseModel):
    __tablename__ = "stakeholder_feedback"

    consultation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    risk_assessment: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3)
    affected_rights: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    wants_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submitted_by_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    submitted_by_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    submitter_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
