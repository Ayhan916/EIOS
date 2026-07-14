"""Immutable Audit Log — SHA-256 hash chain column (ADR-006)

Adds entry_hash (VARCHAR 64) to audit_events.
Existing rows receive NULL; the chain starts from the first new event.

Revision ID: 106
Revises: 105
Create Date: 2026-07-09
"""

import sqlalchemy as sa
from alembic import op

revision = "106"
down_revision = "105"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_events",
        sa.Column("entry_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_audit_events_entry_hash",
        "audit_events",
        ["entry_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_entry_hash", table_name="audit_events")
    op.drop_column("audit_events", "entry_hash")
