"""
EIOS Domain Model — Sector

Primary unit of ESG assessment per Founder Decision (BC-11) and FR-002.
Represents a NACE-classified industry sector.
Company and Supplier are sub-entities of Sector.
"""

from dataclasses import dataclass
from typing import Optional

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class Sector(BaseEntity):
    name: str
    nace_code: str
    nace_description: Optional[str] = None
    risk_profile: Optional[str] = None
    parent_sector_id: Optional[str] = None
    organization_id: Optional[str] = None
