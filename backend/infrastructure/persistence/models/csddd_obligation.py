"""DB models for CSDDD Obligation Rule Engine (ADR-010)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, BaseModel


class CsdddObligationModel(Base):
    """Static CSDDD obligation registry — managed by Legal/Compliance, not AI."""

    __tablename__ = "csddd_obligations"

    article_id: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    article_number: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    obligation_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    trigger_conditions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence_requirements: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    severity_threshold: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class FindingLegalMappingModel(BaseModel):
    """Persisted result of the rule engine for one finding × obligation pair."""

    __tablename__ = "finding_legal_mappings"

    finding_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id: Mapped[str] = mapped_column(
        sa.String(64),
        sa.ForeignKey("csddd_obligations.article_id", ondelete="RESTRICT"),
        nullable=False,
    )
    match_type: Mapped[str] = mapped_column(sa.String(16), nullable=False)  # "exact" | "partial"
    confidence: Mapped[str] = mapped_column(sa.String(16), nullable=False)  # "High" | "Medium"
    matched_conditions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (
        sa.UniqueConstraint("finding_id", "article_id", name="uq_finding_legal_mapping"),
        sa.Index("ix_finding_legal_article", "article_id"),
    )
