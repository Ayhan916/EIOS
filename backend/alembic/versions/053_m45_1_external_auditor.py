"""M45.1 — External Auditor role + SSO production validators.

Changes:
  1. No structural DDL change needed: the users.role column is String(100) with
     no CHECK constraint, so it already accepts 'external_auditor'.
  2. Adds an index on users.role to speed up role-based access queries now that
     external_auditor queries will scan the table.
  3. Documents the new UserRole.EXTERNAL_AUDITOR value and the idp_id normalization
     (production validators leave idp_id="" which is filled in by the enterprise router).

Security note:
  EXTERNAL_AUDITOR tokens are time-limited JWTs with audience="eios-external-audit"
  and are not tied to a users table row — no schema change is needed for them.

Revision ID: 053
Revises: 052
Create Date: 2026-06-22
"""

from alembic import op

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_users_role",
        "users",
        ["role"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_role", table_name="users", if_exists=True)
