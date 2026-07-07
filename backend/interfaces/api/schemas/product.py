"""API Schemas — Product Twin (M27 / KAN-101)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from domain.product import ProductStatus, ProductType, TargetMarket

from .base import EntityResponse

# ── Product ───────────────────────────────────────────────────────────────────


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    product_type: ProductType
    sku: str | None = Field(default=None, max_length=200)
    internal_code: str | None = Field(default=None, max_length=100)
    gtin: str | None = Field(default=None, max_length=20)
    category: str | None = Field(default=None, max_length=200)
    brand: str | None = Field(default=None, max_length=200)
    unit_of_measure: str = Field(default="pcs", max_length=20)
    weight_kg: float | None = Field(default=None, ge=0)
    country_of_manufacture: str | None = Field(default=None, max_length=100)
    is_regulated_product: bool = False
    target_market: TargetMarket | None = None
    description: str | None = None
    notes: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    product_type: ProductType | None = None
    product_status: ProductStatus | None = None
    sku: str | None = None
    internal_code: str | None = None
    gtin: str | None = None
    category: str | None = None
    brand: str | None = None
    unit_of_measure: str | None = Field(default=None, max_length=20)
    weight_kg: float | None = Field(default=None, ge=0)
    country_of_manufacture: str | None = None
    is_regulated_product: bool | None = None
    target_market: TargetMarket | None = None
    description: str | None = None
    notes: str | None = None


class ProductResponse(EntityResponse):
    organization_id: str
    name: str
    product_type: str
    product_status: str
    sku: str | None
    internal_code: str | None
    gtin: str | None
    category: str | None
    brand: str | None
    unit_of_measure: str
    weight_kg: float | None
    country_of_manufacture: str | None
    is_regulated_product: bool
    target_market: str | None
    description: str | None
    notes: str | None

    @classmethod
    def from_model(cls, m: Any) -> ProductResponse:
        return cls(
            id=m.id,
            status=m.status,
            version=m.version,
            created_at=m.created_at,
            updated_at=m.updated_at,
            organization_id=m.organization_id,
            name=m.name,
            product_type=m.product_type,
            product_status=m.product_status,
            sku=m.sku,
            internal_code=m.internal_code,
            gtin=m.gtin,
            category=m.category,
            brand=m.brand,
            unit_of_measure=m.unit_of_measure,
            weight_kg=m.weight_kg,
            country_of_manufacture=m.country_of_manufacture,
            is_regulated_product=m.is_regulated_product,
            target_market=m.target_market,
            description=m.description,
            notes=m.notes,
        )


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    limit: int
    offset: int


# ── BOM Item ──────────────────────────────────────────────────────────────────


class ProductBOMItemCreate(BaseModel):
    material_id: str
    weight_pct: float | None = Field(default=None, ge=0, le=100)
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=20)
    is_substance_of_concern: bool = False
    notes: str | None = None


class ProductBOMItemResponse(EntityResponse):
    organization_id: str
    product_id: str
    material_id: str
    weight_pct: float | None
    quantity: float | None
    unit: str | None
    is_substance_of_concern: bool
    notes: str | None

    @classmethod
    def from_model(cls, m: Any) -> ProductBOMItemResponse:
        return cls(
            id=m.id,
            status=m.status,
            version=m.version,
            created_at=m.created_at,
            updated_at=m.updated_at,
            organization_id=m.organization_id,
            product_id=m.product_id,
            material_id=m.material_id,
            weight_pct=m.weight_pct,
            quantity=m.quantity,
            unit=m.unit,
            is_substance_of_concern=m.is_substance_of_concern,
            notes=m.notes,
        )


# ── Aggregated views ──────────────────────────────────────────────────────────


class ProductComplianceSummary(BaseModel):
    regulation: str
    worst_status: str
    material_count: int
    non_compliant_material_ids: list[str]


class ProductSustainabilitySummary(BaseModel):
    has_data: bool
    bom_materials_total: int = 0
    bom_materials_with_lca: int = 0
    weight_coverage_pct: float = 0.0
    product_carbon_footprint_kg_co2e_per_kg: float | None = None
    product_water_footprint_l_per_kg: float | None = None
    materials_with_concern: int = 0
