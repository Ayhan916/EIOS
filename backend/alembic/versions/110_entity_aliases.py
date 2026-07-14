"""E2-F3: entity_aliases table for EntityLinker (ADR-013).

Revision ID: 110
Revises: 109
Create Date: 2026-07-09

NOTE: This migration is NOT executed automatically.
Run manually: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa

revision = "110"
down_revision = "109"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entity_aliases",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "supplier_id",
            sa.String(36),
            sa.ForeignKey("suppliers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(256), nullable=False),
        sa.Column("alias_confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("source", sa.String(64), nullable=True),
        sa.UniqueConstraint("supplier_id", "alias", name="uq_entity_alias"),
    )
    op.create_index("ix_entity_alias_supplier", "entity_aliases", ["supplier_id"])
    op.create_index("ix_entity_alias_alias", "entity_aliases", ["alias"])


def downgrade() -> None:
    op.drop_index("ix_entity_alias_alias", table_name="entity_aliases")
    op.drop_index("ix_entity_alias_supplier", table_name="entity_aliases")
    op.drop_table("entity_aliases")
