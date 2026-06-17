"""
EIOS Domain Model — Policy

Canonical Enterprise Object per architecture/026.
Represents an enterprise policy that governs behavior and decisions.
Governed object: requires approval before activation (ASTATE-0001).
"""

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class Policy(BaseEntity):
    title: str
    description: str
    policy_type: str = ""
    effective_date: datetime | None = None
    expiry_date: datetime | None = None
    approved_by: str | None = None
    requirement_ids: list[str] = field(default_factory=list)
    control_ids: list[str] = field(default_factory=list)
