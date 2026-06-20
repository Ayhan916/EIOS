"""M39 ESG Operating System API Schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Objectives ────────────────────────────────────────────────────────────────

class CreateObjectiveRequest(BaseModel):
    title: str
    description: str = ""
    category: str
    owner_user_id: str | None = None
    target_value: float | None = None
    unit: str | None = None
    due_date: datetime | None = None


class UpdateObjectiveRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    objective_status: str | None = None
    current_value: float | None = None
    due_date: datetime | None = None


class ESGObjectiveResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str
    category: str
    owner_user_id: str | None
    target_value: float | None
    current_value: float | None
    unit: str | None
    due_date: datetime | None
    objective_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Key Results ───────────────────────────────────────────────────────────────

class CreateKeyResultRequest(BaseModel):
    title: str
    metric_name: str
    target_value: float
    current_value: float = 0.0


class UpdateKeyResultRequest(BaseModel):
    current_value: float | None = None
    title: str | None = None


class ESGKeyResultResponse(BaseModel):
    id: str
    organization_id: str
    objective_id: str
    title: str
    metric_name: str
    target_value: float
    current_value: float
    progress_percent: float
    kr_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Initiatives ───────────────────────────────────────────────────────────────

class CreateInitiativeRequest(BaseModel):
    title: str
    description: str = ""
    owner_user_id: str | None = None
    due_date: datetime | None = None
    linked_objectives: list[str] = Field(default_factory=list)
    linked_suppliers: list[str] = Field(default_factory=list)
    linked_findings: list[str] = Field(default_factory=list)
    linked_risks: list[str] = Field(default_factory=list)


class UpdateInitiativeRequest(BaseModel):
    title: str | None = None
    initiative_status: str | None = None
    due_date: datetime | None = None
    linked_objectives: list[str] | None = None
    linked_suppliers: list[str] | None = None


class ESGInitiativeResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str
    owner_user_id: str | None
    initiative_status: str
    due_date: datetime | None
    linked_objectives: list[str]
    linked_suppliers: list[str]
    linked_findings: list[str]
    linked_risks: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Actions ───────────────────────────────────────────────────────────────────

class CreateActionRequest(BaseModel):
    title: str
    description: str = ""
    source_type: str = "MANUAL"
    source_id: str | None = None
    owner_user_id: str | None = None
    due_date: datetime | None = None
    priority: str = "MEDIUM"
    linked_objectives: list[str] = Field(default_factory=list)


class UpdateActionRequest(BaseModel):
    action_status: str | None = None
    priority: str | None = None
    owner_user_id: str | None = None
    due_date: datetime | None = None


class ESGActionResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str
    source_type: str
    source_id: str | None
    owner_user_id: str | None
    due_date: datetime | None
    action_status: str
    priority: str
    linked_objectives: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Playbooks ─────────────────────────────────────────────────────────────────

class CreatePlaybookRequest(BaseModel):
    title: str
    description: str = ""
    playbook_type: str
    steps: list[dict] = Field(default_factory=list)
    escalation_rules: list[dict] = Field(default_factory=list)
    evidence_required: list[str] = Field(default_factory=list)


class ESGPlaybookResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str
    playbook_type: str
    steps: list[dict]
    escalation_rules: list[dict]
    evidence_required: list[str]
    playbook_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Workflow Executions ───────────────────────────────────────────────────────

class StartWorkflowRequest(BaseModel):
    workflow_type: str
    playbook_id: str | None = None
    linked_entity_type: str | None = None
    linked_entity_id: str | None = None


class ApproveWorkflowStepRequest(BaseModel):
    step_note: str = ""


class RejectWorkflowStepRequest(BaseModel):
    reason: str = ""


class WorkflowExecutionResponse(BaseModel):
    id: str
    organization_id: str
    playbook_id: str | None
    workflow_type: str
    current_step: int
    total_steps: int
    execution_status: str
    steps_completed: list[dict]
    pending_approvals: list[dict]
    initiated_by: str | None
    linked_entity_type: str | None
    linked_entity_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Strategic Risks ───────────────────────────────────────────────────────────

class CreateStrategicRiskRequest(BaseModel):
    title: str
    category: str
    description: str = ""
    risk_level: str = "MEDIUM"
    probability: str = "MEDIUM"
    impact: str = "MEDIUM"
    owner_user_id: str | None = None
    linked_suppliers: list[str] = Field(default_factory=list)
    linked_objectives: list[str] = Field(default_factory=list)
    linked_initiatives: list[str] = Field(default_factory=list)
    linked_compliance_programs: list[str] = Field(default_factory=list)


class UpdateStrategicRiskRequest(BaseModel):
    risk_status: str | None = None
    risk_level: str | None = None
    description: str | None = None


class StrategicRiskResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str
    category: str
    risk_level: str
    probability: str
    impact: str
    risk_status: str
    owner_user_id: str | None
    linked_suppliers: list[str]
    linked_objectives: list[str]
    linked_initiatives: list[str]
    linked_compliance_programs: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Health Score ──────────────────────────────────────────────────────────────

class ESGHealthScoreResponse(BaseModel):
    id: str
    organization_id: str
    overall_score: float
    supplier_intelligence_score: float
    surveillance_score: float
    compliance_score: float
    due_diligence_score: float
    remediation_score: float
    governance_score: float
    calculation_inputs: dict[str, Any]
    formula_version: str
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Escalation Rules ──────────────────────────────────────────────────────────

class CreateEscalationRuleRequest(BaseModel):
    rule_name: str
    condition_entity_type: str
    condition_status: str
    escalate_to_role: str
    condition_overdue_days: int | None = None
    condition_priority: str | None = None
    escalate_to_user_id: str | None = None
    notification_message: str = ""


class EscalationRuleResponse(BaseModel):
    id: str
    organization_id: str
    rule_name: str
    condition_entity_type: str
    condition_status: str
    condition_overdue_days: int | None
    condition_priority: str | None
    escalate_to_role: str
    escalate_to_user_id: str | None
    notification_message: str
    rule_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EscalationTriggeredResponse(BaseModel):
    rule_id: str
    rule_name: str
    entity_type: str
    entity_id: str
    escalate_to_role: str
    escalate_to_user_id: str | None
    message: str
    triggered_at: str


# ── Governance Calendar ───────────────────────────────────────────────────────

class CreateCalendarEventRequest(BaseModel):
    title: str
    event_type: str
    scheduled_at: datetime
    recurrence_rule: str | None = None
    reminder_days: int = 7
    linked_entity_type: str | None = None
    linked_entity_id: str | None = None
    notes: str = ""


class UpdateCalendarEventRequest(BaseModel):
    title: str | None = None
    event_status: str | None = None
    scheduled_at: datetime | None = None
    recurrence_rule: str | None = None
    reminder_days: int | None = None
    notes: str | None = None


class CalendarEventResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    event_type: str
    scheduled_at: datetime
    recurrence_rule: str | None
    reminder_days: int
    event_status: str
    linked_entity_type: str | None
    linked_entity_id: str | None
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── ESG Programs ──────────────────────────────────────────────────────────────

class CreateProgramRequest(BaseModel):
    title: str
    description: str = ""
    linked_objectives: list[str] = Field(default_factory=list)
    linked_initiatives: list[str] = Field(default_factory=list)
    linked_suppliers: list[str] = Field(default_factory=list)


class UpdateProgramRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    program_status: str | None = None
    linked_objectives: list[str] | None = None
    linked_initiatives: list[str] | None = None
    linked_suppliers: list[str] | None = None


class ESGProgramResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str
    program_status: str
    linked_objectives: list[str]
    linked_initiatives: list[str]
    linked_suppliers: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── ESG Controls ──────────────────────────────────────────────────────────────

class CreateControlRequest(BaseModel):
    control_name: str
    control_type: str
    owner_user_id: str | None = None
    frequency: str = "ANNUAL"
    evidence_required: bool = False


class UpdateControlRequest(BaseModel):
    control_name: str | None = None
    control_type: str | None = None
    owner_user_id: str | None = None
    frequency: str | None = None
    evidence_required: bool | None = None
    effectiveness_status: str | None = None


class ESGControlResponse(BaseModel):
    id: str
    organization_id: str
    control_name: str
    control_type: str
    owner_user_id: str | None
    frequency: str
    evidence_required: bool
    effectiveness_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Control Tests ─────────────────────────────────────────────────────────────

class CreateControlTestRequest(BaseModel):
    control_id: str
    test_result: str
    tested_at: datetime
    performed_by: str | None = None
    findings: str = ""


class UpdateControlTestRequest(BaseModel):
    test_result: str | None = None
    findings: str | None = None


class ControlTestResponse(BaseModel):
    id: str
    organization_id: str
    control_id: str
    performed_by: str | None
    test_result: str
    findings: str
    tested_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Compliance Operations ─────────────────────────────────────────────────────

class CreateComplianceOperationRequest(BaseModel):
    framework_name: str
    owner_user_id: str | None = None
    coverage_percent: float = 0.0
    gap_count: int = 0


class UpdateComplianceOperationRequest(BaseModel):
    operation_status: str | None = None
    coverage_percent: float | None = None
    gap_count: int | None = None
    owner_user_id: str | None = None


class ComplianceOperationResponse(BaseModel):
    id: str
    organization_id: str
    framework_name: str
    coverage_percent: float
    gap_count: int
    owner_user_id: str | None
    operation_status: str
    actions: list[Any]
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Accountability ────────────────────────────────────────────────────────────

class AssignAccountabilityRequest(BaseModel):
    entity_type: str
    entity_id: str
    role: str
    assigned_to_user_id: str
    assigned_by_user_id: str | None = None


class AccountabilityAssignmentResponse(BaseModel):
    id: str
    organization_id: str
    entity_type: str
    entity_id: str
    role: str
    assigned_to_user_id: str
    assigned_by_user_id: str | None
    assigned_at: datetime
    assignment_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Timeline ──────────────────────────────────────────────────────────────────

class TimelineEntry(BaseModel):
    event_type: str
    entity_type: str
    entity_id: str
    title: str
    timestamp: datetime
    status: str | None = None


# ── Dashboard ─────────────────────────────────────────────────────────────────

class OperatingSystemDashboard(BaseModel):
    objectives_total: int
    objectives_at_risk: int
    initiatives_total: int
    initiatives_active: int
    actions_open: int
    actions_overdue: int
    escalations_triggered: int
    strategic_risks_critical: int
    latest_health_score: float | None
    top_overdue_actions: list[ESGActionResponse]
    objectives_by_status: dict[str, int]
    recent_strategic_risks: list[StrategicRiskResponse]
    # M39.1 additions
    compliance_operations: int
    governance_calendar_events: int
    programs_total: int
    controls_total: int
