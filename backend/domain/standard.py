"""
EIOS Domain Model — Standard

Canonical Enterprise Object per architecture/026.
Represents an enterprise or external standard (ISO 26000, GRI, ESRS, etc.).
Governed object per ASTATE-0001.
"""

from dataclasses import dataclass, field

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class Standard(BaseEntity):
    title: str
    description: str
    standard_type: str = ""
    reference: str | None = None
    version_label: str | None = None
    requirement_ids: list[str] = field(default_factory=list)
