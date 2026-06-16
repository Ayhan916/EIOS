"""
EIOS Domain Model — Organization

Canonical Enterprise Object per architecture/026.
Represents a tenant organization on the platform.
"""

from dataclasses import dataclass
from typing import Optional

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class Organization(BaseEntity):
    name: str
    description: Optional[str] = None
    organization_type: str = ""
    country: Optional[str] = None
    industry: Optional[str] = None
