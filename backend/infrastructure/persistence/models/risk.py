from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .associations import control_risk, recommendation_risk, risk_finding
from .base import BaseModel


class RiskModel(BaseModel):
    __tablename__ = "risks"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium")
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    assessment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assessments.id"), nullable=True, index=True
    )
    sector_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sectors.id"), nullable=True, index=True
    )
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium")
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    uncertainty: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessment: Mapped[AssessmentModel | None] = relationship(back_populates="risks")
    findings: Mapped[list[FindingModel]] = relationship(
        secondary=risk_finding, back_populates="risks"
    )
    recommendations: Mapped[list[RecommendationModel]] = relationship(
        secondary=recommendation_risk, back_populates="risks"
    )
    controls: Mapped[list[ControlModel]] = relationship(
        secondary=control_risk, back_populates="risks"
    )
