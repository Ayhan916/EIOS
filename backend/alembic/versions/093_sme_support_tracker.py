"""CSDDD-007 — SME Support Tracker (Art. 10 Abs. 2 lit. b)

Revision ID: 093
Revises: 092
Create Date: 2026-07-06

Creates:
  sme_profiles             — EU SME classification per supplier
  sme_support_programs     — support programs per SME supplier
  sme_support_measures     — individual support measures within a program
"""

import sqlalchemy as sa

from alembic import op

revision = "093"
down_revision = "092"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sme_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("classification", sa.String(20), nullable=False, server_default="small"),
        sa.Column("employee_count", sa.Integer, nullable=True),
        sa.Column("annual_revenue_eur", sa.Float, nullable=True),
        sa.Column("is_confirmed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("confirmed_by", sa.String(255), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sme_profiles_org", "sme_profiles", ["organization_id"])
    op.create_index(
        "ix_sme_profiles_supplier", "sme_profiles", ["organization_id", "supplier_id"], unique=True
    )

    op.create_table(
        "sme_support_programs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responsible_user", sa.String(255), nullable=True),
        sa.Column("total_budget_eur", sa.Float, nullable=True),
        sa.Column("spent_budget_eur", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sme_support_programs_org", "sme_support_programs", ["organization_id"])
    op.create_index(
        "ix_sme_support_programs_supplier",
        "sme_support_programs",
        ["organization_id", "supplier_id"],
    )
    op.create_index(
        "ix_sme_support_programs_status", "sme_support_programs", ["organization_id", "status"]
    )

    op.create_table(
        "sme_support_measures",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "program_id",
            sa.String(36),
            sa.ForeignKey("sme_support_programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("support_type", sa.String(30), nullable=False, server_default="training"),
        sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cost_eur", sa.Float, nullable=True),
        sa.Column("impact_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sme_support_measures_org", "sme_support_measures", ["organization_id"])
    op.create_index("ix_sme_support_measures_program", "sme_support_measures", ["program_id"])


def downgrade() -> None:
    op.drop_table("sme_support_measures")
    op.drop_table("sme_support_programs")
    op.drop_table("sme_profiles")
