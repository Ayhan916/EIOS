from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .associations import decision_recommendation, recommendation_finding, recommendation_risk
from .base import BaseModel


class RecommendationModel(BaseModel):
    __tablename__ = "recommendations"

    assessment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("assessments.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium")
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="High")
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    risks: Mapped[list[RiskModel]] = relationship(
        secondary=recommendation_risk, back_populates="recommendations"
    )
    findings: Mapped[list[FindingModel]] = relationship(
        secondary=recommendation_finding, back_populates="recommendations"
    )
    decisions: Mapped[list[DecisionModel]] = relationship(
        secondary=decision_recommendation, back_populates="recommendations"
    )
