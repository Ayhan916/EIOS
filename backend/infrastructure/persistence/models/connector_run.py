"""M34.1 Connector Run & Dataset Validation ORM Models.

connector_runs       — audit log of every connector execution
dataset_validation_results — per-dataset validation outcomes
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ConnectorRunModel(Base):
    """Audit log of a single connector execution."""

    __tablename__ = "connector_runs"
    __table_args__ = (
        Index("ix_connector_runs_name", "connector_name"),
        Index("ix_connector_runs_status", "status"),
        Index("ix_connector_runs_started", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(100), nullable=False)
    connector_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    runtime_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="healthy")
    dataset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    dataset_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_errors_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_source: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduler")
    initiated_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DatasetValidationResultModel(Base):
    """Per-dataset validation outcome (schema checks, row counts, duplicates, hash)."""

    __tablename__ = "dataset_validation_results"
    __table_args__ = (
        Index("ix_validation_results_dataset", "dataset_id"),
        Index("ix_validation_results_valid", "is_valid"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(36), nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    errors_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    warnings_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
