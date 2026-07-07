"""Domain models for CSDDD Art. 15 — Effectiveness Monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.enums import IndicatorDataSource, IndicatorType, ReviewStatus


@dataclass
class EffectivenessIndicator:
    """KPI from the indicator library. organization_id=None means global/seeded."""

    id: UUID
    organization_id: UUID | None
    name: str
    description: str
    indicator_type: IndicatorType
    unit: str
    data_source: IndicatorDataSource
    csddd_article: str
    risk_category: str | None
    is_active: bool
    created_at: datetime


@dataclass
class ReviewLine:
    id: UUID
    review_id: UUID
    indicator_id: UUID
    indicator_name: str
    measured_value: float | None
    measured_text: str | None
    comment: str | None
    auto_populated: bool


@dataclass
class EffectivenessReview:
    id: UUID
    organization_id: UUID
    title: str
    period_start: datetime
    period_end: datetime
    overall_rating: int | None
    key_findings: str | None
    improvement_actions: str | None
    status: ReviewStatus
    submitted_at: datetime | None
    submitted_by: str | None
    approved_at: datetime | None
    approved_by: str | None
    lines: list[ReviewLine]
    created_at: datetime
    updated_at: datetime


@dataclass
class CAPEffectivenessSnapshot:
    cap_id: str
    organization_id: UUID
    baseline_score: float | None
    closed_score: float | None
    risk_delta: float | None
    snapshot_taken_at: datetime | None
