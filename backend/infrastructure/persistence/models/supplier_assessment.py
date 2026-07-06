"""SQLAlchemy models — Supplier Self-Assessment CSDDD (CSDDD-015)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.persistence.models.base import Base


class AssessmentTemplateModel(Base):
    __tablename__ = "assessment_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    questions: Mapped[list[AssessmentQuestionModel]] = relationship(
        "AssessmentQuestionModel", back_populates="template", cascade="all, delete-orphan",
        order_by="AssessmentQuestionModel.sort_order",
    )

    __table_args__ = (
        Index("ix_assessment_templates_org", "organization_id"),
    )


class AssessmentQuestionModel(Base):
    __tablename__ = "assessment_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessment_templates.id", ondelete="CASCADE"), nullable=False
    )
    section: Mapped[str] = mapped_column(String(30), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False, default="yes_no")
    options_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    csddd_article: Mapped[str] = mapped_column(String(50), nullable=False, default="Art. 10")
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    template: Mapped[AssessmentTemplateModel] = relationship(
        "AssessmentTemplateModel", back_populates="questions"
    )

    __table_args__ = (
        Index("ix_assessment_questions_template", "template_id"),
        Index("ix_assessment_questions_section", "section"),
    )


class SupplierAssessmentModel(Base):
    __tablename__ = "supplier_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessment_templates.id"), nullable=False
    )
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sent")
    reference_code: Mapped[str] = mapped_column(String(20), nullable=False)
    # submitted_by_email stored internally — NEVER returned in API response
    _submitted_by_email: Mapped[str | None] = mapped_column("submitted_by_email", String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    responses: Mapped[list[AssessmentResponseModel]] = relationship(
        "AssessmentResponseModel", back_populates="assessment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_supplier_assessments_org_status", "organization_id", "status"),
        Index("ix_supplier_assessments_supplier", "supplier_id"),
    )


class AssessmentResponseModel(Base):
    __tablename__ = "assessment_responses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("supplier_assessments.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessment_questions.id"), nullable=False
    )
    answer_value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assessment: Mapped[SupplierAssessmentModel] = relationship(
        "SupplierAssessmentModel", back_populates="responses"
    )

    __table_args__ = (
        Index("ix_assessment_responses_assessment", "assessment_id"),
    )
