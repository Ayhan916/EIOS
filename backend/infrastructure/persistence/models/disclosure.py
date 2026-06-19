from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class DisclosureFrameworkModel(BaseModel):
    __tablename__ = "disclosure_frameworks"
    __table_args__ = (Index("ix_disclosure_frameworks_code", "code", unique=True),)

    code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    fw_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False, default="Global")
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")


class DisclosureRequirementModel(BaseModel):
    __tablename__ = "disclosure_requirements"
    __table_args__ = (
        Index("ix_disclosure_requirements_framework", "framework_id"),
        Index("ix_disclosure_requirements_ref", "reference"),
    )

    framework_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    reference: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="")


class DisclosureResponseModel(BaseModel):
    __tablename__ = "disclosure_responses"
    __table_args__ = (
        Index("ix_disclosure_responses_org", "organization_id"),
        Index("ix_disclosure_responses_requirement", "requirement_id"),
        UniqueConstraint(
            "organization_id",
            "requirement_id",
            name="uq_disclosure_response_org_req",
        ),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    requirement_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    disclosure_status: Mapped[str] = mapped_column(String(30), nullable=False, default="Not Started")
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    coverage_category: Mapped[str] = mapped_column(String(20), nullable=False, default="Weak")
    coverage_rationale: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    readiness_status: Mapped[str] = mapped_column(String(40), nullable=False, default="Not Started")
    readiness_rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReportingPackageModel(BaseModel):
    """Immutable snapshot of a published sustainability reporting package."""

    __tablename__ = "reporting_packages"
    __table_args__ = (
        Index("ix_reporting_packages_org_fw", "organization_id", "framework_code"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    framework_id: Mapped[str] = mapped_column(String(36), nullable=False)
    framework_code: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    framework_version: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    package_type: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    publication_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_by: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    report_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    report_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
