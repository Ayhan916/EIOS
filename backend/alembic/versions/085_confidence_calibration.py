"""085 — Confidence Calibration Events table (GAP-27)

Revision ID: 085
Revises: 084
Create Date: 2026-07-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "085"
down_revision = "084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calibration_events",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("predicted_confidence", sa.String(10), nullable=False),
        sa.Column("actual_outcome", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("recorded_by", sa.String(36), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_calev_org", "calibration_events", ["organization_id"])
    op.create_index("ix_calev_confidence", "calibration_events", ["predicted_confidence"])
    op.create_index("ix_calev_entity", "calibration_events", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_calev_entity", table_name="calibration_events")
    op.drop_index("ix_calev_confidence", table_name="calibration_events")
    op.drop_index("ix_calev_org", table_name="calibration_events")
    op.drop_table("calibration_events")
