"""097 — Supplier Self-Assessment CSDDD (CSDDD-015 Art. 10 Abs. 2 lit. a).

Tables created:
  - assessment_templates
  - assessment_questions
  - supplier_assessments
  - assessment_responses

Revision ID: 097
Revises: 096
Create Date: 2026-07-06
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "097"
down_revision = "096"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessment_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_assessment_templates_org", "assessment_templates", ["organization_id"])

    op.create_table(
        "assessment_questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "template_id",
            sa.String(36),
            sa.ForeignKey("assessment_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section", sa.String(30), nullable=False),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("question_type", sa.String(20), nullable=False, server_default="yes_no"),
        sa.Column("options_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("csddd_article", sa.String(50), nullable=False, server_default="Art. 10"),
        sa.Column("weight", sa.Integer, nullable=False, server_default="3"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_assessment_questions_template", "assessment_questions", ["template_id"])
    op.create_index("ix_assessment_questions_section", "assessment_questions", ["section"])

    op.create_table(
        "supplier_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "template_id", sa.String(36), sa.ForeignKey("assessment_templates.id"), nullable=False
        ),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("reference_code", sa.String(20), nullable=False),
        sa.Column("submitted_by_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_supplier_assessments_org", "supplier_assessments", ["organization_id"])
    op.create_index(
        "ix_supplier_assessments_org_status", "supplier_assessments", ["organization_id", "status"]
    )
    op.create_index("ix_supplier_assessments_supplier", "supplier_assessments", ["supplier_id"])
    op.create_index("ix_supplier_assessments_token_hash", "supplier_assessments", ["token_hash"])

    op.create_table(
        "assessment_responses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "assessment_id",
            sa.String(36),
            sa.ForeignKey("supplier_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id", sa.String(36), sa.ForeignKey("assessment_questions.id"), nullable=False
        ),
        sa.Column("answer_value", sa.Text, nullable=False, server_default=""),
        sa.Column("answered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_assessment_responses_assessment", "assessment_responses", ["assessment_id"])


def downgrade() -> None:
    op.drop_table("assessment_responses")
    op.drop_table("supplier_assessments")
    op.drop_table("assessment_questions")
    op.drop_table("assessment_templates")
