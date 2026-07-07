"""M50 Supplier Digital Twin — intelligence timeline and twin state tables.

Revision ID: 064_supplier_digital_twin
Revises: 063_m49_security_audit
Create Date: 2026-06-25
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "064"
down_revision = "063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Supplier Digital Twin State ───────────────────────────────────────────
    op.create_table(
        "supplier_digital_twins",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        # Health dimensions
        sa.Column("esg_health", sa.Float, nullable=False, server_default="75.0"),
        sa.Column("compliance_health", sa.Float, nullable=False, server_default="75.0"),
        sa.Column("financial_health", sa.Float, nullable=False, server_default="75.0"),
        sa.Column("geopolitical_health", sa.Float, nullable=False, server_default="75.0"),
        sa.Column("cyber_health", sa.Float, nullable=False, server_default="75.0"),
        sa.Column("human_rights_health", sa.Float, nullable=False, server_default="75.0"),
        sa.Column("environmental_health", sa.Float, nullable=False, server_default="75.0"),
        sa.Column("operational_health", sa.Float, nullable=False, server_default="75.0"),
        sa.Column("overall_health", sa.Float, nullable=False, server_default="75.0"),
        sa.Column("health_trend", sa.String(20), nullable=False, server_default="STABLE"),
        sa.Column("ai_confidence", sa.Float, nullable=False, server_default="0.7"),
        sa.Column("open_recommendations", sa.Integer, nullable=False, server_default="0"),
        sa.Column("open_actions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("event_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("critical_event_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("twin_version", sa.Integer, nullable=False, server_default="1"),
        sa.UniqueConstraint("supplier_id", "organization_id", name="uq_twin_supplier_org"),
    )
    op.create_index("ix_twin_supplier_id", "supplier_digital_twins", ["supplier_id"])
    op.create_index("ix_twin_org_id", "supplier_digital_twins", ["organization_id"])
    op.create_index("ix_twin_overall_health", "supplier_digital_twins", ["overall_health"])

    # ── Intelligence Timeline Events ──────────────────────────────────────────
    op.create_table(
        "intelligence_timeline_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_category", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("why_important", sa.Text, nullable=False, server_default=""),
        sa.Column("regulatory_impact", sa.Text, nullable=False, server_default=""),
        sa.Column("recommended_action", sa.Text, nullable=False, server_default=""),
        sa.Column("source_type", sa.String(30), nullable=False, server_default=""),
        sa.Column("source_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("source_url", sa.Text, nullable=False, server_default=""),
        sa.Column("evidence_ids", sa.Text, nullable=False, server_default="[]"),
        sa.Column("regulation_ids", sa.Text, nullable=False, server_default="[]"),
        sa.Column("risk_ids", sa.Text, nullable=False, server_default="[]"),
        sa.Column("signal_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("twin_dimension_affected", sa.String(40), nullable=False, server_default=""),
        sa.Column("health_delta", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.7"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_ite_supplier_id", "intelligence_timeline_events", ["supplier_id"])
    op.create_index("ix_ite_org_id", "intelligence_timeline_events", ["organization_id"])
    op.create_index("ix_ite_occurred_at", "intelligence_timeline_events", ["occurred_at"])
    op.create_index("ix_ite_severity", "intelligence_timeline_events", ["severity"])
    op.create_index("ix_ite_event_category", "intelligence_timeline_events", ["event_category"])


def downgrade() -> None:
    op.drop_table("intelligence_timeline_events")
    op.drop_table("supplier_digital_twins")
