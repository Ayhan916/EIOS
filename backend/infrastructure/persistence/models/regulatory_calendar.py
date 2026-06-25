"""M47 — Regulatory Calendar: deadline tracking model."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RegulatoryDeadlineModel(Base):
    """A regulatory reporting or compliance deadline.

    Seeded at startup via migration; organisations can add custom deadlines.
    """

    __tablename__ = "regulatory_deadlines"
    __table_args__ = (
        Index("ix_reg_deadline_jurisdiction", "jurisdiction"),
        Index("ix_reg_deadline_framework", "framework_code"),
        Index("ix_reg_deadline_date", "deadline_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    framework_code: Mapped[str] = mapped_column(String(30), nullable=False)
    deadline_name: Mapped[str] = mapped_column(String(500), nullable=False)
    deadline_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False, default="EU")
    # company size scope: Large | SME | All
    entity_size: Mapped[str] = mapped_column(String(20), nullable=False, default="All")
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reporting_year: Mapped[int | None] = mapped_column(String(4), nullable=True)
    # NULL = system-seeded; set to org_id for custom deadlines
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
