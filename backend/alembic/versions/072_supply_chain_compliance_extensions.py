"""M7 Supply Chain Compliance Extensions — product_compliance_scans table.

Revision ID: 072
Revises: 071
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

from alembic import op

revision = "072"
down_revision = "071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_compliance_scans",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("regulation_code", sa.String(50), nullable=False),
        sa.Column("scan_result", sa.String(20), nullable=False, server_default="UNKNOWN"),
        sa.Column("total_materials", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("compliant_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("non_compliant_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unknown_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("flagged_material_ids", JSON, nullable=False, server_default="[]"),
        sa.Column("scan_version", sa.String(10), nullable=False, server_default="1.0"),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scanned_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_pcs_org", "product_compliance_scans", ["organization_id"])
    op.create_index("ix_pcs_product", "product_compliance_scans", ["product_id"])
    op.create_index("ix_pcs_regulation", "product_compliance_scans", ["regulation_code"])
    op.create_index("ix_pcs_result", "product_compliance_scans", ["scan_result"])


def downgrade() -> None:
    op.drop_index("ix_pcs_result", table_name="product_compliance_scans")
    op.drop_index("ix_pcs_regulation", table_name="product_compliance_scans")
    op.drop_index("ix_pcs_product", table_name="product_compliance_scans")
    op.drop_index("ix_pcs_org", table_name="product_compliance_scans")
    op.drop_table("product_compliance_scans")
