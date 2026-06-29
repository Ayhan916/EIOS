"""
EIOS ORM Models — Supplier Twin Extensions (M25 / KAN-85–89)

Five new tables that extend the Supplier entity into a full Enterprise Twin:
  supplier_locations      — plants, warehouses, production sites
  supplier_contacts       — role-based contact persons
  supplier_certifications — ISO / IATF / SA8000 lifecycle management
  supplier_ownerships     — corporate ownership, UBO, LEI, DUNS
  supplier_esg_metrics    — energy, water, waste, workforce KPIs (ESRS-mapped)
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Index, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class SupplierLocationModel(BaseModel):
    """Physical location belonging to a supplier."""

    __tablename__ = "supplier_locations"
    __table_args__ = (
        Index("ix_sloc_supplier", "supplier_id"),
        Index("ix_sloc_org", "organization_id"),
        Index("ix_sloc_type", "location_type"),
        Index("ix_sloc_country", "country"),
    )

    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    location_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    region: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SupplierContactModel(BaseModel):
    """Named contact person at a supplier."""

    __tablename__ = "supplier_contacts"
    __table_args__ = (
        Index("ix_scon_supplier", "supplier_id"),
        Index("ix_scon_org", "organization_id"),
        Index("ix_scon_role", "role"),
    )

    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    first_name: Mapped[str] = mapped_column(String(200), nullable=False)
    last_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="OTHER")
    job_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    department: Mapped[str | None] = mapped_column(String(200), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SupplierCertificationModel(BaseModel):
    """Industry certification held by a supplier with full lifecycle tracking."""

    __tablename__ = "supplier_certifications"
    __table_args__ = (
        Index("ix_scert_supplier", "supplier_id"),
        Index("ix_scert_org", "organization_id"),
        Index("ix_scert_type", "cert_type"),
        Index("ix_scert_valid_until", "valid_until"),
        Index("ix_scert_is_expired", "is_expired_flag"),
    )

    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    cert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    custom_cert_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    issuing_body: Mapped[str | None] = mapped_column(String(300), nullable=True)
    certificate_number: Mapped[str | None] = mapped_column(String(200), nullable=True)
    scope_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_expired_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    location_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SupplierOwnershipModel(BaseModel):
    """Corporate ownership structure of a supplier."""

    __tablename__ = "supplier_ownerships"
    __table_args__ = (
        UniqueConstraint("supplier_id", "organization_id", name="uq_ownership_supplier_org"),
        Index("ix_sown_supplier", "supplier_id"),
        Index("ix_sown_org", "organization_id"),
        Index("ix_sown_publicly_listed", "publicly_listed"),
        Index("ix_sown_is_state_owned", "is_state_owned"),
        Index("ix_sown_parent_country", "parent_company_country"),
    )

    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    ownership_type: Mapped[str] = mapped_column(String(30), nullable=False, default="PRIVATE")
    parent_company_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parent_company_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ownership_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    ultimate_beneficial_owner: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ubo_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ubo_ownership_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    publicly_listed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stock_exchange: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ticker_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    market_cap_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    lei_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    duns_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    vat_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    registration_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_state_owned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state_ownership_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SupplierESGMetricModel(BaseModel):
    """Single ESG metric measurement for a supplier in a reporting period."""

    __tablename__ = "supplier_esg_metrics"
    __table_args__ = (
        UniqueConstraint(
            "supplier_id", "organization_id", "reporting_year", "reporting_period", "metric_type",
            name="uq_esg_metric_supplier_period_type",
        ),
        Index("ix_sesg_supplier", "supplier_id"),
        Index("ix_sesg_org", "organization_id"),
        Index("ix_sesg_year", "reporting_year"),
        Index("ix_sesg_type", "metric_type"),
    )

    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reporting_year: Mapped[int] = mapped_column(Integer, nullable=False)
    reporting_period: Mapped[str] = mapped_column(String(10), nullable=False, default="ANNUAL")
    metric_type: Mapped[str] = mapped_column(String(60), nullable=False)
    custom_metric_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    esrs_reference: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gri_reference: Mapped[str | None] = mapped_column(String(30), nullable=True)
    data_source: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_third_party_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_standard: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SupplierExternalESGRatingModel(BaseModel):
    """External ESG rating from a third-party provider (EcoVadis, MSCI, Sustainalytics, etc.)."""

    __tablename__ = "supplier_external_esg_ratings"
    __table_args__ = (
        UniqueConstraint(
            "supplier_id", "organization_id", "provider", "rating_date",
            name="uq_esg_rating_supplier_provider_date",
        ),
        Index("ix_sext_esg_supplier", "supplier_id"),
        Index("ix_sext_esg_org", "organization_id"),
        Index("ix_sext_esg_provider", "provider"),
        Index("ix_sext_esg_date", "rating_date"),
        Index("ix_sext_esg_valid_until", "valid_until"),
    )

    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    rating_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Numeric scores
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Grade / tier
    grade: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Peer benchmarking
    percentile: Mapped[float | None] = mapped_column(Float, nullable=True)
    peer_group: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Sub-scores
    environmental_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    social_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    governance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ethics_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sustainable_procurement_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Validity
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Source
    report_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    methodology_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
