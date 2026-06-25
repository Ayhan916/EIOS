"""Add missing columns to carbon_inventories (last_calculated_at, recalculation_count).

These columns exist in the ORM model (CarbonInventoryModel) but were omitted from
migration 046 when the table was first created.

Revision ID: 051
Revises: 050
Create Date: 2026-06-22
"""

import sqlalchemy as sa
from alembic import op

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE carbon_inventories "
        "ADD COLUMN IF NOT EXISTS last_calculated_at TIMESTAMP WITH TIME ZONE"
    )
    op.execute(
        "ALTER TABLE carbon_inventories "
        "ADD COLUMN IF NOT EXISTS recalculation_count INTEGER NOT NULL DEFAULT 0"
    )


def downgrade() -> None:
    op.drop_column("carbon_inventories", "recalculation_count")
    op.drop_column("carbon_inventories", "last_calculated_at")
