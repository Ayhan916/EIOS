"""DB model for entity aliases — alternative company name variants (E2-F3)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class EntityAliasModel(Base):
    """Known name variant for a supplier, used by EntityLinker."""

    __tablename__ = "entity_aliases"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    supplier_id: Mapped[str] = mapped_column(
        sa.String(36),
        sa.ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias: Mapped[str] = mapped_column(sa.String(256), nullable=False)
    # confidence that this alias reliably identifies the supplier (0.0–1.0)
    alias_confidence: Mapped[float] = mapped_column(sa.Float, nullable=False, default=1.0)
    source: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("supplier_id", "alias", name="uq_entity_alias"),
        sa.Index("ix_entity_alias_alias", "alias"),
    )
