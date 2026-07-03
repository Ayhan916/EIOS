"""077 — Grievance Mechanism (LkSG §8 / CSDDD Art. 14).

Adds the grievance_reports table required for legal compliance with
LkSG §8 (accessible complaint channel) and CSDDD Art. 14 (grievance mechanism).

Revision ID: 077
Revises: 076
Create Date: 2026-07-03
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "077"
down_revision = "076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "grievance_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="other"),
        sa.Column("grievance_status", sa.String(30), nullable=False, server_default="received"),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        # Confidential — never returned via API
        sa.Column("submitted_by_email", sa.String(320), nullable=True),
        sa.Column("submitted_by_name", sa.String(255), nullable=True),
        sa.Column("is_anonymous", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("anonymized_reference_code", sa.String(20), nullable=False, server_default=""),
        sa.Column("related_supplier_id", sa.String(36), nullable=True),
        sa.Column("assigned_to_user_id", sa.String(36), nullable=True),
        sa.Column("reviewer_notes", sa.Text, nullable=True),
        sa.Column("resolution_notes", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("regulation_refs", sa.String(255), nullable=False,
                  server_default="LkSG §8; CSDDD Art. 14"),
        sa.Column("linked_finding_id", sa.String(36), nullable=True),
        # BaseEntity columns
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(36), nullable=False, server_default=""),
        sa.Column("updated_by", sa.String(36), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_grievance_reports_organization_id", "grievance_reports", ["organization_id"])
    op.create_index("ix_grievance_reports_status", "grievance_reports", ["grievance_status"])
    op.create_index("ix_grievance_reports_reference_code", "grievance_reports", ["anonymized_reference_code"])
    op.create_index("ix_grievance_reports_related_supplier", "grievance_reports", ["related_supplier_id"])


def downgrade() -> None:
    op.drop_index("ix_grievance_reports_related_supplier", table_name="grievance_reports")
    op.drop_index("ix_grievance_reports_reference_code", table_name="grievance_reports")
    op.drop_index("ix_grievance_reports_status", table_name="grievance_reports")
    op.drop_index("ix_grievance_reports_organization_id", table_name="grievance_reports")
    op.drop_table("grievance_reports")
