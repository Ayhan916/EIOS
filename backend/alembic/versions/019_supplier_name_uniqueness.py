"""supplier name uniqueness within org (M27.1)

Revision ID: 019
Revises: 018
Create Date: 2026-06-18

Changes:
  - Drop performance index ix_suppliers_org_name (created in 018)
  - Add UNIQUE constraint uq_suppliers_org_name on (organization_id, name)

Same supplier name across different organizations remains allowed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "019"
down_revision: str | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_suppliers_org_name", table_name="suppliers")
    op.create_unique_constraint(
        "uq_suppliers_org_name",
        "suppliers",
        ["organization_id", "name"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_suppliers_org_name", "suppliers", type_="unique")
    op.create_index("ix_suppliers_org_name", "suppliers", ["organization_id", "name"])
