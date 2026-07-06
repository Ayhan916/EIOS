"""CSDDD-012 — Impact Severity Assessments (Art. 3/6)

Revision ID: 095
Revises: 094
Create Date: 2026-07-06

Creates:
  impact_assessments — OECD RBC severity assessments linked to any EIOS entity
"""

from alembic import op
import sqlalchemy as sa

revision = "095"
down_revision = "094"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "impact_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("impact_type", sa.String(30), nullable=False, server_default="other"),
        sa.Column("entity_type", sa.String(30), nullable=False, server_default="standalone"),
        sa.Column("entity_id", sa.String(36), nullable=True),
        sa.Column("gravity", sa.Integer, nullable=False),
        sa.Column("scope", sa.Integer, nullable=False),
        sa.Column("remediability", sa.Integer, nullable=False),
        sa.Column("likelihood", sa.Integer, nullable=False),
        sa.Column("severity_score", sa.Float, nullable=False),
        sa.Column("priority_score", sa.Float, nullable=False),
        sa.Column("severity_level", sa.String(20), nullable=False),
        sa.Column("justification", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_impact_assessments_org", "impact_assessments", ["organization_id"])
    op.create_index("ix_impact_assessments_org_level", "impact_assessments", ["organization_id", "severity_level"])
    op.create_index("ix_impact_assessments_org_type", "impact_assessments", ["organization_id", "impact_type"])


def downgrade() -> None:
    op.drop_table("impact_assessments")
