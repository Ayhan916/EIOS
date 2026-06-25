"""Fix missing BaseModel columns across 55 tables.

Every ORM model that inherits from BaseModel expects:
  status    VARCHAR(20) NOT NULL DEFAULT 'Active'
  version   INTEGER     NOT NULL DEFAULT 1
  owner     VARCHAR(36) nullable
  created_by  VARCHAR(36) nullable
  updated_by  VARCHAR(36) nullable

Several migrations created tables before BaseModel was standardised,
so these columns are missing. This migration adds them with IF NOT EXISTS
so it is safe to run even if some columns already exist.

Revision ID: 050
Revises: 049
Create Date: 2026-06-22
"""

from alembic import op

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None

# (table, [missing cols])  — generated from DB audit
PATCHES = [
    # ── missing all 5 ──────────────────────────────────────────────────────────
    ("agent_alerts",                    ["status", "version", "owner", "created_by", "updated_by"]),
    ("agent_findings",                  ["status", "version", "owner", "created_by", "updated_by"]),
    ("assessment_evidence",             ["status", "version", "owner", "created_by", "updated_by"]),
    ("control_requirement",             ["status", "version", "owner", "created_by", "updated_by"]),
    ("control_risk",                    ["status", "version", "owner", "created_by", "updated_by"]),
    ("conversation_participants",       ["status", "version", "owner", "created_by", "updated_by"]),
    ("conversations",                   ["status", "version", "owner", "created_by", "updated_by"]),
    ("dataset_validation_results",      ["status", "version", "owner", "created_by", "updated_by"]),
    ("decision_recommendation",         ["status", "version", "owner", "created_by", "updated_by"]),
    ("evidence_requests",               ["status", "version", "owner", "created_by", "updated_by"]),
    ("evidence_submission_files",       ["status", "version", "owner", "created_by", "updated_by"]),
    ("evidence_submissions",            ["status", "version", "owner", "created_by", "updated_by"]),
    ("finding_evidence",                ["status", "version", "owner", "created_by", "updated_by"]),
    ("message_attachments",             ["status", "version", "owner", "created_by", "updated_by"]),
    ("messages",                        ["status", "version", "owner", "created_by", "updated_by"]),
    ("monitoring_agent_runs",           ["status", "version", "owner", "created_by", "updated_by"]),
    ("policy_control",                  ["status", "version", "owner", "created_by", "updated_by"]),
    ("policy_requirement",              ["status", "version", "owner", "created_by", "updated_by"]),
    ("questionnaire_answers",           ["status", "version", "owner", "created_by", "updated_by"]),
    ("questionnaire_assignments",       ["status", "version", "owner", "created_by", "updated_by"]),
    ("questionnaire_questions",         ["status", "version", "owner", "created_by", "updated_by"]),
    ("questionnaire_templates",         ["status", "version", "owner", "created_by", "updated_by"]),
    ("recommendation_drafts",           ["status", "version", "owner", "created_by", "updated_by"]),
    ("recommendation_finding",          ["status", "version", "owner", "created_by", "updated_by"]),
    ("recommendation_risk",             ["status", "version", "owner", "created_by", "updated_by"]),
    ("risk_finding",                    ["status", "version", "owner", "created_by", "updated_by"]),
    ("standard_requirement",            ["status", "version", "owner", "created_by", "updated_by"]),
    ("supplier_activity_events",        ["status", "version", "owner", "created_by", "updated_by"]),
    ("supplier_invitations",            ["status", "version", "owner", "created_by", "updated_by"]),
    ("supplier_password_reset_tokens",  ["status", "version", "owner", "created_by", "updated_by"]),
    ("supplier_users",                  ["status", "version", "owner", "created_by", "updated_by"]),
    # ── missing status, version, owner ─────────────────────────────────────────
    ("carbon_inventories",              ["status", "version", "owner"]),
    ("climate_risk_assessments",        ["status", "version", "owner"]),
    ("csrd_performance_mappings",       ["status", "version", "owner"]),
    ("decarbonization_initiatives",     ["status", "version", "owner"]),
    ("emission_sources",                ["status", "version", "owner"]),
    ("esg_kpis",                        ["status", "version", "owner"]),
    ("esg_targets",                     ["status", "version", "owner"]),
    ("issb_sustainability_mappings",    ["status", "version", "owner"]),
    ("kpi_alerts",                      ["status", "version", "owner"]),
    ("kpi_measurements",                ["status", "version", "owner"]),
    ("net_zero_milestones",             ["status", "version", "owner"]),
    ("net_zero_roadmaps",               ["status", "version", "owner"]),
    ("performance_forecasts",           ["status", "version", "owner"]),
    ("scenario_analyses",               ["status", "version", "owner"]),
    ("science_based_targets",           ["status", "version", "owner"]),
    ("sustainability_assurance_records",["status", "version", "owner"]),
    ("sustainability_objectives",       ["status", "version", "owner"]),
    ("sustainability_performance_reports",["status","version", "owner"]),
    ("sustainability_scorecards",       ["status", "version", "owner"]),
    # ── missing version, owner, created_by, updated_by (has status) ────────────
    ("monitoring_agents",               ["version", "owner", "created_by", "updated_by"]),
    # ── missing owner, status, updated_by, version ─────────────────────────────
    ("escalation_rules",                ["status", "version", "owner", "updated_by"]),
    ("remediation_plans",               ["status", "version", "owner", "updated_by"]),
    ("workflow_jobs",                   ["status", "version", "owner", "updated_by"]),
    # ── missing owner, updated_by, version (has status + created_by) ───────────
    ("connector_runs",                  ["version", "owner", "updated_by"]),
]


def _add(table: str, cols: list[str]) -> None:
    for col in cols:
        if col == "status":
            op.execute(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'Active'"
            )
        elif col == "version":
            op.execute(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1"
            )
        elif col == "owner":
            op.execute(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS owner VARCHAR(36)"
            )
        elif col == "created_by":
            op.execute(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS created_by VARCHAR(36)"
            )
        elif col == "updated_by":
            op.execute(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS updated_by VARCHAR(36)"
            )


def upgrade() -> None:
    for table, cols in PATCHES:
        _add(table, cols)


def downgrade() -> None:
    # Dropping columns added as nullable/defaulted is safe
    for table, cols in PATCHES:
        for col in cols:
            op.execute(
                f"ALTER TABLE {table} DROP COLUMN IF EXISTS {col}"
            )
