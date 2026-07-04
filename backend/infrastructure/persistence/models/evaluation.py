"""ORM models for evaluation_runs, benchmark_results, and calibration_events."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class EvaluationRunModel(BaseModel):
    __tablename__ = "evaluation_runs"

    __table_args__ = (
        Index("ix_evalrun_computed_at", "computed_at"),
        Index("ix_evalrun_run_type", "run_type"),
    )

    run_type: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    agent_run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    accuracy_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    precision_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    hallucination_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    cost_usd_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_usd_last_7d: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cost_usd_last_30d: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    benchmark_status: Mapped[str] = mapped_column(String(10), nullable=False, default="unknown")
    benchmark_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    benchmark_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    platform_health_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    raw_metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    computed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class BenchmarkResultModel(BaseModel):
    __tablename__ = "benchmark_results"

    __table_args__ = (
        Index("ix_benchres_run", "evaluation_run_id"),
        Index("ix_benchres_module", "module"),
    )

    evaluation_run_id: Mapped[str] = mapped_column(String(36), nullable=False)
    benchmark_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    module: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    dimension: Mapped[str] = mapped_column(String(30), nullable=False, default="accuracy")
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    actual_output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class CalibrationEventModel(BaseModel):
    __tablename__ = "calibration_events"

    __table_args__ = (
        Index("ix_calev_org", "organization_id"),
        Index("ix_calev_confidence", "predicted_confidence"),
        Index("ix_calev_entity", "entity_type", "entity_id"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    predicted_confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    actual_outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    recorded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
