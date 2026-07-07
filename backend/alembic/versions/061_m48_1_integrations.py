"""M48.1 — Enterprise Integrations: findings.external_ticket_url column.

Adds ticket tracking columns to findings for JIRA/ServiceNow integration.

Revision: 061
Down revision: 060
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "061"
down_revision = "060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # G-047: JIRA/ServiceNow ticket tracking on findings
    op.add_column(
        "findings",
        sa.Column("external_ticket_url", sa.String(2000), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("external_ticket_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "findings",
        sa.Column("external_ticket_system", sa.String(20), nullable=True),
    )
    op.create_index(
        "ix_findings_external_ticket_id",
        "findings",
        ["external_ticket_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_findings_external_ticket_id", table_name="findings")
    op.drop_column("findings", "external_ticket_system")
    op.drop_column("findings", "external_ticket_id")
    op.drop_column("findings", "external_ticket_url")
