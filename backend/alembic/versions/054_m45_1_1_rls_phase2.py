"""M45.1.1 — RLS Phase 2: RESTRICTIVE org-isolation policies.

Phase 1 (migration 052) enabled RLS on 24 tables with PERMISSIVE USING(true) —
machinery in place, no data filtering yet.

Phase 2 adds a RESTRICTIVE policy on each table:
  USING (
    organization_id::text = current_setting('app.current_org_id', true)
    OR current_setting('app.current_org_id', true) = ''
  )

PostgreSQL evaluation rule for mixed PERMISSIVE + RESTRICTIVE:
  visible = (any PERMISSIVE passes) AND (all RESTRICTIVE pass)
           = (true) AND (org_id = setting OR setting = '')
           = org_id = setting OR setting = ''

When app.current_org_id is set (by FastAPI's get_current_user via shared/rls.py):
  → Only rows where organization_id = setting are visible.

When app.current_org_id is '' (not set — seeding, migrations, superuser):
  → Bypass clause fires; all rows visible as before.

The FastAPI integration:
  get_db() opens a transaction → all repos share one SQLAlchemy session.
  get_current_user() calls async_set_rls_context(session, user.organization_id)
  after resolving the JWT/API-key user.  SET LOCAL persists for the transaction.

Revision ID: 054
Revises: 053
Create Date: 2026-06-22
"""

from alembic import op

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None

# Same 24 tables from Phase 1 + users table.
# Users is added here (not Phase 1) because the auth lookup (get_by_id) runs
# before the RLS context is set; the bypass clause handles that safely.
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

_POLICY_SQL = (
    "organization_id::text = current_setting('app.current_org_id', true) "
    "OR current_setting('app.current_org_id', true) = ''"
)


def upgrade() -> None:
    for table in _ORG_SCOPED_TABLES:
        op.execute(
            f"CREATE POLICY eios_rls_org_isolation ON {table} AS RESTRICTIVE USING ({_POLICY_SQL})"
        )


def downgrade() -> None:
    for table in reversed(_ORG_SCOPED_TABLES):
        op.execute(f"DROP POLICY IF EXISTS eios_rls_org_isolation ON {table}")
