"""M35.1 Supplier Portal Hardening.

Fixes applied:
  F2  — supplier_password_reset_tokens (DB-backed, single-use reset tokens)
  F7  — supplier_users.failed_login_attempts + locked_until (brute-force lockout)
  F8  — evidence_submissions unique constraint (one submission per request per supplier)

Revision ID: 037
Revises: 036
Create Date: 2026-06-20
"""

import sqlalchemy as sa
from alembic import op

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # F7: brute-force lockout columns on supplier_users
    op.add_column(
        "supplier_users",
        sa.Column("failed_login_attempts", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "supplier_users",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )

    # F8: one active submission per (evidence_request_id, supplier_id)
    op.create_unique_constraint(
        "uq_evidence_submission_per_supplier",
        "evidence_submissions",
        ["evidence_request_id", "supplier_id"],
    )

    # F2: DB-backed single-use password reset tokens
    op.create_table(
        "supplier_password_reset_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_supplier_pwd_reset_token_hash", "supplier_password_reset_tokens", ["token_hash"])
    op.create_index("ix_supplier_pwd_reset_email", "supplier_password_reset_tokens", ["email"])


def downgrade() -> None:
    op.drop_index("ix_supplier_pwd_reset_email", "supplier_password_reset_tokens")
    op.drop_index("ix_supplier_pwd_reset_token_hash", "supplier_password_reset_tokens")
    op.drop_table("supplier_password_reset_tokens")
    op.drop_constraint("uq_evidence_submission_per_supplier", "evidence_submissions", type_="unique")
    op.drop_column("supplier_users", "locked_until")
    op.drop_column("supplier_users", "failed_login_attempts")
