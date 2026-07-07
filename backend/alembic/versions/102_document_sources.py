"""102 — Document Sources: registry for external document URLs (annual reports, ESG reports etc.)

Tables created:
  - document_sources   (URL-registry mit Schedule und Status)
  - document_files     (eine Zeile pro heruntergeladener Datei inkl. AI-Extraktion)

Revision ID: 102
Revises: 101
Create Date: 2026-07-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "102"
down_revision = "101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── document_sources ────────────────────────────────────────────────────────
    op.create_table(
        "document_sources",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("supplier_id", sa.String(), nullable=True),
        sa.Column("company_name", sa.String(256), nullable=True),
        sa.Column(
            "doc_type",
            sa.String(64),
            nullable=False,
            comment="annual_report | sustainability_report | audit_report | csrd_report | csddd_disclosure | sector_risk",
        ),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column(
            "schedule",
            sa.String(16),
            nullable=False,
            server_default="monthly",
            comment="daily | weekly | monthly | manual",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(32), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_docsrc_org", "document_sources", ["organization_id"])
    op.create_index("ix_docsrc_supplier", "document_sources", ["supplier_id"])
    op.create_index("ix_docsrc_org_type", "document_sources", ["organization_id", "doc_type"])

    # ── document_files ──────────────────────────────────────────────────────────
    op.create_table(
        "document_files",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("supplier_id", sa.String(), nullable=True),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("company_name", sa.String(256), nullable=True),
        sa.Column("report_year", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(8), nullable=True, server_default="de"),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("pages", sa.Integer(), nullable=True),
        sa.Column("chunks_count", sa.Integer(), nullable=True, server_default="0"),
        # AI-extracted structured data
        sa.Column("extracted_risks", sa.JSON(), nullable=True),
        sa.Column("extracted_targets", sa.JSON(), nullable=True),
        sa.Column("extracted_commitments", sa.JSON(), nullable=True),
        sa.Column("extracted_kpis", sa.JSON(), nullable=True),
        sa.Column("esg_score", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        # Processing status
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="pending",
            comment="pending | downloading | parsing | analyzing | indexing | done | failed",
        ),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_id"], ["document_sources.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_docfile_org", "document_files", ["organization_id"])
    op.create_index("ix_docfile_source", "document_files", ["source_id"])
    op.create_index("ix_docfile_supplier", "document_files", ["supplier_id"])
    op.create_index("ix_docfile_status", "document_files", ["status"])
    op.create_index("ix_docfile_org_type_year", "document_files", ["organization_id", "doc_type", "report_year"])


def downgrade() -> None:
    op.drop_table("document_files")
    op.drop_table("document_sources")
