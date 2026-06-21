"""M41.1 — AI Governance Hardening.

Schema changes:
  - prompt_changes: ADD previous_prompt_text, new_prompt_text
  - ai_regulation_mappings: ADD organization_id FK
  - human_reviews: ADD incident_id FK
  - model_approval_workflows: ADD UNIQUE (model_id, stage)
  - CREATE TABLE ai_regulation_mapping_history

ORM table count: 148 → 149

Revision ID: 045
Revises: 044
Create Date: 2026-06-21
"""

import sqlalchemy as sa
from alembic import op

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── prompt_changes: preserve previous and new prompt text ─────────────────
    op.add_column(
        "prompt_changes",
        sa.Column("previous_prompt_text", sa.Text, nullable=True),
    )
    op.add_column(
        "prompt_changes",
        sa.Column("new_prompt_text", sa.Text, nullable=True),
    )

    # ── ai_regulation_mappings: add tenant isolation column ───────────────────
    op.add_column(
        "ai_regulation_mappings",
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_ai_reg_mappings_org", "ai_regulation_mappings", ["organization_id"]
    )

    # ── human_reviews: link to incidents for severity gate ────────────────────
    op.add_column(
        "human_reviews",
        sa.Column(
            "incident_id",
            sa.String(36),
            sa.ForeignKey("ai_incidents.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_human_reviews_incident", "human_reviews", ["incident_id"])

    # ── model_approval_workflows: prevent duplicate stage entries ─────────────
    op.create_unique_constraint(
        "uq_workflow_model_stage",
        "model_approval_workflows",
        ["model_id", "stage"],
    )

    # ── ai_regulation_mapping_history: audit trail for status changes ─────────
    op.create_table(
        "ai_regulation_mapping_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("version", sa.Integer, nullable=True, default=1),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "mapping_id",
            sa.String(36),
            sa.ForeignKey("ai_regulation_mappings.id"),
            nullable=False,
        ),
        sa.Column("previous_status", sa.String(20), nullable=False),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column("changed_by", sa.String(36), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_ai_reg_mapping_hist_mapping",
        "ai_regulation_mapping_history",
        ["mapping_id"],
    )


def downgrade() -> None:
    op.drop_table("ai_regulation_mapping_history")
    op.drop_constraint(
        "uq_workflow_model_stage", "model_approval_workflows", type_="unique"
    )
    op.drop_index("ix_human_reviews_incident", table_name="human_reviews")
    op.drop_column("human_reviews", "incident_id")
    op.drop_index("ix_ai_reg_mappings_org", table_name="ai_regulation_mappings")
    op.drop_column("ai_regulation_mappings", "organization_id")
    op.drop_column("prompt_changes", "new_prompt_text")
    op.drop_column("prompt_changes", "previous_prompt_text")
