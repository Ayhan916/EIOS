"""ORM model for prioritization_decisions (GAP-18 / CSDDD Art. 10)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class PrioritizationDecisionModel(BaseModel):
    __tablename__ = "prioritization_decisions"

    __table_args__ = (
        Index("ix_prio_org", "organization_id"),
        Index("ix_prio_org_supplier", "organization_id", "supplier_id"),
        Index("ix_prio_org_rank", "organization_id", "priority_rank"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    severity_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    probability_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    people_affected_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    priority_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    resource_capacity_per_quarter: Mapped[int] = mapped_column(Integer, nullable=False, default=4)

    reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")

    overridden_manually: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    override_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    decided_by_user_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    regulation_refs: Mapped[str] = mapped_column(
        String(100), nullable=False, default="CSDDD Art. 10; LkSG §5"
    )
