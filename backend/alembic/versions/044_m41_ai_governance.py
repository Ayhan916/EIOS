"""M41 — AI Governance, Model Risk Management & Assurance Layer.

17 new tables:
  ai_models, ai_use_cases, ai_risk_assessments, ai_controls, ai_control_tests,
  model_approval_workflows, prompt_templates, prompt_changes, ai_decision_logs,
  ai_explanations, human_reviews, model_monitoring_records, model_drift_alerts,
  ai_incidents, ai_policies, ai_assurance_reports, ai_regulation_mappings

ORM table count: 131 → 148

Revision ID: 044
Revises: 043
Create Date: 2026-06-21
"""

import sqlalchemy as sa
from alembic import op

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None

# BaseModel common columns (added to every table)
_BASE_COLS = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(50), nullable=True),
    sa.Column("version", sa.Integer, nullable=True, default=1),
    sa.Column("owner", sa.String(255), nullable=True),
    sa.Column("created_by", sa.String(255), nullable=True),
    sa.Column("updated_by", sa.String(255), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
]


def upgrade() -> None:
    # ── ai_models ─────────────────────────────────────────────────────────────
    op.create_table(
        "ai_models",
        *_BASE_COLS,
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=True),
        sa.Column("purpose", sa.Text, nullable=True),
        sa.Column("owner_user_id", sa.String(36), nullable=True),
        sa.Column("ai_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("metadata", sa.JSON, nullable=True),
    )
    op.create_index("ix_ai_models_org", "ai_models", ["organization_id"])
    op.create_index("ix_ai_models_status", "ai_models", ["ai_status"])

    # ── ai_use_cases ──────────────────────────────────────────────────────────
    op.create_table(
        "ai_use_cases",
        *_BASE_COLS,
        sa.Column(
            "model_id",
            sa.String(36),
            sa.ForeignKey("ai_models.id"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("business_owner", sa.String(255), nullable=True),
        sa.Column("technical_owner", sa.String(255), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column(
            "approval_status", sa.String(20), nullable=False, server_default="PENDING"
        ),
    )
    op.create_index("ix_ai_use_cases_model", "ai_use_cases", ["model_id"])

    # ── ai_risk_assessments ───────────────────────────────────────────────────
    op.create_table(
        "ai_risk_assessments",
        *_BASE_COLS,
        sa.Column(
            "model_id", sa.String(36), sa.ForeignKey("ai_models.id"), nullable=False
        ),
        sa.Column(
            "use_case_id",
            sa.String(36),
            sa.ForeignKey("ai_use_cases.id"),
            nullable=True,
        ),
        sa.Column("methodology", sa.String(255), nullable=True),
        sa.Column("bias_risk", sa.String(20), nullable=True),
        sa.Column("explainability_risk", sa.String(20), nullable=True),
        sa.Column("privacy_risk", sa.String(20), nullable=True),
        sa.Column("regulatory_risk", sa.String(20), nullable=True),
        sa.Column("operational_risk", sa.String(20), nullable=True),
        sa.Column("overall_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("assessor_user_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_ai_risk_model", "ai_risk_assessments", ["model_id"])

    # ── ai_controls ───────────────────────────────────────────────────────────
    op.create_table(
        "ai_controls",
        *_BASE_COLS,
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("control_type", sa.String(20), nullable=False),
        sa.Column("examples", sa.JSON, nullable=True),
        sa.Column(
            "model_id", sa.String(36), sa.ForeignKey("ai_models.id"), nullable=True
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_ai_controls_org", "ai_controls", ["organization_id"])

    # ── ai_control_tests ──────────────────────────────────────────────────────
    op.create_table(
        "ai_control_tests",
        *_BASE_COLS,
        sa.Column(
            "control_id",
            sa.String(36),
            sa.ForeignKey("ai_controls.id"),
            nullable=False,
        ),
        sa.Column(
            "model_id", sa.String(36), sa.ForeignKey("ai_models.id"), nullable=True
        ),
        sa.Column("test_result", sa.String(20), nullable=False),
        sa.Column("tested_by", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_control_tests_ctrl", "ai_control_tests", ["control_id"])

    # ── model_approval_workflows ──────────────────────────────────────────────
    op.create_table(
        "model_approval_workflows",
        *_BASE_COLS,
        sa.Column(
            "model_id", sa.String(36), sa.ForeignKey("ai_models.id"), nullable=False
        ),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column(
            "stage_status", sa.String(20), nullable=False, server_default="PENDING"
        ),
        sa.Column("approver_user_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stage_order", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_model_approval_model", "model_approval_workflows", ["model_id"]
    )

    # ── prompt_templates ──────────────────────────────────────────────────────
    op.create_table(
        "prompt_templates",
        *_BASE_COLS,
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "model_id", sa.String(36), sa.ForeignKey("ai_models.id"), nullable=True
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("prompt_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("prompt_text", sa.Text, nullable=False),
        sa.Column("owner_user_id", sa.String(36), nullable=True),
        sa.Column("is_approved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_prompt_templates_org", "prompt_templates", ["organization_id"])

    # ── prompt_changes ────────────────────────────────────────────────────────
    op.create_table(
        "prompt_changes",
        *_BASE_COLS,
        sa.Column(
            "prompt_id",
            sa.String(36),
            sa.ForeignKey("prompt_templates.id"),
            nullable=False,
        ),
        sa.Column("previous_version", sa.Integer, nullable=False),
        sa.Column("new_version", sa.Integer, nullable=False),
        sa.Column("change_rationale", sa.Text, nullable=True),
        sa.Column("approver_user_id", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_prompt_changes_prompt", "prompt_changes", ["prompt_id"])

    # ── ai_decision_logs ──────────────────────────────────────────────────────
    op.create_table(
        "ai_decision_logs",
        *_BASE_COLS,
        sa.Column(
            "model_id", sa.String(36), sa.ForeignKey("ai_models.id"), nullable=False
        ),
        sa.Column(
            "prompt_id",
            sa.String(36),
            sa.ForeignKey("prompt_templates.id"),
            nullable=True,
        ),
        sa.Column(
            "use_case_id",
            sa.String(36),
            sa.ForeignKey("ai_use_cases.id"),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("inputs_hash", sa.String(64), nullable=False),
        sa.Column("output_hash", sa.String(64), nullable=False),
        sa.Column("decision_type", sa.String(100), nullable=True),
        sa.Column("decision_metadata", sa.JSON, nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_decision_logs_model", "ai_decision_logs", ["model_id"])
    op.create_index("ix_ai_decision_logs_org", "ai_decision_logs", ["organization_id"])

    # ── ai_explanations ───────────────────────────────────────────────────────
    op.create_table(
        "ai_explanations",
        *_BASE_COLS,
        sa.Column(
            "decision_log_id",
            sa.String(36),
            sa.ForeignKey("ai_decision_logs.id"),
            nullable=False,
        ),
        sa.Column("factors", sa.JSON, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("source_references", sa.JSON, nullable=True),
    )
    op.create_index("ix_ai_explanations_log", "ai_explanations", ["decision_log_id"])

    # ── human_reviews ─────────────────────────────────────────────────────────
    op.create_table(
        "human_reviews",
        *_BASE_COLS,
        sa.Column(
            "decision_log_id",
            sa.String(36),
            sa.ForeignKey("ai_decision_logs.id"),
            nullable=True,
        ),
        sa.Column(
            "model_id", sa.String(36), sa.ForeignKey("ai_models.id"), nullable=False
        ),
        sa.Column("reviewer_user_id", sa.String(36), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("override_reason", sa.Text, nullable=True),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_human_reviews_model", "human_reviews", ["model_id"])

    # ── model_monitoring_records ──────────────────────────────────────────────
    op.create_table(
        "model_monitoring_records",
        *_BASE_COLS,
        sa.Column(
            "model_id", sa.String(36), sa.ForeignKey("ai_models.id"), nullable=False
        ),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("avg_latency_ms", sa.Float, nullable=True),
        sa.Column("failure_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_confidence", sa.Float, nullable=True),
        sa.Column("drift_score", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_model_monitoring_model", "model_monitoring_records", ["model_id"]
    )

    # ── model_drift_alerts ────────────────────────────────────────────────────
    op.create_table(
        "model_drift_alerts",
        *_BASE_COLS,
        sa.Column(
            "model_id", sa.String(36), sa.ForeignKey("ai_models.id"), nullable=False
        ),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_resolved", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_drift_alerts_model", "model_drift_alerts", ["model_id"])

    # ── ai_incidents ──────────────────────────────────────────────────────────
    op.create_table(
        "ai_incidents",
        *_BASE_COLS,
        sa.Column(
            "model_id", sa.String(36), sa.ForeignKey("ai_models.id"), nullable=False
        ),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("incident_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("reported_by", sa.String(36), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("esg_action_id", sa.String(36), nullable=True),
        sa.Column("strategic_risk_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_ai_incidents_org", "ai_incidents", ["organization_id"])
    op.create_index("ix_ai_incidents_model", "ai_incidents", ["model_id"])

    # ── ai_policies ───────────────────────────────────────────────────────────
    op.create_table(
        "ai_policies",
        *_BASE_COLS,
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
        sa.Column(
            "enterprise_id",
            sa.String(36),
            sa.ForeignKey("enterprises.id"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("policy_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("policy_body", sa.JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )

    # ── ai_assurance_reports ──────────────────────────────────────────────────
    op.create_table(
        "ai_assurance_reports",
        *_BASE_COLS,
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("report_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("use_case_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("control_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("incident_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("approval_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "overall_status",
            sa.String(30),
            nullable=False,
            server_default="NOT_ASSESSED",
        ),
        sa.Column("generated_by", sa.String(36), nullable=True),
        sa.Column("report_data", sa.JSON, nullable=True),
    )
    op.create_index("ix_ai_assurance_org", "ai_assurance_reports", ["organization_id"])

    # ── ai_regulation_mappings ────────────────────────────────────────────────
    op.create_table(
        "ai_regulation_mappings",
        *_BASE_COLS,
        sa.Column(
            "use_case_id",
            sa.String(36),
            sa.ForeignKey("ai_use_cases.id"),
            nullable=True,
        ),
        sa.Column(
            "risk_assessment_id",
            sa.String(36),
            sa.ForeignKey("ai_risk_assessments.id"),
            nullable=True,
        ),
        sa.Column(
            "control_id",
            sa.String(36),
            sa.ForeignKey("ai_controls.id"),
            nullable=True,
        ),
        sa.Column("framework", sa.String(50), nullable=False),
        sa.Column("article_reference", sa.String(255), nullable=True),
        sa.Column("requirement_text", sa.Text, nullable=True),
        sa.Column(
            "compliance_status",
            sa.String(20),
            nullable=False,
            server_default="NOT_ASSESSED",
        ),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_ai_reg_mappings_framework", "ai_regulation_mappings", ["framework"]
    )


def downgrade() -> None:
    op.drop_table("ai_regulation_mappings")
    op.drop_table("ai_assurance_reports")
    op.drop_table("ai_policies")
    op.drop_table("ai_incidents")
    op.drop_table("model_drift_alerts")
    op.drop_table("model_monitoring_records")
    op.drop_table("human_reviews")
    op.drop_table("ai_explanations")
    op.drop_table("ai_decision_logs")
    op.drop_table("prompt_changes")
    op.drop_table("prompt_templates")
    op.drop_table("model_approval_workflows")
    op.drop_table("ai_control_tests")
    op.drop_table("ai_controls")
    op.drop_table("ai_risk_assessments")
    op.drop_table("ai_use_cases")
    op.drop_table("ai_models")
