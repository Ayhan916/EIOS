"""M34 External Data & Benchmarking Intelligence — Domain Entities.

Architecture principle:
  - ExternalDataset, CountryRiskProfile, SectorBenchmark, ExternalRiskSignal
    are PLATFORM-GLOBAL (no organization_id). They represent objective, versioned
    external facts shared across all tenants.
  - SupplierEnrichment is TENANT-SCOPED. It links a specific supplier (tenant-owned)
    to global external intelligence, producing a combined risk profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .base_entity import BaseEntity
from .enums import (
    CountryRiskLevel,
    DatasetStatus,
    PercentileRank,
    SanctionsExposure,
)


@dataclass(slots=True, kw_only=True)
class ExternalDataset(BaseEntity):
    """Versioned, immutable record of an imported external data source.

    Once imported, datasets are never mutated — superseded datasets remain
    accessible so that historical reports remain reproducible.
    """

    source_name: str  # ExternalSourceName value
    source_version: str  # e.g. "2024-Q1", "2023-annual"
    dataset_hash: str  # SHA-256 of canonical raw data
    imported_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    row_count: int = 0
    dataset_status: str = DatasetStatus.ACTIVE
    description: str = ""


@dataclass(slots=True, kw_only=True)
class CountryRiskProfile(BaseEntity):
    """Per-country risk assessment derived from multiple external datasets.

    Scores are 0–100 (higher = more risk). The overall_risk_score aggregates
    all dimensions with equal weighting by default.
    """

    country_code: str  # ISO 3166-1 alpha-2 (e.g. "CN", "BR")
    country_name: str
    dataset_id: str  # FK to ExternalDataset
    governance_score: float = 0.0  # Higher = worse governance
    corruption_score: float = 0.0  # Higher = more corruption (CPI inverted)
    labour_rights_score: float = 0.0  # Higher = more labour rights risk
    environmental_risk_score: float = 0.0
    human_rights_score: float = 0.0
    sanctions_status: str = "none"  # none / partial / comprehensive
    overall_risk_score: float = 0.0
    risk_level: str = CountryRiskLevel.LOW
    source_name: str = ""
    source_version: str = ""
    data_date: str = ""  # When the underlying data was current (e.g. "2024-01-01")


@dataclass(slots=True, kw_only=True)
class SectorBenchmark(BaseEntity):
    """Sector-level ESG benchmark derived from industry datasets.

    Percentile breakpoints (p10 … p90) let the BenchmarkEngine calculate a
    supplier's position within their sector without exposing peer-level data.
    """

    sector_id: str  # Reference to sectors table
    sector_name: str
    nace_code: str = ""
    dataset_id: str  # FK to ExternalDataset
    average_esg_score: float = 0.0
    average_risk_score: float = 0.0
    average_compliance_coverage: float = 0.0
    average_disclosure_readiness: float = 0.0
    supplier_count: int = 0  # Number of suppliers in the benchmark universe
    p10_esg_score: float = 0.0
    p25_esg_score: float = 0.0
    p50_esg_score: float = 0.0  # Median
    p75_esg_score: float = 0.0
    p90_esg_score: float = 0.0
    source_name: str = ""
    source_version: str = ""
    benchmark_date: str = ""


@dataclass(slots=True, kw_only=True)
class ExternalRiskSignal(BaseEntity):
    """An adverse signal from an external data source.

    Signals may be country-level, sector-level, or linked to a specific
    supplier (via supplier_id + organization_id).
    """

    signal_type: str  # RiskSignalType value
    severity: str  # SignalSeverity value
    description: str
    source_name: str
    source_version: str
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    dataset_id: str = ""
    country_code: str = ""  # ISO code if country-level signal
    sector_code: str = ""  # NACE code if sector-level signal
    supplier_id: str = ""  # Filled when signal is linked to a specific supplier
    organization_id: str = ""  # Tenant scope when supplier_id is set
    is_active: bool = True
    # GAP-10: Event-Attribution completeness (FR-005)
    esg_category: str | None = None  # EsgCategory value
    protected_right: str | None = None  # CSDDDRight value
    frequency: int = (
        0  # Occurrences of this signal type for supplier/sector/country in last 12 months
    )


@dataclass(slots=True, kw_only=True)
class SupplierEnrichment(BaseEntity):
    """Tenant-scoped enrichment linking a supplier to global external intelligence.

    Combines internal supplier scoring with external country risk, sector benchmarks,
    and adverse signal data into a unified Combined Intelligence Profile.
    """

    supplier_id: str
    organization_id: str
    country_code: str = ""
    country_risk_id: str = ""  # FK to CountryRiskProfile
    country_risk_level: str = CountryRiskLevel.LOW
    country_risk_score: float = 0.0
    sanctions_exposure: str = SanctionsExposure.NONE
    sector_benchmark_id: str = ""  # FK to SectorBenchmark
    sector_percentile: float = 0.0  # 0–100
    percentile_rank: str = PercentileRank.MEDIAN
    benchmark_score: float = 0.0
    benchmark_explanation: str = ""
    external_risk_score: float = 0.0  # Aggregated external risk
    combined_risk_score: float = 0.0  # Internal + external combined
    enriched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    dataset_version: str = ""  # Which dataset version produced this enrichment
    active_signal_count: int = 0
