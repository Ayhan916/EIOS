"""Domain models for CSDDD Art. 8 Abs. 3 — Scoping Study Workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from domain.enums import ScopingPriority, ScopingStudyStatus


@dataclass
class ScopingConfig:
    id: UUID
    organization_id: UUID
    version: int
    risk_score_threshold_p1: float  # ≥ this → Priority 1
    risk_score_threshold_p2: float  # ≥ this → Priority 2, else Priority 3
    high_risk_countries: list[str]  # ISO codes or country names
    high_risk_sectors: list[str]  # Industry / NACE sector strings
    revenue_threshold_pct: float  # Supplier revenue share % above which = auto P1
    notes: str
    created_by: str
    created_at: datetime


@dataclass
class ScopingResult:
    supplier_id: str
    supplier_name: str
    country: str
    industry: str
    risk_score: float
    risk_band: str
    priority: ScopingPriority
    reasons: list[str]
    manually_overridden: bool
    override_reason: str | None


@dataclass
class ScopingStudy:
    id: UUID
    organization_id: UUID
    title: str
    report_year: int
    config_id: UUID
    status: ScopingStudyStatus
    results_snapshot: list[dict[str, Any]]  # frozen ScopingResult dicts
    methodology_notes: str
    submitted_at: datetime | None
    submitted_by: str | None
    approved_at: datetime | None
    approved_by: str | None
    next_review_due: datetime | None
    created_at: datetime
    updated_at: datetime
