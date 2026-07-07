"""086 — CSDDD-001 Stakeholder Engagement tables (Art. 13).

Revision ID: 086
Revises: 085
Create Date: 2026-07-05
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "086"
down_revision = "085"
branch_labels = None
depends_on = None

BASE_COLS = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, default="Draft"),
    sa.Column("version", sa.Integer, nullable=False, default=1),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
]


def upgrade() -> None:
    op.create_table(
        "stakeholders",
        *BASE_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("stakeholder_type", sa.String(50), nullable=False, default="other"),
        sa.Column("contact_email", sa.String(320), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, default="de"),
        sa.Column("activity_chain_ids", sa.Text, nullable=False, default="[]"),
        sa.Column("regions", sa.Text, nullable=False, default="[]"),
        sa.Column("risk_topics", sa.Text, nullable=False, default="[]"),
        sa.Column("justification", sa.Text, nullable=False, default=""),
    )
    op.create_index("ix_stakeholders_org", "stakeholders", ["organization_id"])

    op.create_table(
        "stakeholder_consultations",
        *BASE_COLS,
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("stakeholder_ids", sa.Text, nullable=False, default="[]"),
        sa.Column("consultation_date", sa.Date, nullable=True),
        sa.Column("format", sa.String(50), nullable=False, default="meeting"),
        sa.Column("topics", sa.Text, nullable=False, default="[]"),
        sa.Column("description", sa.Text, nullable=False, default=""),
        sa.Column("outcomes", sa.Text, nullable=False, default=""),
        sa.Column("barrier", sa.String(50), nullable=False, default="none"),
        sa.Column("barrier_notes", sa.Text, nullable=False, default=""),
        sa.Column("linked_risk_id", sa.String(36), nullable=True),
        sa.Column("linked_finding_id", sa.String(36), nullable=True),
        sa.Column("linked_cap_id", sa.String(36), nullable=True),
    )
    op.create_index(
        "ix_stakeholder_consultations_org", "stakeholder_consultations", ["organization_id"]
    )
    op.create_index(
        "ix_stakeholder_consultations_date",
        "stakeholder_consultations",
        ["organization_id", "consultation_date"],
    )

    op.create_table(
        "stakeholder_feedback",
        *BASE_COLS,
        sa.Column("consultation_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("risk_assessment", sa.SmallInteger, nullable=False, default=3),
        sa.Column("affected_rights", sa.Text, nullable=False, default="[]"),
        sa.Column("description", sa.Text, nullable=False, default=""),
        sa.Column("wants_contact", sa.Boolean, nullable=False, default=False),
        sa.Column("submitted_by_email", sa.String(320), nullable=True),
        sa.Column("submitted_by_name", sa.String(500), nullable=True),
        sa.Column("submitter_ip", sa.String(45), nullable=True),
    )
    op.create_index(
        "ix_stakeholder_feedback_consultation", "stakeholder_feedback", ["consultation_id"]
    )
    op.create_index("ix_stakeholder_feedback_org", "stakeholder_feedback", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_stakeholder_feedback_org", "stakeholder_feedback")
    op.drop_index("ix_stakeholder_feedback_consultation", "stakeholder_feedback")
    op.drop_table("stakeholder_feedback")

    op.drop_index("ix_stakeholder_consultations_date", "stakeholder_consultations")
    op.drop_index("ix_stakeholder_consultations_org", "stakeholder_consultations")
    op.drop_table("stakeholder_consultations")

    op.drop_index("ix_stakeholders_org", "stakeholders")
    op.drop_table("stakeholders")
