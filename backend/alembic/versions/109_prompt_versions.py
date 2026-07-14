"""ADR-011: Prompt Versioning — prompt_versions table.

Revision ID: 109
Revises: 108
Create Date: 2026-07-09

Seeds the two existing hardcoded prompts from metric_extractor.py as version 1.
These are the source-of-truth prompts from the codebase at migration time.

NOTE: This migration is NOT executed automatically.
Run manually: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "109"
down_revision = "108"
branch_labels = None
depends_on = None

_NOW = sa.func.now()


def upgrade() -> None:
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("prompt_name", sa.String(128), nullable=False, index=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("template", sa.Text, nullable=False),
        sa.Column("variables", JSONB, nullable=False, server_default="[]"),
        sa.Column("active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("prompt_name", "version", name="uq_prompt_name_version"),
    )
    op.create_index("ix_prompt_name_active", "prompt_versions", ["prompt_name", "active"])

    # Seed existing hardcoded prompts from metric_extractor.py as v1
    op.execute(
        sa.text("""
        INSERT INTO prompt_versions (prompt_name, version, template, variables, active)
        VALUES
        (
            'financial_extraction_system',
            1,
            'You are a financial data extraction specialist. Extract key financial metrics from the document text.',
            '[]',
            true
        ),
        (
            'esg_extraction_system',
            1,
            'You are an ESG data extraction specialist. Extract sustainability metrics and targets from the document.',
            '[]',
            true
        )
        """)
    )


def downgrade() -> None:
    op.drop_index("ix_prompt_name_active", table_name="prompt_versions")
    op.drop_table("prompt_versions")
