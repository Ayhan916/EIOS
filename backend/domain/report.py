"""
EIOS Domain Model — Report

Represents a point-in-time executive report generated from an Assessment.
Stores a frozen content snapshot for full auditability — the report remains
accurate even if underlying findings, risks, or recommendations change later.
"""

from dataclasses import dataclass, field
from typing import Any

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class Report(BaseEntity):
    assessment_id: str
    title: str
    generated_by: str  # user_id
    organization_id: str | None = None
    format: str = "pdf"
    # Counts captured at generation time
    finding_count: int = 0
    risk_count: int = 0
    recommendation_count: int = 0
    evidence_count: int = 0
    # Frozen snapshot of the full report payload (for auditability and re-render)
    content_snapshot: dict[str, Any] = field(default_factory=dict)
