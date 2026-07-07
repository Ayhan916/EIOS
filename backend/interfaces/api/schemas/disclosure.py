"""M32 Sustainability Reporting & Disclosure Management — API Schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Disclosure Frameworks ─────────────────────────────────────────────────────


class DisclosureFrameworkResponse(BaseModel):
    id: str
    code: str
    name: str
    fw_version: str
    jurisdiction: str
    effective_date: str | None
    description: str
    status: str


class DisclosureRequirementResponse(BaseModel):
    id: str
    framework_id: str
    reference: str
    title: str
    description: str
    category: str
    status: str


class DisclosureFrameworkDetailResponse(BaseModel):
    framework: DisclosureFrameworkResponse
    requirements: list[DisclosureRequirementResponse]
    total_requirements: int


# ── Disclosure Responses ──────────────────────────────────────────────────────


class CreateDisclosureResponseRequest(BaseModel):
    requirement_id: str


class UpdateDisclosureResponseRequest(BaseModel):
    narrative_text: str | None = None


class SubmitForReviewRequest(BaseModel):
    pass


class ApproveDisclosureRequest(BaseModel):
    pass


class RejectDisclosureRequest(BaseModel):
    rationale: str = ""


class DisclosureResponseSummary(BaseModel):
    id: str
    organization_id: str
    requirement_id: str
    disclosure_status: str
    evidence_coverage: float
    coverage_category: str
    readiness_status: str
    updated_at: str


class CoverageFactor(BaseModel):
    factor: str
    description: str
    raw: float | int
    score: float
    weight: float
    contribution: float


class DisclosureResponseDetail(BaseModel):
    id: str
    organization_id: str
    requirement_id: str
    disclosure_status: str
    narrative_text: str
    evidence_coverage: float
    coverage_category: str
    coverage_rationale: list[CoverageFactor]
    readiness_status: str
    readiness_rationale: str
    reviewed_by: str | None
    approved_by: str | None
    published_at: str | None
    created_at: str
    updated_at: str


# ── Disclosure Workspace (requirement + context in one response) ──────────────


class LinkedEntitySummary(BaseModel):
    id: str
    entity_type: str
    title: str
    severity: str | None = None
    status: str | None = None


class DisclosureWorkspaceResponse(BaseModel):
    requirement: DisclosureRequirementResponse
    response: DisclosureResponseDetail | None
    linked_findings: list[LinkedEntitySummary]
    linked_risks: list[LinkedEntitySummary]
    linked_evidence: list[LinkedEntitySummary]
    open_compliance_gaps: list[LinkedEntitySummary]
    coverage_factors: list[CoverageFactor]


# ── Dashboard ─────────────────────────────────────────────────────────────────


class FrameworkDisclosureSummary(BaseModel):
    framework_id: str
    framework_code: str
    framework_name: str
    fw_version: str
    total_requirements: int
    not_started: int
    draft: int
    in_review: int
    approved: int
    published: int
    completion_pct: float
    avg_coverage: float
    critical_blockers: int


class DisclosureDashboardResponse(BaseModel):
    organization_id: str
    frameworks: list[FrameworkDisclosureSummary]
    total_requirements: int
    total_published: int
    total_approved: int
    total_draft: int
    total_not_started: int
    overall_completion_pct: float
    packages_published: int


# ── Supplier Contribution ─────────────────────────────────────────────────────


class SupplierDisclosureContribution(BaseModel):
    supplier_id: str
    supplier_name: str
    disclosures_impacted: int
    evidence_contributed: int
    open_compliance_gaps: int
    readiness_impact: str


# ── Assessment Disclosure Mapping ─────────────────────────────────────────────


class AssessmentDisclosureMapping(BaseModel):
    assessment_id: str
    assessment_title: str
    disclosure_requirements_impacted: list[DisclosureRequirementResponse]
    coverage_contribution: float
    unresolved_blockers: int


# ── Reporting Packages ────────────────────────────────────────────────────────


class GeneratePackageRequest(BaseModel):
    framework_code: str
    package_type: str = Field(
        description="One of: csrd_package, esrs_package, issb_package, gri_package, tcfd_package, sustainability_statement"
    )


class ReportingPackageSummary(BaseModel):
    id: str
    organization_id: str
    framework_id: str
    framework_code: str
    framework_version: str
    package_type: str
    publication_date: str
    published_by: str
    report_hash: str
    status: str


class ReportingPackageDetail(BaseModel):
    id: str
    organization_id: str
    framework_id: str
    framework_code: str
    framework_version: str
    package_type: str
    publication_date: str
    published_by: str
    report_hash: str
    report_data: dict
    status: str
