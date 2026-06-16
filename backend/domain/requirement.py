"""
EIOS Domain Model — Requirement

Canonical Enterprise Object per architecture/026.
Represents a regulatory or policy requirement (CSDDD, LkSG, CSRD, or internal).
Governed object per ASTATE-0001.
"""

from dataclasses import dataclass, field
from typing import Optional

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class Requirement(BaseEntity):
    title: str
    description: str
    source: str
    article: Optional[str] = None
    mandatory: bool = True
    requirement_type: str = ""
    control_ids: list[str] = field(default_factory=list)
