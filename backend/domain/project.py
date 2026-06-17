"""
EIOS Domain Model — Project

Canonical Enterprise Object per architecture/026.
Represents an implementation or strategic initiative.
"""

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity
from .enums import RiskLevel


@dataclass(slots=True, kw_only=True)
class Project(BaseEntity):
    title: str
    description: str
    project_type: str = ""
    priority: RiskLevel = field(default=RiskLevel.MEDIUM)
    start_date: datetime | None = None
    end_date: datetime | None = None
    organization_id: str | None = None
