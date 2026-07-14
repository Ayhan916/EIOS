"""DB model for supply chain edges — tier-2/3 graph (E5-F3)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SupplyChainEdgeModel(Base):
    """One directed relationship: buyer → supplier at a declared tier.

    Both buyer_id and supplier_id reference the suppliers table.
    A tier-2 edge has tier=2 and buyer_id pointing to a tier-1 supplier.
    """

    __tablename__ = "supply_chain_edges"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    buyer_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Tier from the perspective of the ROOT organisation (1 = direct, 2 = indirect …)
    tier: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    commodity_code: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    # Reliability of this edge (0.0–1.0); 1.0 = verified, lower = inferred
    confidence: Mapped[float] = mapped_column(sa.Float, nullable=False, default=1.0)

    __table_args__ = (
        sa.UniqueConstraint("buyer_id", "supplier_id", name="uq_supply_chain_edge"),
        sa.Index("ix_sce_buyer_id", "buyer_id"),
        sa.Index("ix_sce_supplier_id", "supplier_id"),
        sa.Index("ix_sce_tier", "tier"),
    )
