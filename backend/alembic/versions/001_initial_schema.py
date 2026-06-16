"""Initial EIOS enterprise schema

Revision ID: 001
Revises:
Create Date: 2026-06-16

Creates all 17 entity tables and 11 association tables for the
complete EIOS canonical object model per architecture/026.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

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


def _common() -> list[sa.Column]:  # type: ignore[type-arg]
    return [sa.Column(c.name, c.type, **{k: v for k, v in c._constructor_args[1].items()
                                         if k != "name"})  # type: ignore[attr-defined]
            for c in _COMMON]


def upgrade() -> None:
    # --- organizations ---
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("organization_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("industry", sa.String(255), nullable=True),
    )

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(100), nullable=False, server_default=""),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # --- sectors ---
    op.create_table(
        "sectors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("nace_code", sa.String(20), nullable=False),
        sa.Column("nace_description", sa.String(500), nullable=True),
        sa.Column("risk_profile", sa.String(2000), nullable=True),
        sa.Column("parent_sector_id", sa.String(36), sa.ForeignKey("sectors.id"), nullable=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
    )
    op.create_index("ix_sectors_nace_code", "sectors", ["nace_code"])

    # --- assessments ---
    op.create_table(
        "assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("assessment_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("scope", sa.String(500), nullable=False, server_default=""),
        sa.Column("methodology", sa.String(500), nullable=True),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="High"),
        sa.Column("sector_id", sa.String(36), sa.ForeignKey("sectors.id"), nullable=True),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("approval_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_assessments_sector_id", "assessments", ["sector_id"])

    # --- evidences ---
    op.create_table(
        "evidences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("evidence_type", sa.String(50), nullable=False, server_default="Document"),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="High"),
        sa.Column("url", sa.String(2000), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reliability_score", sa.Float, nullable=True),
    )

    # --- findings ---
    op.create_table(
        "findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("assessment_id", sa.String(36), sa.ForeignKey("assessments.id"), nullable=False),
        sa.Column("category", sa.String(100), nullable=False, server_default=""),
        sa.Column("severity", sa.String(20), nullable=False, server_default="Medium"),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="High"),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("uncertainty", sa.Text, nullable=True),
    )
    op.create_index("ix_findings_assessment_id", "findings", ["assessment_id"])

    # --- risks ---
    op.create_table(
        "risks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="Medium"),
        sa.Column("category", sa.String(100), nullable=False, server_default=""),
        sa.Column("assessment_id", sa.String(36), sa.ForeignKey("assessments.id"), nullable=True),
        sa.Column("sector_id", sa.String(36), sa.ForeignKey("sectors.id"), nullable=True),
        sa.Column("probability", sa.Float, nullable=True),
        sa.Column("impact", sa.Float, nullable=True),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="Medium"),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("uncertainty", sa.Text, nullable=True),
    )
    op.create_index("ix_risks_assessment_id", "risks", ["assessment_id"])
    op.create_index("ix_risks_sector_id", "risks", ["sector_id"])

    # --- recommendations ---
    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="Medium"),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="High"),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("action_required", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(36), nullable=True),
    )

    # --- decisions ---
    op.create_table(
        "decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("rationale", sa.Text, nullable=False),
        sa.Column("decided_by", sa.String(255), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("context", sa.Text, nullable=True),
    )

    # --- controls ---
    op.create_table(
        "controls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("control_type", sa.String(50), nullable=False, server_default="Preventive"),
        sa.Column("effectiveness", sa.Float, nullable=True),
        sa.Column("automated", sa.Boolean, nullable=False, server_default="false"),
    )

    # --- requirements ---
    op.create_table(
        "requirements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("article", sa.String(100), nullable=True),
        sa.Column("mandatory", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("requirement_type", sa.String(100), nullable=False, server_default=""),
    )

    # --- policies ---
    op.create_table(
        "policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("policy_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(36), nullable=True),
    )

    # --- standards ---
    op.create_table(
        "standards",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("standard_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("version_label", sa.String(100), nullable=True),
    )

    # --- assets ---
    op.create_table(
        "assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("asset_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("asset_class", sa.String(100), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
    )

    # --- processes ---
    op.create_table(
        "processes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("process_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("steps", postgresql.ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("owner_domain", sa.String(100), nullable=True),
        sa.Column("automated", sa.Boolean, nullable=False, server_default="false"),
    )

    # --- projects ---
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("project_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("priority", sa.String(20), nullable=False, server_default="Medium"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
    )

    # --- tasks ---
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("task_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("assignee_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="Medium"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])

    # --- association tables ---
    op.create_table(
        "assessment_evidence",
        sa.Column("assessment_id", sa.String(36), sa.ForeignKey("assessments.id"), primary_key=True),
        sa.Column("evidence_id", sa.String(36), sa.ForeignKey("evidences.id"), primary_key=True),
    )
    op.create_table(
        "finding_evidence",
        sa.Column("finding_id", sa.String(36), sa.ForeignKey("findings.id"), primary_key=True),
        sa.Column("evidence_id", sa.String(36), sa.ForeignKey("evidences.id"), primary_key=True),
    )
    op.create_table(
        "risk_finding",
        sa.Column("risk_id", sa.String(36), sa.ForeignKey("risks.id"), primary_key=True),
        sa.Column("finding_id", sa.String(36), sa.ForeignKey("findings.id"), primary_key=True),
    )
    op.create_table(
        "recommendation_risk",
        sa.Column("recommendation_id", sa.String(36), sa.ForeignKey("recommendations.id"), primary_key=True),
        sa.Column("risk_id", sa.String(36), sa.ForeignKey("risks.id"), primary_key=True),
    )
    op.create_table(
        "recommendation_finding",
        sa.Column("recommendation_id", sa.String(36), sa.ForeignKey("recommendations.id"), primary_key=True),
        sa.Column("finding_id", sa.String(36), sa.ForeignKey("findings.id"), primary_key=True),
    )
    op.create_table(
        "control_risk",
        sa.Column("control_id", sa.String(36), sa.ForeignKey("controls.id"), primary_key=True),
        sa.Column("risk_id", sa.String(36), sa.ForeignKey("risks.id"), primary_key=True),
    )
    op.create_table(
        "control_requirement",
        sa.Column("control_id", sa.String(36), sa.ForeignKey("controls.id"), primary_key=True),
        sa.Column("requirement_id", sa.String(36), sa.ForeignKey("requirements.id"), primary_key=True),
    )
    op.create_table(
        "policy_requirement",
        sa.Column("policy_id", sa.String(36), sa.ForeignKey("policies.id"), primary_key=True),
        sa.Column("requirement_id", sa.String(36), sa.ForeignKey("requirements.id"), primary_key=True),
    )
    op.create_table(
        "policy_control",
        sa.Column("policy_id", sa.String(36), sa.ForeignKey("policies.id"), primary_key=True),
        sa.Column("control_id", sa.String(36), sa.ForeignKey("controls.id"), primary_key=True),
    )
    op.create_table(
        "standard_requirement",
        sa.Column("standard_id", sa.String(36), sa.ForeignKey("standards.id"), primary_key=True),
        sa.Column("requirement_id", sa.String(36), sa.ForeignKey("requirements.id"), primary_key=True),
    )
    op.create_table(
        "decision_recommendation",
        sa.Column("decision_id", sa.String(36), sa.ForeignKey("decisions.id"), primary_key=True),
        sa.Column("recommendation_id", sa.String(36), sa.ForeignKey("recommendations.id"), primary_key=True),
    )


def downgrade() -> None:
    for table in [
        "decision_recommendation", "standard_requirement", "policy_control",
        "policy_requirement", "control_requirement", "control_risk",
        "recommendation_finding", "recommendation_risk", "risk_finding",
        "finding_evidence", "assessment_evidence",
        "tasks", "projects", "processes", "assets", "standards",
        "policies", "requirements", "controls", "decisions",
        "recommendations", "risks", "findings", "evidences",
        "assessments", "sectors", "users", "organizations",
    ]:
        op.drop_table(table)
