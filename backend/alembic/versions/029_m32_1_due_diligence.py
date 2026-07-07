"""m32_1_due_diligence

M32.1 — Supply Chain Due Diligence Reporting (LkSG & CSDDD).

Creates:
  due_diligence_reports — immutable snapshots of LkSG/CSDDD/HR/Env/Remediation reports

report_data, report_hash, and framework_version are protected by a PL/pgSQL
immutability trigger, identical to the pattern in compliance_reports (M31.1),
board_reports (M29), and reporting_packages (M32).

Revision ID: 029
Revises: 028
Create Date: 2026-06-19
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None

_BASE_COLS = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
]


def upgrade() -> None:
    op.create_table(
        "due_diligence_reports",
        *_BASE_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("report_type", sa.String(40), nullable=False),
        sa.Column("framework", sa.String(30), nullable=False, server_default=""),
        sa.Column("framework_version", sa.String(50), nullable=False, server_default=""),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_by", sa.String(36), nullable=False, server_default=""),
        sa.Column("report_data", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("report_hash", sa.String(64), nullable=False, server_default=""),
    )
    op.create_index("ix_dd_reports_org", "due_diligence_reports", ["organization_id"])
    op.create_index(
        "ix_dd_reports_org_type", "due_diligence_reports", ["organization_id", "report_type"]
    )
    op.create_index(
        "ix_dd_reports_org_framework", "due_diligence_reports", ["organization_id", "framework"]
    )

    # Immutability trigger — same pattern as compliance_reports, reporting_packages, board_reports
    op.execute("""
        CREATE OR REPLACE FUNCTION due_diligence_reports_immutability_check()
        RETURNS TRIGGER LANGUAGE plpgsql AS $func$
        BEGIN
            IF (NEW.report_data IS DISTINCT FROM OLD.report_data OR
                NEW.report_hash IS DISTINCT FROM OLD.report_hash OR
                NEW.framework_version IS DISTINCT FROM OLD.framework_version) THEN
                RAISE EXCEPTION
                    'due_diligence_reports.% is immutable after generation (report_id=%)',
                    TG_OP, OLD.id
                USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END; $func$
    """)
    op.execute("""
        CREATE TRIGGER due_diligence_reports_immutability
        BEFORE UPDATE ON due_diligence_reports
        FOR EACH ROW EXECUTE FUNCTION due_diligence_reports_immutability_check()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS due_diligence_reports_immutability ON due_diligence_reports")
    op.execute("DROP FUNCTION IF EXISTS due_diligence_reports_immutability_check()")
    op.drop_index("ix_dd_reports_org_framework", table_name="due_diligence_reports")
    op.drop_index("ix_dd_reports_org_type", table_name="due_diligence_reports")
    op.drop_index("ix_dd_reports_org", table_name="due_diligence_reports")
    op.drop_table("due_diligence_reports")
