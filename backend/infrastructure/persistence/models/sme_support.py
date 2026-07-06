"""SQLAlchemy persistence models — SME Support Tracker (CSDDD Art. 10)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.persistence.models.base import Base


class SMEProfileModel(Base):
    __tablename__ = "sme_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    classification: Mapped[str] = mapped_column(String(20), nullable=False, default="small")
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annual_revenue_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confirmed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    programs: Mapped[list[SupportProgramModel]] = relationship(
        "SupportProgramModel", back_populates="sme_profile", cascade="all, delete-orphan",
        foreign_keys="SupportProgramModel.supplier_id",
        primaryjoin="SMEProfileModel.supplier_id == SupportProgramModel.supplier_id",
        overlaps="sme_profile",
    )

    __table_args__ = (
        Index("ix_sme_profiles_supplier", "organization_id", "supplier_id", unique=True),
    )


class SupportProgramModel(Base):
    __tablename__ = "sme_support_programs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responsible_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_budget_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    spent_budget_eur: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sme_profile: Mapped[SMEProfileModel | None] = relationship(
        "SMEProfileModel",
        foreign_keys=[supplier_id],
        primaryjoin="SupportProgramModel.supplier_id == SMEProfileModel.supplier_id",
        back_populates="programs",
        overlaps="programs",
    )
    measures: Mapped[list[SupportMeasureModel]] = relationship(
        "SupportMeasureModel", back_populates="program", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_sme_support_programs_supplier", "organization_id", "supplier_id"),
        Index("ix_sme_support_programs_status", "organization_id", "status"),
    )


class SupportMeasureModel(Base):
    __tablename__ = "sme_support_measures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    program_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sme_support_programs.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    support_type: Mapped[str] = mapped_column(String(30), nullable=False, default="training")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cost_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    impact_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    program: Mapped[SupportProgramModel] = relationship("SupportProgramModel", back_populates="measures")

    __table_args__ = (
        Index("ix_sme_support_measures_program", "program_id"),
    )
