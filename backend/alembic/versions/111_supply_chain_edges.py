"""E5-F3: supply_chain_edges table for Tier-2/3 graph traversal.

Revision ID: 111
Revises: 110
Create Date: 2026-07-09

NOTE: This migration is NOT executed automatically.
Run manually: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa

revision = "111"
down_revision = "110"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supply_chain_edges",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "buyer_id",
            sa.String(36),
            sa.ForeignKey("suppliers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "supplier_id",
            sa.String(36),
            sa.ForeignKey("suppliers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tier", sa.Integer, nullable=False),
        sa.Column("commodity_code", sa.String(64), nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.UniqueConstraint("buyer_id", "supplier_id", name="uq_supply_chain_edge"),
    )
    op.create_index("ix_sce_buyer_id", "supply_chain_edges", ["buyer_id"])
    op.create_index("ix_sce_supplier_id", "supply_chain_edges", ["supplier_id"])
    op.create_index("ix_sce_tier", "supply_chain_edges", ["tier"])


def downgrade() -> None:
    op.drop_index("ix_sce_tier", table_name="supply_chain_edges")
    op.drop_index("ix_sce_supplier_id", table_name="supply_chain_edges")
    op.drop_index("ix_sce_buyer_id", table_name="supply_chain_edges")
    op.drop_table("supply_chain_edges")
