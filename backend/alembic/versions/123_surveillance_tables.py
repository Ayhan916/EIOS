"""create surveillance tables

Revision ID: 123
Revises: 122
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "123"
down_revision = "122"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "surveillance_signals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(36), nullable=True),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signal_status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("acknowledged_by", sa.String(36), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("episode_id", sa.String(36), nullable=True),
        sa.Column("explainability_json", JSONB(), nullable=False, server_default="{}"),
        sa.Column("dedupe_key", sa.String(300), nullable=True),
    )
    op.create_index("ix_signals_org", "surveillance_signals", ["organization_id"])
    op.create_index("ix_signals_supplier", "surveillance_signals", ["supplier_id"])
    op.create_index("ix_signals_status", "surveillance_signals", ["signal_status"])
    op.create_index("ix_signals_severity", "surveillance_signals", ["severity"])
    op.create_index("ix_signals_detected_at", "surveillance_signals", ["detected_at"])
    op.create_index("ix_signals_type", "surveillance_signals", ["signal_type"])
    op.create_index("ix_signals_episode", "surveillance_signals", ["episode_id"])

    op.create_table(
        "supplier_watchlists",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("watch_reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity", sa.String(20), nullable=False, server_default="HIGH"),
        sa.Column("added_by_type", sa.String(30), nullable=False, server_default="MANUAL"),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_by", sa.String(36), nullable=True),
        sa.Column("watchlist_status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.UniqueConstraint("organization_id", "supplier_id", name="uq_watchlist_org_supplier"),
    )
    op.create_index("ix_watchlist_org", "supplier_watchlists", ["organization_id"])
    op.create_index("ix_watchlist_supplier", "supplier_watchlists", ["supplier_id"])

    op.create_table(
        "risk_episodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity", sa.String(20), nullable=False, server_default="HIGH"),
        sa.Column("episode_status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signal_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resolved_by", sa.String(36), nullable=True),
    )
    op.create_index("ix_episodes_org", "risk_episodes", ["organization_id"])
    op.create_index("ix_episodes_supplier", "risk_episodes", ["supplier_id"])
    op.create_index("ix_episodes_status", "risk_episodes", ["episode_status"])

    op.create_table(
        "risk_trends",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("esg_score_start", sa.Float(), nullable=True),
        sa.Column("esg_score_end", sa.Float(), nullable=True),
        sa.Column("risk_score_start", sa.Float(), nullable=True),
        sa.Column("risk_score_end", sa.Float(), nullable=True),
        sa.Column("score_delta", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("trend", sa.String(20), nullable=False, server_default="STABLE"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("signal_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "supplier_id", "period", name="uq_risk_trend_org_supplier_period"),
    )
    op.create_index("ix_risk_trends_supplier", "risk_trends", ["supplier_id"])
    op.create_index("ix_risk_trends_org_period", "risk_trends", ["organization_id", "period"])


def downgrade() -> None:
    op.drop_table("risk_trends")
    op.drop_table("risk_episodes")
    op.drop_table("supplier_watchlists")
    op.drop_table("surveillance_signals")
