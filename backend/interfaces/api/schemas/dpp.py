"""API Schemas — Digital Product Passport (M28 / KAN-94)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from domain.dpp import DPPFormat, DPPStatus
from .base import EntityResponse


class DPPCreate(BaseModel):
    product_id: str
    format: DPPFormat
    product_category: str | None = Field(default=None, max_length=200)
    # Battery-Regulation fields
    battery_chemistry: str | None = Field(default=None, max_length=20)
    capacity_wh: float | None = Field(default=None, ge=0)
    nominal_voltage_v: float | None = Field(default=None, ge=0)
    declared_capacity_cycles: int | None = Field(default=None, ge=0)
    # Sustainability (declared)
    carbon_footprint_kg_co2e: float | None = Field(default=None, ge=0)
    carbon_footprint_source: str | None = Field(default=None, max_length=30)
    recycled_content_pct: float | None = Field(default=None, ge=0, le=100)
    renewable_content_pct: float | None = Field(default=None, ge=0, le=100)
    # Manufacturer
    manufacturer_name: str | None = Field(default=None, max_length=300)
    manufacturer_country: str | None = Field(default=None, max_length=100)
    manufacturing_date: date | None = None
    # Lifecycle
    valid_from: date | None = None
    valid_until: date | None = None
    # Evidence
    evidence_id: str | None = None
    notes: str | None = None


class DPPUpdate(BaseModel):
    dpp_status: DPPStatus | None = None
    product_category: str | None = None
    battery_chemistry: str | None = None
    capacity_wh: float | None = Field(default=None, ge=0)
    nominal_voltage_v: float | None = Field(default=None, ge=0)
    declared_capacity_cycles: int | None = Field(default=None, ge=0)
    carbon_footprint_kg_co2e: float | None = Field(default=None, ge=0)
    carbon_footprint_source: str | None = None
    recycled_content_pct: float | None = Field(default=None, ge=0, le=100)
    renewable_content_pct: float | None = Field(default=None, ge=0, le=100)
    manufacturer_name: str | None = None
    manufacturer_country: str | None = None
    manufacturing_date: date | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    evidence_id: str | None = None
    notes: str | None = None


class DPPResponse(EntityResponse):
    organization_id: str
    product_id: str
    format: str
    dpp_status: str
    passport_uid: str
    qr_payload: str | None
    product_category: str | None
    battery_chemistry: str | None
    capacity_wh: float | None
    nominal_voltage_v: float | None
    declared_capacity_cycles: int | None
    carbon_footprint_kg_co2e: float | None
    carbon_footprint_source: str | None
    recycled_content_pct: float | None
    renewable_content_pct: float | None
    substances_of_concern_count: int
    non_compliant_regulations_count: int
    manufacturer_name: str | None
    manufacturer_country: str | None
    manufacturing_date: date | None
    valid_from: date | None
    valid_until: date | None
    disclosed_at: datetime | None
    is_public: bool
    is_expired: bool
    evidence_id: str | None
    notes: str | None

    @classmethod
    def from_model(cls, m: Any) -> "DPPResponse":
        today = date.today()
        is_expired = m.valid_until is not None and m.valid_until < today
        return cls(
            id=m.id,
            status=m.status,
            version=m.version,
            created_at=m.created_at,
            updated_at=m.updated_at,
            organization_id=m.organization_id,
            product_id=m.product_id,
            format=m.format,
            dpp_status=m.dpp_status,
            passport_uid=m.passport_uid,
            qr_payload=m.qr_payload,
            product_category=m.product_category,
            battery_chemistry=m.battery_chemistry,
            capacity_wh=m.capacity_wh,
            nominal_voltage_v=m.nominal_voltage_v,
            declared_capacity_cycles=m.declared_capacity_cycles,
            carbon_footprint_kg_co2e=m.carbon_footprint_kg_co2e,
            carbon_footprint_source=m.carbon_footprint_source,
            recycled_content_pct=m.recycled_content_pct,
            renewable_content_pct=m.renewable_content_pct,
            substances_of_concern_count=m.substances_of_concern_count,
            non_compliant_regulations_count=m.non_compliant_regulations_count,
            manufacturer_name=m.manufacturer_name,
            manufacturer_country=m.manufacturer_country,
            manufacturing_date=m.manufacturing_date,
            valid_from=m.valid_from,
            valid_until=m.valid_until,
            disclosed_at=m.disclosed_at,
            is_public=m.disclosed_at is not None,
            is_expired=is_expired,
            evidence_id=m.evidence_id,
            notes=m.notes,
        )


class DPPListResponse(BaseModel):
    items: list[DPPResponse]
    total: int
    limit: int
    offset: int
