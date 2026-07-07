"""M46.2 — GHG Protocol engine ORM models.

Two tables:
  ghg_emission_factors  — standard DEFRA 2023 / EPA 2023 factors (seeded in migration)
  ghg_calculations      — per-activity calculation records (auditable trail)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class GHGEmissionFactorModel(Base):
    __tablename__ = "ghg_emission_factors"
    __table_args__ = (
        Index("ix_ghg_factors_scope_cat", "scope", "category"),
        Index("ix_ghg_factors_source", "source", "region"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    subcategory: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    factor_kgco2e_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, default=2023)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GHGCalculationModel(Base):
    __tablename__ = "ghg_calculations"
    __table_args__ = (
        Index("ix_ghg_calc_org", "organization_id"),
        Index("ix_ghg_calc_supplier", "supplier_id"),
        Index("ix_ghg_calc_scope", "scope"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    supplier_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("suppliers.id"), nullable=True
    )
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    subcategory: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    factor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ghg_emission_factors.id"), nullable=False
    )
    factor_kgco2e_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    result_kgco2e: Mapped[float] = mapped_column(Float, nullable=False)
    result_tco2e: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reporting_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
