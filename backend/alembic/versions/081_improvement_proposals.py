"""081 — Self-Improvement Loop: improvement_proposals table (GAP-05).

Revision ID: 081
Revises: 080
Create Date: 2026-07-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "081"
down_revision = "080"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "improvement_proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, default="ACTIVE"),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("weakness_type", sa.String(60), nullable=False, default=""),
        sa.Column("affected_module", sa.String(120), nullable=False, default=""),
        sa.Column("current_value", sa.Float, nullable=False, default=0.0),
        sa.Column("target_value", sa.Float, nullable=False, default=0.0),
        sa.Column("expected_impact", sa.Float, nullable=False, default=0.0),
        sa.Column("priority_score", sa.Float, nullable=False, default=0.0),
        sa.Column("title", sa.String(255), nullable=False, default=""),
        sa.Column("description", sa.Text, nullable=False, default=""),
        sa.Column("suggested_action", sa.Text, nullable=False, default=""),
        sa.Column("approval_status", sa.String(20), nullable=False, default="DRAFT"),
        sa.Column("approved_by_user_id", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by_user_id", sa.String(36), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reject_reason", sa.Text, nullable=True),
        sa.Column("before_evaluation_run_id", sa.String(36), nullable=True),
        sa.Column("after_evaluation_run_id", sa.String(36), nullable=True),
        sa.Column("verified_improvement", sa.Float, nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_improv_status", "improvement_proposals", ["approval_status"])
    op.create_index("ix_improv_module", "improvement_proposals", ["affected_module"])
    op.create_index("ix_improv_priority", "improvement_proposals", ["priority_score"])


def downgrade() -> None:
    op.drop_index("ix_improv_priority", "improvement_proposals")
    op.drop_index("ix_improv_module", "improvement_proposals")
    op.drop_index("ix_improv_status", "improvement_proposals")
    op.drop_table("improvement_proposals")
