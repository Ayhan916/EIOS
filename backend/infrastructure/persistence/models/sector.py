from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class SectorModel(BaseModel):
    __tablename__ = "sectors"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    nace_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    nace_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    risk_profile: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    parent_sector_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sectors.id"), nullable=True
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True
    )

    parent: Mapped[SectorModel | None] = relationship(
        back_populates="children", remote_side="SectorModel.id"
    )
    children: Mapped[list[SectorModel]] = relationship(back_populates="parent")
    organization: Mapped[OrganizationModel | None] = relationship(back_populates="sectors")
    assessments: Mapped[list[AssessmentModel]] = relationship(back_populates="sector")
