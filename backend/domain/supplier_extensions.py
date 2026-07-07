"""
EIOS Domain — Supplier Twin Extensions (M25 / KAN-85–89)

Extends the Supplier entity with the multi-dimensional structure required
for the Enterprise Digital Supply Chain Twin:
  - SupplierLocation    (plants, warehouses, production sites)
  - SupplierContact     (role-based contact persons)
  - SupplierCertification (ISO, IATF, SA8000 lifecycle)
  - SupplierOwnership   (corporate ownership, UBO, LEI)
  - SupplierESGMetric   (energy, water, waste, social KPIs)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum

from .base_entity import BaseEntity

# ── Enumerations ──────────────────────────────────────────────────────────────


class LocationType(str, Enum):
    PLANT = "PLANT"
    PRODUCTION_SITE = "PRODUCTION_SITE"
    WAREHOUSE = "WAREHOUSE"
    OFFICE = "OFFICE"
    HQ = "HQ"
    PORT = "PORT"
    DISTRIBUTION_CENTER = "DISTRIBUTION_CENTER"
    R_AND_D = "R_AND_D"
    MINE = "MINE"
    SMELTER = "SMELTER"


class ContactRole(str, Enum):
    SUSTAINABILITY = "SUSTAINABILITY"
    PROCUREMENT = "PROCUREMENT"
    LEGAL = "LEGAL"
    QUALITY = "QUALITY"
    FINANCE = "FINANCE"
    EXECUTIVE = "EXECUTIVE"
    OPERATIONS = "OPERATIONS"
    COMPLIANCE = "COMPLIANCE"
    HSE = "HSE"
    OTHER = "OTHER"


class CertificationType(str, Enum):
    ISO_14001 = "ISO_14001"  # Environmental Management
    ISO_45001 = "ISO_45001"  # Occupational H&S
    ISO_9001 = "ISO_9001"  # Quality Management
    ISO_50001 = "ISO_50001"  # Energy Management
    ISO_27001 = "ISO_27001"  # Information Security
    IATF_16949 = "IATF_16949"  # Automotive Quality
    SA8000 = "SA8000"  # Social Accountability
    EMAS = "EMAS"  # EU Eco-Management
    REACH = "REACH"  # EU Chemicals
    ROHS = "RoHS"  # Restriction of Hazardous Substances
    OHSAS_18001 = "OHSAS_18001"  # H&S (predecessor to ISO 45001)
    FSC = "FSC"  # Forest Stewardship Council
    RSPO = "RSPO"  # Responsible Sourcing of Palm Oil
    RMAP = "RMAP"  # Responsible Minerals Assurance Process
    CDP = "CDP"  # Carbon Disclosure Project
    ECOVADIS = "ECOVADIS"  # EcoVadis sustainability rating
    TISAX = "TISAX"  # Automotive Information Security
    CUSTOM = "CUSTOM"


class OwnershipType(str, Enum):
    PARENT_COMPANY = "PARENT_COMPANY"
    SUBSIDIARY = "SUBSIDIARY"
    JOINT_VENTURE = "JOINT_VENTURE"
    CONSORTIUM = "CONSORTIUM"
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    STATE_OWNED = "STATE_OWNED"
    FAMILY_OWNED = "FAMILY_OWNED"
    PRIVATE_EQUITY = "PRIVATE_EQUITY"


class ESGMetricType(str, Enum):
    # Environmental — Energy
    ENERGY_TOTAL_MWH = "ENERGY_TOTAL_MWH"
    ENERGY_RENEWABLE_MWH = "ENERGY_RENEWABLE_MWH"
    ENERGY_RENEWABLE_PCT = "ENERGY_RENEWABLE_PCT"
    ELECTRICITY_RENEWABLE_PCT = "ELECTRICITY_RENEWABLE_PCT"
    # Environmental — Water (ESRS E3)
    WATER_WITHDRAWAL_M3 = "WATER_WITHDRAWAL_M3"
    WATER_RECYCLED_M3 = "WATER_RECYCLED_M3"
    WATER_RECYCLED_PCT = "WATER_RECYCLED_PCT"
    WATER_STRESS_AREA_PCT = "WATER_STRESS_AREA_PCT"
    # Environmental — Waste (ESRS E5)
    WASTE_TOTAL_TONNES = "WASTE_TOTAL_TONNES"
    WASTE_RECYCLED_TONNES = "WASTE_RECYCLED_TONNES"
    WASTE_RECYCLED_PCT = "WASTE_RECYCLED_PCT"
    WASTE_HAZARDOUS_TONNES = "WASTE_HAZARDOUS_TONNES"
    WASTE_LANDFILL_TONNES = "WASTE_LANDFILL_TONNES"
    # Environmental — Biodiversity (ESRS E4)
    BIODIVERSITY_AREA_HA = "BIODIVERSITY_AREA_HA"
    PROTECTED_AREA_OPERATIONS_HA = "PROTECTED_AREA_OPERATIONS_HA"
    # Environmental — Air (ESRS E2)
    AIR_NOX_TONNES = "AIR_NOX_TONNES"
    AIR_SOX_TONNES = "AIR_SOX_TONNES"
    AIR_PARTICULATES_TONNES = "AIR_PARTICULATES_TONNES"
    AIR_VOC_TONNES = "AIR_VOC_TONNES"
    # Social — Workforce (ESRS S1)
    WORKFORCE_TOTAL = "WORKFORCE_TOTAL"
    WORKFORCE_FEMALE = "WORKFORCE_FEMALE"
    WORKFORCE_FEMALE_PCT = "WORKFORCE_FEMALE_PCT"
    WORKFORCE_MGMT_FEMALE_PCT = "WORKFORCE_MGMT_FEMALE_PCT"
    WORKFORCE_BOARD_FEMALE_PCT = "WORKFORCE_BOARD_FEMALE_PCT"
    # Social — Safety (ESRS S1)
    INJURY_RATE_PER_1M_HOURS = "INJURY_RATE_PER_1M_HOURS"
    LOST_TIME_INJURY_RATE = "LOST_TIME_INJURY_RATE"
    FATALITIES = "FATALITIES"
    TRAINING_HOURS_PER_EMPLOYEE = "TRAINING_HOURS_PER_EMPLOYEE"
    # Social — Community
    COMMUNITY_INVESTMENT_EUR = "COMMUNITY_INVESTMENT_EUR"
    # Governance
    WHISTLEBLOWER_CASES = "WHISTLEBLOWER_CASES"
    CORRUPTION_INCIDENTS = "CORRUPTION_INCIDENTS"
    # Custom
    CUSTOM = "CUSTOM"


# ── Domain Entities ───────────────────────────────────────────────────────────


@dataclass(slots=True, kw_only=True)
class SupplierLocation(BaseEntity):
    """A physical location belonging to a supplier (plant, warehouse, office)."""

    supplier_id: str
    organization_id: str
    location_type: LocationType
    name: str
    address: str | None = None
    city: str | None = None
    country: str = ""
    postal_code: str | None = None
    region: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    capacity_description: str | None = None
    employee_count: int | None = None
    is_primary: bool = False
    is_active: bool = True
    notes: str | None = None


@dataclass(slots=True, kw_only=True)
class SupplierContact(BaseEntity):
    """A named contact person at a supplier."""

    supplier_id: str
    organization_id: str
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    role: ContactRole = ContactRole.OTHER
    job_title: str | None = None
    department: str | None = None
    language: str = "en"
    is_primary: bool = False
    is_active: bool = True
    notes: str | None = None


@dataclass(slots=True, kw_only=True)
class SupplierCertification(BaseEntity):
    """An industry certification held by a supplier with lifecycle tracking."""

    supplier_id: str
    organization_id: str
    cert_type: CertificationType
    custom_cert_name: str | None = None
    issuing_body: str | None = None
    certificate_number: str | None = None
    scope_description: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    is_verified: bool = False
    verified_by: str | None = None
    verified_at: datetime | None = None
    evidence_id: str | None = None
    location_id: str | None = None
    notes: str | None = None

    @property
    def is_expired(self) -> bool:
        if self.valid_until is None:
            return False
        return self.valid_until < datetime.now(UTC).date()

    @property
    def days_until_expiry(self) -> int | None:
        if self.valid_until is None:
            return None
        delta = self.valid_until - datetime.now(UTC).date()
        return delta.days


@dataclass(slots=True, kw_only=True)
class SupplierOwnership(BaseEntity):
    """Corporate ownership structure of a supplier."""

    supplier_id: str
    organization_id: str
    ownership_type: OwnershipType = OwnershipType.PRIVATE
    # Parent company information
    parent_company_name: str | None = None
    parent_company_country: str | None = None
    ownership_percentage: float | None = None
    # Ultimate Beneficial Owner
    ultimate_beneficial_owner: str | None = None
    ubo_country: str | None = None
    ubo_ownership_pct: float | None = None
    # Capital markets
    publicly_listed: bool = False
    stock_exchange: str | None = None
    ticker_symbol: str | None = None
    market_cap_eur: float | None = None
    # Legal identifiers
    lei_code: str | None = None  # Legal Entity Identifier (ISO 17442)
    duns_number: str | None = None  # Dun & Bradstreet
    vat_number: str | None = None
    registration_number: str | None = None
    registration_country: str | None = None
    # State ownership flag — relevant for geopolitical risk
    is_state_owned: bool = False
    state_ownership_pct: float | None = None
    notes: str | None = None


@dataclass(slots=True, kw_only=True)
class SupplierESGMetric(BaseEntity):
    """A single ESG metric measurement for a supplier in a reporting period."""

    supplier_id: str
    organization_id: str
    reporting_year: int
    reporting_period: str = "ANNUAL"  # ANNUAL | H1 | H2 | Q1 | Q2 | Q3 | Q4
    metric_type: ESGMetricType
    custom_metric_name: str | None = None
    value: float
    unit: str
    # ESRS standard reference (e.g., E3-3, S1-14, G1-1)
    esrs_reference: str | None = None
    gri_reference: str | None = None
    data_source: str | None = None
    is_third_party_verified: bool = False
    verification_standard: str | None = None
    evidence_id: str | None = None
    notes: str | None = None


# ── KAN-90 — External ESG Ratings ────────────────────────────────────────────


class ESGRatingProvider(str, Enum):
    ECOVADIS = "ECOVADIS"
    MSCI = "MSCI"
    SUSTAINALYTICS = "SUSTAINALYTICS"
    CDP = "CDP"
    ISS_ESG = "ISS_ESG"
    REFINITIV = "REFINITIV"
    SP_GLOBAL = "SP_GLOBAL"
    BLOOMBERG_ESG = "BLOOMBERG_ESG"
    FTSE_RUSSELL = "FTSE_RUSSELL"
    MOODY_ESG = "MOODY_ESG"
    OTHER = "OTHER"


@dataclass(slots=True, kw_only=True)
class ExternalESGRating(BaseEntity):
    """An external ESG rating received from a third-party provider (EcoVadis, MSCI, etc.)."""

    supplier_id: str
    organization_id: str
    provider: ESGRatingProvider
    rating_date: date
    # Numeric score (provider-specific scale — stored alongside percentage for comparability)
    score: float | None = None
    max_score: float | None = None
    score_pct: float | None = None  # 0–100 normalised, computed if score+max_score given
    # Tier / letter grade (EcoVadis: Bronze/Silver/Gold/Platinum; MSCI: AAA–CCC)
    grade: str | None = None
    # Peer benchmarking
    percentile: float | None = None  # 0–100
    peer_group: str | None = None
    # Sub-scores (environment / social / governance)
    environmental_score: float | None = None
    social_score: float | None = None
    governance_score: float | None = None
    # EcoVadis-specific sub-topic scores
    ethics_score: float | None = None
    sustainable_procurement_score: float | None = None
    # Validity / expiry
    valid_until: date | None = None
    # Source metadata
    report_url: str | None = None
    methodology_version: str | None = None
    # Optional link to an uploaded evidence file
    evidence_id: str | None = None
    notes: str | None = None

    @property
    def is_expired(self) -> bool:
        if self.valid_until is None:
            return False
        return self.valid_until < datetime.now(UTC).date()

    @property
    def days_until_expiry(self) -> int | None:
        if self.valid_until is None:
            return None
        return (self.valid_until - datetime.now(UTC).date()).days
