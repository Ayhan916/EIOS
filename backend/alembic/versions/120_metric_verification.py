"""metric verification columns

Revision ID: 120
Revises: 119
Create Date: 2026-07-15
"""

import sqlalchemy as sa
from alembic import op

revision = "120"
down_revision = "119"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("company_metrics", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("company_metrics", sa.Column("reference_value", sa.Numeric(20, 4), nullable=True))
    op.add_column("company_metrics", sa.Column("reference_source", sa.String(128), nullable=True))
    op.add_column("company_metrics", sa.Column("reference_url", sa.String(512), nullable=True))
    op.add_column("company_metrics", sa.Column("verification_note", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("company_metrics", "verification_note")
    op.drop_column("company_metrics", "reference_url")
    op.drop_column("company_metrics", "reference_source")
    op.drop_column("company_metrics", "reference_value")
    op.drop_column("company_metrics", "is_verified")
