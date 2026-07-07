"""M39 ESG Operating System — initial schema.

Creates 15 new tables that form the ESG Operating System layer on top of
the existing EIOS module stack (M01–M38):

  esg_objectives                — organizational ESG targets
  esg_key_results               — measurable milestones per objective
  esg_initiatives               — structured programs of work
  governance_calendar_events    — board / compliance / review schedule
  esg_programs                  — portfolio-level program grouping
  esg_controls                  — preventive / detective / corrective controls
  control_tests                 — point-in-time effectiveness test results
  compliance_operations         — continuous framework-specific readiness ops
  esg_actions                   — unified action inbox across all EIOS modules
  accountability_assignments    — owner / reviewer / approver / sponsor records
  esg_playbooks                 — step-based response playbooks
  workflow_executions           — live playbook / governance workflow state
  governance_escalation_rules   — rule-based governance escalation matrix
  esg_health_scores             — deterministic org ESG health score snapshots
  strategic_risks               — organization-wide strategic ESG risks

Revision ID: 040
Revises: 039
Create Date: 2026-06-20
"""

import sqlalchemy as sa

from alembic import op

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None

_COMMON = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
]


def upgrade() -> None:
    # ── 1. esg_objectives ────────────────────────────────────────────────────
    op.create_table(
        "esg_objectives",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("owner_user_id", sa.String(36), nullable=True),
        sa.Column("target_value", sa.Float, nullable=True),
        sa.Column("current_value", sa.Float, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("objective_status", sa.String(20), nullable=False, server_default="NOT_STARTED"),
    )
    op.create_index("ix_esg_obj_org", "esg_objectives", ["organization_id"])
    op.create_index("ix_esg_obj_category", "esg_objectives", ["category"])
    op.create_index("ix_esg_obj_status", "esg_objectives", ["objective_status"])
    op.create_index("ix_esg_obj_owner", "esg_objectives", ["owner_user_id"])

    # ── 2. esg_key_results ───────────────────────────────────────────────────
    op.create_table(
        "esg_key_results",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("objective_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("target_value", sa.Float, nullable=False, server_default="0"),
        sa.Column("current_value", sa.Float, nullable=False, server_default="0"),
        sa.Column("progress_percent", sa.Float, nullable=False, server_default="0"),
        sa.Column("kr_status", sa.String(20), nullable=False, server_default="NOT_STARTED"),
    )
    op.create_index("ix_esg_kr_org", "esg_key_results", ["organization_id"])
    op.create_index("ix_esg_kr_objective", "esg_key_results", ["objective_id"])
    op.create_index("ix_esg_kr_status", "esg_key_results", ["kr_status"])

    # ── 3. esg_initiatives ───────────────────────────────────────────────────
    op.create_table(
        "esg_initiatives",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("owner_user_id", sa.String(36), nullable=True),
        sa.Column("initiative_status", sa.String(20), nullable=False, server_default="PLANNED"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "linked_objectives", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column(
            "linked_suppliers", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column(
            "linked_findings", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column(
            "linked_risks", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
    )
    op.create_index("ix_esg_init_org", "esg_initiatives", ["organization_id"])
    op.create_index("ix_esg_init_status", "esg_initiatives", ["initiative_status"])
    op.create_index("ix_esg_init_owner", "esg_initiatives", ["owner_user_id"])

    # ── 4. governance_calendar_events ────────────────────────────────────────
    op.create_table(
        "governance_calendar_events",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recurrence_rule", sa.String(255), nullable=True),
        sa.Column("reminder_days", sa.Integer, nullable=False, server_default="7"),
        sa.Column("event_status", sa.String(20), nullable=False, server_default="SCHEDULED"),
        sa.Column("linked_entity_type", sa.String(50), nullable=True),
        sa.Column("linked_entity_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
    )
    op.create_index("ix_gcal_org", "governance_calendar_events", ["organization_id"])
    op.create_index("ix_gcal_type", "governance_calendar_events", ["event_type"])
    op.create_index("ix_gcal_scheduled_at", "governance_calendar_events", ["scheduled_at"])
    op.create_index("ix_gcal_status", "governance_calendar_events", ["event_status"])

    # ── 5. esg_programs ──────────────────────────────────────────────────────
    op.create_table(
        "esg_programs",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("program_status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "linked_objectives", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column(
            "linked_initiatives", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column(
            "linked_suppliers", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
    )
    op.create_index("ix_esg_prog_org", "esg_programs", ["organization_id"])
    op.create_index("ix_esg_prog_status", "esg_programs", ["program_status"])

    # ── 6. esg_controls ──────────────────────────────────────────────────────
    op.create_table(
        "esg_controls",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("control_name", sa.String(255), nullable=False),
        sa.Column("control_type", sa.String(20), nullable=False),
        sa.Column("owner_user_id", sa.String(36), nullable=True),
        sa.Column("frequency", sa.String(30), nullable=False, server_default="ANNUAL"),
        sa.Column("evidence_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "effectiveness_status", sa.String(25), nullable=False, server_default="NOT_TESTED"
        ),
    )
    op.create_index("ix_esg_ctrl_org", "esg_controls", ["organization_id"])
    op.create_index("ix_esg_ctrl_type", "esg_controls", ["control_type"])
    op.create_index("ix_esg_ctrl_effectiveness", "esg_controls", ["effectiveness_status"])

    # ── 7. control_tests ─────────────────────────────────────────────────────
    op.create_table(
        "control_tests",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("control_id", sa.String(36), nullable=False),
        sa.Column("performed_by", sa.String(36), nullable=True),
        sa.Column("test_result", sa.String(10), nullable=False),
        sa.Column("findings", sa.Text, nullable=False, server_default=""),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ctest_org", "control_tests", ["organization_id"])
    op.create_index("ix_ctest_control", "control_tests", ["control_id"])
    op.create_index("ix_ctest_result", "control_tests", ["test_result"])
    op.create_index("ix_ctest_tested_at", "control_tests", ["tested_at"])

    # ── 8. compliance_operations ─────────────────────────────────────────────
    op.create_table(
        "compliance_operations",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("framework_name", sa.String(50), nullable=False),
        sa.Column("coverage_percent", sa.Float, nullable=False, server_default="0"),
        sa.Column("gap_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("owner_user_id", sa.String(36), nullable=True),
        sa.Column("operation_status", sa.String(20), nullable=False, server_default="NOT_STARTED"),
        sa.Column("actions", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_compop_org", "compliance_operations", ["organization_id"])
    op.create_index("ix_compop_framework", "compliance_operations", ["framework_name"])
    op.create_index("ix_compop_status", "compliance_operations", ["operation_status"])

    # ── 9. esg_actions ───────────────────────────────────────────────────────
    op.create_table(
        "esg_actions",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="MANUAL"),
        sa.Column("source_id", sa.String(36), nullable=True),
        sa.Column("owner_user_id", sa.String(36), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("action_status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("priority", sa.String(10), nullable=False, server_default="MEDIUM"),
        sa.Column(
            "linked_objectives", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
    )
    op.create_index("ix_esg_act_org", "esg_actions", ["organization_id"])
    op.create_index("ix_esg_act_status", "esg_actions", ["action_status"])
    op.create_index("ix_esg_act_priority", "esg_actions", ["priority"])
    op.create_index("ix_esg_act_owner", "esg_actions", ["owner_user_id"])
    op.create_index("ix_esg_act_due_date", "esg_actions", ["due_date"])
    op.create_index("ix_esg_act_source", "esg_actions", ["source_type", "source_id"])

    # ── 10. accountability_assignments ───────────────────────────────────────
    op.create_table(
        "accountability_assignments",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(25), nullable=False),
        sa.Column("assigned_to_user_id", sa.String(36), nullable=False),
        sa.Column("assigned_by_user_id", sa.String(36), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assignment_status", sa.String(10), nullable=False, server_default="ACTIVE"),
    )
    op.create_index("ix_acct_org", "accountability_assignments", ["organization_id"])
    op.create_index("ix_acct_entity", "accountability_assignments", ["entity_type", "entity_id"])
    op.create_index("ix_acct_user", "accountability_assignments", ["assigned_to_user_id"])
    op.create_index("ix_acct_role", "accountability_assignments", ["role"])

    # ── 11. esg_playbooks ────────────────────────────────────────────────────
    op.create_table(
        "esg_playbooks",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("playbook_type", sa.String(30), nullable=False),
        sa.Column("steps", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "escalation_rules", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column(
            "evidence_required", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column("playbook_status", sa.String(10), nullable=False, server_default="ACTIVE"),
    )
    op.create_index("ix_esg_pb_org", "esg_playbooks", ["organization_id"])
    op.create_index("ix_esg_pb_type", "esg_playbooks", ["playbook_type"])
    op.create_index("ix_esg_pb_status", "esg_playbooks", ["playbook_status"])

    # ── 12. workflow_executions ──────────────────────────────────────────────
    op.create_table(
        "workflow_executions",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("playbook_id", sa.String(36), nullable=True),
        sa.Column("workflow_type", sa.String(50), nullable=False),
        sa.Column("current_step", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_steps", sa.Integer, nullable=False, server_default="0"),
        sa.Column("execution_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column(
            "steps_completed", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column(
            "pending_approvals", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column("initiated_by", sa.String(36), nullable=True),
        sa.Column("linked_entity_type", sa.String(50), nullable=True),
        sa.Column("linked_entity_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_wfexec_org", "workflow_executions", ["organization_id"])
    op.create_index("ix_wfexec_playbook", "workflow_executions", ["playbook_id"])
    op.create_index("ix_wfexec_status", "workflow_executions", ["execution_status"])
    op.create_index("ix_wfexec_initiated_by", "workflow_executions", ["initiated_by"])

    # ── 13. governance_escalation_rules ──────────────────────────────────────
    op.create_table(
        "governance_escalation_rules",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("rule_name", sa.String(255), nullable=False),
        sa.Column("condition_entity_type", sa.String(50), nullable=False),
        sa.Column("condition_status", sa.String(30), nullable=False),
        sa.Column("condition_overdue_days", sa.Integer, nullable=True),
        sa.Column("condition_priority", sa.String(10), nullable=True),
        sa.Column("escalate_to_role", sa.String(30), nullable=False),
        sa.Column("escalate_to_user_id", sa.String(36), nullable=True),
        sa.Column("notification_message", sa.Text, nullable=False, server_default=""),
        sa.Column("rule_status", sa.String(10), nullable=False, server_default="ACTIVE"),
    )
    op.create_index("ix_gov_esc_org", "governance_escalation_rules", ["organization_id"])
    op.create_index("ix_gov_esc_status", "governance_escalation_rules", ["rule_status"])

    # ── 14. esg_health_scores ────────────────────────────────────────────────
    op.create_table(
        "esg_health_scores",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("overall_score", sa.Float, nullable=False),
        sa.Column("supplier_intelligence_score", sa.Float, nullable=False),
        sa.Column("surveillance_score", sa.Float, nullable=False),
        sa.Column("compliance_score", sa.Float, nullable=False),
        sa.Column("due_diligence_score", sa.Float, nullable=False),
        sa.Column("remediation_score", sa.Float, nullable=False),
        sa.Column("governance_score", sa.Float, nullable=False),
        sa.Column(
            "calculation_inputs", sa.dialects.postgresql.JSONB, nullable=False, server_default="{}"
        ),
        sa.Column("formula_version", sa.String(10), nullable=False, server_default="1.0"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_health_org", "esg_health_scores", ["organization_id"])
    op.create_index("ix_health_calculated_at", "esg_health_scores", ["calculated_at"])

    # ── 15. strategic_risks ──────────────────────────────────────────────────
    op.create_table(
        "strategic_risks",
        *_COMMON,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("risk_level", sa.String(10), nullable=False, server_default="MEDIUM"),
        sa.Column("probability", sa.String(10), nullable=False, server_default="MEDIUM"),
        sa.Column("impact", sa.String(10), nullable=False, server_default="MEDIUM"),
        sa.Column("risk_status", sa.String(15), nullable=False, server_default="IDENTIFIED"),
        sa.Column("owner_user_id", sa.String(36), nullable=True),
        sa.Column(
            "linked_suppliers", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column(
            "linked_objectives", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column(
            "linked_initiatives", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"
        ),
        sa.Column(
            "linked_compliance_programs",
            sa.dialects.postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
    )
    op.create_index("ix_strat_risk_org", "strategic_risks", ["organization_id"])
    op.create_index("ix_strat_risk_level", "strategic_risks", ["risk_level"])
    op.create_index("ix_strat_risk_status", "strategic_risks", ["risk_status"])
    op.create_index("ix_strat_risk_owner", "strategic_risks", ["owner_user_id"])


def downgrade() -> None:
    for table in [
        "strategic_risks",
        "esg_health_scores",
        "governance_escalation_rules",
        "workflow_executions",
        "esg_playbooks",
        "accountability_assignments",
        "esg_actions",
        "compliance_operations",
        "control_tests",
        "esg_controls",
        "esg_programs",
        "governance_calendar_events",
        "esg_initiatives",
        "esg_key_results",
        "esg_objectives",
    ]:
        op.drop_table(table)
