"""Add chunk_comments table for P2-D annotations

Revision ID: 127
Revises: 126
Create Date: 2026-07-16
"""
from alembic import op
import sqlalchemy as sa

revision = "127"
down_revision = "126"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chunk_comments",
        sa.Column("id", sa.String(), primary_key=True, server_default=sa.text("gen_random_uuid()::text")),
        sa.Column("chunk_id", sa.String(), sa.ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_chunk_comments_chunk", "chunk_comments", ["chunk_id"])
    op.create_index("idx_chunk_comments_org", "chunk_comments", ["organization_id"])


def downgrade() -> None:
    op.drop_index("idx_chunk_comments_org")
    op.drop_index("idx_chunk_comments_chunk")
    op.drop_table("chunk_comments")
