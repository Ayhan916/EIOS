"""M38 Network Intelligence API Schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ── Relationships ─────────────────────────────────────────────────────────────

class CreateRelationshipRequest(BaseModel):
    supplier_id: str
    related_supplier_id: str
    relationship_type: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: str = ""


class SupplierRelationshipResponse(BaseModel):
    id: str
    organization_id: str
    supplier_id: str
    related_supplier_id: str
    relationship_type: str
    confidence: float
    source: str
    rationale: str
    relationship_status: str
    removed_at: datetime | None
    removed_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Suggested Relationships ───────────────────────────────────────────────────

class SuggestedRelationshipResponse(BaseModel):
    id: str
    organization_id: str
    supplier_id: str
    related_supplier_id: str
    relationship_type: str
    confidence: float
    rationale: str
    suggestion_source: str
    suggestion_status: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewSuggestionRequest(BaseModel):
    review_note: str = ""


# ── Exposure Signals ──────────────────────────────────────────────────────────

class NetworkExposureSignalResponse(BaseModel):
    id: str
    organization_id: str
    origin_supplier_id: str
    impacted_supplier_id: str
    exposure_type: str
    propagation_path: list[str]
    path_length: int
    confidence: float
    severity: str
    rationale: str
    source_signal_id: str | None
    source_finding_id: str | None
    exposure_status: str
    detected_at: datetime
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Criticality ───────────────────────────────────────────────────────────────

class SupplierCriticalityResponse(BaseModel):
    id: str
    organization_id: str
    supplier_id: str
    criticality: str
    criticality_score: float
    degree_centrality: float
    inbound_degree: int
    outbound_degree: int
    connected_component_size: int
    dependency_score: float
    assessment_count: int
    finding_count: int
    open_remediation_count: int
    calculation_inputs: dict = Field(default_factory=dict)
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Dependency Analysis ───────────────────────────────────────────────────────

class DependencyAnalysisResponse(BaseModel):
    id: str
    organization_id: str
    supplier_id: str | None
    dependency_score: float
    concentration_score: float
    diversification_score: float
    critical_supplier_count: int
    single_point_of_failure_count: int
    calculation_inputs: dict = Field(default_factory=dict)
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Resilience ────────────────────────────────────────────────────────────────

class ResilienceAssessmentResponse(BaseModel):
    id: str
    organization_id: str
    supplier_id: str | None
    resilience_score: float
    diversification_score: float
    concentration_score: float
    redundancy_score: float
    calculation_inputs: dict = Field(default_factory=dict)
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Incident Clusters ─────────────────────────────────────────────────────────

class IncidentClusterResponse(BaseModel):
    id: str
    organization_id: str
    cluster_name: str
    root_cause: str
    severity: str
    cluster_status: str
    affected_supplier_ids: list[str]
    finding_ids: list[str]
    signal_ids: list[str]
    risk_ids: list[str]
    compliance_gap_ids: list[str]
    resolved_at: datetime | None
    resolved_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Centrality ────────────────────────────────────────────────────────────────

class CentralityRecord(BaseModel):
    supplier_id: str
    inbound_degree: int
    outbound_degree: int
    degree_centrality: float
    connected_component_size: int


# ── Neighborhood / Graph ─────────────────────────────────────────────────────

class NeighborhoodResponse(BaseModel):
    supplier_id: str
    neighbors: dict[str, int]


class ShortestPathResponse(BaseModel):
    src: str
    dst: str
    path: list[str] | None
    path_length: int | None


# ── Dashboard ─────────────────────────────────────────────────────────────────

class NetworkDashboard(BaseModel):
    total_relationships: int
    pending_suggestions: int
    active_exposures: int
    active_clusters: int
    critical_suppliers: int
    resilience_score: float | None
    dependency_score: float | None
    top_critical: list[SupplierCriticalityResponse]
    recent_exposures: list[NetworkExposureSignalResponse]
    recent_clusters: list[IncidentClusterResponse]


# ── Discovery ─────────────────────────────────────────────────────────────────

class DiscoveryResult(BaseModel):
    shared_country: int
    shared_sector: int
    shared_sanctions: int
    shared_regulatory: int
    total: int


# ── Network Watchlist (M38.1) ─────────────────────────────────────────────────

class NetworkWatchlistEntryResponse(BaseModel):
    id: str
    organization_id: str
    watched_supplier_id: str
    related_supplier_id: str
    distance: int
    has_active_alert: bool = False
    created_at: datetime
    updated_at: datetime
