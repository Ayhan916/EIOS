from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class SupplierScoreModel(BaseModel):
    """
    Immutable audit record of a supplier score calculation.

    Each (re)calculation inserts a new row.  Rows are never updated.
    Latest score per supplier = ORDER BY created_at DESC LIMIT 1.
    """

    __tablename__ = "supplier_scores"
    __table_args__ = (
        Index("ix_supplier_scores_supplier_created", "supplier_id", "created_at"),
        Index("ix_supplier_scores_org_risk", "organization_id", "risk_score"),
    )

    supplier_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False, index=True
    )
    score_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")

    # ESG scores (higher = better)
    esg_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    environmental_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    social_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    governance_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)

    # Risk score (higher = worse)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_band: Mapped[str] = mapped_column(String(20), nullable=False, default="Low")

    # Trend vs previous snapshot
    trend: Mapped[str] = mapped_column(String(20), nullable=False, default="Stable")
    trend_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Peer benchmark
    sector_percentile: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Auditability — raw inputs and explanation persisted with every calculation
    inputs: Mapped[dict] = mapped_column(JSON, nullable=False)
    drivers: Mapped[list] = mapped_column(JSON, nullable=False)

    supplier: Mapped[SupplierModel] = relationship(back_populates="scores")
