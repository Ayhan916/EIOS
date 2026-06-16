"""
EIOS Domain Model — Recommendation

Canonical Enterprise Object per architecture/026.
Represents a mitigation proposal for identified risks.
AI-generated + governed: requires approval before activation (ASTATE-0001).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .base_entity import BaseEntity
from .enums import ConfidenceLevel, RiskLevel


@dataclass(slots=True, kw_only=True)
class Recommendation(BaseEntity):
    title: str
    description: str
    assessment_id: Optional[str] = None
    risk_ids: list[str] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)
    priority: RiskLevel = field(default=RiskLevel.MEDIUM)
    confidence: ConfidenceLevel = field(default=ConfidenceLevel.HIGH)
    reasoning: Optional[str] = None
    action_required: bool = True
    due_date: Optional[datetime] = None
    approved_by: Optional[str] = None
