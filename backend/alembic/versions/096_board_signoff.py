"""096 — Board Sign-off Trail (CSDDD Art. 22).

Tables created:
  - board_signoff_requests
  - board_decisions

Revision ID: 096
Revises: 095
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "096"
down_revision = "095"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "board_signoff_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("signoff_type", sa.String(30), nullable=False, server_default="other"),
        sa.Column("entity_type", sa.String(30), nullable=True),
        sa.Column("entity_id", sa.String(36), nullable=True),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_by_role", sa.String(30), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("document_ref", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_board_signoff_requests_org", "board_signoff_requests", ["organization_id"])
    op.create_index("ix_board_signoff_requests_org_status", "board_signoff_requests", ["organization_id", "status"])
    op.create_index("ix_board_signoff_requests_org_type", "board_signoff_requests", ["organization_id", "signoff_type"])

    op.create_table(
        "board_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("request_id", sa.String(36), sa.ForeignKey("board_signoff_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("decided_by", sa.String(255), nullable=False),
        sa.Column("decided_by_role", sa.String(30), nullable=False, server_default="board_member"),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_board_decisions_org", "board_decisions", ["organization_id"])
    op.create_index("ix_board_decisions_request", "board_decisions", ["request_id"])


def downgrade() -> None:
    op.drop_table("board_decisions")
    op.drop_table("board_signoff_requests")
