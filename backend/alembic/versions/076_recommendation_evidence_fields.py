"""recommendation evidence fields (GAP-06)

Revision ID: 076
Revises: 075
Create Date: 2026-07-03
"""

from alembic import op
import sqlalchemy as sa

revision = "076"
down_revision = "075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("recommendations", sa.Column("expected_benefit", sa.Text(), nullable=True))
    op.add_column("recommendations", sa.Column("expected_risk", sa.Text(), nullable=True))
    op.add_column("recommendations", sa.Column("expected_roi", sa.Text(), nullable=True))
    op.add_column(
        "recommendations",
        sa.Column("implementation_complexity", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recommendations", "implementation_complexity")
    op.drop_column("recommendations", "expected_roi")
    op.drop_column("recommendations", "expected_risk")
    op.drop_column("recommendations", "expected_benefit")
