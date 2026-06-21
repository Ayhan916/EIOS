"""M40.2-M40.4 — Enterprise Identity Completion.

Changes:
  1. scim_tokens: add idp_id FK to identity_providers (nullable for back-compat)
  2. scim_tokens: add scope column (READ_ONLY | PROVISIONING | FULL_ADMIN)

The new secret providers (Vault, AWS) and SSO validation layer have no schema
footprint — they are pure application-layer additions.

Revision ID: 043
Revises: 042
Create Date: 2026-06-21
"""

import sqlalchemy as sa
from alembic import op

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── scim_tokens: idp_id binding ──────────────────────────────────────────
    op.add_column(
        "scim_tokens",
        sa.Column(
            "idp_id",
            sa.String(36),
            sa.ForeignKey("identity_providers.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_scim_token_idp", "scim_tokens", ["idp_id"])

    # ── scim_tokens: scope ────────────────────────────────────────────────────
    op.add_column(
        "scim_tokens",
        sa.Column(
            "scope",
            sa.String(20),
            nullable=False,
            server_default="FULL_ADMIN",
        ),
    )
    op.create_index("ix_scim_token_scope", "scim_tokens", ["scope"])


def downgrade() -> None:
    op.drop_index("ix_scim_token_scope", "scim_tokens")
    op.drop_column("scim_tokens", "scope")

    op.drop_index("ix_scim_token_idp", "scim_tokens")
    op.drop_column("scim_tokens", "idp_id")
