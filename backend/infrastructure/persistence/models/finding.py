from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .associations import finding_evidence, recommendation_finding, risk_finding
from .base import BaseModel


class FindingModel(BaseModel):
    __tablename__ = "findings"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessments.id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium")
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="High")
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    uncertainty: Mapped[str | None] = mapped_column(Text, nullable=True)
    # M25: Evidence intelligence
    evidence_strength: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evidence_source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # GAP-08: Numeric 1-10 scoring
    severity_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    probability_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # E3-F1: ADR-003 — "Hypothetical" = no evidence yet, "Evidenced" = ≥1 evidence ref
    evidence_quality_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="Hypothetical"
    )

    assessment: Mapped[AssessmentModel] = relationship(back_populates="findings")
    evidence: Mapped[list[EvidenceModel]] = relationship(
        secondary=finding_evidence, back_populates="findings"
    )
    risks: Mapped[list[RiskModel]] = relationship(secondary=risk_finding, back_populates="findings")
    recommendations: Mapped[list[RecommendationModel]] = relationship(
        secondary=recommendation_finding, back_populates="findings"
    )
    evidence_links: Mapped[list[FindingEvidenceLinkModel]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )
