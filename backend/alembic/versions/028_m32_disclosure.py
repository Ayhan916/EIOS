"""m32_disclosure

M32 — Sustainability Reporting & Disclosure Management.

Creates:
  disclosure_frameworks       — reporting standards (CSRD/ESRS/ISSB/GRI/TCFD)
  disclosure_requirements     — itemised disclosure obligations per framework
  disclosure_responses        — org drafts/approvals against each requirement
  reporting_packages          — immutable published reporting snapshots

The reporting_packages table carries the same PL/pgSQL immutability trigger
pattern used for compliance_reports (M31.1) and board_reports (M29) to
guarantee historical reproducibility.

Revision ID: 028
Revises: 027
Create Date: 2026-06-19
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "028"
down_revision = "027"
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
    # ── disclosure_frameworks ────────────────────────────────────────────────
    op.create_table(
        "disclosure_frameworks",
        *_BASE_COLS,
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("fw_version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("jurisdiction", sa.String(50), nullable=False, server_default="Global"),
        sa.Column("effective_date", sa.Date, nullable=True),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
    )
    op.create_index(
        "ix_disclosure_frameworks_code",
        "disclosure_frameworks",
        ["code"],
        unique=True,
    )

    # ── disclosure_requirements ──────────────────────────────────────────────
    op.create_table(
        "disclosure_requirements",
        *_BASE_COLS,
        sa.Column("framework_id", sa.String(36), nullable=False),
        sa.Column("reference", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("category", sa.String(50), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_disclosure_requirements_framework",
        "disclosure_requirements",
        ["framework_id"],
    )
    op.create_index(
        "ix_disclosure_requirements_ref",
        "disclosure_requirements",
        ["reference"],
    )

    # ── disclosure_responses ─────────────────────────────────────────────────
    op.create_table(
        "disclosure_responses",
        *_BASE_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("requirement_id", sa.String(36), nullable=False),
        sa.Column("disclosure_status", sa.String(30), nullable=False, server_default="Not Started"),
        sa.Column("narrative_text", sa.Text, nullable=False, server_default=""),
        sa.Column("evidence_coverage", sa.Float, nullable=False, server_default="0"),
        sa.Column("coverage_category", sa.String(20), nullable=False, server_default="Weak"),
        sa.Column("coverage_rationale", postgresql.JSON, nullable=False),
        sa.Column("readiness_status", sa.String(40), nullable=False, server_default="Not Started"),
        sa.Column("readiness_rationale", sa.Text, nullable=False, server_default=""),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_disclosure_responses_org",
        "disclosure_responses",
        ["organization_id"],
    )
    op.create_index(
        "ix_disclosure_responses_requirement",
        "disclosure_responses",
        ["requirement_id"],
    )
    op.create_unique_constraint(
        "uq_disclosure_response_org_req",
        "disclosure_responses",
        ["organization_id", "requirement_id"],
    )

    # ── reporting_packages ───────────────────────────────────────────────────
    op.create_table(
        "reporting_packages",
        *_BASE_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("framework_id", sa.String(36), nullable=False),
        sa.Column("framework_code", sa.String(30), nullable=False, server_default=""),
        sa.Column("framework_version", sa.String(50), nullable=False, server_default=""),
        sa.Column("package_type", sa.String(50), nullable=False, server_default=""),
        sa.Column("publication_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_by", sa.String(36), nullable=False, server_default=""),
        sa.Column("report_data", postgresql.JSON, nullable=False),
        sa.Column("report_hash", sa.String(64), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_reporting_packages_org_fw",
        "reporting_packages",
        ["organization_id", "framework_code"],
    )

    # Immutability trigger: prevent mutation of published package content
    op.execute("""
        CREATE OR REPLACE FUNCTION reporting_packages_immutability_check()
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
                    'reporting_packages.% is immutable after publication (package_id=%)',
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
        CREATE TRIGGER reporting_packages_immutability
        BEFORE UPDATE ON reporting_packages
        FOR EACH ROW
        EXECUTE FUNCTION reporting_packages_immutability_check();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS reporting_packages_immutability ON reporting_packages;")
    op.execute("DROP FUNCTION IF EXISTS reporting_packages_immutability_check();")
    op.drop_table("reporting_packages")
    op.drop_table("disclosure_responses")
    op.drop_table("disclosure_requirements")
    op.drop_table("disclosure_frameworks")
