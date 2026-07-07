"""CSDDD Sector Risk Register — TASK-003 Phase 2 tables.

Creates three tables:
  sector_right_scores       — approved probability scores per NACE × CSDDD right
  calibration_suggestions   — RAG-generated score suggestions pending Founder review
  scenario_suggestions      — news-triggered scenario suggestions pending confirmation

Revision ID: 075
Revises: 074
Create Date: 2026-07-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "075"
down_revision: str | None = "074"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── sector_right_scores ────────────────────────────────────────────────
    op.create_table(
        "sector_right_scores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=True),
        # Sector identifier
        sa.Column("nace_2digit", sa.String(4), nullable=False),
        # CSDDD right (CSDDDRight enum value)
        sa.Column("csddd_right", sa.String(64), nullable=False),
        # Score
        sa.Column("probability", sa.Integer, nullable=False),  # 1–10
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("sources", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("calibration_version", sa.String(20), nullable=False, server_default="v1.0"),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_sector_right_scores_nace_right",
        "sector_right_scores",
        ["nace_2digit", "csddd_right"],
    )
    op.create_index(
        "ix_sector_right_scores_org",
        "sector_right_scores",
        ["organization_id"],
    )

    # ── calibration_suggestions ────────────────────────────────────────────
    op.create_table(
        "calibration_suggestions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("nace_2digit", sa.String(4), nullable=False),
        sa.Column("csddd_right", sa.String(64), nullable=False),
        sa.Column("suggested_probability", sa.Integer, nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("reasoning", sa.Text, nullable=False, server_default=""),
        sa.Column("sources", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_calibration_suggestions_status",
        "calibration_suggestions",
        ["status"],
    )

    # ── scenario_suggestions ───────────────────────────────────────────────
    op.create_table(
        "scenario_suggestions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("scenario_type", sa.String(64), nullable=False),
        sa.Column("affected_nace_codes", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("trigger_article_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("trigger_keywords_matched", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("sample_headlines", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("activated_by", sa.String(36), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_scenario_suggestions_type_status",
        "scenario_suggestions",
        ["scenario_type", "status"],
    )


def downgrade() -> None:
    op.drop_table("scenario_suggestions")
    op.drop_table("calibration_suggestions")
    op.drop_table("sector_right_scores")
