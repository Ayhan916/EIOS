"""M46.3 — API schemas for milestones, schedules, certificates, risk drafts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ── G-040 Remediation Milestones ─────────────────────────────────────────────

class RemediationMilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    due_date: datetime | None = None
    sort_order: int = 0


class RemediationMilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    due_date: datetime | None = None
    milestone_status: str | None = None
    sort_order: int | None = None


class RemediationMilestoneResponse(BaseModel):
    id: str
    plan_id: str
    title: str
    description: str | None
    due_date: datetime | None
    completed_at: datetime | None
    completed_by: str | None
    milestone_status: str
    sort_order: int
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── G-041 Assessment Schedules ───────────────────────────────────────────────

class AssessmentScheduleCreate(BaseModel):
    supplier_id: str
    frequency_days: int = Field(ge=7, le=3650, description="Reassessment interval in days")
    template_assessment_id: str | None = None
    next_due_at: datetime | None = None


class AssessmentScheduleResponse(BaseModel):
    id: str
    organization_id: str
    supplier_id: str
    frequency_days: int
    last_triggered_at: datetime | None
    next_due_at: datetime
    template_assessment_id: str | None
    is_active: bool
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── G-046 Supplier Certificates ──────────────────────────────────────────────

class SupplierCertificateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    cert_type: str = Field(min_length=1, max_length=100)
    expires_at: datetime
    issued_at: datetime | None = None
    alert_days_before: int = Field(default=30, ge=1, le=365)
    issuer: str | None = Field(default=None, max_length=500)
    certificate_number: str | None = Field(default=None, max_length=200)
    notes: str | None = None


class SupplierCertificateResponse(BaseModel):
    id: str
    supplier_id: str
    organization_id: str
    name: str
    cert_type: str
    issued_at: datetime | None
    expires_at: datetime
    alert_days_before: int
    last_alert_sent_at: datetime | None
    issuer: str | None
    certificate_number: str | None
    notes: str | None
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── G-056 Risk Drafts ────────────────────────────────────────────────────────

class RiskDraftResponse(BaseModel):
    id: str
    organization_id: str
    supplier_id: str | None
    signal_id: str | None
    draft_title: str
    draft_description: str
    draft_severity: str
    draft_category: str | None
    draft_likelihood: str | None
    llm_model: str
    review_status: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    promoted_risk_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AcceptRiskDraftRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)
    override_severity: str | None = None
    override_title: str | None = Field(default=None, max_length=500)


class DraftRiskFromSignalRequest(BaseModel):
    signal_id: str
    supplier_id: str | None = None
