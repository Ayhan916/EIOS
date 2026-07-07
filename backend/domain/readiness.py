"""Domain model — CSDDD Readiness Score (CSDDD-011)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ArticleScore:
    article: str
    title: str
    earned_points: int
    max_points: int
    score_pct: float
    level: str  # ReadinessLevel
    gaps: list[str]  # human-readable gap descriptions


@dataclass
class ReadinessSnapshot:
    id: str
    organization_id: str
    overall_score_pct: float
    overall_level: str  # ReadinessLevel
    article_scores: list[ArticleScore]
    computed_at: datetime
    computed_by: str | None
