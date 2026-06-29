"""Supplier Twin Extensions — M25 / KAN-85-89

Adds five tables that extend the Supplier entity into a full Enterprise
Digital Supply Chain Twin:
  - supplier_locations      (plants, warehouses, production sites)
  - supplier_contacts       (role-based contact persons)
  - supplier_certifications (ISO/IATF/SA8000 lifecycle management)
  - supplier_ownerships     (corporate ownership, UBO, LEI, DUNS)
  - supplier_esg_metrics    (energy, water, waste, workforce KPIs — ESRS-mapped)

Revision ID: 065
Revises: 064
Create Date: 2026-06-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "065"
down_revision = "064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── supplier_locations ────────────────────────────────────────────────────
    op.create_table(
        "supplier_locations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("location_type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("city", sa.String(200), nullable=True),
        sa.Column("country", sa.String(100), nullable=False, server_default=""),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("region", sa.String(200), nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("capacity_description", sa.Text, nullable=True),
        sa.Column("employee_count", sa.Integer, nullable=True),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_sloc_supplier", "supplier_locations", ["supplier_id"])
    op.create_index("ix_sloc_org", "supplier_locations", ["organization_id"])
    op.create_index("ix_sloc_type", "supplier_locations", ["location_type"])
    op.create_index("ix_sloc_country", "supplier_locations", ["country"])

    # ── supplier_contacts ─────────────────────────────────────────────────────
    op.create_table(
        "supplier_contacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("first_name", sa.String(200), nullable=False),
        sa.Column("last_name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(500), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("role", sa.String(30), nullable=False, server_default="OTHER"),
        sa.Column("job_title", sa.String(300), nullable=True),
        sa.Column("department", sa.String(200), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_scon_supplier", "supplier_contacts", ["supplier_id"])
    op.create_index("ix_scon_org", "supplier_contacts", ["organization_id"])
    op.create_index("ix_scon_role", "supplier_contacts", ["role"])

    # ── supplier_certifications ───────────────────────────────────────────────
    op.create_table(
        "supplier_certifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("cert_type", sa.String(30), nullable=False),
        sa.Column("custom_cert_name", sa.String(300), nullable=True),
        sa.Column("issuing_body", sa.String(300), nullable=True),
        sa.Column("certificate_number", sa.String(200), nullable=True),
        sa.Column("scope_description", sa.Text, nullable=True),
        sa.Column("valid_from", sa.Date, nullable=True),
        sa.Column("valid_until", sa.Date, nullable=True),
        sa.Column("is_expired_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("verified_by", sa.String(36), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_id", sa.String(36), nullable=True),
        sa.Column("location_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_scert_supplier", "supplier_certifications", ["supplier_id"])
    op.create_index("ix_scert_org", "supplier_certifications", ["organization_id"])
    op.create_index("ix_scert_type", "supplier_certifications", ["cert_type"])
    op.create_index("ix_scert_valid_until", "supplier_certifications", ["valid_until"])
    op.create_index("ix_scert_is_expired", "supplier_certifications", ["is_expired_flag"])

    # ── supplier_ownerships ───────────────────────────────────────────────────
    op.create_table(
        "supplier_ownerships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("ownership_type", sa.String(30), nullable=False, server_default="PRIVATE"),
        sa.Column("parent_company_name", sa.String(500), nullable=True),
        sa.Column("parent_company_country", sa.String(100), nullable=True),
        sa.Column("ownership_percentage", sa.Float, nullable=True),
        sa.Column("ultimate_beneficial_owner", sa.String(500), nullable=True),
        sa.Column("ubo_country", sa.String(100), nullable=True),
        sa.Column("ubo_ownership_pct", sa.Float, nullable=True),
        sa.Column("publicly_listed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("stock_exchange", sa.String(100), nullable=True),
        sa.Column("ticker_symbol", sa.String(20), nullable=True),
        sa.Column("market_cap_eur", sa.Float, nullable=True),
        sa.Column("lei_code", sa.String(20), nullable=True),
        sa.Column("duns_number", sa.String(20), nullable=True),
        sa.Column("vat_number", sa.String(50), nullable=True),
        sa.Column("registration_number", sa.String(100), nullable=True),
        sa.Column("registration_country", sa.String(100), nullable=True),
        sa.Column("is_state_owned", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("state_ownership_pct", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.UniqueConstraint("supplier_id", "organization_id", name="uq_ownership_supplier_org"),
    )
    op.create_index("ix_sown_supplier", "supplier_ownerships", ["supplier_id"])
    op.create_index("ix_sown_org", "supplier_ownerships", ["organization_id"])
    op.create_index("ix_sown_publicly_listed", "supplier_ownerships", ["publicly_listed"])
    op.create_index("ix_sown_is_state_owned", "supplier_ownerships", ["is_state_owned"])
    op.create_index("ix_sown_parent_country", "supplier_ownerships", ["parent_company_country"])

    # ── supplier_esg_metrics ──────────────────────────────────────────────────
    op.create_table(
        "supplier_esg_metrics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("reporting_year", sa.Integer, nullable=False),
        sa.Column("reporting_period", sa.String(10), nullable=False, server_default="ANNUAL"),
        sa.Column("metric_type", sa.String(60), nullable=False),
        sa.Column("custom_metric_name", sa.String(300), nullable=True),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("esrs_reference", sa.String(20), nullable=True),
        sa.Column("gri_reference", sa.String(30), nullable=True),
        sa.Column("data_source", sa.String(300), nullable=True),
        sa.Column("is_third_party_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("verification_standard", sa.String(100), nullable=True),
        sa.Column("evidence_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.UniqueConstraint(
            "supplier_id", "organization_id", "reporting_year", "reporting_period", "metric_type",
            name="uq_esg_metric_supplier_period_type",
        ),
    )
    op.create_index("ix_sesg_supplier", "supplier_esg_metrics", ["supplier_id"])
    op.create_index("ix_sesg_org", "supplier_esg_metrics", ["organization_id"])
    op.create_index("ix_sesg_year", "supplier_esg_metrics", ["reporting_year"])
    op.create_index("ix_sesg_type", "supplier_esg_metrics", ["metric_type"])


def downgrade() -> None:
    op.drop_table("supplier_esg_metrics")
    op.drop_table("supplier_ownerships")
    op.drop_table("supplier_certifications")
    op.drop_table("supplier_contacts")
    op.drop_table("supplier_locations")
