"""
EIOS Domain Model — Task

Canonical Enterprise Object per architecture/026.
Represents a discrete unit of work within a Project.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .base_entity import BaseEntity
from .enums import RiskLevel


@dataclass(slots=True, kw_only=True)
class Task(BaseEntity):
    title: str
    description: str
    task_type: str = ""
    project_id: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: RiskLevel = field(default=RiskLevel.MEDIUM)
    due_date: Optional[datetime] = None
    completed: bool = False
