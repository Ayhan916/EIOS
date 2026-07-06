"""CSDDD-011 — CSDDD Readiness Snapshots

Revision ID: 094
Revises: 093
Create Date: 2026-07-06

Creates:
  readiness_snapshots — audit trail of readiness score computations
"""

from alembic import op
import sqlalchemy as sa

revision = "094"
down_revision = "093"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "readiness_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("overall_score_pct", sa.Float, nullable=False),
        sa.Column("overall_level", sa.String(20), nullable=False),
        sa.Column("article_scores_json", sa.Text, nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("computed_by", sa.String(255), nullable=True),
    )
    op.create_index("ix_readiness_snapshots_org", "readiness_snapshots", ["organization_id"])
    op.create_index("ix_readiness_snapshots_org_date", "readiness_snapshots", ["organization_id", "computed_at"])


def downgrade() -> None:
    op.drop_table("readiness_snapshots")
