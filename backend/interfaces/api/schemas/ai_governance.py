"""M41 — AI Governance Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ── AI Model ──────────────────────────────────────────────────────────────────


class AIModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., min_length=1, max_length=100)
    model_type: str = Field(
        ..., pattern="^(LLM|CLASSIFICATION|RISK_SCORING|EMBEDDING|RANKING|FORECASTING|OTHER)$"
    )
    model_version: str | None = None
    purpose: str | None = None
    owner_user_id: str | None = None
    metadata_: dict[str, Any] = Field(default_factory=dict, alias="metadata")

    class Config:
        populate_by_name = True


class AIModelStatusUpdate(BaseModel):
    ai_status: str = Field(..., pattern="^(DRAFT|ACTIVE|RETIRED|SUSPENDED)$")


class AIModelResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    provider: str
    model_type: str
    model_version: str | None
    purpose: str | None
    owner_user_id: str | None
    ai_status: str
    metadata_: dict[str, Any] = Field(default_factory=dict, alias="metadata")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


# ── Approval Workflow ─────────────────────────────────────────────────────────


class WorkflowStageAdvance(BaseModel):
    stage: str
    approved: bool = True
    notes: str | None = None


class WorkflowStageResponse(BaseModel):
    id: str
    model_id: str
    stage: str
    stage_status: str
    stage_order: int
    approver_user_id: str | None
    notes: str | None
    completed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Use Case ──────────────────────────────────────────────────────────────────


class AIUseCaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    business_owner: str | None = None
    technical_owner: str | None = None
    risk_level: str = Field("MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")


class AIUseCaseResponse(BaseModel):
    id: str
    model_id: str
    organization_id: str
    title: str
    description: str | None
    business_owner: str | None
    technical_owner: str | None
    risk_level: str
    approval_status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Risk Assessment ───────────────────────────────────────────────────────────


class RiskAssessmentCreate(BaseModel):
    use_case_id: str | None = None
    methodology: str | None = None
    bias_risk: str | None = Field(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    explainability_risk: str | None = Field(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    privacy_risk: str | None = Field(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    regulatory_risk: str | None = Field(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    operational_risk: str | None = Field(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    overall_score: float = Field(0.0, ge=0.0, le=100.0)
    rationale: str | None = None


class RiskAssessmentResponse(BaseModel):
    id: str
    model_id: str
    use_case_id: str | None
    methodology: str | None
    bias_risk: str | None
    explainability_risk: str | None
    privacy_risk: str | None
    regulatory_risk: str | None
    operational_risk: str | None
    overall_score: float
    rationale: str | None
    assessor_user_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Controls ──────────────────────────────────────────────────────────────────


class AIControlCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    control_type: str = Field(..., pattern="^(PREVENTIVE|DETECTIVE|CORRECTIVE)$")
    description: str | None = None
    examples: list[str] = Field(default_factory=list)
    model_id: str | None = None


class AIControlResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    control_type: str
    description: str | None
    examples: list
    model_id: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ControlTestCreate(BaseModel):
    test_result: str = Field(..., pattern="^(PASS|FAIL|PARTIAL)$")
    model_id: str | None = None
    notes: str | None = None


class ControlTestResponse(BaseModel):
    id: str
    control_id: str
    model_id: str | None
    test_result: str
    tested_by: str | None
    notes: str | None
    tested_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ── Prompt Templates ──────────────────────────────────────────────────────────


class PromptTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    prompt_text: str = Field(..., min_length=1)
    model_id: str | None = None
    owner_user_id: str | None = None


class PromptTemplateRevise(BaseModel):
    new_text: str = Field(..., min_length=1)
    change_rationale: str = Field(..., min_length=1)


class PromptTemplateResponse(BaseModel):
    id: str
    organization_id: str
    model_id: str | None
    name: str
    prompt_version: int
    is_approved: bool
    approved_by: str | None
    approved_at: datetime | None
    is_active: bool
    owner_user_id: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromptChangeResponse(BaseModel):
    id: str
    prompt_id: str
    previous_version: int
    new_version: int
    previous_prompt_text: str | None
    new_prompt_text: str | None
    change_rationale: str | None
    approver_user_id: str | None
    approved_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Decision Logging ──────────────────────────────────────────────────────────


class DecisionLogCreate(BaseModel):
    # Caller provides pre-computed SHA-256 hashes (64-char hex). Raw data must
    # never be sent to this endpoint.
    inputs_hash: str = Field(..., min_length=64, max_length=64)
    output_hash: str = Field(..., min_length=64, max_length=64)
    prompt_id: str | None = None
    use_case_id: str | None = None
    user_id: str | None = None
    decision_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionLogResponse(BaseModel):
    id: str
    model_id: str
    prompt_id: str | None
    use_case_id: str | None
    organization_id: str
    user_id: str | None
    inputs_hash: str
    output_hash: str
    decision_type: str | None
    decision_metadata: dict[str, Any]
    logged_at: datetime

    class Config:
        from_attributes = True


class ExplanationCreate(BaseModel):
    factors: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    rationale: str | None = None
    source_references: list = Field(default_factory=list)


class ExplanationResponse(BaseModel):
    id: str
    decision_log_id: str
    factors: list
    confidence: float | None
    rationale: str | None
    source_references: list
    created_at: datetime

    class Config:
        from_attributes = True


class HumanReviewCreate(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED|OVERRIDE|FLAGGED)$")
    decision_log_id: str | None = None
    incident_id: str | None = None
    override_reason: str | None = None
    rationale: str | None = None


class HumanReviewResponse(BaseModel):
    id: str
    decision_log_id: str | None
    incident_id: str | None
    model_id: str
    reviewer_user_id: str
    decision: str
    override_reason: str | None
    rationale: str | None
    reviewed_at: datetime

    class Config:
        from_attributes = True


# ── Monitoring ────────────────────────────────────────────────────────────────


class MonitoringSnapshotCreate(BaseModel):
    period_start: datetime
    period_end: datetime
    avg_latency_ms: float | None = None
    failure_count: int = 0
    usage_count: int = 0
    avg_confidence: float | None = Field(None, ge=0.0, le=1.0)
    drift_score: float | None = Field(None, ge=0.0, le=1.0)
    notes: str | None = None


class MonitoringSnapshotResponse(BaseModel):
    id: str
    model_id: str
    organization_id: str
    period_start: datetime
    period_end: datetime
    avg_latency_ms: float | None
    failure_count: int
    usage_count: int
    avg_confidence: float | None
    drift_score: float | None
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DriftAlertResponse(BaseModel):
    id: str
    model_id: str
    alert_type: str
    severity: str
    description: str
    detected_at: datetime
    is_resolved: bool
    resolved_at: datetime | None

    class Config:
        from_attributes = True


# ── Incidents ─────────────────────────────────────────────────────────────────


class AIIncidentCreate(BaseModel):
    incident_type: str = Field(
        ...,
        pattern="^(HALLUCINATION|POLICY_VIOLATION|PRIVACY_CONCERN|BIAS_CONCERN|UNSAFE_OUTPUT|OTHER)$",
    )
    severity: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    description: str = Field(..., min_length=1)
    # model_id required when using the flat /incidents endpoint
    model_id: str | None = None
    reported_by: str | None = None


class AIIncidentResolve(BaseModel):
    esg_action_id: str | None = None
    strategic_risk_id: str | None = None


class AIIncidentResponse(BaseModel):
    id: str
    model_id: str
    organization_id: str
    incident_type: str
    severity: str
    description: str
    reported_by: str | None
    is_resolved: bool
    resolved_at: datetime | None
    esg_action_id: str | None
    strategic_risk_id: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Policies ──────────────────────────────────────────────────────────────────


class AIPolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    policy_type: str = Field(
        ...,
        pattern="^(APPROVED_PROVIDERS|PROHIBITED_USE_CASES|RETENTION|REVIEW_REQUIREMENTS|OTHER)$",
    )
    description: str | None = None
    policy_body: dict[str, Any] = Field(default_factory=dict)
    enterprise_id: str | None = None


class AIPolicyResponse(BaseModel):
    id: str
    organization_id: str | None
    enterprise_id: str | None
    name: str
    policy_type: str
    description: str | None
    policy_body: dict[str, Any]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Regulation Mappings ───────────────────────────────────────────────────────


class RegulationMappingCreate(BaseModel):
    framework: str = Field(..., pattern="^(EU_AI_ACT|NIST_AI_RMF|ISO_42001|OTHER)$")
    use_case_id: str | None = None
    risk_assessment_id: str | None = None
    control_id: str | None = None
    article_reference: str | None = None
    requirement_text: str | None = None
    compliance_status: str = Field(
        "NOT_ASSESSED",
        pattern="^(COMPLIANT|PARTIAL|NON_COMPLIANT|NOT_ASSESSED)$",
    )
    notes: str | None = None


class RegulationMappingStatusUpdate(BaseModel):
    compliance_status: str = Field(..., pattern="^(COMPLIANT|PARTIAL|NON_COMPLIANT|NOT_ASSESSED)$")


class RegulationMappingResponse(BaseModel):
    id: str
    organization_id: str | None
    use_case_id: str | None
    risk_assessment_id: str | None
    control_id: str | None
    framework: str
    article_reference: str | None
    requirement_text: str | None
    compliance_status: str
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class RegulationMappingHistoryResponse(BaseModel):
    id: str
    mapping_id: str
    previous_status: str
    new_status: str
    changed_by: str
    changed_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ── Assurance Reports ─────────────────────────────────────────────────────────


class AssuranceReportCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    period_start: datetime
    period_end: datetime


class AssuranceReportResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    report_period_start: datetime
    report_period_end: datetime
    model_count: int
    use_case_count: int
    control_count: int
    incident_count: int
    approval_count: int
    overall_status: str
    generated_by: str | None
    report_data: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────────────────────────────────────


class AIGovernanceDashboard(BaseModel):
    organization_id: str
    total_models: int
    active_models: int
    draft_models: int
    total_use_cases: int
    pending_approvals: int
    open_incidents: int
    unresolved_drift_alerts: int
    active_policies: int
    last_report_status: str | None
