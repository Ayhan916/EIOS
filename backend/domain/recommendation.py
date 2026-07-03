"""
EIOS Domain Model — Recommendation

Canonical Enterprise Object per architecture/026.
Represents a mitigation proposal for identified risks.
AI-generated + governed: requires approval before activation (ASTATE-0001).
"""

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity
from .enums import ActionStatus, ConfidenceLevel, RiskLevel


@dataclass(slots=True, kw_only=True)
class Recommendation(BaseEntity):
    title: str
    description: str
    assessment_id: str | None = None
    risk_ids: list[str] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)
    priority: RiskLevel = field(default=RiskLevel.MEDIUM)
    confidence: ConfidenceLevel = field(default=ConfidenceLevel.HIGH)
    reasoning: str | None = None
    action_required: bool = True
    due_date: datetime | None = None
    approved_by: str | None = None
    action_status: ActionStatus = field(default=ActionStatus.OPEN)
    assigned_to_id: str | None = None
    expected_benefit: str | None = None
    expected_risk: str | None = None
    expected_roi: str | None = None
    implementation_complexity: str | None = None
