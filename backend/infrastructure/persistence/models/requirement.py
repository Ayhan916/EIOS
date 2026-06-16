from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .associations import control_requirement, policy_requirement, standard_requirement
from .base import BaseModel


class RequirementModel(BaseModel):
    __tablename__ = "requirements"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    article: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requirement_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    controls: Mapped[list[ControlModel]] = relationship(
        secondary=control_requirement, back_populates="requirements"
    )
    policies: Mapped[list[PolicyModel]] = relationship(
        secondary=policy_requirement, back_populates="requirements"
    )
    standards: Mapped[list[StandardModel]] = relationship(
        secondary=standard_requirement, back_populates="requirements"
    )
