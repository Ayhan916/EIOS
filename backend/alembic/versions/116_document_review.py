"""Document Review: parsed_text, review_status, review_notes, audit log table.

Revision ID: 116
Revises: 115
Create Date: 2026-07-14

Adds to document_files:
  parsed_text    TEXT         — full extracted markdown stored after parsing
  review_status  VARCHAR(16)  — draft | in_review | approved  (default: draft)
  review_notes   TEXT         — free-text QA notes

Creates document_review_log table for audit trail of manual changes.
"""

from alembic import op
import sqlalchemy as sa

revision = "116"
down_revision = "115"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_files", sa.Column("parsed_text", sa.Text, nullable=True))
    op.add_column("document_files", sa.Column("review_status", sa.String(16), nullable=False, server_default="draft"))
    op.add_column("document_files", sa.Column("review_notes", sa.Text, nullable=True))

    op.create_table(
        "document_review_log",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("doc_file_id", sa.String, sa.ForeignKey("document_files.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("organization_id", sa.String, nullable=False, index=True),
        sa.Column("user_id", sa.String, nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("field", sa.String(64), nullable=True),
        sa.Column("old_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("document_review_log")
    op.drop_column("document_files", "review_notes")
    op.drop_column("document_files", "review_status")
    op.drop_column("document_files", "parsed_text")
