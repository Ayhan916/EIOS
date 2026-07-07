"""M8 Scope 3 Supply Chain Carbon Inventory — product_carbon_footprints + scope3_inventories.

Revision ID: 073
Revises: 072
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

from alembic import op

revision = "073"
down_revision = "072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_carbon_footprints",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("reporting_year", sa.Integer(), nullable=False),
        sa.Column("pcf_kg_co2e_per_unit", sa.Float(), nullable=True),
        sa.Column("pcf_source", sa.String(30), nullable=False, server_default="computed"),
        sa.Column("bom_materials_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bom_materials_with_lca", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weight_coverage_pct", sa.Float(), nullable=True),
        sa.Column("material_breakdown", JSON, nullable=False, server_default="[]"),
        sa.Column("calc_version", sa.String(10), nullable=False, server_default="1.0"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("calculated_by", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_pcf_org", "product_carbon_footprints", ["organization_id"])
    op.create_index("ix_pcf_product", "product_carbon_footprints", ["product_id"])
    op.create_index("ix_pcf_year", "product_carbon_footprints", ["reporting_year"])
    op.create_index("ix_pcf_result", "product_carbon_footprints", ["pcf_kg_co2e_per_unit"])

    op.create_table(
        "scope3_inventories",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("reporting_year", sa.Integer(), nullable=False),
        sa.Column("total_pcf_kg_co2e", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_pcf_tco2e", sa.Float(), nullable=False, server_default="0"),
        sa.Column("products_included", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("products_with_full_lca", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("products_with_partial_lca", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("products_without_lca", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("top_contributors", JSON, nullable=False, server_default="[]"),
        sa.Column("calc_version", sa.String(10), nullable=False, server_default="1.0"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("calculated_by", sa.String(36), nullable=True),
        sa.UniqueConstraint(
            "organization_id", "reporting_year", name="uq_scope3_inventory_org_year"
        ),
    )
    op.create_index("ix_scope3_inv_org", "scope3_inventories", ["organization_id"])
    op.create_index("ix_scope3_inv_year", "scope3_inventories", ["reporting_year"])


def downgrade() -> None:
    op.drop_index("ix_scope3_inv_year", table_name="scope3_inventories")
    op.drop_index("ix_scope3_inv_org", table_name="scope3_inventories")
    op.drop_table("scope3_inventories")

    op.drop_index("ix_pcf_result", table_name="product_carbon_footprints")
    op.drop_index("ix_pcf_year", table_name="product_carbon_footprints")
    op.drop_index("ix_pcf_product", table_name="product_carbon_footprints")
    op.drop_index("ix_pcf_org", table_name="product_carbon_footprints")
    op.drop_table("product_carbon_footprints")
