"""
EIOS ORM Model — Digital Product Passport (M28 / KAN-92)

Single table: digital_product_passports
Links to products via product_id.
Computed fields (substances_of_concern_count, non_compliant_regulations_count)
are updated by the service layer when a snapshot is requested.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class DigitalProductPassportModel(BaseModel):
    __tablename__ = "digital_product_passports"
    __table_args__ = (
        Index("ix_dpp_org", "organization_id"),
        Index("ix_dpp_product", "product_id"),
        Index("ix_dpp_status", "status"),
        Index("ix_dpp_format", "format"),
        Index("ix_dpp_uid", "passport_uid", unique=True),
        Index("ix_dpp_disclosed", "disclosed_at"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    product_id: Mapped[str] = mapped_column(String(36), nullable=False)
    format: Mapped[str] = mapped_column(String(30), nullable=False)
    dpp_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")

    # Digital identity
    passport_uid: Mapped[str] = mapped_column(String(36), nullable=False)
    qr_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Product context
    product_category: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Battery-Regulation fields
    battery_chemistry: Mapped[str | None] = mapped_column(String(20), nullable=True)
    capacity_wh: Mapped[float | None] = mapped_column(Float, nullable=True)
    nominal_voltage_v: Mapped[float | None] = mapped_column(Float, nullable=True)
    declared_capacity_cycles: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Sustainability
    carbon_footprint_kg_co2e: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbon_footprint_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    recycled_content_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    renewable_content_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Computed aggregates (refreshed on snapshot)
    substances_of_concern_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    non_compliant_regulations_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Manufacturer / provenance
    manufacturer_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    manufacturer_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    manufacturing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Lifecycle
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    disclosed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Evidence / notes
    evidence_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
