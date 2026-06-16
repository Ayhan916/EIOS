from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from .associations import assessment_evidence
from .base import BaseModel


class AssessmentModel(BaseModel):
    __tablename__ = "assessments"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    scope: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    methodology: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="High")
    sector_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sectors.id"), nullable=True, index=True
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True, index=True
    )
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approval_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Extraction audit trail (M16)
    extraction_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    sector: Mapped[SectorModel | None] = relationship(back_populates="assessments")
    evidence: Mapped[list[EvidenceModel]] = relationship(
        secondary=assessment_evidence, back_populates="assessments"
    )
    findings: Mapped[list[FindingModel]] = relationship(back_populates="assessment")
    risks: Mapped[list[RiskModel]] = relationship(back_populates="assessment")
