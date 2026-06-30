"""Base ERP Adapter — M6

Defines the abstract interface all ERP adapters must implement.
Adapters translate between ERP-native data formats and EIOS canonical schemas.

Inbound (ERP → EIOS):  fetch_materials() / fetch_bom()
Outbound (EIOS → ERP): push_dpp()

Adapters never write to the database — they return normalized dicts.
The sync service owns the DB writes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ERPMaterialRecord:
    """Normalized material record from an ERP system."""
    external_ref: str
    name: str
    material_type: str = "RAW_MATERIAL"
    cas_number: str | None = None
    unit_of_measure: str | None = None
    description: str | None = None
    country_of_origin: str | None = None
    is_substance_of_concern: bool = False
    raw: dict = field(default_factory=dict)


@dataclass
class ERPBOMRecord:
    """Normalized BOM line from an ERP system."""
    product_external_ref: str
    material_external_ref: str
    quantity: float = 1.0
    unit_of_measure: str | None = None
    weight_pct: float | None = None
    is_substance_of_concern: bool = False
    raw: dict = field(default_factory=dict)


@dataclass
class ERPDPPRecord:
    """Passport data to push outbound to an ERP system."""
    passport_uid: str
    product_external_ref: str
    carbon_footprint_kg_co2e: float | None
    recycled_content_pct: float | None
    substances_of_concern_count: int
    non_compliant_regulations_count: int
    disclosed_at: str | None
    raw: dict = field(default_factory=dict)


class BaseERPAdapter(ABC):
    """Abstract ERP adapter — implement per system type."""

    @abstractmethod
    async def test_connection(self) -> bool:
        """Verify connectivity to the ERP system. Returns True if reachable."""

    @abstractmethod
    async def fetch_materials(self) -> list[ERPMaterialRecord]:
        """Pull all materials from the ERP system."""

    @abstractmethod
    async def fetch_bom(self) -> list[ERPBOMRecord]:
        """Pull all BOM lines from the ERP system."""

    @abstractmethod
    async def push_dpp(self, records: list[ERPDPPRecord]) -> dict:
        """Push DPP data back to the ERP system.
        Returns a summary dict: {pushed: int, failed: int, errors: list[str]}
        """
