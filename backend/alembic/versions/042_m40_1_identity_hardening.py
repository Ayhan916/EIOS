"""M40.1 — Enterprise Identity & Provisioning Hardening.

Changes:
  1. Creates `secret_references` table — stores (provider, identifier) pointers;
     raw secrets are never persisted to the database.
  2. Adds `secret_reference_id` FK column to `identity_providers`.
  3. Drops `client_secret_encrypted` column from `identity_providers` —
     replaced by the SecretReference pattern.
  4. Creates `scim_tokens` table — SCIM bearer tokens (SHA-256 hash only).

Revision ID: 042
Revises: 041
Create Date: 2026-06-21
"""

import sqlalchemy as sa

from alembic import op

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None

_COMMON = [
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("owner", sa.String(36), nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
]


def upgrade() -> None:
    # ── 1. secret_references ─────────────────────────────────────────────────
    op.create_table(
        "secret_references",
        *_COMMON,
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("secret_identifier", sa.String(500), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("reference_created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_secref_provider", "secret_references", ["provider"])

    # ── 2. Add secret_reference_id to identity_providers ─────────────────────
    op.add_column(
        "identity_providers",
        sa.Column(
            "secret_reference_id",
            sa.String(36),
            sa.ForeignKey("secret_references.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_idp_secret_ref", "identity_providers", ["secret_reference_id"])

    # ── 3. Drop client_secret_encrypted ──────────────────────────────────────
    op.drop_column("identity_providers", "client_secret_encrypted")

    # ── 4. scim_tokens ───────────────────────────────────────────────────────
    op.create_table(
        "scim_tokens",
        *_COMMON,
        sa.Column(
            "enterprise_id",
            sa.String(36),
            sa.ForeignKey("enterprises.id"),
            nullable=False,
        ),
        # SHA-256 hex digest of the raw bearer token (64 chars)
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("use_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_scim_token_enterprise", "scim_tokens", ["enterprise_id"])
    op.create_index("ix_scim_token_hash", "scim_tokens", ["token_hash"], unique=True)
    op.create_index("ix_scim_token_active", "scim_tokens", ["is_active"])


def downgrade() -> None:
    # Restore client_secret_encrypted before removing secret_references
    op.drop_table("scim_tokens")

    op.drop_index("ix_idp_secret_ref", "identity_providers")
    op.drop_column("identity_providers", "secret_reference_id")

    op.add_column(
        "identity_providers",
        sa.Column("client_secret_encrypted", sa.Text, nullable=True),
    )

    op.drop_table("secret_references")
