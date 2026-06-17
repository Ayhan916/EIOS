from __future__ import annotations

from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .associations import control_requirement, control_risk, policy_control
from .base import BaseModel


class ControlModel(BaseModel):
    __tablename__ = "controls"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    control_type: Mapped[str] = mapped_column(String(50), nullable=False, default="Preventive")
    effectiveness: Mapped[float | None] = mapped_column(Float, nullable=True)
    automated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    risks: Mapped[list[RiskModel]] = relationship(secondary=control_risk, back_populates="controls")
    requirements: Mapped[list[RequirementModel]] = relationship(
        secondary=control_requirement, back_populates="controls"
    )
    policies: Mapped[list[PolicyModel]] = relationship(
        secondary=policy_control, back_populates="controls"
    )
