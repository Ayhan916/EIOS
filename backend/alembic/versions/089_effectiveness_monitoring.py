"""CSDDD-003 — Effectiveness Monitoring (Art. 15)

Revision ID: 089
Revises: 088
Create Date: 2026-07-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "089"
down_revision = "088"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Indicator library
    op.create_table(
        "effectiveness_indicators",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("indicator_type", sa.String(50), nullable=False),
        sa.Column("unit", sa.String(100), nullable=False, server_default=""),
        sa.Column("data_source", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("csddd_article", sa.String(50), nullable=False, server_default=""),
        sa.Column("risk_category", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Effectiveness reviews
    op.create_table(
        "effectiveness_reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("overall_rating", sa.Integer(), nullable=True),
        sa.Column("key_findings", sa.Text(), nullable=True),
        sa.Column("improvement_actions", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Review measurement lines
    op.create_table(
        "review_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "review_id",
            UUID(as_uuid=True),
            sa.ForeignKey("effectiveness_reviews.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("indicator_id", UUID(as_uuid=True), nullable=False),
        sa.Column("indicator_name", sa.String(255), nullable=False),
        sa.Column("measured_value", sa.Float(), nullable=True),
        sa.Column("measured_text", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("auto_populated", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Add baseline_score and closed_score to existing CAP table (S3)
    op.add_column("corrective_action_plans", sa.Column("baseline_score", sa.Float(), nullable=True))
    op.add_column("corrective_action_plans", sa.Column("closed_score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("corrective_action_plans", "closed_score")
    op.drop_column("corrective_action_plans", "baseline_score")
    op.drop_table("review_lines")
    op.drop_table("effectiveness_reviews")
    op.drop_table("effectiveness_indicators")
