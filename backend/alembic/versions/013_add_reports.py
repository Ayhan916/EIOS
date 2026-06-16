"""
EIOS Migration 013 — Reports (M18)

Adds the reports table for executive PDF report storage.

Each report stores:
  - Metadata (assessment_id, generated_by, counts)
  - A frozen JSON snapshot of all data at generation time (for auditability)
  - The rendered PDF as binary data
"""

from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assessment_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("generated_by", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("format", sa.String(20), nullable=False, default="pdf"),
        sa.Column("finding_count", sa.Integer, nullable=False, default=0),
        sa.Column("risk_count", sa.Integer, nullable=False, default=0),
        sa.Column("recommendation_count", sa.Integer, nullable=False, default=0),
        sa.Column("evidence_count", sa.Integer, nullable=False, default=0),
        sa.Column("content_snapshot", sa.JSON, nullable=True),
        sa.Column("pdf_data", sa.LargeBinary, nullable=True),
    )
    op.create_index("ix_reports_assessment_id", "reports", ["assessment_id"])
    op.create_index("ix_reports_organization_id", "reports", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_organization_id", table_name="reports")
    op.drop_index("ix_reports_assessment_id", table_name="reports")
    op.drop_table("reports")
