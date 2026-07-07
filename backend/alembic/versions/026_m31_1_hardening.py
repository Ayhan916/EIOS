"""m31_1_hardening

M31.1 — Regulatory Intelligence Hardening.

Changes:
  requirement_mappings — add DB-level unique constraint (tenant-safe duplicate prevention)
  requirement_mappings — add regulation_version_at_mapping column
  compliance_gaps      — add regulation_version_at_calculation column

Revision ID: 026
Revises: 025
Create Date: 2026-06-19
"""

import sqlalchemy as sa

from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── requirement_mappings: version traceability ────────────────────────────
    op.add_column(
        "requirement_mappings",
        sa.Column(
            "regulation_version_at_mapping",
            sa.String(20),
            nullable=False,
            server_default="1.0",
        ),
    )

    # ── requirement_mappings: DB-level duplicate prevention ───────────────────
    op.create_unique_constraint(
        "uq_req_mappings_entity_requirement",
        "requirement_mappings",
        ["organization_id", "regulation_requirement_id", "entity_type", "entity_id"],
    )

    # ── compliance_gaps: version traceability ─────────────────────────────────
    op.add_column(
        "compliance_gaps",
        sa.Column(
            "regulation_version_at_calculation",
            sa.String(20),
            nullable=False,
            server_default="1.0",
        ),
    )


def downgrade() -> None:
    op.drop_column("compliance_gaps", "regulation_version_at_calculation")
    op.drop_constraint("uq_req_mappings_entity_requirement", "requirement_mappings", type_="unique")
    op.drop_column("requirement_mappings", "regulation_version_at_mapping")
