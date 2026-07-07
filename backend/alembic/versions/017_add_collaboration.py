"""add collaboration review workflow and comments (M26)

Revision ID: 017
Revises: 016
Create Date: 2026-06-18

Adds:
  - comments table (polymorphic: Assessment/Finding/Risk/Recommendation)
  - review_actions table (formal governance decisions)
  - assessments.review_status VARCHAR(30)
  - assessments.assigned_reviewer_id VARCHAR(36)
  - assessments.review_due_date TIMESTAMP WITH TIME ZONE
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "017"
down_revision: str | None = "016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── comments ──────────────────────────────────────────────────────────────
    op.create_table(
        "comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, default="Active"),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column(
            "author_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mentioned_user_ids", sa.Text, nullable=True),
    )
    op.create_index("ix_comments_entity", "comments", ["entity_type", "entity_id"])
    op.create_index("ix_comments_author", "comments", ["author_id"])

    # ── review_actions ────────────────────────────────────────────────────────
    op.create_table(
        "review_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, default="Active"),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "assessment_id",
            sa.String(36),
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor_email", sa.String(254), nullable=False),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
    )
    op.create_index("ix_review_actions_assessment", "review_actions", ["assessment_id"])
    op.create_index("ix_review_actions_actor", "review_actions", ["actor_id"])

    # ── assessments review workflow columns ───────────────────────────────────
    op.add_column(
        "assessments",
        sa.Column("review_status", sa.String(30), nullable=False, server_default="Draft"),
    )
    op.add_column(
        "assessments",
        sa.Column("assigned_reviewer_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "assessments",
        sa.Column("review_due_date", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessments", "review_due_date")
    op.drop_column("assessments", "assigned_reviewer_id")
    op.drop_column("assessments", "review_status")
    op.drop_index("ix_review_actions_actor", table_name="review_actions")
    op.drop_index("ix_review_actions_assessment", table_name="review_actions")
    op.drop_table("review_actions")
    op.drop_index("ix_comments_author", table_name="comments")
    op.drop_index("ix_comments_entity", table_name="comments")
    op.drop_table("comments")
