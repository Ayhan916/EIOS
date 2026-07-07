"""Material Twin — M26 / KAN-91–97

Five tables for the Material aggregate:
  materials                     — core identity, classification, CAS/HS codes
  material_compositions         — BOM (bill-of-materials) links
  material_sourcing             — supplier→material sourcing records
  material_compliance_flags     — per-regulation compliance status
  material_sustainability_metrics — LCA / sustainability KPIs

Revision ID: 067
Revises: 066
Create Date: 2026-06-12
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "067"
down_revision = "066"
branch_labels = None
depends_on = None

_AUDIT_COLS = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
    sa.Column(
        "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
    ),
]


def upgrade() -> None:
    # ── materials ─────────────────────────────────────────────────────────────
    op.create_table(
        "materials",
        *_AUDIT_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("material_type", sa.String(30), nullable=False),
        sa.Column("material_status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("internal_code", sa.String(100), nullable=True),
        sa.Column("cas_number", sa.String(20), nullable=True),
        sa.Column("ec_number", sa.String(20), nullable=True),
        sa.Column("iupac_name", sa.Text, nullable=True),
        sa.Column("molecular_formula", sa.String(200), nullable=True),
        sa.Column("hs_code", sa.String(15), nullable=True),
        sa.Column("un_number", sa.String(10), nullable=True),
        sa.Column("ghs_hazard_class", sa.String(200), nullable=True),
        sa.Column("unit_of_measure", sa.String(20), nullable=False, server_default="kg"),
        sa.Column("weight_per_unit_kg", sa.Float, nullable=True),
        sa.Column("country_of_origin", sa.String(100), nullable=True),
        sa.Column("is_critical_raw_material", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("recycled_content_pct", sa.Float, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_mat_org", "materials", ["organization_id"])
    op.create_index("ix_mat_type", "materials", ["material_type"])
    op.create_index("ix_mat_status", "materials", ["material_status"])
    op.create_index("ix_mat_cas", "materials", ["cas_number"])
    op.create_index("ix_mat_hs", "materials", ["hs_code"])
    op.create_index("ix_mat_crm", "materials", ["is_critical_raw_material"])

    # ── material_compositions ─────────────────────────────────────────────────
    op.create_table(
        "material_compositions",
        *_AUDIT_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("parent_material_id", sa.String(36), nullable=False),
        sa.Column("child_material_id", sa.String(36), nullable=False),
        sa.Column("weight_pct", sa.Float, nullable=True),
        sa.Column("quantity", sa.Float, nullable=True),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_unique_constraint(
        "uq_mat_comp_parent_child",
        "material_compositions",
        ["organization_id", "parent_material_id", "child_material_id"],
    )
    op.create_index("ix_mcomp_parent", "material_compositions", ["parent_material_id"])
    op.create_index("ix_mcomp_child", "material_compositions", ["child_material_id"])
    op.create_index("ix_mcomp_org", "material_compositions", ["organization_id"])

    # ── material_sourcing ─────────────────────────────────────────────────────
    op.create_table(
        "material_sourcing",
        *_AUDIT_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("material_id", sa.String(36), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("country_of_origin", sa.String(100), nullable=True),
        sa.Column("annual_volume", sa.Float, nullable=True),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("price_per_unit_eur", sa.Float, nullable=True),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("lead_time_days", sa.Integer, nullable=True),
        sa.Column("sourcing_risk", sa.String(10), nullable=False, server_default="MEDIUM"),
        sa.Column("certification_required", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_unique_constraint(
        "uq_mat_sourcing_material_supplier",
        "material_sourcing",
        ["organization_id", "material_id", "supplier_id"],
    )
    op.create_index("ix_msrc_material", "material_sourcing", ["material_id"])
    op.create_index("ix_msrc_supplier", "material_sourcing", ["supplier_id"])
    op.create_index("ix_msrc_org", "material_sourcing", ["organization_id"])
    op.create_index("ix_msrc_country", "material_sourcing", ["country_of_origin"])
    op.create_index("ix_msrc_risk", "material_sourcing", ["sourcing_risk"])

    # ── material_compliance_flags ─────────────────────────────────────────────
    op.create_table(
        "material_compliance_flags",
        *_AUDIT_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("material_id", sa.String(36), nullable=False),
        sa.Column("regulation", sa.String(30), nullable=False),
        sa.Column("custom_regulation_name", sa.String(200), nullable=True),
        sa.Column("compliance_status", sa.String(20), nullable=False, server_default="UNKNOWN"),
        sa.Column("assessed_at", sa.Date, nullable=True),
        sa.Column("valid_until", sa.Date, nullable=True),
        sa.Column("assessor", sa.String(300), nullable=True),
        sa.Column("evidence_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_unique_constraint(
        "uq_mat_compliance_material_reg",
        "material_compliance_flags",
        ["organization_id", "material_id", "regulation"],
    )
    op.create_index("ix_mcf_material", "material_compliance_flags", ["material_id"])
    op.create_index("ix_mcf_org", "material_compliance_flags", ["organization_id"])
    op.create_index("ix_mcf_regulation", "material_compliance_flags", ["regulation"])
    op.create_index("ix_mcf_status", "material_compliance_flags", ["compliance_status"])
    op.create_index("ix_mcf_valid_until", "material_compliance_flags", ["valid_until"])

    # ── material_sustainability_metrics ───────────────────────────────────────
    op.create_table(
        "material_sustainability_metrics",
        *_AUDIT_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("material_id", sa.String(36), nullable=False),
        sa.Column("reporting_year", sa.Integer, nullable=False),
        sa.Column("carbon_footprint_kg_co2e_per_kg", sa.Float, nullable=True),
        sa.Column("carbon_scope", sa.String(30), nullable=False, server_default="cradle_to_gate"),
        sa.Column("water_footprint_l_per_kg", sa.Float, nullable=True),
        sa.Column("energy_mj_per_kg", sa.Float, nullable=True),
        sa.Column("energy_renewable_pct", sa.Float, nullable=True),
        sa.Column("recycled_content_pct", sa.Float, nullable=True),
        sa.Column("recyclability_pct", sa.Float, nullable=True),
        sa.Column("biodegradable", sa.Boolean, nullable=True),
        sa.Column("data_source", sa.String(300), nullable=True),
        sa.Column("is_third_party_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("verification_standard", sa.String(100), nullable=True),
        sa.Column("evidence_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_unique_constraint(
        "uq_mat_sustain_material_year",
        "material_sustainability_metrics",
        ["organization_id", "material_id", "reporting_year"],
    )
    op.create_index("ix_msus_material", "material_sustainability_metrics", ["material_id"])
    op.create_index("ix_msus_org", "material_sustainability_metrics", ["organization_id"])
    op.create_index("ix_msus_year", "material_sustainability_metrics", ["reporting_year"])


def downgrade() -> None:
    op.drop_table("material_sustainability_metrics")
    op.drop_table("material_compliance_flags")
    op.drop_table("material_sourcing")
    op.drop_table("material_compositions")
    op.drop_table("materials")
