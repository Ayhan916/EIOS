"""m33_copilot

M33 — AI Sustainability Copilot.

Creates:
  copilot_conversations — persistent conversation threads (tenant-isolated)
  copilot_messages      — individual messages with full audit trail

Revision ID: 030
Revises: 029
Create Date: 2026-06-19
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None

_BASE_COLS = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
]


def upgrade() -> None:
    op.create_table(
        "copilot_conversations",
        *_BASE_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default=""),
        sa.Column("context_type", sa.String(30), nullable=False, server_default="general"),
        sa.Column("context_id", sa.String(36), nullable=True),
        sa.Column("message_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_copilot_convs_org", "copilot_conversations", ["organization_id"])
    op.create_index("ix_copilot_convs_user", "copilot_conversations", ["user_id"])
    op.create_index(
        "ix_copilot_convs_org_user",
        "copilot_conversations",
        ["organization_id", "user_id"],
    )

    op.create_table(
        "copilot_messages",
        *_BASE_COLS,
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("intent", sa.String(30), nullable=False, server_default=""),
        sa.Column("citations", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("retrieved_sources", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("model_used", sa.String(100), nullable=False, server_default=""),
        sa.Column("generation_ms", sa.Integer, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_copilot_messages_conv", "copilot_messages", ["conversation_id"])
    op.create_index("ix_copilot_messages_org", "copilot_messages", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_copilot_messages_org", "copilot_messages")
    op.drop_index("ix_copilot_messages_conv", "copilot_messages")
    op.drop_table("copilot_messages")

    op.drop_index("ix_copilot_convs_org_user", "copilot_conversations")
    op.drop_index("ix_copilot_convs_user", "copilot_conversations")
    op.drop_index("ix_copilot_convs_org", "copilot_conversations")
    op.drop_table("copilot_conversations")
