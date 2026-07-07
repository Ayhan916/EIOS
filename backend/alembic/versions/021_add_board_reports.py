"""021 add board_reports and report_schedules

Revision ID: 021
Revises: 020
Create Date: 2026-06-18
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "board_reports",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="Active"),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("report_version", sa.String(10), nullable=False, default="1.0"),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("executive_summary", sa.Text, nullable=False, default=""),
        sa.Column("report_data", JSON, nullable=False),
        sa.Column("supplier_snapshot", JSON, nullable=False),
    )
    op.create_index("ix_board_reports_org_id", "board_reports", ["organization_id"])
    op.create_index(
        "ix_board_reports_org_created", "board_reports", ["organization_id", "created_at"]
    )

    op.create_table(
        "report_schedules",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="Active"),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column("frequency", sa.String(20), nullable=False, default="monthly"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_config", JSON, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
    )
    op.create_index("ix_report_schedules_org_id", "report_schedules", ["organization_id"])
    op.create_index(
        "ix_report_schedules_org_active", "report_schedules", ["organization_id", "is_active"]
    )


def downgrade() -> None:
    op.drop_table("report_schedules")
    op.drop_table("board_reports")
