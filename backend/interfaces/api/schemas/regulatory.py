from __future__ import annotations

from pydantic import BaseModel, Field


# ── Regulations ───────────────────────────────────────────────────────────────


class RegulationResponse(BaseModel):
    id: str
    code: str
    name: str
    jurisdiction: str
    reg_version: str
    reg_status: str
    description: str
    requirement_count: int = 0


class RegulationRequirementResponse(BaseModel):
    id: str
    regulation_id: str
    code: str
    reference: str
    title: str
    description: str
    category: str
    pillar: str
    severity: str
    obligation_type: str


# ── Requirement Mappings ──────────────────────────────────────────────────────


class CreateMappingRequest(BaseModel):
    regulation_requirement_id: str
    entity_type: str = Field(..., pattern="^(finding|risk|recommendation)$")
    entity_id: str
    rationale: str = ""
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    supplier_id: str | None = None
    assessment_id: str | None = None


class RequirementMappingResponse(BaseModel):
    id: str
    organization_id: str
    regulation_requirement_id: str
    requirement_code: str = ""
    requirement_title: str = ""
    entity_type: str
    entity_id: str
    confidence: float
    rationale: str
    mapping_method: str
    mapping_version: str
    regulation_version_at_mapping: str = "1.0"
    mapped_at: str
    supplier_id: str | None
    assessment_id: str | None


# ── Compliance Gaps ───────────────────────────────────────────────────────────


class ComplianceGapResponse(BaseModel):
    id: str
    organization_id: str
    regulation_requirement_id: str
    requirement_code: str = ""
    requirement_title: str = ""
    supplier_id: str | None
    gap_type: str
    severity: str
    description: str
    source_entity_type: str | None
    source_entity_id: str | None
    calculated_at: str
    calculation_version: str = "1.0"
    regulation_version_at_calculation: str = "1.0"
    is_resolved: bool


class GapSummary(BaseModel):
    total: int
    critical: int
    high: int
    medium: int
    low: int
    by_gap_type: dict[str, int]
    by_framework: dict[str, int]


# ── Framework Status ──────────────────────────────────────────────────────────


class FrameworkStatusResponse(BaseModel):
    regulation_code: str
    regulation_name: str
    status: str
    total_requirements: int
    covered_requirements: int
    coverage_ratio: float
    open_gap_count: int
    critical_gap_count: int
    high_gap_count: int
    medium_gap_count: int
    low_gap_count: int
    explanation: str
    top_gap_requirement_codes: list[str]


class ComplianceDashboardResponse(BaseModel):
    organization_id: str
    overall_coverage_ratio: float
    total_open_gaps: int
    total_critical_gaps: int
    frameworks: list[FrameworkStatusResponse]


# ── Supplier Compliance ───────────────────────────────────────────────────────


class SupplierComplianceResponse(BaseModel):
    supplier_id: str
    mappings: list[RequirementMappingResponse]
    gaps: list[ComplianceGapResponse]
    framework_statuses: list[FrameworkStatusResponse]
    total_mappings: int
    total_open_gaps: int


# ── Assessment Compliance ─────────────────────────────────────────────────────


class AssessmentComplianceDetailResponse(BaseModel):
    assessment_id: str
    mappings: list[RequirementMappingResponse]
    covered_requirement_codes: list[str]
    coverage_ratio: float
    framework_coverage: list[dict]


# ── Compliance Reports ────────────────────────────────────────────────────────


class ComplianceReportSummary(BaseModel):
    id: str
    organization_id: str
    report_type: str
    framework_code: str
    framework_version: str
    generated_at: str
    generated_by: str
    report_hash: str


class ComplianceReportResponse(BaseModel):
    id: str
    organization_id: str
    report_type: str
    framework_code: str
    framework_version: str
    generated_at: str
    generated_by: str
    report_hash: str
    report_data: dict
