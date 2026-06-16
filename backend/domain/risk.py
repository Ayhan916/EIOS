"""
EIOS Domain Model — Risk

Canonical Enterprise Object per architecture/026.
Represents an identified and classified enterprise risk.
AI-generated + governed: requires approval before activation (ASTATE-0001).
"""

from dataclasses import dataclass, field
from typing import Optional

from .base_entity import BaseEntity
from .enums import ConfidenceLevel, RiskLevel


@dataclass(slots=True, kw_only=True)
class Risk(BaseEntity):
    title: str
    description: str
    risk_level: RiskLevel = field(default=RiskLevel.MEDIUM)
    category: str = ""
    assessment_id: Optional[str] = None
    sector_id: Optional[str] = None
    finding_ids: list[str] = field(default_factory=list)
    probability: Optional[float] = None
    impact: Optional[float] = None
    confidence: ConfidenceLevel = field(default=ConfidenceLevel.MEDIUM)
    reasoning: Optional[str] = None
    uncertainty: Optional[str] = None
