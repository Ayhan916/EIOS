"""M30.1: Add payload column to webhook_deliveries for recovery worker

Revision ID: 023
Revises: 022
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "webhook_deliveries",
        sa.Column("payload", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("webhook_deliveries", "payload")
