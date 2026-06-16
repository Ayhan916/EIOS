from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .associations import policy_control, policy_requirement
from .base import BaseModel


class PolicyModel(BaseModel):
    __tablename__ = "policies"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    effective_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expiry_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    requirements: Mapped[list[RequirementModel]] = relationship(
        secondary=policy_requirement, back_populates="policies"
    )
    controls: Mapped[list[ControlModel]] = relationship(
        secondary=policy_control, back_populates="policies"
    )
