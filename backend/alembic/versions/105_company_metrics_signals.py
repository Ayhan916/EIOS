"""company_metrics and company_signals tables

Revision ID: 105
Revises: 104
Create Date: 2026-07-08
"""

import sqlalchemy as sa
from alembic import op

revision = "105"
down_revision = "104"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_metrics",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("company_name", sa.String(256), nullable=False),
        sa.Column("supplier_id", sa.String(), nullable=True),
        sa.Column("metric_type", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric(20, 4), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("period", sa.String(8), nullable=False, server_default="FY"),
        sa.Column("source_doc_id", sa.String(), sa.ForeignKey("document_files.id", ondelete="SET NULL"), nullable=True),
        sa.Column("confidence", sa.String(16), nullable=False, server_default="exact"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "company_name", "metric_type", "year", "period", name="uq_company_metric_year"),
    )
    op.create_index("ix_cm_org", "company_metrics", ["organization_id"])
    op.create_index("ix_cm_org_company", "company_metrics", ["organization_id", "company_name"])
    op.create_index("ix_cm_metric_year", "company_metrics", ["metric_type", "year"])
    op.create_index("ix_cm_supplier", "company_metrics", ["supplier_id"])

    op.create_table(
        "company_signals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("company_name", sa.String(256), nullable=False),
        sa.Column("supplier_id", sa.String(), nullable=True),
        sa.Column("signal_type", sa.String(64), nullable=False),
        sa.Column("dimension", sa.String(32), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False, server_default="neutral"),
        sa.Column("severity", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("source_doc_id", sa.String(), sa.ForeignKey("document_files.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cs_org", "company_signals", ["organization_id"])
    op.create_index("ix_cs_org_company", "company_signals", ["organization_id", "company_name"])
    op.create_index("ix_cs_dimension", "company_signals", ["organization_id", "dimension"])
    op.create_index("ix_cs_signal_type", "company_signals", ["signal_type"])
    op.create_index("ix_cs_year", "company_signals", ["organization_id", "year"])
    op.create_index("ix_cs_supplier", "company_signals", ["supplier_id"])


def downgrade() -> None:
    op.drop_table("company_signals")
    op.drop_table("company_metrics")
