"""
EIOS Domain Model — Supplier

The primary subject of ESG due diligence. A Supplier owns assessments,
findings, risks, and recommendations, making it the top-level business entity
in the EIOS data model (M27).
"""

from dataclasses import dataclass, field

from .base_entity import BaseEntity
from .enums import ChainDirection, SupplierStatus, SupplierTier


@dataclass(slots=True, kw_only=True)
class Supplier(BaseEntity):
    organization_id: str
    name: str
    legal_name: str | None = None
    country: str = ""
    industry: str = ""
    nace_code: str | None = None
    website: str | None = None
    supplier_tier: SupplierTier = field(default=SupplierTier.TIER_1)
    supplier_status: SupplierStatus = field(default=SupplierStatus.ACTIVE)
    notes: str | None = None
    chain_direction: str = ChainDirection.UPSTREAM.value
    downstream_type: str | None = None
