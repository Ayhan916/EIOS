"""Domain models for CSDDD Art. 15 — Effectiveness Monitoring."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from domain.enums import IndicatorDataSource, IndicatorType, ReviewStatus


@dataclass
class EffectivenessIndicator:
    """KPI from the indicator library. organization_id=None means global/seeded."""
    id: UUID
    organization_id: Optional[UUID]
    name: str
    description: str
    indicator_type: IndicatorType
    unit: str
    data_source: IndicatorDataSource
    csddd_article: str
    risk_category: Optional[str]
    is_active: bool
    created_at: datetime


@dataclass
class ReviewLine:
    id: UUID
    review_id: UUID
    indicator_id: UUID
    indicator_name: str
    measured_value: Optional[float]
    measured_text: Optional[str]
    comment: Optional[str]
    auto_populated: bool


@dataclass
class EffectivenessReview:
    id: UUID
    organization_id: UUID
    title: str
    period_start: datetime
    period_end: datetime
    overall_rating: Optional[int]
    key_findings: Optional[str]
    improvement_actions: Optional[str]
    status: ReviewStatus
    submitted_at: Optional[datetime]
    submitted_by: Optional[str]
    approved_at: Optional[datetime]
    approved_by: Optional[str]
    lines: list[ReviewLine]
    created_at: datetime
    updated_at: datetime


@dataclass
class CAPEffectivenessSnapshot:
    cap_id: str
    organization_id: UUID
    baseline_score: Optional[float]
    closed_score: Optional[float]
    risk_delta: Optional[float]
    snapshot_taken_at: Optional[datetime]
