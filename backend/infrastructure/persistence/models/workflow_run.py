from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class WorkflowRunModel(BaseModel):
    __tablename__ = "workflow_runs"

    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True, index=True
    )
    workflow_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    steps_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verdict: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    verdict_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall_risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recommendation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
