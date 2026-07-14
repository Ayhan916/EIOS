"""DB model for versioned prompt registry (ADR-011)."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PromptVersionModel(Base):
    """Versioned prompt template — one row per named prompt version."""

    __tablename__ = "prompt_versions"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    prompt_name: Mapped[str] = mapped_column(sa.String(128), nullable=False, index=True)
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    template: Mapped[str] = mapped_column(sa.Text, nullable=False)
    variables: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )

    __table_args__ = (
        sa.UniqueConstraint("prompt_name", "version", name="uq_prompt_name_version"),
        sa.Index("ix_prompt_name_active", "prompt_name", "active"),
    )
