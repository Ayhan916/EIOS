"""M47 — Multi-Region Data Residency: audit log table.

Revision ID: 058
Revises: 057
Create Date: 2026-06-23
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_residency_audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("request_path", sa.String(1000), nullable=False, server_default=""),
        sa.Column("request_method", sa.String(10), nullable=False, server_default=""),
        sa.Column("org_region", sa.String(10), nullable=True),
        sa.Column("instance_region", sa.String(10), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_draudit_org", "data_residency_audit_log", ["organization_id"])
    op.create_index("ix_draudit_event_type", "data_residency_audit_log", ["event_type"])
    op.create_index("ix_draudit_created_at", "data_residency_audit_log", ["created_at"])

    # Index data_residency on organizations for region-based filtering
    op.create_index(
        "ix_organizations_data_residency",
        "organizations",
        ["data_residency"],
        postgresql_where=sa.text("data_residency IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_organizations_data_residency", table_name="organizations")
    op.drop_index("ix_draudit_created_at", table_name="data_residency_audit_log")
    op.drop_index("ix_draudit_event_type", table_name="data_residency_audit_log")
    op.drop_index("ix_draudit_org", table_name="data_residency_audit_log")
    op.drop_table("data_residency_audit_log")
