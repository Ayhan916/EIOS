from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl

from domain.enums import ChainDirection, SupplierStatus, SupplierTier

from .base import EntityResponse


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    legal_name: str | None = Field(default=None, max_length=500)
    country: str = Field(default="", max_length=100)
    industry: str = Field(default="", max_length=200)
    nace_code: str | None = Field(default=None, max_length=20)
    website: str | None = Field(default=None, max_length=500)
    supplier_tier: SupplierTier = SupplierTier.TIER_1
    notes: str | None = None
    chain_direction: str = ChainDirection.UPSTREAM.value
    downstream_type: str | None = None


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    legal_name: str | None = Field(default=None, max_length=500)
    country: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=200)
    nace_code: str | None = Field(default=None, max_length=20)
    website: str | None = Field(default=None, max_length=500)
    supplier_tier: SupplierTier | None = None
    supplier_status: SupplierStatus | None = None
    notes: str | None = None
    chain_direction: str | None = None
    downstream_type: str | None = None


class SupplierResponse(EntityResponse):
    organization_id: str
    name: str
    legal_name: str | None = None
    country: str
    industry: str
    nace_code: str | None = None
    website: str | None = None
    supplier_tier: str
    supplier_status: str
    notes: str | None = None
    chain_direction: str = ChainDirection.UPSTREAM.value
    downstream_type: str | None = None


class SupplierRiskProfile(BaseModel):
    supplier_id: str
    supplier_name: str
    total_assessments: int
    approved_assessments: int
    assessments_in_review: int
    last_assessment_date: str | None
    total_findings: int
    findings_by_severity: dict[str, int]
    total_risks: int
    risks_by_severity: dict[str, int]
    open_recommendations: int
    open_actions: int
    overdue_actions: int
