"""M34 External Data & Benchmarking Intelligence ORM Models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class ExternalDatasetModel(BaseModel):
    """Versioned, immutable external data source record."""

    __tablename__ = "external_datasets"
    __table_args__ = (
        UniqueConstraint("source_name", "source_version", name="uq_external_datasets_source_version"),
        Index("ix_external_datasets_source", "source_name"),
        Index("ix_external_datasets_status", "dataset_status"),
    )

    source_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_version: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dataset_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")


class CountryRiskProfileModel(BaseModel):
    """Per-country risk assessment derived from external datasets."""

    __tablename__ = "country_risk_profiles"
    __table_args__ = (
        Index("ix_country_risk_code", "country_code"),
        Index("ix_country_risk_dataset", "dataset_id"),
        Index("ix_country_risk_level", "risk_level"),
    )

    country_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    country_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    governance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    corruption_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    labour_rights_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    environmental_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    human_rights_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sanctions_status: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    overall_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    source_name: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    source_version: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    data_date: Mapped[str] = mapped_column(String(20), nullable=False, default="")


class SectorBenchmarkModel(BaseModel):
    """Sector-level ESG benchmark derived from industry datasets."""

    __tablename__ = "sector_benchmarks"
    __table_args__ = (
        Index("ix_sector_benchmarks_sector", "sector_id"),
        Index("ix_sector_benchmarks_nace", "nace_code"),
        Index("ix_sector_benchmarks_dataset", "dataset_id"),
    )

    sector_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    sector_name: Mapped[str] = mapped_column(String(200), nullable=False)
    nace_code: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    dataset_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    average_esg_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_compliance_coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_disclosure_readiness: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    supplier_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    p10_esg_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p25_esg_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p50_esg_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p75_esg_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p90_esg_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_name: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    source_version: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    benchmark_date: Mapped[str] = mapped_column(String(20), nullable=False, default="")


class ExternalRiskSignalModel(BaseModel):
    """Adverse risk signal from an external source."""

    __tablename__ = "external_risk_signals"
    __table_args__ = (
        Index("ix_ext_signals_supplier", "supplier_id"),
        Index("ix_ext_signals_country", "country_code"),
        Index("ix_ext_signals_org", "organization_id"),
        Index("ix_ext_signals_type", "signal_type"),
    )

    signal_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(String(50), nullable=False)
    source_version: Mapped[str] = mapped_column(String(50), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dataset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    country_code: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    sector_code: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # GAP-10: Event-Attribution completeness (FR-005)
    esg_category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    protected_right: Mapped[str | None] = mapped_column(String(60), nullable=True)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SupplierEnrichmentModel(BaseModel):
    """Tenant-scoped supplier enrichment combining internal + external intelligence."""

    __tablename__ = "supplier_enrichments"
    __table_args__ = (
        UniqueConstraint("supplier_id", "organization_id", name="uq_supplier_enrichments_supplier_org"),
        Index("ix_supplier_enrichments_supplier", "supplier_id"),
        Index("ix_supplier_enrichments_org", "organization_id"),
        Index("ix_supplier_enrichments_risk", "combined_risk_score"),
    )

    supplier_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    country_risk_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    country_risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    country_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sanctions_exposure: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    sector_benchmark_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sector_percentile: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    percentile_rank: Mapped[str] = mapped_column(String(20), nullable=False, default="median")
    benchmark_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    benchmark_explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    external_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    combined_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    enriched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    active_signal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
