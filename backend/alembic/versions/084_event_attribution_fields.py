"""GAP-10: Add esg_category, protected_right, frequency to external_risk_signals

Revision ID: 084
Revises: 083
Create Date: 2026-07-04
"""

from alembic import op
import sqlalchemy as sa

revision = "084"
down_revision = "083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("external_risk_signals", sa.Column("esg_category", sa.String(20), nullable=True))
    op.add_column("external_risk_signals", sa.Column("protected_right", sa.String(60), nullable=True))
    op.add_column("external_risk_signals", sa.Column("frequency", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("external_risk_signals", "frequency")
    op.drop_column("external_risk_signals", "protected_right")
    op.drop_column("external_risk_signals", "esg_category")
