"""
EIOS Migration 010 — Organisation Isolation + RBAC

Adds organization_id to root entities (assessments, evidences, workflow_runs,
workflow_jobs) to enforce tenant data isolation. Each root entity now carries
the tenant FK, scoping all queries to the authenticated user's organisation.

Changes:
  - assessments.organization_id  → FK organizations.id, nullable, indexed
  - evidences.organization_id    → FK organizations.id, nullable, indexed
  - workflow_runs.organization_id → FK organizations.id, nullable, indexed
  - workflow_jobs.organization_id → nullable, indexed (no FK — jobs table is
                                    infrastructure, not a business entity)
  - users.role default            → "viewer" (was "")

Revision: 010
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # assessments
    op.add_column(
        "assessments",
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True
        ),
    )
    op.create_index("ix_assessments_organization_id", "assessments", ["organization_id"])

    # evidences
    op.add_column(
        "evidences",
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True
        ),
    )
    op.create_index("ix_evidences_organization_id", "evidences", ["organization_id"])

    # workflow_runs
    op.add_column(
        "workflow_runs",
        sa.Column(
            "organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True
        ),
    )
    op.create_index("ix_workflow_runs_organization_id", "workflow_runs", ["organization_id"])

    # workflow_jobs (no FK — operational table)
    op.add_column(
        "workflow_jobs",
        sa.Column("organization_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_workflow_jobs_organization_id", "workflow_jobs", ["organization_id"])

    # users.role default
    op.alter_column("users", "role", server_default="viewer")


def downgrade() -> None:
    op.alter_column("users", "role", server_default="")

    op.drop_index("ix_workflow_jobs_organization_id", table_name="workflow_jobs")
    op.drop_column("workflow_jobs", "organization_id")

    op.drop_index("ix_workflow_runs_organization_id", table_name="workflow_runs")
    op.drop_column("workflow_runs", "organization_id")

    op.drop_index("ix_evidences_organization_id", table_name="evidences")
    op.drop_column("evidences", "organization_id")

    op.drop_index("ix_assessments_organization_id", table_name="assessments")
    op.drop_column("assessments", "organization_id")
