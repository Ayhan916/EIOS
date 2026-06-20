"""M37 Surveillance API Schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SurveillanceSignalResponse(BaseModel):
    id: str
    organization_id: str
    supplier_id: str | None
    source_type: str
    source_id: str | None
    signal_type: str
    severity: str
    confidence: float
    title: str
    description: str
    detected_at: datetime
    expires_at: datetime | None
    signal_status: str
    acknowledged_by: str | None
    acknowledged_at: datetime | None
    episode_id: str | None
    explainability_json: dict = Field(default_factory=dict)
    dedupe_key: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AcknowledgeSignalRequest(BaseModel):
    pass


class DismissSignalRequest(BaseModel):
    pass


class SupplierWatchlistResponse(BaseModel):
    id: str
    organization_id: str
    supplier_id: str
    watch_reason: str
    severity: str
    added_by_type: str
    created_by: str | None
    watchlist_status: str
    removed_at: datetime | None
    removed_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AddWatchlistRequest(BaseModel):
    supplier_id: str
    watch_reason: str
    severity: str = "HIGH"


class RiskEpisodeResponse(BaseModel):
    id: str
    organization_id: str
    supplier_id: str | None
    title: str
    description: str
    severity: str
    episode_status: str
    started_at: datetime
    closed_at: datetime | None
    signal_count: int
    resolved_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CreateEpisodeRequest(BaseModel):
    title: str
    description: str = ""
    severity: str = "HIGH"
    supplier_id: str | None = None


class TransitionEpisodeRequest(BaseModel):
    new_status: str


class RiskTrendResponse(BaseModel):
    id: str
    organization_id: str
    supplier_id: str
    period: str
    esg_score_start: float | None
    esg_score_end: float | None
    risk_score_start: float | None
    risk_score_end: float | None
    score_delta: float
    trend: str
    confidence: float
    computed_at: datetime

    model_config = {"from_attributes": True}


class HeatmapCell(BaseModel):
    dimension: str
    key: str
    signal_count: int
    max_severity: str


class RiskTimelineEvent(BaseModel):
    event_type: str
    timestamp: datetime | None
    title: str
    severity: str
    entity_id: str
    signal_type: str | None


class SurveillanceDashboard(BaseModel):
    total_suppliers: int
    suppliers_at_risk: int
    suppliers_improving: int
    suppliers_deteriorating: int
    suppliers_stable: int
    suppliers_needing_review: int
    watchlist_count: int
    active_signals: int
    critical_signals: int
    open_episodes: int
    recent_signals: list[SurveillanceSignalResponse] = Field(default_factory=list)
    recent_episodes: list[RiskEpisodeResponse] = Field(default_factory=list)
    watchlist: list[SupplierWatchlistResponse] = Field(default_factory=list)
