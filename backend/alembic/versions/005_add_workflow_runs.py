"""Add workflow_runs table and extend agent_runs with workflow linkage

Revision ID: 005
Revises: 004
Create Date: 2026-06-16

Creates the workflow_runs table (one record per workflow execution) and
adds workflow_run_id + step_index to agent_runs so each agent step in a
workflow is fully traceable back to its parent execution.

Traceability chain:
  Evidence → EvidenceChunk → AgentRun (retrieval step)
           → WorkflowRun → DueDiligenceVerdict
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("workflow_type", sa.String(50), nullable=False, index=True),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("steps_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_steps", sa.Integer, nullable=False, server_default="0"),
        sa.Column("verdict", sa.String(30), nullable=True, index=True),
        sa.Column("verdict_reasoning", sa.Text, nullable=True),
        sa.Column("overall_risk_level", sa.String(20), nullable=True),
        sa.Column("total_input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("run_metadata", JSONB, nullable=False, server_default="{}"),
    )

    # Extend agent_runs with workflow linkage columns
    op.add_column(
        "agent_runs",
        sa.Column("workflow_run_id", sa.String(36), nullable=True, index=True),
    )
    op.add_column(
        "agent_runs",
        sa.Column("step_index", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("agent_runs", "step_index")
    op.drop_column("agent_runs", "workflow_run_id")
    op.drop_table("workflow_runs")
