"""M34 External Intelligence — Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ── External Dataset ──────────────────────────────────────────────────────────

class ExternalDatasetResponse(BaseModel):
    id: str
    source_name: str
    source_version: str
    dataset_hash: str
    imported_at: datetime
    row_count: int
    dataset_status: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    datasets: list[ExternalDatasetResponse]
    total: int


# ── Country Risk ──────────────────────────────────────────────────────────────

class CountryRiskResponse(BaseModel):
    id: str
    country_code: str
    country_name: str
    dataset_id: str
    governance_score: float
    corruption_score: float
    labour_rights_score: float
    environmental_risk_score: float
    human_rights_score: float
    sanctions_status: str
    overall_risk_score: float
    risk_level: str
    source_name: str
    source_version: str
    data_date: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CountryRiskListResponse(BaseModel):
    profiles: list[CountryRiskResponse]
    total: int


# ── Sector Benchmark ──────────────────────────────────────────────────────────

class SectorBenchmarkResponse(BaseModel):
    id: str
    sector_id: str
    sector_name: str
    nace_code: str
    dataset_id: str
    average_esg_score: float
    average_risk_score: float
    average_compliance_coverage: float
    average_disclosure_readiness: float
    supplier_count: int
    p10_esg_score: float
    p25_esg_score: float
    p50_esg_score: float
    p75_esg_score: float
    p90_esg_score: float
    source_name: str
    source_version: str
    benchmark_date: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SectorBenchmarkListResponse(BaseModel):
    benchmarks: list[SectorBenchmarkResponse]
    total: int


# ── External Risk Signal ──────────────────────────────────────────────────────

class ExternalRiskSignalResponse(BaseModel):
    id: str
    signal_type: str
    severity: str
    description: str
    source_name: str
    source_version: str
    observed_at: datetime
    dataset_id: str | None
    country_code: str
    sector_code: str
    supplier_id: str
    organization_id: str
    is_active: bool
    created_at: datetime
    # GAP-10: Event-Attribution completeness
    esg_category: str | None = None
    protected_right: str | None = None
    frequency: int = 0

    model_config = {"from_attributes": True}


class CreateSignalRequest(BaseModel):
    signal_type: str = Field(..., description="RiskSignalType value")
    severity: str = Field(..., description="SignalSeverity value")
    description: str = Field(..., min_length=1)
    source_name: str
    source_version: str
    observed_at: datetime
    dataset_id: str | None = None
    country_code: str = ""
    sector_code: str = ""
    supplier_id: str = ""
    # Optional overrides; auto-derived if omitted
    esg_category: str | None = None
    protected_right: str | None = None


class SignalListResponse(BaseModel):
    signals: list[ExternalRiskSignalResponse]
    total: int


# ── Supplier Enrichment ───────────────────────────────────────────────────────

class SupplierEnrichmentResponse(BaseModel):
    id: str
    supplier_id: str
    organization_id: str
    country_code: str
    country_risk_level: str
    country_risk_score: float
    sanctions_exposure: str
    sector_percentile: float
    percentile_rank: str
    benchmark_score: float
    benchmark_explanation: str
    external_risk_score: float
    combined_risk_score: float
    enriched_at: datetime
    dataset_version: str
    active_signal_count: int

    model_config = {"from_attributes": True}


class EnrichSupplierRequest(BaseModel):
    supplier_id: str
    country_code: str
    sector_id: str
    nace_code: str = ""
    internal_esg_score: float = Field(..., ge=0.0, le=100.0)
    dataset_version: str = ""


class EnrichmentListResponse(BaseModel):
    enrichments: list[SupplierEnrichmentResponse]
    total: int
