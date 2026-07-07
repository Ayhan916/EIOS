"""M41 — AI Governance, Model Risk Management & Assurance Layer ORM Models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel

# ── Enums (string literals) ───────────────────────────────────────────────────

AI_MODEL_STATUSES = ("DRAFT", "ACTIVE", "RETIRED", "SUSPENDED")
AI_MODEL_TYPES = (
    "LLM",
    "CLASSIFICATION",
    "RISK_SCORING",
    "EMBEDDING",
    "RANKING",
    "FORECASTING",
    "OTHER",
)
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
APPROVAL_STATUSES = ("PENDING", "APPROVED", "REJECTED")
CONTROL_TYPES = ("PREVENTIVE", "DETECTIVE", "CORRECTIVE")
TEST_RESULTS = ("PASS", "FAIL", "PARTIAL")
WORKFLOW_STAGES = ("review", "risk_assessment", "control_validation", "executive_approval")
WORKFLOW_STAGE_STATUSES = ("PENDING", "IN_PROGRESS", "APPROVED", "REJECTED", "SKIPPED")
# Terminal states that cannot be transitioned out of
TERMINAL_WORKFLOW_STATUSES = frozenset({"APPROVED", "REJECTED", "SKIPPED"})
DRIFT_ALERT_TYPES = (
    "CONFIDENCE_DEGRADATION",
    "DISTRIBUTION_SHIFT",
    "ABNORMAL_USAGE",
)
INCIDENT_TYPES = (
    "HALLUCINATION",
    "POLICY_VIOLATION",
    "PRIVACY_CONCERN",
    "BIAS_CONCERN",
    "UNSAFE_OUTPUT",
    "OTHER",
)
AI_POLICY_TYPES = (
    "APPROVED_PROVIDERS",
    "PROHIBITED_USE_CASES",
    "RETENTION",
    "REVIEW_REQUIREMENTS",
    "OTHER",
)
ASSURANCE_STATUSES = ("COMPLIANT", "PARTIALLY_COMPLIANT", "NON_COMPLIANT")
REGULATION_FRAMEWORKS = ("EU_AI_ACT", "NIST_AI_RMF", "ISO_42001", "OTHER")
COMPLIANCE_STATUSES = ("COMPLIANT", "PARTIAL", "NON_COMPLIANT", "NOT_ASSESSED")
HUMAN_REVIEW_DECISIONS = ("APPROVED", "REJECTED", "OVERRIDE", "FLAGGED")
# Severities that require human review before incident resolution
HIGH_SEVERITY_LEVELS = frozenset({"HIGH", "CRITICAL"})


class AIModelModel(BaseModel):
    """Registered AI model in the AI Asset Inventory."""

    __tablename__ = "ai_models"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ai_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)


class AIUseCaseModel(BaseModel):
    """A specific use case for an AI model within an organization."""

    __tablename__ = "ai_use_cases"

    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_models.id"), nullable=False)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    technical_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    approval_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")


class AIRiskAssessmentModel(BaseModel):
    """Structured risk assessment for an AI model or use case."""

    __tablename__ = "ai_risk_assessments"

    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_models.id"), nullable=False)
    use_case_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_use_cases.id"), nullable=True
    )
    methodology: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bias_risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    explainability_risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    privacy_risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    regulatory_risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    operational_risk: Mapped[str | None] = mapped_column(String(20), nullable=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AIControlModel(BaseModel):
    """A governance control applied to one or more AI models."""

    __tablename__ = "ai_controls"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_type: Mapped[str] = mapped_column(String(20), nullable=False)
    examples: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    model_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_models.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AIControlTestModel(BaseModel):
    """Result of testing an AI governance control."""

    __tablename__ = "ai_control_tests"

    control_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ai_controls.id"), nullable=False
    )
    model_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_models.id"), nullable=True
    )
    test_result: Mapped[str] = mapped_column(String(20), nullable=False)
    tested_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelApprovalWorkflowModel(BaseModel):
    """One stage in a model approval workflow."""

    __tablename__ = "model_approval_workflows"
    __table_args__ = (UniqueConstraint("model_id", "stage", name="uq_workflow_model_stage"),)

    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_models.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    stage_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    approver_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PromptTemplateModel(BaseModel):
    """Versioned prompt template in the Prompt Registry."""

    __tablename__ = "prompt_templates"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    model_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_models.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PromptChangeModel(BaseModel):
    """Change record for a prompt template version bump — preserves full text history."""

    __tablename__ = "prompt_changes"

    prompt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("prompt_templates.id"), nullable=False
    )
    previous_version: Mapped[int] = mapped_column(Integer, nullable=False)
    new_version: Mapped[int] = mapped_column(Integer, nullable=False)
    # Full text snapshots — enables complete historical reconstruction
    previous_prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    approver_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AIDecisionLogModel(BaseModel):
    """Audit log of an AI-assisted decision. No raw sensitive data stored."""

    __tablename__ = "ai_decision_logs"

    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_models.id"), nullable=False)
    prompt_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("prompt_templates.id"), nullable=True
    )
    use_case_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_use_cases.id"), nullable=True
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # SHA-256 of inputs — raw data never stored, stored as-is from caller
    inputs_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # SHA-256 of output — raw data never stored, stored as-is from caller
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    decision_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AIExplanationModel(BaseModel):
    """Explainability record for an AI decision."""

    __tablename__ = "ai_explanations"

    decision_log_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ai_decision_logs.id"), nullable=False
    )
    factors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_references: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class HumanReviewModel(BaseModel):
    """Human oversight review of an AI-assisted decision or model output."""

    __tablename__ = "human_reviews"

    decision_log_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_decision_logs.id"), nullable=True
    )
    # Nullable FK to ai_incidents — required for HIGH/CRITICAL severity gate
    incident_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_incidents.id"), nullable=True
    )
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_models.id"), nullable=False)
    reviewer_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModelMonitoringRecordModel(BaseModel):
    """Periodic monitoring snapshot for an AI model."""

    __tablename__ = "model_monitoring_records"

    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_models.id"), nullable=False)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    drift_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ModelDriftAlertModel(BaseModel):
    """Alert fired when model drift is detected."""

    __tablename__ = "model_drift_alerts"

    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_models.id"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AIIncidentModel(BaseModel):
    """AI incident (hallucination, policy violation, bias, etc.)."""

    __tablename__ = "ai_incidents"

    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_models.id"), nullable=False)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    incident_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reported_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    esg_action_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    strategic_risk_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AIPolicyModel(BaseModel):
    """AI governance policy (approved providers, prohibited use cases, etc.)."""

    __tablename__ = "ai_policies"

    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True
    )
    enterprise_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("enterprises.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_body: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AIAssuranceReportModel(BaseModel):
    """Consolidated AI assurance report for a period."""

    __tablename__ = "ai_assurance_reports"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    report_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    report_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    use_case_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    control_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incident_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approval_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overall_status: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_ASSESSED")
    generated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    report_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class AIRegulationMappingModel(BaseModel):
    """Maps AI governance artefacts to regulatory frameworks."""

    __tablename__ = "ai_regulation_mappings"

    # Organization scope — added in M41.1 hardening
    organization_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True
    )
    use_case_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_use_cases.id"), nullable=True
    )
    risk_assessment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_risk_assessments.id"), nullable=True
    )
    control_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_controls.id"), nullable=True
    )
    framework: Mapped[str] = mapped_column(String(50), nullable=False)
    article_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requirement_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="NOT_ASSESSED"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AIRegulationMappingHistoryModel(BaseModel):
    """Audit history of compliance_status changes on regulation mappings."""

    __tablename__ = "ai_regulation_mapping_history"

    mapping_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ai_regulation_mappings.id"), nullable=False
    )
    previous_status: Mapped[str] = mapped_column(String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(36), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
