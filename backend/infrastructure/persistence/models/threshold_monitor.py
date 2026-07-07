"""SQLAlchemy models — CSDDD Threshold Monitor (CSDDD-010)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.models.base import Base


class CompanyProfileModel(Base):
    __tablename__ = "company_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    employee_count_worldwide: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    net_revenue_eur_millions: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    headquarters_country: Mapped[str] = mapped_column(String(2), nullable=False, default="DE")
    sector: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    non_eu_company: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_company_profiles_org_year", "organization_id", "fiscal_year", unique=True),
    )
