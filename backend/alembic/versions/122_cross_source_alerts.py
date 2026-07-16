"""cross_source_alerts table

Revision ID: 122
Revises: 121
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa

revision = "122"
down_revision = "121"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cross_source_alerts",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("organization_id", sa.String, nullable=False, index=True),
        sa.Column("trigger_signal_id", sa.String, sa.ForeignKey("company_signals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("trigger_company", sa.String(256), nullable=False),
        sa.Column("trigger_nace", sa.String(16), nullable=True),
        sa.Column("trigger_signal_type", sa.String(64), nullable=False),
        sa.Column("trigger_description", sa.Text, nullable=False),
        sa.Column("impact_type", sa.String(64), nullable=False),
        # sector_stress | upstream_pressure | downstream_risk | shared_supplier_risk
        sa.Column("severity", sa.String(16), nullable=False, default="medium"),
        sa.Column("affected_nace_codes", sa.JSON, nullable=False, default=list),
        sa.Column("affected_suppliers", sa.JSON, nullable=False, default=list),
        # [{id, name, nace_code, relation}]
        sa.Column("reasoning", sa.Text, nullable=False),
        sa.Column("recommended_actions", sa.JSON, nullable=False, default=list),
        sa.Column("status", sa.String(16), nullable=False, default="open"),
        # open | acknowledged | resolved
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_csa_org", "cross_source_alerts", ["organization_id"])
    op.create_index("ix_csa_severity", "cross_source_alerts", ["severity"])
    op.create_index("ix_csa_status", "cross_source_alerts", ["status"])


def downgrade() -> None:
    op.drop_table("cross_source_alerts")
