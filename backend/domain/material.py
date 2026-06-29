"""
EIOS Domain — Material Twin (M26 / KAN-91–97)

Digital representation of raw materials, components, and substances
in the enterprise supply chain. Each Material is a first-class aggregate
with its own BOM composition, supplier sourcing, compliance flags,
and sustainability metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, date
from enum import Enum

from .base_entity import BaseEntity


# ── Enumerations ──────────────────────────────────────────────────────────────

class MaterialType(str, Enum):
    RAW_MATERIAL = "RAW_MATERIAL"
    PROCESSED_MATERIAL = "PROCESSED_MATERIAL"
    COMPONENT = "COMPONENT"
    SUBSTANCE = "SUBSTANCE"
    ALLOY = "ALLOY"
    POLYMER = "POLYMER"
    COMPOSITE = "COMPOSITE"
    PACKAGING = "PACKAGING"
    ENERGY_CARRIER = "ENERGY_CARRIER"
    OTHER = "OTHER"


class MaterialStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PHASING_OUT = "PHASING_OUT"
    RESTRICTED = "RESTRICTED"
    BANNED = "BANNED"
    ARCHIVED = "ARCHIVED"


class ComplianceRegulation(str, Enum):
    REACH_SVHC = "REACH_SVHC"              # EU REACH — Substances of Very High Concern
    ROHS = "ROHS"                           # Restriction of Hazardous Substances
    CONFLICT_MINERALS = "CONFLICT_MINERALS" # 3TG — EU Conflict Minerals / Dodd-Frank
    EUDR = "EUDR"                           # EU Deforestation Regulation
    BATTERY_REGULATION = "BATTERY_REGULATION"  # EU Battery Regulation 2023/1542
    UFLPA = "UFLPA"                         # Uyghur Forced Labor Prevention Act
    CBAM = "CBAM"                           # Carbon Border Adjustment Mechanism
    POP = "POP"                             # Persistent Organic Pollutants
    WEEE = "WEEE"                           # Waste Electrical and Electronic Equipment
    SCIP = "SCIP"                           # EU SCIP database (SVHC in articles)
    TSCA = "TSCA"                           # US Toxic Substances Control Act
    PACKAGING_REGULATION = "PACKAGING_REGULATION"
    CUSTOM = "CUSTOM"


class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    UNDER_REVIEW = "UNDER_REVIEW"
    EXEMPTED = "EXEMPTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class SourcingRisk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ── Domain Entities ───────────────────────────────────────────────────────────

@dataclass(slots=True, kw_only=True)
class Material(BaseEntity):
    """Core Material entity — represents a material, substance, or component in the supply chain."""

    organization_id: str
    name: str
    material_type: MaterialType
    material_status: MaterialStatus = MaterialStatus.ACTIVE

    # Internal reference
    internal_code: str | None = None        # ERP / PLM material number

    # Chemical identification (substances)
    cas_number: str | None = None           # Chemical Abstracts Service number
    ec_number: str | None = None            # European Community EINECS number
    iupac_name: str | None = None
    molecular_formula: str | None = None

    # Trade classification
    hs_code: str | None = None              # Harmonized System code (6–10 digits)
    un_number: str | None = None            # UN dangerous goods number
    ghs_hazard_class: str | None = None

    # Physical / commercial
    unit_of_measure: str = "kg"             # kg, t, l, m², m³, pcs
    weight_per_unit_kg: float | None = None

    # Provenance
    country_of_origin: str | None = None

    # Critical Raw Materials (EU CRM list 2023)
    is_critical_raw_material: bool = False
    recycled_content_pct: float | None = None

    description: str | None = None
    notes: str | None = None


@dataclass(slots=True, kw_only=True)
class MaterialComposition(BaseEntity):
    """Bill-of-Materials link: a material contains another material at a given weight fraction."""

    organization_id: str
    parent_material_id: str
    child_material_id: str
    weight_pct: float | None = None         # percentage of total weight (0–100)
    quantity: float | None = None
    unit: str | None = None
    notes: str | None = None


@dataclass(slots=True, kw_only=True)
class MaterialSourcing(BaseEntity):
    """Tracks which supplier provides a given material and from which country."""

    organization_id: str
    material_id: str
    supplier_id: str
    country_of_origin: str | None = None
    annual_volume: float | None = None
    unit: str | None = None
    price_per_unit_eur: float | None = None
    is_primary: bool = False
    lead_time_days: int | None = None
    sourcing_risk: SourcingRisk = SourcingRisk.MEDIUM
    certification_required: str | None = None  # e.g. "FSC", "RSPO"
    notes: str | None = None


@dataclass(slots=True, kw_only=True)
class MaterialComplianceFlag(BaseEntity):
    """Compliance assessment of a material against a specific regulation."""

    organization_id: str
    material_id: str
    regulation: ComplianceRegulation
    custom_regulation_name: str | None = None
    compliance_status: ComplianceStatus = ComplianceStatus.UNKNOWN
    assessed_at: date | None = None
    valid_until: date | None = None
    assessor: str | None = None             # user/body that performed assessment
    evidence_id: str | None = None
    notes: str | None = None

    @property
    def is_expired(self) -> bool:
        if self.valid_until is None:
            return False
        return self.valid_until < datetime.now(UTC).date()


@dataclass(slots=True, kw_only=True)
class MaterialSustainabilityMetric(BaseEntity):
    """Life-cycle sustainability data for a material (cradle-to-gate or cradle-to-grave)."""

    organization_id: str
    material_id: str
    reporting_year: int
    # Carbon
    carbon_footprint_kg_co2e_per_kg: float | None = None
    carbon_scope: str = "cradle_to_gate"    # cradle_to_gate | cradle_to_grave | cradle_to_cradle
    # Water
    water_footprint_l_per_kg: float | None = None
    # Energy
    energy_mj_per_kg: float | None = None
    energy_renewable_pct: float | None = None
    # Circularity
    recycled_content_pct: float | None = None
    recyclability_pct: float | None = None
    biodegradable: bool | None = None
    # Source / verification
    data_source: str | None = None          # e.g. ecoinvent 3.9, supplier EPD
    is_third_party_verified: bool = False
    verification_standard: str | None = None  # ISO 14040, EPD, PEF
    evidence_id: str | None = None
    notes: str | None = None
