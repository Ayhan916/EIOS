"""compliance_reports

M31.1 — Compliance Report Persistence.

Creates:
  compliance_reports — immutable snapshot table for generated compliance PDFs

Immutability trigger prevents mutation of report_data, report_hash, and
framework_version after initial insert, guaranteeing historical reproducibility.

Revision ID: 027
Revises: 026
Create Date: 2026-06-19
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "027"
down_revision = "026"
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
        "compliance_reports",
        *_BASE_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("report_type", sa.String(30), nullable=False),
        sa.Column("framework_code", sa.String(30), nullable=False, server_default=""),
        sa.Column("framework_version", sa.String(50), nullable=False, server_default=""),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_by", sa.String(36), nullable=False, server_default=""),
        sa.Column("report_data", postgresql.JSON, nullable=False),
        sa.Column("report_hash", sa.String(64), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_compliance_reports_org_type",
        "compliance_reports",
        ["organization_id", "report_type"],
    )

    # Immutability trigger: prevent mutation of content fields after insert
    op.execute("""
        CREATE OR REPLACE FUNCTION compliance_reports_immutability_check()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF (
                NEW.report_data IS DISTINCT FROM OLD.report_data OR
                NEW.report_hash IS DISTINCT FROM OLD.report_hash OR
                NEW.framework_version IS DISTINCT FROM OLD.framework_version
            ) THEN
                RAISE EXCEPTION
                    'compliance_reports.% is immutable after creation (report_id=%)',
                    CASE
                        WHEN NEW.report_data IS DISTINCT FROM OLD.report_data THEN 'report_data'
                        WHEN NEW.report_hash IS DISTINCT FROM OLD.report_hash THEN 'report_hash'
                        ELSE 'framework_version'
                    END,
                    OLD.id
                USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$;
    """)

    op.execute("""
        CREATE TRIGGER compliance_reports_immutability
        BEFORE UPDATE ON compliance_reports
        FOR EACH ROW
        EXECUTE FUNCTION compliance_reports_immutability_check();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS compliance_reports_immutability ON compliance_reports;")
    op.execute("DROP FUNCTION IF EXISTS compliance_reports_immutability_check();")
    op.drop_table("compliance_reports")
