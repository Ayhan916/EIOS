from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .associations import decision_recommendation
from .base import BaseModel


class DecisionModel(BaseModel):
    __tablename__ = "decisions"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by: Mapped[str] = mapped_column(String(255), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    context: Mapped[str | None] = mapped_column(Text, nullable=True)

    recommendations: Mapped[list[RecommendationModel]] = relationship(
        secondary=decision_recommendation, back_populates="decisions"
    )
