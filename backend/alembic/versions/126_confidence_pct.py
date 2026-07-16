"""Add confidence_pct to company_metrics

Revision ID: 126
Revises: 125
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa

revision = "126"
down_revision = "125"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "company_metrics",
        sa.Column("confidence_pct", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("company_metrics", "confidence_pct")
