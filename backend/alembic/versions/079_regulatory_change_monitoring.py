"""079 — Regulatory Change Monitoring (GAP-19).

Creates regulatory_changes and regulatory_change_impacts tables.
Supports automatic impact scanning when regulatory frameworks change
(LkSG, CSDDD, CSRD) and flags affected assessments for re-review.

Revision ID: 079
Revises: 078
Create Date: 2026-07-03
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "079"
down_revision = "078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regulatory_changes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("framework_code", sa.String(30), nullable=False, server_default=""),
        sa.Column("change_title", sa.String(500), nullable=False, server_default=""),
        sa.Column("change_description", sa.Text, nullable=False, server_default=""),
        sa.Column("affected_article", sa.String(200), nullable=False, server_default=""),
        sa.Column("effective_date", sa.Date, nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="moderate"),
        sa.Column("change_status", sa.String(30), nullable=False, server_default="new"),
        sa.Column("source_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("source_url", sa.String(2000), nullable=False, server_default=""),
        sa.Column("affected_sectors", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("affected_frameworks", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("impact_summary", sa.Text, nullable=False, server_default=""),
        sa.Column("impacted_assessment_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("impacted_gap_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("regulation_refs", sa.String(500), nullable=False, server_default=""),
    )
    op.create_index("ix_regchg_framework", "regulatory_changes", ["framework_code"])
    op.create_index("ix_regchg_org", "regulatory_changes", ["organization_id"])
    op.create_index("ix_regchg_status", "regulatory_changes", ["change_status"])

    op.create_table(
        "regulatory_change_impacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("change_id", sa.String(36), nullable=False),
        sa.Column("assessment_id", sa.String(36), nullable=True),
        sa.Column("compliance_gap_id", sa.String(36), nullable=True),
        sa.Column(
            "impact_type", sa.String(50), nullable=False, server_default="assessment_re_review"
        ),
        sa.Column("re_review_required", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("notification_sent", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("acknowledged_by_user_id", sa.String(36), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_regchgimp_org", "regulatory_change_impacts", ["organization_id"])
    op.create_index("ix_regchgimp_change", "regulatory_change_impacts", ["change_id"])
    op.create_index("ix_regchgimp_assessment", "regulatory_change_impacts", ["assessment_id"])


def downgrade() -> None:
    op.drop_index("ix_regchgimp_assessment", table_name="regulatory_change_impacts")
    op.drop_index("ix_regchgimp_change", table_name="regulatory_change_impacts")
    op.drop_index("ix_regchgimp_org", table_name="regulatory_change_impacts")
    op.drop_table("regulatory_change_impacts")

    op.drop_index("ix_regchg_status", table_name="regulatory_changes")
    op.drop_index("ix_regchg_org", table_name="regulatory_changes")
    op.drop_index("ix_regchg_framework", table_name="regulatory_changes")
    op.drop_table("regulatory_changes")
