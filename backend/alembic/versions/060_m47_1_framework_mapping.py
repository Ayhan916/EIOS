"""M47.1 — Control Framework Mapping: control_framework_mappings table.

Revision ID: 060
Revises: 059
Create Date: 2026-06-23
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "control_framework_mappings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("control_id", sa.String(36), nullable=False),
        sa.Column("framework_code", sa.String(30), nullable=False),
        sa.Column("framework_control_id", sa.String(100), nullable=False),
        sa.Column("framework_control_name", sa.String(500), nullable=False, server_default=""),
        sa.Column("mapping_type", sa.String(20), nullable=False, server_default="direct"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.UniqueConstraint(
            "control_id",
            "framework_code",
            "framework_control_id",
            name="uq_ctrl_fw_mapping",
        ),
    )
    op.create_index("ix_ctrl_fw_control_id", "control_framework_mappings", ["control_id"])
    op.create_index("ix_ctrl_fw_code", "control_framework_mappings", ["framework_code"])
    op.create_index("ix_ctrl_fw_org", "control_framework_mappings", ["organization_id"])

    # Seed example framework controls (ISO 27001 — Information Security)
    # Real deployments populate this via the API
    pass


def downgrade() -> None:
    op.drop_index("ix_ctrl_fw_org", table_name="control_framework_mappings")
    op.drop_index("ix_ctrl_fw_code", table_name="control_framework_mappings")
    op.drop_index("ix_ctrl_fw_control_id", table_name="control_framework_mappings")
    op.drop_table("control_framework_mappings")
