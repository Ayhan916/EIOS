"""
EIOS Domain Model — Risk

Canonical Enterprise Object per architecture/026.
Represents an identified and classified enterprise risk.
AI-generated + governed: requires approval before activation (ASTATE-0001).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base_entity import BaseEntity
from .enums import ConfidenceLevel, RiskLevel
from .value_objects import ConfidenceCard


@dataclass(slots=True, kw_only=True)
class Risk(BaseEntity):
    title: str
    description: str
    risk_level: RiskLevel = field(default=RiskLevel.MEDIUM)
    category: str = ""
    assessment_id: str | None = None
    sector_id: str | None = None
    finding_ids: list[str] = field(default_factory=list)
    probability: float | None = None
    impact: float | None = None
    confidence: ConfidenceLevel = field(default=ConfidenceLevel.MEDIUM)
    # ADR-015: structured confidence — derived from `confidence` when not explicitly set
    confidence_card: ConfidenceCard | None = field(default=None)
    reasoning: str | None = None
    uncertainty: str | None = None
    # GAP-08: Numeric 1-10 scoring
    severity_score: int | None = None
    probability_score: int | None = None
