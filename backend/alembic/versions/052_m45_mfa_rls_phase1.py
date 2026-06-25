"""M45 — MFA tables + RLS Phase 1 (PERMISSIVE).

Changes:
  1. Add mfa_enabled, encrypted_mfa_secret, mfa_confirmed_at to users table
  2. Create mfa_backup_codes table
  3. Enable Row Level Security PERMISSIVE on all org-scoped tables
     (USING (true) — no filtering yet, sets up the framework for Phase 2)

RLS Phase 2 (RESTRICTIVE with actual org_id filtering) will be applied in
migration 053 after the FastAPI session propagation middleware is deployed
and validated in a non-production environment.

Revision ID: 052
Revises: 051
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None

# Tables that hold organisation-scoped data and must have RLS enabled.
# System/reference tables (sectors, frameworks, standards) are excluded.
_ORG_SCOPED_TABLES = [
    "suppliers",
    "assessments",
    "evidences",
    "projects",
    "reports",
    "notifications",
    "disclosure_responses",
    "reporting_packages",
    "compliance_gaps",
    "compliance_reports",
    "due_diligence_reports",
    "sustainability_objectives",
    "esg_targets",
    "esg_kpis",
    "emission_sources",
    "carbon_inventories",
    "supplier_scores",
    "board_reports",
]


def upgrade() -> None:
    # ── 1. MFA columns on users ──────────────────────────────────────────────
    op.execute(
        "ALTER TABLE users "
        "ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE"
    )
    op.execute(
        "ALTER TABLE users "
        "ADD COLUMN IF NOT EXISTS encrypted_mfa_secret VARCHAR(512)"
    )
    op.execute(
        "ALTER TABLE users "
        "ADD COLUMN IF NOT EXISTS mfa_confirmed_at TIMESTAMP WITH TIME ZONE"
    )

    # ── 2. MFA backup codes table ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS mfa_backup_codes (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            code_hash VARCHAR(255) NOT NULL,
            used_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_mfa_backup_codes_user_id "
        "ON mfa_backup_codes (user_id)"
    )

    # ── 3. RLS Phase 1 — PERMISSIVE (USING true, no filtering) ──────────────
    # This enables the RLS machinery without any data impact.
    # Phase 2 migration will tighten to actual org_id filtering.
    for table in _ORG_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY eios_rls_permissive ON {table} "
            f"USING (true)"
        )


def downgrade() -> None:
    # Remove RLS
    for table in reversed(_ORG_SCOPED_TABLES):
        try:
            op.execute(f"DROP POLICY IF EXISTS eios_rls_permissive ON {table}")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        except Exception:
            pass

    # Drop backup codes table
    op.execute("DROP TABLE IF EXISTS mfa_backup_codes")

    # Remove MFA columns
    op.drop_column("users", "mfa_confirmed_at")
    op.drop_column("users", "encrypted_mfa_secret")
    op.drop_column("users", "mfa_enabled")
