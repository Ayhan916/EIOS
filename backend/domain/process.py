"""
EIOS Domain Model — Process

Canonical Enterprise Object per architecture/026.
Represents an enterprise business process.
"""

from dataclasses import dataclass, field

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class Process(BaseEntity):
    title: str
    description: str
    process_type: str = ""
    steps: list[str] = field(default_factory=list)
    owner_domain: str | None = None
    automated: bool = False
