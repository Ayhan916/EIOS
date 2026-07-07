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

    # M40 — Enterprise hierarchy links (all nullable for backward compat)
    enterprise_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    business_unit_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    legal_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    region_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    # EU | UK | US | APAC
    data_residency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED
    data_classification: Mapped[str] = mapped_column(String(20), nullable=False, default="INTERNAL")

    users: Mapped[list[UserModel]] = relationship(back_populates="organization")
    sectors: Mapped[list[SectorModel]] = relationship(back_populates="organization")
    projects: Mapped[list[ProjectModel]] = relationship(back_populates="organization")
    assets: Mapped[list[AssetModel]] = relationship(back_populates="organization")
