"""m34_1_connectors

M34.1 — Live Intelligence Connectors & Automated Data Operations.

New tables:
  connector_runs               — audit log of every connector execution
  dataset_validation_results   — per-dataset validation outcome records

Revision ID: 034
Revises: 033
Create Date: 2026-06-19
"""

import sqlalchemy as sa
from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None

_AUDIT_COLS = [
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
]


def upgrade() -> None:
    # ── connector_runs ────────────────────────────────────────────────────────
    op.create_table(
        "connector_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("connector_name", sa.String(100), nullable=False),
        sa.Column("connector_version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("runtime_seconds", sa.Float, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="healthy"),
        sa.Column("dataset_id", sa.String(36), nullable=True),
        sa.Column("dataset_hash", sa.String(64), nullable=True),
        sa.Column("row_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("validation_errors_json", sa.Text, nullable=True),
        *_AUDIT_COLS,
    )
    op.create_index("ix_connector_runs_name", "connector_runs", ["connector_name"])
    op.create_index("ix_connector_runs_status", "connector_runs", ["status"])
    op.create_index("ix_connector_runs_started", "connector_runs", ["started_at"])

    # ── dataset_validation_results ────────────────────────────────────────────
    op.create_table(
        "dataset_validation_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dataset_id", sa.String(36), nullable=False),
        sa.Column("is_valid", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("errors_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("warnings_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("row_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
        *_AUDIT_COLS,
    )
    op.create_index(
        "ix_validation_results_dataset", "dataset_validation_results", ["dataset_id"]
    )
    op.create_index(
        "ix_validation_results_valid", "dataset_validation_results", ["is_valid"]
    )


def downgrade() -> None:
    op.drop_table("dataset_validation_results")
    op.drop_table("connector_runs")
