"""
EIOS Migration 009 — Add workflow_jobs table

Enables async workflow execution: POST /workflows/run returns 202 + job_id
immediately. Background tasks poll and update job status (pending → running →
completed | failed). Clients poll GET /workflows/jobs/{id} for results.

Revision: 009
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workflow_type", sa.String(50), nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("job_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("workflow_run_id", sa.String(36), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("job_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workflow_jobs_workflow_type", "workflow_jobs", ["workflow_type"])
    op.create_index("ix_workflow_jobs_created_by", "workflow_jobs", ["created_by"])
    op.create_index("ix_workflow_jobs_job_status", "workflow_jobs", ["job_status"])


def downgrade() -> None:
    op.drop_index("ix_workflow_jobs_job_status", table_name="workflow_jobs")
    op.drop_index("ix_workflow_jobs_created_by", table_name="workflow_jobs")
    op.drop_index("ix_workflow_jobs_workflow_type", table_name="workflow_jobs")
    op.drop_table("workflow_jobs")
