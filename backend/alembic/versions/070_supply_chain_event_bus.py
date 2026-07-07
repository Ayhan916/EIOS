"""Supply Chain Event Bus — M5

Two new tables:
  event_outbox  — transactional outbox for guaranteed Kafka delivery
  event_log     — immutable audit trail of consumed events

Revision ID: 070
Revises: 069
Create Date: 2026-06-29
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "070"
down_revision = "069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_outbox",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("topic", sa.String(200), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.String(36), nullable=False),
        sa.Column("payload_json", sa.Text, nullable=False),
        sa.Column("outbox_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_event_outbox_org", "event_outbox", ["organization_id"])
    op.create_index("ix_event_outbox_status", "event_outbox", ["outbox_status"])
    op.create_index("ix_event_outbox_pending", "event_outbox", ["outbox_status", "created_at"])

    op.create_table(
        "event_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("topic", sa.String(200), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.String(36), nullable=False),
        sa.Column("payload_json", sa.Text, nullable=False),
        sa.Column("handler_status", sa.String(20), nullable=False, server_default="OK"),
        sa.Column("handler_error", sa.Text, nullable=True),
        sa.Column("kafka_partition", sa.Integer, nullable=True),
        sa.Column("kafka_offset", sa.Integer, nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_event_log_org", "event_log", ["organization_id"])
    op.create_index("ix_event_log_event_type", "event_log", ["event_type"])
    op.create_index("ix_event_log_aggregate_id", "event_log", ["aggregate_id"])
    op.create_index("ix_event_log_consumed_at", "event_log", ["consumed_at"])
    op.create_index("ix_event_log_org_type", "event_log", ["organization_id", "event_type"])


def downgrade() -> None:
    op.drop_index("ix_event_log_org_type", table_name="event_log")
    op.drop_index("ix_event_log_consumed_at", table_name="event_log")
    op.drop_index("ix_event_log_aggregate_id", table_name="event_log")
    op.drop_index("ix_event_log_event_type", table_name="event_log")
    op.drop_index("ix_event_log_org", table_name="event_log")
    op.drop_table("event_log")

    op.drop_index("ix_event_outbox_pending", table_name="event_outbox")
    op.drop_index("ix_event_outbox_status", table_name="event_outbox")
    op.drop_index("ix_event_outbox_org", table_name="event_outbox")
    op.drop_table("event_outbox")
