"""M34.2 External Intelligence Hardening.

Adds trigger_source and initiated_by_user_id to connector_runs table.

Revision ID: 035
Revises: 034
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "connector_runs",
        sa.Column(
            "trigger_source",
            sa.String(20),
            nullable=False,
            server_default="scheduler",
        ),
    )
    op.add_column(
        "connector_runs",
        sa.Column(
            "initiated_by_user_id",
            sa.String(36),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("connector_runs", "initiated_by_user_id")
    op.drop_column("connector_runs", "trigger_source")
