"""Add page_number and scope to company_metrics

Revision ID: 121_metric_page_scope
Revises: 120_metric_verification
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa

revision = "121"
down_revision = "120"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("company_metrics", sa.Column("page_number", sa.Integer(), nullable=True))
    op.add_column("company_metrics", sa.Column("scope", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("company_metrics", "scope")
    op.drop_column("company_metrics", "page_number")
