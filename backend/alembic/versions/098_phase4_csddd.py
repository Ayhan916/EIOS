"""098 — Phase 4: ESAP Export, Threshold Monitor, Regulatory Radar.

Tables created:
  - esap_submissions              (CSDDD-009)
  - company_profiles              (CSDDD-010)
  - regulatory_sources            (CSDDD-014)
  - regulatory_changes            (CSDDD-014)
  - regulatory_feed_entries       (CSDDD-014)

Revision ID: 098
Revises: 097
Create Date: 2026-07-06
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "098"
down_revision = "097"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CSDDD-009 — ESAP submissions
    op.create_table(
        "esap_submissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("report_year", sa.Integer, nullable=False),
        sa.Column("export_format", sa.String(10), nullable=False, server_default="json"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by", sa.String(255), nullable=True),
        sa.Column("confirmation_reference", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_esap_submissions_org", "esap_submissions", ["organization_id"])

    # CSDDD-010 — Company profiles
    op.create_table(
        "company_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("fiscal_year", sa.Integer, nullable=False),
        sa.Column("employee_count_worldwide", sa.Integer, nullable=False, server_default="0"),
        sa.Column("net_revenue_eur_millions", sa.Float, nullable=False, server_default="0"),
        sa.Column("headquarters_country", sa.String(2), nullable=False, server_default="DE"),
        sa.Column("sector", sa.String(100), nullable=False, server_default=""),
        sa.Column("non_eu_company", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_company_profiles_org", "company_profiles", ["organization_id"])
    op.create_unique_constraint(
        "uq_company_profiles_org_year", "company_profiles", ["organization_id", "fiscal_year"]
    )

    # CSDDD-014 — Regulatory sources
    op.create_table(
        "regulatory_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(500), nullable=False, server_default=""),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("relevance_score", sa.Integer, nullable=False, server_default="3"),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("rss_feed_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_regulatory_sources_org", "regulatory_sources", ["organization_id"])

    # CSDDD-014 — CSDDD-specific regulatory changes (separate from GAP-19 table)
    op.create_table(
        "csddd_regulatory_changes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("source_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text, nullable=False, server_default=""),
        sa.Column("affected_articles_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("action_required", sa.String(10), nullable=False, server_default="pending"),
        sa.Column("action_description", sa.Text, nullable=False, server_default=""),
        sa.Column("impact_modules_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("estimated_effort_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("url_hash", sa.String(64), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_csddd_regulatory_changes_org", "csddd_regulatory_changes", ["organization_id"]
    )
    op.create_index(
        "ix_csddd_regulatory_changes_org_status",
        "csddd_regulatory_changes",
        ["organization_id", "status"],
    )

    # CSDDD-014 — Feed entries (deduplication)
    op.create_table(
        "regulatory_feed_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("url_hash", sa.String(64), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("url", sa.String(500), nullable=False, server_default=""),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text, nullable=False, server_default=""),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("converted_to_change_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_regulatory_feed_entries_source", "regulatory_feed_entries", ["source_id"])
    op.create_unique_constraint(
        "uq_regulatory_feed_entries_url_hash", "regulatory_feed_entries", ["url_hash"]
    )


def downgrade() -> None:
    op.drop_table("regulatory_feed_entries")
    op.drop_table("csddd_regulatory_changes")
    op.drop_table("regulatory_sources")
    op.drop_table("company_profiles")
    op.drop_table("esap_submissions")
