"""Add action_status and assigned_to_id to recommendations

Revision ID: 014
Revises: 013
Create Date: 2026-06-18
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recommendations",
        sa.Column("action_status", sa.String(20), nullable=False, server_default="open"),
    )
    op.add_column(
        "recommendations",
        sa.Column("assigned_to_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_recommendations_action_status",
        "recommendations",
        ["action_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_recommendations_action_status", table_name="recommendations")
    op.drop_column("recommendations", "assigned_to_id")
    op.drop_column("recommendations", "action_status")
