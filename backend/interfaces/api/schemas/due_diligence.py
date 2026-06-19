"""M32.1 Due Diligence Reporting — API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Dashboard ─────────────────────────────────────────────────────────────────


class DueDiligenceKPIResponse(BaseModel):
    organization_id: str
    total_suppliers: int
    critical_suppliers: int
    high_risk_suppliers: int
    unresolved_hr_risks: int
    unresolved_env_risks: int
    overdue_actions: int
    open_actions: int
    remediation_completion_pct: float
    avg_esg_score: float
    avg_risk_score: float
    reports_generated: int


# ── Report ────────────────────────────────────────────────────────────────────


class GenerateDueDiligenceReportRequest(BaseModel):
    report_type: str = Field(
        description="One of: lksgg_annual, csddd, human_rights, environmental, preventive_measures, remediation"
    )
    reporting_year: int | None = Field(default=None, description="Reporting year (for LkSG annual report)")


class DueDiligenceReportSummary(BaseModel):
    id: str
    organization_id: str
    report_type: str
    framework: str
    framework_version: str
    generated_at: str
    generated_by: str
    report_hash: str
    status: str


class DueDiligenceReportDetail(BaseModel):
    id: str
    organization_id: str
    report_type: str
    framework: str
    framework_version: str
    generated_at: str
    generated_by: str
    report_hash: str
    report_data: dict
    status: str


# ── Supplier Due Diligence ─────────────────────────────────────────────────────


class SupplierDueDiligenceSummary(BaseModel):
    supplier_id: str
    supplier_name: str
    country: str
    tier: str
    risk_band: str
    esg_score: float
    risk_score: float
    trend: str
    critical_findings: int
    high_findings: int
    open_actions: int
    overdue_actions: int
    hr_findings: int
    env_findings: int


class SupplierDueDiligenceDetail(BaseModel):
    supplier_id: str
    supplier_name: str
    country: str
    industry: str
    tier: str
    risk_band: str
    esg_score: float
    environmental_score: float
    social_score: float
    governance_score: float
    risk_score: float
    trend: str
    critical_findings: int
    high_findings: int
    open_actions: int
    overdue_actions: int
    hr_findings: int
    env_findings: int
    unresolved_gaps: int
    lksgg_coverage: str
    csddd_coverage: str
    explainability: list[dict]


# ── Human Rights ──────────────────────────────────────────────────────────────


class HumanRightsTopicSummary(BaseModel):
    topic: str
    display_name: str
    finding_count: int
    critical_findings: int
    high_findings: int
    risk_count: int
    suppliers_impacted: int


class HumanRightsReportResponse(BaseModel):
    organization_id: str
    total_hr_findings: int
    total_hr_risks: int
    suppliers_impacted: int
    open_remediation_actions: int
    overdue_actions: int
    resolved_actions: int
    by_topic: list[HumanRightsTopicSummary]


# ── Environmental ─────────────────────────────────────────────────────────────


class EnvironmentalTopicSummary(BaseModel):
    topic: str
    display_name: str
    finding_count: int
    critical_findings: int
    risk_count: int
    unresolved_risks: int
    suppliers_impacted: int


class EnvironmentalReportResponse(BaseModel):
    organization_id: str
    total_env_findings: int
    total_env_risks: int
    unresolved_risks: int
    suppliers_impacted: int
    mitigation_controls: int
    effective_controls: int
    by_topic: list[EnvironmentalTopicSummary]


# ── Remediation ───────────────────────────────────────────────────────────────


class RemediationReportResponse(BaseModel):
    organization_id: str
    total: int
    open: int
    in_progress: int
    completed: int
    overdue: int
    closure_rate: float
    avg_resolution_days: float | None
    by_priority: dict
    top_overdue: list[dict]


# ── Preventive Measures ────────────────────────────────────────────────────────


class PreventiveMeasureItem(BaseModel):
    id: str
    title: str
    control_type: str
    effectiveness_score: float | None
    effectiveness_status: str


class PreventiveMeasuresCategoryResponse(BaseModel):
    category: str
    display_name: str
    total: int
    by_effectiveness: dict
    items: list[PreventiveMeasureItem]


class PreventiveMeasuresReportResponse(BaseModel):
    organization_id: str
    total_controls: int
    preventive: int
    detective: int
    corrective: int
    by_effectiveness: dict
    by_category: list[PreventiveMeasuresCategoryResponse]
