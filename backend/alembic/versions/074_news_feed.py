"""News Feed — news_articles + news_supplier_assignments tables.

Revision ID: 074
Revises: 073
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "074"
down_revision = "073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "news_articles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("source_name", sa.String(200), nullable=True),
        sa.Column("image_url", sa.Text, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("translated_title", sa.Text, nullable=True),
        sa.Column("translated_summary", sa.Text, nullable=True),
        sa.Column("match_type", sa.String(20), nullable=False, server_default="supplier"),
        sa.Column("match_query", sa.String(500), nullable=True),
    )
    op.create_index("ix_news_articles_org_fetched", "news_articles", ["organization_id", "fetched_at"])
    op.create_index("ix_news_articles_published", "news_articles", ["published_at"])

    op.create_table(
        "news_supplier_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("article_id", sa.String(36), sa.ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False, index=True),
        sa.Column("match_reason", sa.String(20), nullable=False),
    )
    op.create_index("ix_news_assign_article", "news_supplier_assignments", ["article_id"])
    op.create_index("ix_news_assign_supplier", "news_supplier_assignments", ["supplier_id"])


def downgrade() -> None:
    op.drop_table("news_supplier_assignments")
    op.drop_table("news_articles")
