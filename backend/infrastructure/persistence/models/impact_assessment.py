"""SQLAlchemy model — Impact Severity Assessments (CSDDD Art. 3/6)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.models.base import Base


class ImpactAssessmentModel(Base):
    __tablename__ = "impact_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    impact_type: Mapped[str] = mapped_column(String(30), nullable=False, default="other")
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False, default="standalone")
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    gravity: Mapped[int] = mapped_column(Integer, nullable=False)
    scope: Mapped[int] = mapped_column(Integer, nullable=False)
    remediability: Mapped[int] = mapped_column(Integer, nullable=False)
    likelihood: Mapped[int] = mapped_column(Integer, nullable=False)
    severity_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    severity_level: Mapped[str] = mapped_column(String(20), nullable=False)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_impact_assessments_org_level", "organization_id", "severity_level"),
        Index("ix_impact_assessments_org_type", "organization_id", "impact_type"),
    )
