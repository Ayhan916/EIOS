"""API Schemas — Supplier Twin Extensions (M25 / KAN-85–89)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from domain.supplier_extensions import (
    CertificationType,
    ContactRole,
    ESGMetricType,
    ESGRatingProvider,
    LocationType,
    OwnershipType,
)

from .base import EntityResponse

# ── Supplier Location ─────────────────────────────────────────────────────────


class SupplierLocationCreate(BaseModel):
    location_type: LocationType
    name: str = Field(min_length=1, max_length=500)
    address: str | None = None
    city: str | None = None
    country: str = Field(default="", max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    region: str | None = Field(default=None, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    capacity_description: str | None = None
    employee_count: int | None = Field(default=None, ge=0)
    is_primary: bool = False
    notes: str | None = None


class SupplierLocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    address: str | None = None
    city: str | None = None
    country: str | None = Field(default=None, max_length=100)
    postal_code: str | None = None
    region: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    capacity_description: str | None = None
    employee_count: int | None = Field(default=None, ge=0)
    is_primary: bool | None = None
    is_active: bool | None = None
    notes: str | None = None


class SupplierLocationResponse(EntityResponse):
    supplier_id: str
    organization_id: str
    location_type: str
    name: str
    address: str | None
    city: str | None
    country: str
    postal_code: str | None
    region: str | None
    latitude: float | None
    longitude: float | None
    capacity_description: str | None
    employee_count: int | None
    is_primary: bool
    is_active: bool
    notes: str | None


# ── Supplier Contact ──────────────────────────────────────────────────────────


class SupplierContactCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=200)
    last_name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=50)
    role: ContactRole = ContactRole.OTHER
    job_title: str | None = Field(default=None, max_length=300)
    department: str | None = Field(default=None, max_length=200)
    language: str = Field(default="en", max_length=10)
    is_primary: bool = False
    notes: str | None = None


class SupplierContactUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=200)
    last_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = None
    phone: str | None = None
    role: ContactRole | None = None
    job_title: str | None = None
    department: str | None = None
    is_primary: bool | None = None
    is_active: bool | None = None
    notes: str | None = None


class SupplierContactResponse(EntityResponse):
    supplier_id: str
    organization_id: str
    first_name: str
    last_name: str
    full_name: str
    email: str | None
    phone: str | None
    role: str
    job_title: str | None
    department: str | None
    language: str
    is_primary: bool
    is_active: bool
    notes: str | None

    @classmethod
    def from_model(cls, m: Any) -> SupplierContactResponse:
        return cls(
            id=m.id,
            status=m.status,
            version=m.version,
            created_at=m.created_at,
            updated_at=m.updated_at,
            supplier_id=m.supplier_id,
            organization_id=m.organization_id,
            first_name=m.first_name,
            last_name=m.last_name,
            full_name=f"{m.first_name} {m.last_name}",
            email=m.email,
            phone=m.phone,
            role=m.role,
            job_title=m.job_title,
            department=m.department,
            language=m.language,
            is_primary=m.is_primary,
            is_active=m.is_active,
            notes=m.notes,
        )


# ── Supplier Certification ────────────────────────────────────────────────────


class SupplierCertificationCreate(BaseModel):
    cert_type: CertificationType
    custom_cert_name: str | None = Field(default=None, max_length=300)
    issuing_body: str | None = Field(default=None, max_length=300)
    certificate_number: str | None = Field(default=None, max_length=200)
    scope_description: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    evidence_id: str | None = None
    location_id: str | None = None
    notes: str | None = None


class SupplierCertificationResponse(EntityResponse):
    supplier_id: str
    organization_id: str
    cert_type: str
    custom_cert_name: str | None
    issuing_body: str | None
    certificate_number: str | None
    scope_description: str | None
    valid_from: date | None
    valid_until: date | None
    is_expired: bool
    days_until_expiry: int | None
    is_verified: bool
    verified_at: datetime | None
    evidence_id: str | None
    location_id: str | None
    notes: str | None

    @classmethod
    def from_model(cls, m: Any) -> SupplierCertificationResponse:
        today = date.today()
        is_expired = m.valid_until is not None and m.valid_until < today
        days = (m.valid_until - today).days if m.valid_until is not None else None
        return cls(
            id=m.id,
            status=m.status,
            version=m.version,
            created_at=m.created_at,
            updated_at=m.updated_at,
            supplier_id=m.supplier_id,
            organization_id=m.organization_id,
            cert_type=m.cert_type,
            custom_cert_name=m.custom_cert_name,
            issuing_body=m.issuing_body,
            certificate_number=m.certificate_number,
            scope_description=m.scope_description,
            valid_from=m.valid_from,
            valid_until=m.valid_until,
            is_expired=is_expired,
            days_until_expiry=days,
            is_verified=m.is_verified,
            verified_at=m.verified_at,
            evidence_id=m.evidence_id,
            location_id=m.location_id,
            notes=m.notes,
        )


# ── Supplier Ownership ────────────────────────────────────────────────────────


class SupplierOwnershipUpsert(BaseModel):
    ownership_type: OwnershipType = OwnershipType.PRIVATE
    parent_company_name: str | None = Field(default=None, max_length=500)
    parent_company_country: str | None = Field(default=None, max_length=100)
    ownership_percentage: float | None = Field(default=None, ge=0, le=100)
    ultimate_beneficial_owner: str | None = Field(default=None, max_length=500)
    ubo_country: str | None = Field(default=None, max_length=100)
    ubo_ownership_pct: float | None = Field(default=None, ge=0, le=100)
    publicly_listed: bool = False
    stock_exchange: str | None = Field(default=None, max_length=100)
    ticker_symbol: str | None = Field(default=None, max_length=20)
    market_cap_eur: float | None = Field(default=None, ge=0)
    lei_code: str | None = Field(default=None, max_length=20)
    duns_number: str | None = Field(default=None, max_length=20)
    vat_number: str | None = Field(default=None, max_length=50)
    registration_number: str | None = Field(default=None, max_length=100)
    registration_country: str | None = Field(default=None, max_length=100)
    is_state_owned: bool = False
    state_ownership_pct: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = None


class SupplierOwnershipResponse(EntityResponse):
    supplier_id: str
    organization_id: str
    ownership_type: str
    parent_company_name: str | None
    parent_company_country: str | None
    ownership_percentage: float | None
    ultimate_beneficial_owner: str | None
    ubo_country: str | None
    ubo_ownership_pct: float | None
    publicly_listed: bool
    stock_exchange: str | None
    ticker_symbol: str | None
    market_cap_eur: float | None
    lei_code: str | None
    duns_number: str | None
    vat_number: str | None
    registration_number: str | None
    registration_country: str | None
    is_state_owned: bool
    state_ownership_pct: float | None
    notes: str | None


# ── Supplier ESG Metrics ──────────────────────────────────────────────────────


class SupplierESGMetricRecord(BaseModel):
    reporting_year: int = Field(ge=2000, le=2100)
    metric_type: ESGMetricType
    value: float
    unit: str = Field(min_length=1, max_length=50)
    reporting_period: str = Field(default="ANNUAL", max_length=10)
    custom_metric_name: str | None = Field(default=None, max_length=300)
    esrs_reference: str | None = Field(default=None, max_length=20)
    gri_reference: str | None = Field(default=None, max_length=30)
    data_source: str | None = Field(default=None, max_length=300)
    is_third_party_verified: bool = False
    verification_standard: str | None = Field(default=None, max_length=100)
    evidence_id: str | None = None
    notes: str | None = None


class SupplierESGMetricResponse(EntityResponse):
    supplier_id: str
    organization_id: str
    reporting_year: int
    reporting_period: str
    metric_type: str
    custom_metric_name: str | None
    value: float
    unit: str
    esrs_reference: str | None
    gri_reference: str | None
    data_source: str | None
    is_third_party_verified: bool
    verification_standard: str | None
    evidence_id: str | None
    notes: str | None


# ── External ESG Ratings (KAN-90) ─────────────────────────────────────────────


class ExternalESGRatingCreate(BaseModel):
    provider: ESGRatingProvider
    rating_date: date
    score: float | None = None
    max_score: float | None = None
    score_pct: float | None = Field(default=None, ge=0, le=100)
    grade: str | None = Field(default=None, max_length=30)
    percentile: float | None = Field(default=None, ge=0, le=100)
    peer_group: str | None = Field(default=None, max_length=300)
    environmental_score: float | None = None
    social_score: float | None = None
    governance_score: float | None = None
    ethics_score: float | None = None
    sustainable_procurement_score: float | None = None
    valid_until: date | None = None
    report_url: str | None = Field(default=None, max_length=1000)
    methodology_version: str | None = Field(default=None, max_length=100)
    evidence_id: str | None = None
    notes: str | None = None


class ExternalESGRatingResponse(EntityResponse):
    supplier_id: str
    organization_id: str
    provider: str
    rating_date: date
    score: float | None
    max_score: float | None
    score_pct: float | None
    grade: str | None
    percentile: float | None
    peer_group: str | None
    environmental_score: float | None
    social_score: float | None
    governance_score: float | None
    ethics_score: float | None
    sustainable_procurement_score: float | None
    valid_until: date | None
    is_expired: bool
    days_until_expiry: int | None
    report_url: str | None
    methodology_version: str | None
    evidence_id: str | None
    notes: str | None

    @classmethod
    def from_model(cls, m: Any) -> ExternalESGRatingResponse:
        from datetime import date as date_type

        today = date_type.today()
        is_expired = m.valid_until is not None and m.valid_until < today
        days = (m.valid_until - today).days if m.valid_until is not None else None
        return cls(
            id=m.id,
            created_at=m.created_at,
            updated_at=m.updated_at,
            supplier_id=m.supplier_id,
            organization_id=m.organization_id,
            provider=m.provider,
            rating_date=m.rating_date,
            score=m.score,
            max_score=m.max_score,
            score_pct=m.score_pct,
            grade=m.grade,
            percentile=m.percentile,
            peer_group=m.peer_group,
            environmental_score=m.environmental_score,
            social_score=m.social_score,
            governance_score=m.governance_score,
            ethics_score=m.ethics_score,
            sustainable_procurement_score=m.sustainable_procurement_score,
            valid_until=m.valid_until,
            is_expired=is_expired,
            days_until_expiry=days,
            report_url=m.report_url,
            methodology_version=m.methodology_version,
            evidence_id=m.evidence_id,
            notes=m.notes,
        )
