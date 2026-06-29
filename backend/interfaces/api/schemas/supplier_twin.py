"""M50 Supplier Digital Twin — Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HealthDimensionResponse(BaseModel):
    name: str
    label: str
    score: float
    status: str  # CRITICAL | AT_RISK | MODERATE | HEALTHY

    model_config = {"from_attributes": True}


class SupplierDigitalTwinResponse(BaseModel):
    id: str
    supplier_id: str
    organization_id: str

    # Health dimensions
    esg_health: float
    compliance_health: float
    financial_health: float
    geopolitical_health: float
    cyber_health: float
    human_rights_health: float
    environmental_health: float
    operational_health: float

    overall_health: float
    health_trend: str
    ai_confidence: float

    open_recommendations: int
    open_actions: int
    event_count: int
    critical_event_count: int
    last_event_at: Optional[datetime]
    last_updated_at: datetime
    twin_version: int

    # Derived
    dimensions: list[HealthDimensionResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class IntelligenceTimelineEventResponse(BaseModel):
    id: str
    supplier_id: str
    organization_id: str

    event_type: str
    event_category: str
    severity: str

    title: str
    summary: str

    why_important: str
    regulatory_impact: str
    recommended_action: str

    source_type: str
    source_name: str
    source_url: str
    evidence_ids: str
    regulation_ids: str
    risk_ids: str
    signal_id: str

    twin_dimension_affected: str
    health_delta: float
    confidence: float

    occurred_at: datetime
    processed_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class TimelineListResponse(BaseModel):
    events: list[IntelligenceTimelineEventResponse]
    total: int
    supplier_id: str


class ProcessSignalsResponse(BaseModel):
    supplier_id: str
    events_created: int
    twin_updated: bool
    message: str


class IntelligenceFeedResponse(BaseModel):
    events: list[IntelligenceTimelineEventResponse]
    total: int
    organization_id: str


class CollectIntelligenceResponse(BaseModel):
    sources_attempted: int
    sources_ok: int
    entities_checked: int
    suppliers_matched: int
    signals_created: int
    twins_updated: int
    events_created: int
    duration_seconds: float
    errors: list[str]
    message: str
