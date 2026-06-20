"""M36 Autonomous ESG Monitoring Agents.

Creates:
  monitoring_agents         — agent type registry
  monitoring_agent_runs     — immutable run history
  agent_findings            — agent-generated findings
  agent_alerts              — escalated alerts
  escalation_rules          — per-org configurable escalation rules
  recommendation_drafts     — human-approval-pending recommendation drafts

Revision ID: 038
Revises: 037
Create Date: 2026-06-20
"""

import sqlalchemy as sa
from alembic import op

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "monitoring_agents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("run_interval_hours", sa.Integer, nullable=False, server_default="24"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint("uq_monitoring_agent_type", "monitoring_agents", ["agent_type"])
    op.create_index("ix_monitoring_agents_status", "monitoring_agents", ["status"])

    op.create_table(
        "monitoring_agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_status", sa.String(20), nullable=False, server_default="RUNNING"),
        sa.Column("findings_generated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("alerts_generated", sa.Integer, nullable=False, server_default="0"),
        sa.Column("actions_recommended", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("execution_time_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_monitoring_runs_agent", "monitoring_agent_runs", ["agent_id"])
    op.create_index("ix_monitoring_runs_org", "monitoring_agent_runs", ["organization_id"])
    op.create_index("ix_monitoring_runs_started", "monitoring_agent_runs", ["started_at"])

    op.create_table(
        "agent_findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=True),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("agent_run_id", sa.String(36), nullable=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("evidence", sa.Text, nullable=False, server_default=""),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0.8"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finding_status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("acknowledged_by", sa.String(36), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rule_triggered", sa.String(200), nullable=False, server_default=""),
        sa.Column("source_data_json", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_findings_org", "agent_findings", ["organization_id"])
    op.create_index("ix_agent_findings_supplier", "agent_findings", ["supplier_id"])
    op.create_index("ix_agent_findings_agent", "agent_findings", ["agent_id"])
    op.create_index("ix_agent_findings_status", "agent_findings", ["finding_status"])
    op.create_index("ix_agent_findings_severity", "agent_findings", ["severity"])

    op.create_table(
        "agent_alerts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=True),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("agent_finding_id", sa.String(36), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="WARNING"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message", sa.Text, nullable=False, server_default=""),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_alerts_org", "agent_alerts", ["organization_id"])
    op.create_index("ix_agent_alerts_supplier", "agent_alerts", ["supplier_id"])
    op.create_index("ix_agent_alerts_severity", "agent_alerts", ["severity"])
    op.create_index("ix_agent_alerts_acknowledged", "agent_alerts", ["acknowledged_at"])

    op.create_table(
        "escalation_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("agent_type", sa.String(50), nullable=False, server_default="*"),
        sa.Column("condition_json", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("escalation_severity", sa.String(20), nullable=False, server_default="WARNING"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_escalation_rules_org", "escalation_rules", ["organization_id"])
    op.create_index("ix_escalation_rules_agent_type", "escalation_rules", ["agent_type"])

    op.create_table(
        "recommendation_drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=True),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("agent_finding_id", sa.String(36), nullable=True),
        sa.Column("recommendation_text", sa.Text, nullable=False),
        sa.Column("rationale", sa.Text, nullable=False, server_default=""),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0.8"),
        sa.Column("draft_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recommendation_drafts_org", "recommendation_drafts", ["organization_id"])
    op.create_index("ix_recommendation_drafts_supplier", "recommendation_drafts", ["supplier_id"])
    op.create_index("ix_recommendation_drafts_status", "recommendation_drafts", ["draft_status"])


def downgrade() -> None:
    op.drop_table("recommendation_drafts")
    op.drop_table("escalation_rules")
    op.drop_table("agent_alerts")
    op.drop_table("agent_findings")
    op.drop_table("monitoring_agent_runs")
    op.drop_table("monitoring_agents")
