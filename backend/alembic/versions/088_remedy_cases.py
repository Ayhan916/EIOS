"""CSDDD-004 — Remedy Case Manager (Art. 12)

Revision ID: 088
Revises: 087
Create Date: 2026-07-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "088"
down_revision = "087"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "remedy_cases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("incident_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("affected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("affected_type", sa.String(50), nullable=False),
        sa.Column("rights", sa.Text(), nullable=True),
        sa.Column("remedy_types", sa.Text(), nullable=True),
        sa.Column("severity_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("impact_causation", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("source_grievance_id", UUID(as_uuid=True), nullable=True),
        sa.Column("co_responsible_parties", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.String(255), nullable=True),
        sa.Column("closure_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "remedy_beneficiaries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "remedy_case_id",
            UUID(as_uuid=True),
            sa.ForeignKey("remedy_cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("reference", sa.String(255), nullable=False),
        sa.Column("affected_type", sa.String(50), nullable=False),
        sa.Column("promised_compensation", sa.Float(), nullable=True),
        sa.Column("received_compensation", sa.Float(), nullable=True),
        sa.Column("confirmation_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "remedy_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "remedy_case_id",
            UUID(as_uuid=True),
            sa.ForeignKey("remedy_cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="todo"),
        sa.Column("responsible_party", sa.String(255), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "remedy_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "remedy_case_id",
            UUID(as_uuid=True),
            sa.ForeignKey("remedy_cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("performed_by", sa.String(255), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("remedy_audit_logs")
    op.drop_table("remedy_actions")
    op.drop_table("remedy_beneficiaries")
    op.drop_table("remedy_cases")
