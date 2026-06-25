"""Row Level Security context management (M45.1.1).

Sets the PostgreSQL session-level parameter `app.current_org_id` so that
RESTRICTIVE RLS policies on org-scoped tables automatically filter rows to
the authenticated user's organisation.

Design:
  SET LOCAL app.current_org_id = '<org_uuid>'

  • SET LOCAL: scoped to the current transaction — auto-resets at rollback or
    commit.  Safe under connection pooling because each request runs inside its
    own transaction (opened by get_db's session.begin()).

  • When app.current_org_id is '' (not set, e.g. during seeding/migrations):
    the policy bypass clause fires and all rows are visible.

  • When app.current_org_id is a valid org UUID:
    only rows where organization_id matches are visible.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# SET LOCAL does not accept parameterized values in PostgreSQL.
# Use set_config() which supports $1 placeholders and is equivalent to SET LOCAL
# when is_local=true (resets on transaction commit/rollback).
_SET_RLS_SQL = text("SELECT set_config('app.current_org_id', :org_id, true)")
_CLEAR_RLS_SQL = text("SELECT set_config('app.current_org_id', '', true)")


async def async_set_rls_context(session: AsyncSession, org_id: str | None) -> None:
    """Bind the current transaction to a single organisation via PostgreSQL SET LOCAL.

    Call this once per request after the user is authenticated, before any
    business-data queries run.  The shared SQLAlchemy session (cached by
    FastAPI's DI within a single request) propagates this setting to all repos.

    No-op when org_id is None or empty (superuser / system operations bypass RLS
    via the ``OR current_setting(...) = ''`` clause in the policy).
    """
    if org_id:
        await session.execute(_SET_RLS_SQL, {"org_id": org_id})


async def async_clear_rls_context(session: AsyncSession) -> None:
    """Explicitly clear the RLS context for the current transaction.

    Not normally needed — transactions reset SET LOCAL on commit/rollback.
    Useful in tests that reuse a session across multiple operations.
    """
    await session.execute(_CLEAR_RLS_SQL)
