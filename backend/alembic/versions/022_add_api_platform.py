"""M30 API Platform: service_accounts, api_keys, webhook_subscriptions, webhook_deliveries

Revision ID: 022
Revises: 021
Create Date: 2026-06-12
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── service_accounts ──────────────────────────────────────────────────────
    op.create_table(
        "service_accounts",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("status", sa.String, nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String, nullable=True),
        sa.Column("created_by", sa.String, nullable=True),
        sa.Column("updated_by", sa.String, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("organization_id", sa.String, nullable=False),
        sa.Column("name", sa.String(200), nullable=False, server_default=""),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_service_accounts_org_id", "service_accounts", ["organization_id"])

    # ── api_keys ──────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("status", sa.String, nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String, nullable=True),
        sa.Column("created_by", sa.String, nullable=True),
        sa.Column("updated_by", sa.String, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("organization_id", sa.String, nullable=False),
        sa.Column("service_account_id", sa.String, nullable=True),
        sa.Column("name", sa.String(200), nullable=False, server_default=""),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("scopes", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requests_total", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("requests_this_minute", sa.Integer, nullable=False, server_default="0"),
        sa.Column("minute_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requests_this_hour", sa.Integer, nullable=False, server_default="0"),
        sa.Column("hour_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rate_limit_per_minute", sa.Integer, nullable=False, server_default="60"),
        sa.Column("rate_limit_per_hour", sa.Integer, nullable=False, server_default="1000"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.String, nullable=True),
    )
    op.create_index("ix_api_keys_org_id", "api_keys", ["organization_id"])
    op.create_unique_constraint("uq_api_keys_key_hash", "api_keys", ["key_hash"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])

    # ── webhook_subscriptions ─────────────────────────────────────────────────
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("status", sa.String, nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String, nullable=True),
        sa.Column("created_by", sa.String, nullable=True),
        sa.Column("updated_by", sa.String, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("organization_id", sa.String, nullable=False),
        sa.Column("name", sa.String(200), nullable=False, server_default=""),
        sa.Column("target_url", sa.Text, nullable=False, server_default=""),
        sa.Column("secret", sa.String(256), nullable=False, server_default=""),
        sa.Column("events", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("failure_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_webhook_subscriptions_org_id", "webhook_subscriptions", ["organization_id"])

    # ── webhook_deliveries ────────────────────────────────────────────────────
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("status", sa.String, nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String, nullable=True),
        sa.Column("created_by", sa.String, nullable=True),
        sa.Column("updated_by", sa.String, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("subscription_id", sa.String, nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False, server_default=""),
        sa.Column("payload_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("delivery_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("response_code", sa.Integer, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_webhook_deliveries_subscription_id", "webhook_deliveries", ["subscription_id"]
    )
    op.create_index(
        "ix_webhook_deliveries_delivery_status", "webhook_deliveries", ["delivery_status"]
    )
    op.create_index("ix_webhook_deliveries_retry_at", "webhook_deliveries", ["retry_at"])


def downgrade() -> None:
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_subscriptions")
    op.drop_table("api_keys")
    op.drop_table("service_accounts")
