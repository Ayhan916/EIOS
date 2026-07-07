"""Pydantic schemas — M7 Supply Chain Compliance Extensions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from infrastructure.persistence.models.regulatory import ProductComplianceScanModel


class ProductComplianceScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    product_id: str
    regulation_code: str
    scan_result: str
    total_materials: int
    compliant_count: int
    non_compliant_count: int
    unknown_count: int
    flagged_material_ids: list[str]
    scan_version: str
    scanned_at: datetime
    scanned_by: str | None

    @classmethod
    def from_model(cls, m: ProductComplianceScanModel) -> ProductComplianceScanResponse:
        return cls.model_validate(m)


class ProductComplianceScanListResponse(BaseModel):
    items: list[ProductComplianceScanResponse]
    total: int


class ScanTriggerRequest(BaseModel):
    regulation_code: str


class MaterialStatsResponse(BaseModel):
    total_active: int
    non_compliant: int
    substances_of_concern_in_bom: int


class ProductStatsResponse(BaseModel):
    total_active: int
    scanned: int
    non_compliant: int


class DPPStatsResponse(BaseModel):
    total: int
    disclosed: int
    non_compliant: int


class AtRiskRegulationResponse(BaseModel):
    regulation_code: str
    non_compliant_materials: int


class SupplyChainComplianceSummaryResponse(BaseModel):
    organization_id: str
    materials: MaterialStatsResponse
    products: ProductStatsResponse
    digital_product_passports: DPPStatsResponse
    top_at_risk_regulations: list[AtRiskRegulationResponse]
