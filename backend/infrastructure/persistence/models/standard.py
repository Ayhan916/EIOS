from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .associations import standard_requirement
from .base import BaseModel


class StandardModel(BaseModel):
    __tablename__ = "standards"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    standard_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version_label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    requirements: Mapped[list[RequirementModel]] = relationship(
        secondary=standard_requirement, back_populates="standards"
    )
