"""100 — commodity supplier fields

Adds supplier_type, commodity, commodity_code to suppliers table.
"""

from alembic import op
import sqlalchemy as sa

revision = "100"
down_revision = "099"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "suppliers",
        sa.Column("supplier_type", sa.String(30), nullable=False, server_default="manufacturing"),
    )
    op.add_column(
        "suppliers",
        sa.Column("commodity", sa.String(100), nullable=True),
    )
    op.add_column(
        "suppliers",
        sa.Column("commodity_code", sa.String(20), nullable=True),
    )
    op.create_index("ix_suppliers_supplier_type", "suppliers", ["supplier_type"])
    op.create_index("ix_suppliers_commodity_code", "suppliers", ["commodity_code"])


def downgrade() -> None:
    op.drop_index("ix_suppliers_commodity_code", table_name="suppliers")
    op.drop_index("ix_suppliers_supplier_type", table_name="suppliers")
    op.drop_column("suppliers", "commodity_code")
    op.drop_column("suppliers", "commodity")
    op.drop_column("suppliers", "supplier_type")
