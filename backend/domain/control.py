"""
EIOS Domain Model — Control

Canonical Enterprise Object per architecture/026.
Represents a risk control measure (preventive, detective, or corrective).
"""

from dataclasses import dataclass, field

from .base_entity import BaseEntity
from .enums import ControlType


@dataclass(slots=True, kw_only=True)
class Control(BaseEntity):
    title: str
    description: str
    control_type: ControlType = field(default=ControlType.PREVENTIVE)
    risk_ids: list[str] = field(default_factory=list)
    requirement_ids: list[str] = field(default_factory=list)
    effectiveness: float | None = None
    automated: bool = False
