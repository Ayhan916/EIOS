"""M44.1 — Strategy Intelligence Completion: 5 new tables + 3 table extensions.

Revision ID: 049
Revises: 048
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def _base():
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    # ── New table: scenario_templates ────────────────────────────────────────
    op.create_table(
        "scenario_templates",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("template_name", sa.String(255), nullable=False),
        sa.Column("template_type", sa.String(40), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("default_assumptions", sa.JSON, nullable=True),
        sa.Column("default_time_horizon_years", sa.Integer, nullable=False, server_default="5"),
        sa.Column("scenario_type", sa.String(20), nullable=False),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_approved", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_scenario_templates_org", "scenario_templates", ["organization_id"])

    # ── New table: strategy_methodologies ────────────────────────────────────
    op.create_table(
        "strategy_methodologies",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("methodology_name", sa.String(255), nullable=False),
        sa.Column("methodology_version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("formula_description", sa.Text, nullable=True),
        sa.Column("assumptions", sa.JSON, nullable=True),
        sa.Column("applicable_to", sa.JSON, nullable=True),
        sa.Column("approval_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_strategy_methodologies_org", "strategy_methodologies", ["organization_id"])

    # ── New table: scenario_comparisons ──────────────────────────────────────
    op.create_table(
        "scenario_comparisons",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("comparison_name", sa.String(255), nullable=False),
        sa.Column("scenario_ids", sa.JSON, nullable=True),
        sa.Column("kpi_delta", sa.JSON, nullable=True),
        sa.Column("emissions_delta", sa.JSON, nullable=True),
        sa.Column("risk_delta", sa.JSON, nullable=True),
        sa.Column("value_delta", sa.JSON, nullable=True),
        sa.Column("comparison_methodology", sa.String(100), nullable=True),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_scenario_comparisons_org", "scenario_comparisons", ["organization_id"])

    # ── New table: stress_test_templates ─────────────────────────────────────
    op.create_table(
        "stress_test_templates",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("template_name", sa.String(255), nullable=False),
        sa.Column("template_type", sa.String(20), nullable=False),
        sa.Column("default_assumptions", sa.JSON, nullable=True),
        sa.Column("methodology", sa.Text, nullable=True),
        sa.Column("severity_level", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_stress_test_templates_org", "stress_test_templates", ["organization_id"])

    # ── New table: forecast_window_policies ──────────────────────────────────
    op.create_table(
        "forecast_window_policies",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("policy_name", sa.String(255), nullable=False),
        sa.Column("min_window", sa.Integer, nullable=False),
        sa.Column("max_window", sa.Integer, nullable=False),
        sa.Column("default_window", sa.Integer, nullable=False),
        sa.Column(
            "applicable_methodology",
            sa.String(40),
            nullable=False,
            server_default="WEIGHTED_MOVING_AVERAGE",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index(
        "ix_forecast_window_policies_org", "forecast_window_policies", ["organization_id"]
    )

    # ── ALTER: transition_pathways — add milestone_frequency ─────────────────
    op.add_column(
        "transition_pathways",
        sa.Column("milestone_frequency", sa.String(20), nullable=False, server_default="ANNUAL"),
    )

    # ── ALTER: strategic_forecast_summaries — add trend/delta/progress cols ──
    op.add_column(
        "strategic_forecast_summaries", sa.Column("trend_direction", sa.String(20), nullable=True)
    )
    op.add_column(
        "strategic_forecast_summaries", sa.Column("forecast_delta", sa.Float, nullable=True)
    )
    op.add_column(
        "strategic_forecast_summaries", sa.Column("pathway_progress_pct", sa.Float, nullable=True)
    )
    op.add_column(
        "strategic_forecast_summaries", sa.Column("scenario_confidence", sa.Float, nullable=True)
    )

    # ── ALTER: strategic_scenario_reports — add appendix/sensitivity cols ────
    op.add_column(
        "strategic_scenario_reports", sa.Column("methodology_appendix", sa.JSON, nullable=True)
    )
    op.add_column(
        "strategic_scenario_reports", sa.Column("assumption_appendix", sa.JSON, nullable=True)
    )
    op.add_column(
        "strategic_scenario_reports", sa.Column("sensitivity_analysis", sa.JSON, nullable=True)
    )
    op.add_column(
        "strategic_scenario_reports", sa.Column("comparison_summary", sa.JSON, nullable=True)
    )


def downgrade() -> None:
    # Reverse report columns
    op.drop_column("strategic_scenario_reports", "comparison_summary")
    op.drop_column("strategic_scenario_reports", "sensitivity_analysis")
    op.drop_column("strategic_scenario_reports", "assumption_appendix")
    op.drop_column("strategic_scenario_reports", "methodology_appendix")

    # Reverse forecast summary columns
    op.drop_column("strategic_forecast_summaries", "scenario_confidence")
    op.drop_column("strategic_forecast_summaries", "pathway_progress_pct")
    op.drop_column("strategic_forecast_summaries", "forecast_delta")
    op.drop_column("strategic_forecast_summaries", "trend_direction")

    # Reverse pathway column
    op.drop_column("transition_pathways", "milestone_frequency")

    # Drop new tables (reverse FK dependency order)
    op.drop_index("ix_forecast_window_policies_org", table_name="forecast_window_policies")
    op.drop_table("forecast_window_policies")

    op.drop_index("ix_stress_test_templates_org", table_name="stress_test_templates")
    op.drop_table("stress_test_templates")

    op.drop_index("ix_scenario_comparisons_org", table_name="scenario_comparisons")
    op.drop_table("scenario_comparisons")

    op.drop_index("ix_strategy_methodologies_org", table_name="strategy_methodologies")
    op.drop_table("strategy_methodologies")

    op.drop_index("ix_scenario_templates_org", table_name="scenario_templates")
    op.drop_table("scenario_templates")
