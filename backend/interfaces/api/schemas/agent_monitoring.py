"""M36 Agent Monitoring API Schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MonitoringAgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_type: str
    name: str
    description: str
    status: str
    enabled: bool
    run_interval_hours: int
    last_run_at: datetime | None
    next_run_at: datetime | None
    run_count: int
    success_count: int
    failure_count: int
    created_at: datetime
    updated_at: datetime


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    organization_id: str | None
    started_at: datetime
    completed_at: datetime | None
    run_status: str
    findings_generated: int
    alerts_generated: int
    actions_recommended: int
    error_message: str | None
    execution_time_ms: int | None
    created_at: datetime


class AgentFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    supplier_id: str | None
    agent_id: str
    agent_run_id: str | None
    category: str
    severity: str
    title: str
    description: str
    evidence: str
    confidence_score: float
    detected_at: datetime
    finding_status: str
    acknowledged_by: str | None
    acknowledged_at: datetime | None
    rule_triggered: str
    source_data_json: dict
    created_at: datetime
    updated_at: datetime


class AgentAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    supplier_id: str | None
    agent_id: str
    agent_finding_id: str | None
    severity: str
    title: str
    message: str
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    created_at: datetime


class EscalationRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    description: str
    agent_type: str
    condition_json: dict
    escalation_severity: str
    enabled: bool
    created_by: str
    created_at: datetime


class EscalationRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    agent_type: str = "*"
    condition_json: dict
    escalation_severity: str = "WARNING"


class RecommendationDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    supplier_id: str | None
    agent_id: str
    agent_finding_id: str | None
    recommendation_text: str
    rationale: str
    confidence_score: float
    draft_status: str
    approved_by: str | None
    approved_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime


class ApproveDraftRequest(BaseModel):
    pass  # no body required — approver identity from JWT


class RejectDraftRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class AcknowledgeFindingRequest(BaseModel):
    pass  # approver identity from JWT


class AcknowledgeAlertRequest(BaseModel):
    pass  # approver identity from JWT


class TriggerAgentRunRequest(BaseModel):
    agent_type: str
    # organization_id intentionally removed — always scoped to the calling user's org
    # to prevent cross-tenant agent execution (M36.1 F1)


class AgentHealthInfo(BaseModel):
    """Per-agent operational health snapshot for the dashboard."""

    agent_id: str
    agent_type: str
    name: str
    status: str
    enabled: bool
    last_successful_run: datetime | None
    consecutive_failures: int
    avg_runtime_ms: float | None
    success_rate: float | None
    backlog_count: int


class AgentDashboard(BaseModel):
    active_agents: int
    paused_agents: int
    failed_agents: int
    total_open_findings: int
    total_unacknowledged_alerts: int
    total_critical_alerts: int
    total_pending_drafts: int
    recent_findings: list[AgentFindingResponse]
    recent_alerts: list[AgentAlertResponse]
    per_agent_health: list[AgentHealthInfo] = Field(default_factory=list)
