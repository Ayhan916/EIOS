from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .associations import finding_evidence, risk_finding
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

    assessment: Mapped[AssessmentModel] = relationship(back_populates="findings")
    evidence: Mapped[list[EvidenceModel]] = relationship(
        secondary=finding_evidence, back_populates="findings"
    )
    risks: Mapped[list[RiskModel]] = relationship(secondary=risk_finding, back_populates="findings")
