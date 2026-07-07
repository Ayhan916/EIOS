"""M39 ESG Operating System — ORM Models.

Tables:
  esg_objectives                — organizational ESG targets (OKR-style)
  esg_key_results               — measurable milestones within an objective
  esg_initiatives               — structured programs of work driving objectives
  governance_calendar_events    — board/compliance/review scheduled events
  esg_programs                  — portfolio-level grouping of objectives + initiatives
  esg_controls                  — preventive / detective / corrective controls
  control_tests                 — point-in-time effectiveness tests for a control
  compliance_operations         — framework-specific continuous readiness ops
  esg_actions                   — unified action inbox across all EIOS modules
  accountability_assignments    — owner / reviewer / approver / sponsor records
  esg_playbooks                 — step-based response playbooks
  workflow_executions           — live execution of a playbook or governance workflow
  governance_escalation_rules   — rule-based governance escalation matrix
  esg_health_scores             — deterministic org-level ESG health score snapshots
  strategic_risks               — organization-wide strategic ESG risks
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel

# ── 1. ESG Objectives ─────────────────────────────────────────────────────────


class ESGObjectiveModel(BaseModel):
    """Organization-level ESG objective (OKR frame).

    objective_status lifecycle:
      NOT_STARTED → ON_TRACK / AT_RISK / OFF_TRACK → COMPLETED
    """

    __tablename__ = "esg_objectives"
    __table_args__ = (
        Index("ix_esg_obj_org", "organization_id"),
        Index("ix_esg_obj_category", "category"),
        Index("ix_esg_obj_status", "objective_status"),
        Index("ix_esg_obj_owner", "owner_user_id"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # ENVIRONMENTAL | SOCIAL | GOVERNANCE | COMPLIANCE | DUE_DILIGENCE | SUPPLIER_RISK
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # NOT_STARTED | ON_TRACK | AT_RISK | OFF_TRACK | COMPLETED
    objective_status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_STARTED")


# ── 2. ESG Key Results ────────────────────────────────────────────────────────


class ESGKeyResultModel(BaseModel):
    """Measurable sub-target within an ESGObjective.

    progress_percent is stored computed (0–100) so dashboards never recalculate.
    """

    __tablename__ = "esg_key_results"
    __table_args__ = (
        Index("ix_esg_kr_org", "organization_id"),
        Index("ix_esg_kr_objective", "objective_id"),
        Index("ix_esg_kr_status", "kr_status"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    objective_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # NOT_STARTED | ON_TRACK | AT_RISK | OFF_TRACK | COMPLETED
    kr_status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_STARTED")


# ── 3. ESG Initiatives ────────────────────────────────────────────────────────


class ESGInitiativeModel(BaseModel):
    """Structured program of work driving one or more ESGObjectives.

    Linked items (suppliers, findings, risks, objectives) are stored as JSONB
    ID lists to avoid hard FK dependencies across module boundaries.
    """

    __tablename__ = "esg_initiatives"
    __table_args__ = (
        Index("ix_esg_init_org", "organization_id"),
        Index("ix_esg_init_status", "initiative_status"),
        Index("ix_esg_init_owner", "owner_user_id"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # PLANNED | ACTIVE | BLOCKED | COMPLETED | CANCELLED
    initiative_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PLANNED")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linked_objectives: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    linked_suppliers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    linked_findings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    linked_risks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


# ── 4. Governance Calendar Events ─────────────────────────────────────────────


class GovernanceCalendarEventModel(BaseModel):
    """Scheduled governance event (board review, supplier review, reporting cycle, etc.)."""

    __tablename__ = "governance_calendar_events"
    __table_args__ = (
        Index("ix_gcal_org", "organization_id"),
        Index("ix_gcal_type", "event_type"),
        Index("ix_gcal_scheduled_at", "scheduled_at"),
        Index("ix_gcal_status", "event_status"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # BOARD_REVIEW | SUPPLIER_REVIEW | COMPLIANCE_REVIEW | DUE_DILIGENCE_REVIEW | ANNUAL_REPORTING
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # iCal RRULE string, e.g. "FREQ=QUARTERLY" — null means one-off
    recurrence_rule: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reminder_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    # SCHEDULED | COMPLETED | CANCELLED
    event_status: Mapped[str] = mapped_column(String(20), nullable=False, default="SCHEDULED")
    linked_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    linked_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


# ── 5. ESG Programs ───────────────────────────────────────────────────────────


class ESGProgramModel(BaseModel):
    """Portfolio-level grouping of objectives, initiatives and supplier reviews."""

    __tablename__ = "esg_programs"
    __table_args__ = (
        Index("ix_esg_prog_org", "organization_id"),
        Index("ix_esg_prog_status", "program_status"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # ACTIVE | COMPLETED | ARCHIVED
    program_status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    linked_objectives: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    linked_initiatives: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    linked_suppliers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


# ── 6. ESG Controls ───────────────────────────────────────────────────────────


class ESGControlModel(BaseModel):
    """ESG control framework entry.

    effectiveness_status is updated after each ControlTest run.
    """

    __tablename__ = "esg_controls"
    __table_args__ = (
        Index("ix_esg_ctrl_org", "organization_id"),
        Index("ix_esg_ctrl_type", "control_type"),
        Index("ix_esg_ctrl_effectiveness", "effectiveness_status"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    control_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # PREVENTIVE | DETECTIVE | CORRECTIVE
    control_type: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    frequency: Mapped[str] = mapped_column(String(30), nullable=False, default="ANNUAL")
    evidence_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # EFFECTIVE | PARTIALLY_EFFECTIVE | INEFFECTIVE | NOT_TESTED
    effectiveness_status: Mapped[str] = mapped_column(
        String(25), nullable=False, default="NOT_TESTED"
    )


# ── 7. Control Tests ──────────────────────────────────────────────────────────


class ControlTestModel(BaseModel):
    """Point-in-time effectiveness test result for an ESGControl."""

    __tablename__ = "control_tests"
    __table_args__ = (
        Index("ix_ctest_org", "organization_id"),
        Index("ix_ctest_control", "control_id"),
        Index("ix_ctest_result", "test_result"),
        Index("ix_ctest_tested_at", "tested_at"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    control_id: Mapped[str] = mapped_column(String(36), nullable=False)
    performed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # PASS | FAIL | PARTIAL
    test_result: Mapped[str] = mapped_column(String(10), nullable=False)
    findings: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ── 8. Compliance Operations ──────────────────────────────────────────────────


class ComplianceOperationModel(BaseModel):
    """Continuous readiness operation for a specific regulatory framework.

    Integrates with M31 Regulatory Intelligence gap data.
    """

    __tablename__ = "compliance_operations"
    __table_args__ = (
        Index("ix_compop_org", "organization_id"),
        Index("ix_compop_framework", "framework_name"),
        Index("ix_compop_status", "operation_status"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # CSRD | CSDDD | ESRS | LKSGG | ISSB | custom
    framework_name: Mapped[str] = mapped_column(String(50), nullable=False)
    coverage_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    gap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # NOT_STARTED | IN_PROGRESS | COMPLETED
    operation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_STARTED")
    actions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── 9. ESG Actions ────────────────────────────────────────────────────────────


class ESGActionModel(BaseModel):
    """Unified action object aggregating actions from all EIOS modules.

    source_type / source_id link back to the originating module entity
    without a hard FK — cross-module references are ephemeral IDs.
    """

    __tablename__ = "esg_actions"
    __table_args__ = (
        Index("ix_esg_act_org", "organization_id"),
        Index("ix_esg_act_status", "action_status"),
        Index("ix_esg_act_priority", "priority"),
        Index("ix_esg_act_owner", "owner_user_id"),
        Index("ix_esg_act_due_date", "due_date"),
        Index("ix_esg_act_source", "source_type", "source_id"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # FINDING | RISK | RECOMMENDATION | SURVEILLANCE_SIGNAL | COMPLIANCE_GAP
    # | DUE_DILIGENCE | NETWORK_EXPOSURE | MANUAL
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="MANUAL")
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # OPEN | IN_PROGRESS | BLOCKED | COMPLETED | CANCELLED
    action_status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    # LOW | MEDIUM | HIGH | CRITICAL
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="MEDIUM")
    linked_objectives: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


# ── 10. Accountability Assignments ────────────────────────────────────────────


class AccountabilityAssignmentModel(BaseModel):
    """Tracks who owns, reviews, approves, or sponsors an entity."""

    __tablename__ = "accountability_assignments"
    __table_args__ = (
        Index("ix_acct_org", "organization_id"),
        Index("ix_acct_entity", "entity_type", "entity_id"),
        Index("ix_acct_user", "assigned_to_user_id"),
        Index("ix_acct_role", "role"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # OWNER | REVIEWER | APPROVER | EXECUTIVE_SPONSOR
    role: Mapped[str] = mapped_column(String(25), nullable=False)
    assigned_to_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    assigned_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # ACTIVE | REMOVED
    assignment_status: Mapped[str] = mapped_column(String(10), nullable=False, default="ACTIVE")


# ── 11. ESG Playbooks ─────────────────────────────────────────────────────────


class ESGPlaybookModel(BaseModel):
    """Response playbook defining investigation/escalation steps.

    steps: list of {step_number, title, description, owner_role, required_evidence}
    escalation_rules: list of {condition, escalate_to_role, message}
    evidence_required: list of strings describing required evidence types
    """

    __tablename__ = "esg_playbooks"
    __table_args__ = (
        Index("ix_esg_pb_org", "organization_id"),
        Index("ix_esg_pb_type", "playbook_type"),
        Index("ix_esg_pb_status", "playbook_status"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # CHILD_LABOUR | HUMAN_RIGHTS | SANCTIONS | COMPLIANCE_FAILURE | ENVIRONMENTAL | CUSTOM
    playbook_type: Mapped[str] = mapped_column(String(30), nullable=False)
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    escalation_rules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence_required: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # ACTIVE | ARCHIVED
    playbook_status: Mapped[str] = mapped_column(String(10), nullable=False, default="ACTIVE")


# ── 12. Workflow Executions ───────────────────────────────────────────────────


class WorkflowExecutionModel(BaseModel):
    """Live execution of a playbook or governance workflow.

    Human approval is required at each checkpoint — the execution halts at
    AWAITING_APPROVAL until a human approves or rejects the current step.
    """

    __tablename__ = "workflow_executions"
    __table_args__ = (
        Index("ix_wfexec_org", "organization_id"),
        Index("ix_wfexec_playbook", "playbook_id"),
        Index("ix_wfexec_status", "execution_status"),
        Index("ix_wfexec_initiated_by", "initiated_by"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    playbook_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    workflow_type: Mapped[str] = mapped_column(String(50), nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # PENDING | IN_PROGRESS | AWAITING_APPROVAL | COMPLETED | CANCELLED | REJECTED
    execution_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    steps_completed: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    pending_approvals: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    initiated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    linked_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    linked_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


# ── 13. Governance Escalation Rules ──────────────────────────────────────────


class GovernanceEscalationRuleModel(BaseModel):
    """Rule-based governance escalation matrix.

    When condition_entity_type + condition_status + overdue threshold is met,
    the system surfaces an escalation (notification / flag) to escalate_to_role.

    These rules are EVALUATED only — humans decide whether to act.
    """

    __tablename__ = "governance_escalation_rules"
    __table_args__ = (
        Index("ix_gov_esc_org", "organization_id"),
        Index("ix_gov_esc_status", "rule_status"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Entity type the rule watches: ESGAction | ESGInitiative | StrategicRisk | etc.
    condition_entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    condition_status: Mapped[str] = mapped_column(String(30), nullable=False)
    condition_overdue_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    condition_priority: Mapped[str | None] = mapped_column(String(10), nullable=True)
    escalate_to_role: Mapped[str] = mapped_column(String(30), nullable=False)
    escalate_to_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notification_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # ACTIVE | INACTIVE
    rule_status: Mapped[str] = mapped_column(String(10), nullable=False, default="ACTIVE")


# ── 14. ESG Health Scores ─────────────────────────────────────────────────────


class OrganizationESGHealthScoreModel(BaseModel):
    """Immutable snapshot of an organization's ESG health score.

    Deterministic formula — same inputs always produce the same score.
    calculation_inputs stores all source values for full explainability.
    """

    __tablename__ = "esg_health_scores"
    __table_args__ = (
        Index("ix_health_org", "organization_id"),
        Index("ix_health_calculated_at", "calculated_at"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    supplier_intelligence_score: Mapped[float] = mapped_column(Float, nullable=False)
    surveillance_score: Mapped[float] = mapped_column(Float, nullable=False)
    compliance_score: Mapped[float] = mapped_column(Float, nullable=False)
    due_diligence_score: Mapped[float] = mapped_column(Float, nullable=False)
    remediation_score: Mapped[float] = mapped_column(Float, nullable=False)
    governance_score: Mapped[float] = mapped_column(Float, nullable=False)
    # All input values, sub-scores, and formula parameters — immutable
    calculation_inputs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    formula_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ── 15. Strategic Risks ───────────────────────────────────────────────────────


class StrategicRiskModel(BaseModel):
    """Organization-wide strategic ESG risk.

    Distinguished from operational (supplier-level) risks: strategic risks
    are org-wide, linked to objectives and compliance programs.
    """

    __tablename__ = "strategic_risks"
    __table_args__ = (
        Index("ix_strat_risk_org", "organization_id"),
        Index("ix_strat_risk_level", "risk_level"),
        Index("ix_strat_risk_status", "risk_status"),
        Index("ix_strat_risk_owner", "owner_user_id"),
    )

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # ENVIRONMENTAL | SOCIAL | GOVERNANCE | REGULATORY | OPERATIONAL
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    # LOW | MEDIUM | HIGH | CRITICAL
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False, default="MEDIUM")
    # LOW | MEDIUM | HIGH
    probability: Mapped[str] = mapped_column(String(10), nullable=False, default="MEDIUM")
    # LOW | MEDIUM | HIGH | CRITICAL
    impact: Mapped[str] = mapped_column(String(10), nullable=False, default="MEDIUM")
    # IDENTIFIED | MITIGATING | ACCEPTED | CLOSED
    risk_status: Mapped[str] = mapped_column(String(15), nullable=False, default="IDENTIFIED")
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    linked_suppliers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    linked_objectives: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    linked_initiatives: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    linked_compliance_programs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
