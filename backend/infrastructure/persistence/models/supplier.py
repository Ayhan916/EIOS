from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class SupplierModel(BaseModel):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_suppliers_org_name"),
    )

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    industry: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    nace_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    supplier_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="Tier 1")
    supplier_status: Mapped[str] = mapped_column(String(20), nullable=False, default="Active")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessments: Mapped[list[AssessmentModel]] = relationship(back_populates="supplier")
