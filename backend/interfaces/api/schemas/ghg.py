"""M46.2 — GHG Protocol API schemas (G-030)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GHGCalculateRequest(BaseModel):
    scope: str = Field(description="SCOPE1, SCOPE2, or SCOPE3")
    category: str = Field(
        description="e.g. fuel_combustion, purchased_electricity, business_travel"
    )
    subcategory: str = Field(description="e.g. natural_gas, diesel, electricity")
    amount: float = Field(gt=0, description="Activity quantity in the specified unit")
    unit: str = Field(description="Unit of the activity amount, e.g. kWh, litre, km")
    source: str = Field(description="Factor source: DEFRA_2023 or EPA_2023")
    region: str = Field(description="Geographic region: UK, US, etc.")
    supplier_id: str | None = Field(
        default=None, description="Optional supplier this emission is attributed to"
    )
    notes: str | None = Field(default=None, max_length=2000)
    reporting_year: int | None = Field(default=None, ge=2000, le=2100)


class GHGCalculationResponse(BaseModel):
    calculation_id: str
    scope: str
    category: str
    subcategory: str
    amount: float
    unit: str
    factor_id: str
    factor_kgco2e_per_unit: float
    result_kgco2e: float
    result_tco2e: float
    source: str
    region: str
    description: str
    notes: str | None
    reporting_year: int | None
    calculated_at: datetime


class GHGEmissionFactorResponse(BaseModel):
    id: str
    scope: str
    category: str
    subcategory: str
    unit: str
    factor_kgco2e_per_unit: float
    source: str
    region: str
    year: int
    description: str | None
    is_custom: bool

    model_config = {"from_attributes": True}


class GHGBulkCalculateItem(BaseModel):
    scope: str
    category: str
    subcategory: str
    amount: float = Field(gt=0)
    unit: str
    source: str
    region: str
    supplier_id: str | None = None
    notes: str | None = None
    reporting_year: int | None = None


class GHGBulkCalculateRequest(BaseModel):
    activities: list[GHGBulkCalculateItem] = Field(min_length=1, max_length=500)


class GHGBulkCalculateResponse(BaseModel):
    results: list[GHGCalculationResponse]
    errors: list[dict]
    total_kgco2e: float
    total_tco2e: float
