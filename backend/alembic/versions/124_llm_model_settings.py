"""Add llm_model_settings to organization_settings.

Revision ID: 124
Revises: 123
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "124"
down_revision = "123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organization_settings",
        sa.Column("llm_model_settings", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organization_settings", "llm_model_settings")
