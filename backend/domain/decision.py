"""
EIOS Domain Model — Decision

Canonical Enterprise Object per architecture/026.
Represents a formal governance decision.
Governed: requires Founder or authorized authority sign-off.
"""

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class Decision(BaseEntity):
    title: str
    description: str
    rationale: str
    decided_by: str
    decided_at: datetime | None = None
    decision_type: str = ""
    context: str | None = None
    recommendation_ids: list[str] = field(default_factory=list)
    affected_object_ids: list[str] = field(default_factory=list)
