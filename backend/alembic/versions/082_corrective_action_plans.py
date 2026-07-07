"""082 — Corrective Action Plans table (GAP-20).

Revision ID: 082
Revises: 081
Create Date: 2026-07-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "082"
down_revision = "081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "corrective_action_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, default="ACTIVE"),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finding_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, default=""),
        sa.Column("description", sa.Text, nullable=False, default=""),
        sa.Column("responsible_party", sa.String(255), nullable=False, default=""),
        sa.Column("deadline", sa.Date, nullable=True),
        sa.Column("cap_status", sa.String(30), nullable=False, default="DRAFT"),
        sa.Column("evidence_note", sa.Text, nullable=False, default=""),
        sa.Column("evidence_file_url", sa.Text, nullable=True),
        sa.Column("evidence_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_note", sa.Text, nullable=False, default=""),
        sa.Column("verified_by_user_id", sa.String(36), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("insufficient_reason", sa.Text, nullable=False, default=""),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_user_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_cap_org_status", "corrective_action_plans", ["organization_id", "cap_status"]
    )
    op.create_index(
        "ix_cap_org_deadline", "corrective_action_plans", ["organization_id", "deadline"]
    )
    op.create_index("ix_cap_finding", "corrective_action_plans", ["finding_id"])


def downgrade() -> None:
    op.drop_index("ix_cap_org_deadline", "corrective_action_plans")
    op.drop_index("ix_cap_org_status", "corrective_action_plans")
    op.drop_index("ix_cap_finding", "corrective_action_plans")
    op.drop_table("corrective_action_plans")
