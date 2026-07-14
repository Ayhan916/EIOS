"""Audit Log — previous_hash column + immutability trigger (ADR-006 / E3-F2)

Adds previous_hash (VARCHAR 64) to audit_events so each row carries the
full chain link (previous_hash + entry_hash).

Also installs a PostgreSQL trigger that raises an exception on any
UPDATE or DELETE, enforcing row-level immutability at the DB layer.

Revision ID: 114
Revises: 113
Create Date: 2026-07-09
"""

import sqlalchemy as sa
from alembic import op

revision = "114"
down_revision = "113"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_events",
        sa.Column("previous_hash", sa.String(64), nullable=True),
    )

    # Immutability trigger — prevents UPDATE and DELETE on audit_events
    op.execute("""
        CREATE OR REPLACE FUNCTION fn_audit_events_immutable()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION
                'audit_events are immutable: UPDATE and DELETE are not permitted (ADR-006)';
        END;
        $$
    """)

    op.execute("""
        CREATE TRIGGER trg_audit_events_immutable
            BEFORE UPDATE OR DELETE ON audit_events
            FOR EACH ROW EXECUTE FUNCTION fn_audit_events_immutable()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_immutable ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS fn_audit_events_immutable()")
    op.drop_column("audit_events", "previous_hash")
