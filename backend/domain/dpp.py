"""
M28 — Digital Product Passport Domain (KAN-92)

The Digital Product Passport (DPP) is an EU regulatory artefact that
packages key sustainability, compliance and traceability data about a
product into a machine-readable, publicly accessible format.

Covered regulations:
  EU Battery Regulation 2023/1542   (mandatory DPP for batteries from 2026)
  EU ESPR / Ecodesign               (general DPP framework)
  EU Textile Regulation             (in draft)
  EU Packaging Regulation
  Custom                            (organisation-defined format)

The DPP links to a Product Twin (product_id) and inherits:
  - PCF (product_carbon_footprint_kg_co2e_per_kg) from material LCA
  - Compliance summary from material compliance flags
  - Substances of concern from BOM items
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class DPPFormat(str, Enum):
    BATTERY_REGULATION = "BATTERY_REGULATION"
    ESPR_GENERAL = "ESPR_GENERAL"
    TEXTILE = "TEXTILE"
    ELECTRONICS = "ELECTRONICS"
    PACKAGING = "PACKAGING"
    CUSTOM = "CUSTOM"


class DPPStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"


@dataclass
class DigitalProductPassport:
    """Core DPP entity.

    Stores both declared values (entered manually / from supplier data) and
    computed values derived from the linked Product / Material Twin.
    """

    id: str
    organization_id: str
    product_id: str  # link to ProductModel
    format: DPPFormat
    status: DPPStatus

    # Digital identity
    passport_uid: str  # public-facing UUID (stable, referenced in QR)
    qr_payload: str | None  # URL / JSON embedded in QR code

    # Product category context
    product_category: str | None  # free-text, e.g. "LFP battery cell"

    # Battery-Regulation-specific (nullable for other formats)
    battery_chemistry: str | None  # LFP, NMC, NCA, LCO, …
    capacity_wh: float | None
    nominal_voltage_v: float | None
    declared_capacity_cycles: int | None

    # Declared sustainability values
    carbon_footprint_kg_co2e: float | None  # product-level PCF (can be overridden)
    carbon_footprint_source: str | None  # "computed" | "declared" | "third-party"
    recycled_content_pct: float | None
    renewable_content_pct: float | None

    # Computed / aggregated (populated by service from twin data)
    substances_of_concern_count: int
    non_compliant_regulations_count: int

    # Manufacturer / provenance
    manufacturer_name: str | None
    manufacturer_country: str | None
    manufacturing_date: date | None

    # Lifecycle / publication
    valid_from: date | None
    valid_until: date | None
    disclosed_at: datetime | None  # when first published (not null = public)

    # Evidence
    evidence_id: str | None
    notes: str | None

    # Audit
    created_at: datetime
    updated_at: datetime
    created_by: str | None

    @property
    def is_public(self) -> bool:
        return self.disclosed_at is not None

    @property
    def is_expired(self) -> bool:
        if self.valid_until is None:
            return False
        return self.valid_until < date.today()
