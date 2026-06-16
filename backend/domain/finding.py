"""
EIOS Domain Model — Finding

Canonical Enterprise Object per architecture/026.
Represents a specific observation produced by an Assessment.
AI-generated: carries reasoning and uncertainty per architecture/008 (AAM-0001).
"""

from dataclasses import dataclass, field
from typing import Optional

from .base_entity import BaseEntity
from .enums import ConfidenceLevel, RiskLevel


@dataclass(slots=True, kw_only=True)
class Finding(BaseEntity):
    title: str
    description: str
    assessment_id: str
    category: str = ""
    severity: RiskLevel = field(default=RiskLevel.MEDIUM)
    confidence: ConfidenceLevel = field(default=ConfidenceLevel.HIGH)
    evidence_ids: list[str] = field(default_factory=list)
    reasoning: Optional[str] = None
    uncertainty: Optional[str] = None
