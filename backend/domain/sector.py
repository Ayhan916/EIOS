"""
EIOS Domain Model — Sector

Primary unit of ESG assessment per Founder Decision (BC-11) and FR-002.
Represents a NACE-classified industry sector.
Company and Supplier are sub-entities of Sector.
"""

from dataclasses import dataclass

from .base_entity import BaseEntity


@dataclass(slots=True, kw_only=True)
class Sector(BaseEntity):
    name: str
    nace_code: str
    nace_description: str | None = None
    risk_profile: str | None = None
    parent_sector_id: str | None = None
    organization_id: str | None = None
