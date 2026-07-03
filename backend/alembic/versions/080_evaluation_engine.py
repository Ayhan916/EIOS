"""080 — Evaluation Engine (GAP-02 / FR-014).

Creates evaluation_runs and benchmark_results tables for tracking
AI platform quality metrics: accuracy, confidence, hallucination rate,
cost, and benchmark pass/fail status.

Revision ID: 080
Revises: 079
Create Date: 2026-07-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "080"
down_revision = "079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("run_type", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("window_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("agent_run_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("accuracy_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("precision_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("recall_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("hallucination_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("error_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("cost_usd_total", sa.Float, nullable=False, server_default="0"),
        sa.Column("cost_usd_last_7d", sa.Float, nullable=False, server_default="0"),
        sa.Column("cost_usd_last_30d", sa.Float, nullable=False, server_default="0"),
        sa.Column("benchmark_status", sa.String(10), nullable=False, server_default="unknown"),
        sa.Column("benchmark_passed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("benchmark_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("platform_health_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("raw_metrics", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_evalrun_computed_at", "evaluation_runs", ["computed_at"])
    op.create_index("ix_evalrun_run_type", "evaluation_runs", ["run_type"])

    op.create_table(
        "benchmark_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluation_run_id", sa.String(36), nullable=False),
        sa.Column("benchmark_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("module", sa.String(50), nullable=False, server_default=""),
        sa.Column("dimension", sa.String(30), nullable=False, server_default="accuracy"),
        sa.Column("passed", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("score", sa.Float, nullable=False, server_default="0"),
        sa.Column("expected_output", sa.Text, nullable=False, server_default=""),
        sa.Column("actual_output", sa.Text, nullable=False, server_default=""),
        sa.Column("failure_reason", sa.Text, nullable=False, server_default=""),
        sa.Column("duration_ms", sa.Float, nullable=False, server_default="0"),
    )
    op.create_index("ix_benchres_run", "benchmark_results", ["evaluation_run_id"])
    op.create_index("ix_benchres_module", "benchmark_results", ["module"])


def downgrade() -> None:
    op.drop_index("ix_benchres_module", table_name="benchmark_results")
    op.drop_index("ix_benchres_run", table_name="benchmark_results")
    op.drop_table("benchmark_results")

    op.drop_index("ix_evalrun_run_type", table_name="evaluation_runs")
    op.drop_index("ix_evalrun_computed_at", table_name="evaluation_runs")
    op.drop_table("evaluation_runs")
