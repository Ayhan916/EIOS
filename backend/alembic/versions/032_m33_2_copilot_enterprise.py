"""m33_2_copilot_enterprise

M33.2 — Copilot Enterprise Hardening & Audit Excellence.

Changes:
  copilot_messages — add 6 columns:
    confidence_level, confidence_factors, contradiction_count,
    context_budget_used, context_truncated, freshness_summary

New tables:
  copilot_contradictions   — pre-LLM contradiction records
  copilot_citation_integrity — per-citation integrity records
  copilot_feedback         — user feedback on answers
  copilot_answer_reviews   — executive review decisions
  copilot_audit_packages   — immutable audit packages

Revision ID: 032
Revises: 031
Create Date: 2026-06-19
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "032"
down_revision = "031"
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
    # ── Extend copilot_messages ──────────────────────────────────────────────
    op.add_column("copilot_messages", sa.Column("confidence_level", sa.String(20), nullable=True))
    op.add_column(
        "copilot_messages", sa.Column("confidence_factors", postgresql.JSON, nullable=True)
    )
    op.add_column("copilot_messages", sa.Column("contradiction_count", sa.Integer, nullable=True))
    op.add_column("copilot_messages", sa.Column("context_budget_used", sa.Integer, nullable=True))
    op.add_column("copilot_messages", sa.Column("context_truncated", sa.Boolean, nullable=True))
    op.add_column(
        "copilot_messages", sa.Column("freshness_summary", postgresql.JSON, nullable=True)
    )

    # ── copilot_contradictions ───────────────────────────────────────────────
    op.create_table(
        "copilot_contradictions",
        *_BASE_COLS,
        sa.Column("message_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("contradiction_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("involved_objects", postgresql.JSON, nullable=False, server_default="[]"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_copilot_contradictions_msg", "copilot_contradictions", ["message_id"])
    op.create_index("ix_copilot_contradictions_org", "copilot_contradictions", ["organization_id"])

    # ── copilot_citation_integrity ───────────────────────────────────────────
    op.create_table(
        "copilot_citation_integrity",
        *_BASE_COLS,
        sa.Column("message_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("citation_type", sa.String(30), nullable=False),
        sa.Column("object_id", sa.String(36), nullable=False),
        sa.Column("integrity_status", sa.String(20), nullable=False),
        sa.Column("citation_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("citation_snapshot", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_copilot_citation_integrity_msg", "copilot_citation_integrity", ["message_id"]
    )
    op.create_index(
        "ix_copilot_citation_integrity_org", "copilot_citation_integrity", ["organization_id"]
    )

    # ── copilot_feedback ─────────────────────────────────────────────────────
    op.create_table(
        "copilot_feedback",
        *_BASE_COLS,
        sa.Column("message_id", sa.String(36), nullable=False),
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("rating", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text, nullable=False, server_default=""),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_copilot_feedback_msg", "copilot_feedback", ["message_id"])
    op.create_index("ix_copilot_feedback_org", "copilot_feedback", ["organization_id"])

    # ── copilot_answer_reviews ───────────────────────────────────────────────
    op.create_table(
        "copilot_answer_reviews",
        *_BASE_COLS,
        sa.Column("message_id", sa.String(36), nullable=False),
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("reviewer_id", sa.String(36), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_copilot_reviews_msg", "copilot_answer_reviews", ["message_id"])
    op.create_index("ix_copilot_reviews_org", "copilot_answer_reviews", ["organization_id"])

    # ── copilot_audit_packages ───────────────────────────────────────────────
    op.create_table(
        "copilot_audit_packages",
        *_BASE_COLS,
        sa.Column("message_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("package_hash", sa.String(64), nullable=False),
        sa.Column("json_payload", postgresql.JSON, nullable=False, server_default="{}"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_copilot_audit_packages_msg", "copilot_audit_packages", ["message_id"])
    op.create_index("ix_copilot_audit_packages_org", "copilot_audit_packages", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_copilot_audit_packages_org", "copilot_audit_packages")
    op.drop_index("ix_copilot_audit_packages_msg", "copilot_audit_packages")
    op.drop_table("copilot_audit_packages")

    op.drop_index("ix_copilot_reviews_org", "copilot_answer_reviews")
    op.drop_index("ix_copilot_reviews_msg", "copilot_answer_reviews")
    op.drop_table("copilot_answer_reviews")

    op.drop_index("ix_copilot_feedback_org", "copilot_feedback")
    op.drop_index("ix_copilot_feedback_msg", "copilot_feedback")
    op.drop_table("copilot_feedback")

    op.drop_index("ix_copilot_citation_integrity_org", "copilot_citation_integrity")
    op.drop_index("ix_copilot_citation_integrity_msg", "copilot_citation_integrity")
    op.drop_table("copilot_citation_integrity")

    op.drop_index("ix_copilot_contradictions_org", "copilot_contradictions")
    op.drop_index("ix_copilot_contradictions_msg", "copilot_contradictions")
    op.drop_table("copilot_contradictions")

    op.drop_column("copilot_messages", "freshness_summary")
    op.drop_column("copilot_messages", "context_truncated")
    op.drop_column("copilot_messages", "context_budget_used")
    op.drop_column("copilot_messages", "contradiction_count")
    op.drop_column("copilot_messages", "confidence_factors")
    op.drop_column("copilot_messages", "confidence_level")
