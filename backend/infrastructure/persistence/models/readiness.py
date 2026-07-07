"""SQLAlchemy model — CSDDD Readiness Snapshots (CSDDD-011)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.models.base import Base


class ReadinessSnapshotModel(Base):
    __tablename__ = "readiness_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    overall_score_pct: Mapped[float] = mapped_column(Float, nullable=False)
    overall_level: Mapped[str] = mapped_column(String(20), nullable=False)
    article_scores_json: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    computed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (Index("ix_readiness_snapshots_org_date", "organization_id", "computed_at"),)
