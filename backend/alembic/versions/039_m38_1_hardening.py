"""M38.1 Supplier Network Intelligence Hardening.

Changes:
  - network_exposure_signals: add partial unique index on
    (organization_id, origin_supplier_id, impacted_supplier_id, exposure_type)
    WHERE exposure_status = 'ACTIVE'
    (P0: prevents duplicate ACTIVE signals for the same origin/impacted/type pair)

  - network_watchlist_entries (NEW): persists BFS-expanded watchlist neighborhoods
    per watched supplier, enabling alert surfacing for related suppliers
    (P4: Spec Section 13 — Network Watchlist Integration)

Revision ID: 039
Revises: 038
Create Date: 2026-06-20
"""

import sqlalchemy as sa
from alembic import op

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # P0: partial unique index on network_exposure_signals
    op.create_index(
        "uq_nexp_active_signal",
        "network_exposure_signals",
        ["organization_id", "origin_supplier_id", "impacted_supplier_id", "exposure_type"],
        unique=True,
        postgresql_where=sa.text("exposure_status = 'ACTIVE'"),
    )

    # P4: network watchlist entries table
    op.create_table(
        "network_watchlist_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("watched_supplier_id", sa.String(36), nullable=False),
        sa.Column("related_supplier_id", sa.String(36), nullable=False),
        sa.Column("distance", sa.Integer, nullable=False, server_default="1"),
    )

    op.create_index(
        "ix_nwl_org",
        "network_watchlist_entries",
        ["organization_id"],
    )
    op.create_index(
        "ix_nwl_watched",
        "network_watchlist_entries",
        ["watched_supplier_id"],
    )
    op.create_index(
        "ix_nwl_related",
        "network_watchlist_entries",
        ["related_supplier_id"],
    )
    op.create_unique_constraint(
        "uq_nwl_pair",
        "network_watchlist_entries",
        ["organization_id", "watched_supplier_id", "related_supplier_id"],
    )


def downgrade() -> None:
    op.drop_table("network_watchlist_entries")
    op.drop_index("uq_nexp_active_signal", table_name="network_exposure_signals")
