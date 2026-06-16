"""
EIOS Domain Model — Project

Canonical Enterprise Object per architecture/026.
Represents an implementation or strategic initiative.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .base_entity import BaseEntity
from .enums import RiskLevel


@dataclass(slots=True, kw_only=True)
class Project(BaseEntity):
    title: str
    description: str
    project_type: str = ""
    priority: RiskLevel = field(default=RiskLevel.MEDIUM)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    organization_id: Optional[str] = None
