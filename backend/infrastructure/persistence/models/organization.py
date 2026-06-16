from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class OrganizationModel(BaseModel):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    organization_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list[UserModel]] = relationship(back_populates="organization")
    sectors: Mapped[list[SectorModel]] = relationship(back_populates="organization")
    projects: Mapped[list[ProjectModel]] = relationship(back_populates="organization")
    assets: Mapped[list[AssetModel]] = relationship(back_populates="organization")
