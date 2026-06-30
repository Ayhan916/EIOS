"""Pydantic schemas — M8 Scope 3 Supply Chain Carbon Inventory."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from infrastructure.persistence.models.scope3 import (
    ProductCarbonFootprintModel,
    Scope3InventoryModel,
)


class MaterialBreakdownItem(BaseModel):
    material_id: str
    material_name: str
    weight_pct: float
    co2e_per_kg: float | None
    contribution_kg_co2e: float | None


class ProductCarbonFootprintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    product_id: str
    reporting_year: int
    pcf_kg_co2e_per_unit: float | None
    pcf_source: str
    bom_materials_total: int
    bom_materials_with_lca: int
    weight_coverage_pct: float | None
    material_breakdown: list[dict]
    calc_version: str
    calculated_at: datetime
    calculated_by: str | None
    notes: str | None

    @classmethod
    def from_model(cls, m: ProductCarbonFootprintModel) -> "ProductCarbonFootprintResponse":
        return cls.model_validate(m)


class ProductCarbonFootprintListResponse(BaseModel):
    items: list[ProductCarbonFootprintResponse]
    total: int


class PCFCalculateRequest(BaseModel):
    reporting_year: int
    notes: str | None = None


class TopContributor(BaseModel):
    product_id: str
    pcf_kg_co2e: float
    weight_coverage_pct: float | None


class Scope3InventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    reporting_year: int
    total_pcf_kg_co2e: float
    total_pcf_tco2e: float
    products_included: int
    products_with_full_lca: int
    products_with_partial_lca: int
    products_without_lca: int
    top_contributors: list[dict]
    calc_version: str
    calculated_at: datetime
    calculated_by: str | None

    @classmethod
    def from_model(cls, m: Scope3InventoryModel) -> "Scope3InventoryResponse":
        return cls.model_validate(m)


class Scope3InventoryListResponse(BaseModel):
    items: list[Scope3InventoryResponse]
    total: int


class Scope3OrgSummaryResponse(BaseModel):
    organization_id: str
    reporting_year: int | None
    total_products_with_pcf: int
    total_pcf_kg_co2e: float
    total_pcf_tco2e: float
    avg_pcf_kg_co2e_per_product: float | None
    lca_coverage_pct: float | None
