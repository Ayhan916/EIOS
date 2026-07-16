"""Add pipeline_settings to organization_settings.

Revision ID: 125
Revises: 124
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "125"
down_revision = "124"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organization_settings",
        sa.Column("pipeline_settings", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organization_settings", "pipeline_settings")
