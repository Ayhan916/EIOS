"""m33_1_copilot_hardening

M33.1 — Copilot Auditability & Conversation Hardening.

Adds full audit snapshot columns to copilot_messages so every assistant
response is permanently reproducible from stored data.

Revision ID: 031
Revises: 030
Create Date: 2026-06-19
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "copilot_messages",
        sa.Column("retrieval_snapshot", postgresql.JSON, nullable=True),
    )
    op.add_column(
        "copilot_messages",
        sa.Column("assembled_context", sa.Text, nullable=True),
    )
    op.add_column(
        "copilot_messages",
        sa.Column("system_prompt_snapshot", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("copilot_messages", "system_prompt_snapshot")
    op.drop_column("copilot_messages", "assembled_context")
    op.drop_column("copilot_messages", "retrieval_snapshot")
