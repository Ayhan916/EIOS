"""Add audit_events table and extend workflow_runs with assessment linkage

Revision ID: 006
Revises: 005
Create Date: 2026-06-16

audit_events: immutable compliance record for every significant system action.
  Written once; never updated. Enables regulatory auditability (CSDDD Art. 10).

workflow_runs extensions:
  assessment_id   — FK-style pointer to the Assessment created from this workflow
  finding_count   — number of structured findings extracted
  risk_count      — number of structured risks extracted
  recommendation_count — number of structured recommendations extracted

Traceability chain after this migration:
  Evidence → EvidenceChunk → AgentRun → WorkflowRun → Assessment → [Finding, Risk, Recommendation]
                                                      → AuditEvent (workflow.completed)
                                                      → AuditEvent (assessment.created)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Active"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("actor_id", sa.String(36), nullable=True, index=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=True, index=True),
        sa.Column("entity_id", sa.String(36), nullable=True, index=True),
        sa.Column("outcome", sa.String(20), nullable=False, server_default="success"),
        sa.Column("detail", sa.Text, nullable=True),
        sa.Column("event_metadata", JSONB, nullable=False, server_default="{}"),
    )

    op.add_column("workflow_runs", sa.Column("assessment_id", sa.String(36), nullable=True))
    op.add_column("workflow_runs", sa.Column("finding_count", sa.Integer, nullable=False, server_default="0"))
    op.add_column("workflow_runs", sa.Column("risk_count", sa.Integer, nullable=False, server_default="0"))
    op.add_column("workflow_runs", sa.Column("recommendation_count", sa.Integer, nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("workflow_runs", "recommendation_count")
    op.drop_column("workflow_runs", "risk_count")
    op.drop_column("workflow_runs", "finding_count")
    op.drop_column("workflow_runs", "assessment_id")
    op.drop_table("audit_events")
