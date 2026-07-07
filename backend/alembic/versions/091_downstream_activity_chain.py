"""CSDDD-005 — Downstream Activity Chain (Art. 2/3)

Revision ID: 091
Revises: 090
Create Date: 2026-07-05

Adds chain_direction and downstream_type to suppliers table.
Existing rows default to 'upstream' (all historical suppliers are upstream).
"""

import sqlalchemy as sa

from alembic import op

revision = "091"
down_revision = "090"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "suppliers",
        sa.Column("chain_direction", sa.String(20), nullable=False, server_default="upstream"),
    )
    op.add_column(
        "suppliers",
        sa.Column("downstream_type", sa.String(50), nullable=True),
    )
    op.create_index("ix_suppliers_chain_direction", "suppliers", ["chain_direction"])


def downgrade() -> None:
    op.drop_index("ix_suppliers_chain_direction", table_name="suppliers")
    op.drop_column("suppliers", "downstream_type")
    op.drop_column("suppliers", "chain_direction")
