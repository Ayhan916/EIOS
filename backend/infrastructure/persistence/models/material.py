"""
EIOS ORM Models — Material Twin (M26 / KAN-91–97)

Five tables for the Material aggregate:
  materials                     — core material identity
  material_compositions         — BOM (bill-of-materials) links
  material_sourcing             — supplier→material sourcing records
  material_compliance_flags     — per-regulation compliance status
  material_sustainability_metrics — LCA / sustainability KPIs
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class MaterialModel(BaseModel):
    """Core material entity — identity, classification, physical properties."""

    __tablename__ = "materials"
    __table_args__ = (
        Index("ix_mat_org", "organization_id"),
        Index("ix_mat_type", "material_type"),
        Index("ix_mat_status", "material_status"),
        Index("ix_mat_cas", "cas_number"),
        Index("ix_mat_hs", "hs_code"),
        Index("ix_mat_crm", "is_critical_raw_material"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    material_type: Mapped[str] = mapped_column(String(30), nullable=False)
    material_status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    # ERP reference (M6) — matches ERP material number (e.g. SAP MATNR)
    external_ref: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    # Internal reference
    internal_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Chemical identifiers
    cas_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ec_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    iupac_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    molecular_formula: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Trade
    hs_code: Mapped[str | None] = mapped_column(String(15), nullable=True)
    un_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ghs_hazard_class: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Physical / commercial
    unit_of_measure: Mapped[str] = mapped_column(String(20), nullable=False, default="kg")
    weight_per_unit_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    country_of_origin: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # CRM / circular economy
    is_critical_raw_material: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recycled_content_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class MaterialCompositionModel(BaseModel):
    """BOM link — one material contains another at a given weight fraction."""

    __tablename__ = "material_compositions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "parent_material_id", "child_material_id",
            name="uq_mat_comp_parent_child",
        ),
        Index("ix_mcomp_parent", "parent_material_id"),
        Index("ix_mcomp_child", "child_material_id"),
        Index("ix_mcomp_org", "organization_id"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    parent_material_id: Mapped[str] = mapped_column(String(36), nullable=False)
    child_material_id: Mapped[str] = mapped_column(String(36), nullable=False)
    weight_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class MaterialSourcingModel(BaseModel):
    """Sourcing record — which supplier provides a material and from which country."""

    __tablename__ = "material_sourcing"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "material_id", "supplier_id",
            name="uq_mat_sourcing_material_supplier",
        ),
        Index("ix_msrc_material", "material_id"),
        Index("ix_msrc_supplier", "supplier_id"),
        Index("ix_msrc_org", "organization_id"),
        Index("ix_msrc_country", "country_of_origin"),
        Index("ix_msrc_risk", "sourcing_risk"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    material_id: Mapped[str] = mapped_column(String(36), nullable=False)
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    country_of_origin: Mapped[str | None] = mapped_column(String(100), nullable=True)
    annual_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    price_per_unit_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sourcing_risk: Mapped[str] = mapped_column(String(10), nullable=False, default="MEDIUM")
    certification_required: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class MaterialComplianceFlagModel(BaseModel):
    """Compliance assessment of a material against a regulatory framework."""

    __tablename__ = "material_compliance_flags"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "material_id", "regulation",
            name="uq_mat_compliance_material_reg",
        ),
        Index("ix_mcf_material", "material_id"),
        Index("ix_mcf_org", "organization_id"),
        Index("ix_mcf_regulation", "regulation"),
        Index("ix_mcf_status", "compliance_status"),
        Index("ix_mcf_valid_until", "valid_until"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    material_id: Mapped[str] = mapped_column(String(36), nullable=False)
    regulation: Mapped[str] = mapped_column(String(30), nullable=False)
    custom_regulation_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    compliance_status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNKNOWN")
    assessed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    assessor: Mapped[str | None] = mapped_column(String(300), nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class MaterialSustainabilityMetricModel(BaseModel):
    """Life-cycle sustainability data (LCA) for a material."""

    __tablename__ = "material_sustainability_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "material_id", "reporting_year",
            name="uq_mat_sustain_material_year",
        ),
        Index("ix_msus_material", "material_id"),
        Index("ix_msus_org", "organization_id"),
        Index("ix_msus_year", "reporting_year"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    material_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reporting_year: Mapped[int] = mapped_column(Integer, nullable=False)
    # Carbon
    carbon_footprint_kg_co2e_per_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbon_scope: Mapped[str] = mapped_column(String(30), nullable=False, default="cradle_to_gate")
    # Water
    water_footprint_l_per_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Energy
    energy_mj_per_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_renewable_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Circularity
    recycled_content_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    recyclability_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    biodegradable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Source / verification
    data_source: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_third_party_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_standard: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
