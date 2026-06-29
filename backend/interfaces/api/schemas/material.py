"""API Schemas — Material Twin (M26 / KAN-91–97)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from domain.material import (
    ComplianceRegulation,
    ComplianceStatus,
    MaterialStatus,
    MaterialType,
    SourcingRisk,
)
from .base import EntityResponse


# ── Material Core ─────────────────────────────────────────────────────────────

class MaterialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    material_type: MaterialType
    internal_code: str | None = Field(default=None, max_length=100)
    cas_number: str | None = Field(default=None, max_length=20)
    ec_number: str | None = Field(default=None, max_length=20)
    iupac_name: str | None = None
    molecular_formula: str | None = Field(default=None, max_length=200)
    hs_code: str | None = Field(default=None, max_length=15)
    un_number: str | None = Field(default=None, max_length=10)
    ghs_hazard_class: str | None = Field(default=None, max_length=200)
    unit_of_measure: str = Field(default="kg", max_length=20)
    weight_per_unit_kg: float | None = Field(default=None, ge=0)
    country_of_origin: str | None = Field(default=None, max_length=100)
    is_critical_raw_material: bool = False
    recycled_content_pct: float | None = Field(default=None, ge=0, le=100)
    description: str | None = None
    notes: str | None = None


class MaterialUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    material_type: MaterialType | None = None
    material_status: MaterialStatus | None = None
    internal_code: str | None = None
    cas_number: str | None = None
    ec_number: str | None = None
    iupac_name: str | None = None
    hs_code: str | None = None
    unit_of_measure: str | None = Field(default=None, max_length=20)
    weight_per_unit_kg: float | None = Field(default=None, ge=0)
    country_of_origin: str | None = None
    is_critical_raw_material: bool | None = None
    recycled_content_pct: float | None = Field(default=None, ge=0, le=100)
    description: str | None = None
    notes: str | None = None


class MaterialResponse(EntityResponse):
    organization_id: str
    name: str
    material_type: str
    material_status: str
    internal_code: str | None
    cas_number: str | None
    ec_number: str | None
    iupac_name: str | None
    molecular_formula: str | None
    hs_code: str | None
    un_number: str | None
    ghs_hazard_class: str | None
    unit_of_measure: str
    weight_per_unit_kg: float | None
    country_of_origin: str | None
    is_critical_raw_material: bool
    recycled_content_pct: float | None
    description: str | None
    notes: str | None

    @classmethod
    def from_model(cls, m: Any) -> "MaterialResponse":
        return cls(
            id=m.id,
            status=m.status,
            version=m.version,
            created_at=m.created_at,
            updated_at=m.updated_at,
            organization_id=m.organization_id,
            name=m.name,
            material_type=m.material_type,
            material_status=m.material_status,
            internal_code=m.internal_code,
            cas_number=m.cas_number,
            ec_number=m.ec_number,
            iupac_name=m.iupac_name,
            molecular_formula=m.molecular_formula,
            hs_code=m.hs_code,
            un_number=m.un_number,
            ghs_hazard_class=m.ghs_hazard_class,
            unit_of_measure=m.unit_of_measure,
            weight_per_unit_kg=m.weight_per_unit_kg,
            country_of_origin=m.country_of_origin,
            is_critical_raw_material=m.is_critical_raw_material,
            recycled_content_pct=m.recycled_content_pct,
            description=m.description,
            notes=m.notes,
        )


class MaterialListResponse(BaseModel):
    items: list[MaterialResponse]
    total: int
    limit: int
    offset: int


# ── Composition / BOM ─────────────────────────────────────────────────────────

class MaterialCompositionCreate(BaseModel):
    child_material_id: str
    weight_pct: float | None = Field(default=None, ge=0, le=100)
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=20)
    notes: str | None = None


class MaterialCompositionResponse(EntityResponse):
    organization_id: str
    parent_material_id: str
    child_material_id: str
    weight_pct: float | None
    quantity: float | None
    unit: str | None
    notes: str | None

    @classmethod
    def from_model(cls, m: Any) -> "MaterialCompositionResponse":
        return cls(
            id=m.id,
            status=m.status,
            version=m.version,
            created_at=m.created_at,
            updated_at=m.updated_at,
            organization_id=m.organization_id,
            parent_material_id=m.parent_material_id,
            child_material_id=m.child_material_id,
            weight_pct=m.weight_pct,
            quantity=m.quantity,
            unit=m.unit,
            notes=m.notes,
        )


# ── Sourcing ──────────────────────────────────────────────────────────────────

class MaterialSourcingCreate(BaseModel):
    supplier_id: str
    country_of_origin: str | None = Field(default=None, max_length=100)
    annual_volume: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=20)
    price_per_unit_eur: float | None = Field(default=None, ge=0)
    is_primary: bool = False
    lead_time_days: int | None = Field(default=None, ge=0)
    sourcing_risk: SourcingRisk = SourcingRisk.MEDIUM
    certification_required: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class MaterialSourcingResponse(EntityResponse):
    organization_id: str
    material_id: str
    supplier_id: str
    country_of_origin: str | None
    annual_volume: float | None
    unit: str | None
    price_per_unit_eur: float | None
    is_primary: bool
    lead_time_days: int | None
    sourcing_risk: str
    certification_required: str | None
    notes: str | None

    @classmethod
    def from_model(cls, m: Any) -> "MaterialSourcingResponse":
        return cls(
            id=m.id,
            status=m.status,
            version=m.version,
            created_at=m.created_at,
            updated_at=m.updated_at,
            organization_id=m.organization_id,
            material_id=m.material_id,
            supplier_id=m.supplier_id,
            country_of_origin=m.country_of_origin,
            annual_volume=m.annual_volume,
            unit=m.unit,
            price_per_unit_eur=m.price_per_unit_eur,
            is_primary=m.is_primary,
            lead_time_days=m.lead_time_days,
            sourcing_risk=m.sourcing_risk,
            certification_required=m.certification_required,
            notes=m.notes,
        )


# ── Compliance Flags ──────────────────────────────────────────────────────────

class MaterialComplianceUpsert(BaseModel):
    regulation: ComplianceRegulation
    compliance_status: ComplianceStatus
    custom_regulation_name: str | None = Field(default=None, max_length=200)
    assessed_at: date | None = None
    valid_until: date | None = None
    assessor: str | None = Field(default=None, max_length=300)
    evidence_id: str | None = None
    notes: str | None = None


class MaterialComplianceResponse(EntityResponse):
    organization_id: str
    material_id: str
    regulation: str
    custom_regulation_name: str | None
    compliance_status: str
    assessed_at: date | None
    valid_until: date | None
    assessor: str | None
    evidence_id: str | None
    notes: str | None
    is_expired: bool

    @classmethod
    def from_model(cls, m: Any) -> "MaterialComplianceResponse":
        from datetime import date as _date
        today = _date.today()
        is_expired = m.valid_until is not None and m.valid_until < today
        return cls(
            id=m.id,
            status=m.status,
            version=m.version,
            created_at=m.created_at,
            updated_at=m.updated_at,
            organization_id=m.organization_id,
            material_id=m.material_id,
            regulation=m.regulation,
            custom_regulation_name=m.custom_regulation_name,
            compliance_status=m.compliance_status,
            assessed_at=m.assessed_at,
            valid_until=m.valid_until,
            assessor=m.assessor,
            evidence_id=m.evidence_id,
            notes=m.notes,
            is_expired=is_expired,
        )


# ── Sustainability Metrics ────────────────────────────────────────────────────

class MaterialSustainabilityUpsert(BaseModel):
    reporting_year: int = Field(ge=2000, le=2100)
    carbon_footprint_kg_co2e_per_kg: float | None = Field(default=None, ge=0)
    carbon_scope: str = Field(default="cradle_to_gate", max_length=30)
    water_footprint_l_per_kg: float | None = Field(default=None, ge=0)
    energy_mj_per_kg: float | None = Field(default=None, ge=0)
    energy_renewable_pct: float | None = Field(default=None, ge=0, le=100)
    recycled_content_pct: float | None = Field(default=None, ge=0, le=100)
    recyclability_pct: float | None = Field(default=None, ge=0, le=100)
    biodegradable: bool | None = None
    data_source: str | None = Field(default=None, max_length=300)
    is_third_party_verified: bool = False
    verification_standard: str | None = Field(default=None, max_length=100)
    evidence_id: str | None = None
    notes: str | None = None


class MaterialSustainabilityResponse(EntityResponse):
    organization_id: str
    material_id: str
    reporting_year: int
    carbon_footprint_kg_co2e_per_kg: float | None
    carbon_scope: str
    water_footprint_l_per_kg: float | None
    energy_mj_per_kg: float | None
    energy_renewable_pct: float | None
    recycled_content_pct: float | None
    recyclability_pct: float | None
    biodegradable: bool | None
    data_source: str | None
    is_third_party_verified: bool
    verification_standard: str | None
    evidence_id: str | None
    notes: str | None

    @classmethod
    def from_model(cls, m: Any) -> "MaterialSustainabilityResponse":
        return cls(
            id=m.id,
            status=m.status,
            version=m.version,
            created_at=m.created_at,
            updated_at=m.updated_at,
            organization_id=m.organization_id,
            material_id=m.material_id,
            reporting_year=m.reporting_year,
            carbon_footprint_kg_co2e_per_kg=m.carbon_footprint_kg_co2e_per_kg,
            carbon_scope=m.carbon_scope,
            water_footprint_l_per_kg=m.water_footprint_l_per_kg,
            energy_mj_per_kg=m.energy_mj_per_kg,
            energy_renewable_pct=m.energy_renewable_pct,
            recycled_content_pct=m.recycled_content_pct,
            recyclability_pct=m.recyclability_pct,
            biodegradable=m.biodegradable,
            data_source=m.data_source,
            is_third_party_verified=m.is_third_party_verified,
            verification_standard=m.verification_standard,
            evidence_id=m.evidence_id,
            notes=m.notes,
        )
