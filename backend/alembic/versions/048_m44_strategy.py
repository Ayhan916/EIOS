"""M44 — Digital Twin, Strategic Planning & Scenario Intelligence Platform.

Creates 21 new tables:
  enterprise_digital_twins, digital_twin_snapshots,
  strategic_plans, strategic_objectives,
  strategy_scenarios, scenario_assumptions, scenario_executions,
  climate_stress_tests, supplier_shock_scenarios, financial_stress_tests,
  transition_pathways, net_zero_pathways,
  strategic_risk_projections,
  portfolio_optimizations, investment_scenarios,
  forecast_methodology_records, forecast_models, forecast_results,
  board_simulations, strategic_forecast_summaries,
  strategic_scenario_reports

ORM table count: 188 → 209

Revision ID: 048
Revises: 047
Create Date: 2026-06-22

Migration integrity:
  - All PKs: String(36) UUID
  - FKs with CASCADE:
      digital_twin_snapshots.twin_id → enterprise_digital_twins.id
      strategic_objectives.plan_id → strategic_plans.id
      scenario_assumptions.scenario_id → strategy_scenarios.id
      scenario_executions.scenario_id → strategy_scenarios.id
      net_zero_pathways.pathway_id → transition_pathways.id
      forecast_results.forecast_model_id → forecast_models.id
  - FKs with SET NULL (nullable):
      investment_scenarios.optimization_id → portfolio_optimizations.id
      forecast_models.methodology_record_id → forecast_methodology_records.id
  - Indexes: organization_id on every table; FK columns indexed
  - is_final: all output/report tables have immutability flag
  - BaseModel columns on every table: id, status, version, owner,
    created_by, updated_by, created_at, updated_at
"""

import sqlalchemy as sa
from alembic import op

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def _base():
    """Return a fresh copy of BaseModel columns."""
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
    # ── 1: enterprise_digital_twins ──────────────────────────────────────────
    op.create_table(
        "enterprise_digital_twins",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("twin_version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("business_units", sa.JSON, nullable=True),
        sa.Column("legal_entities", sa.JSON, nullable=True),
        sa.Column("regions", sa.JSON, nullable=True),
        sa.Column("supplier_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("esg_programs", sa.JSON, nullable=True),
        sa.Column("kpi_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("risk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("emissions_baseline_tco2e", sa.Float, nullable=True),
        sa.Column("financial_baseline", sa.JSON, nullable=True),
        sa.Column("assumptions", sa.JSON, nullable=True),
        sa.Column("model_config_data", sa.JSON, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_enterprise_digital_twins_org", "enterprise_digital_twins", ["organization_id"])

    # ── 2: digital_twin_snapshots (child of enterprise_digital_twins) ────────
    op.create_table(
        "digital_twin_snapshots",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "twin_id", sa.String(36),
            sa.ForeignKey("enterprise_digital_twins.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snapshot_type", sa.String(20), nullable=False),
        sa.Column("snapshot_period", sa.String(20), nullable=False),
        sa.Column("sustainability_state", sa.JSON, nullable=True),
        sa.Column("financial_esg_state", sa.JSON, nullable=True),
        sa.Column("hierarchy_state", sa.JSON, nullable=True),
        sa.Column("climate_risk_state", sa.JSON, nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_digital_twin_snapshots_org", "digital_twin_snapshots", ["organization_id"])
    op.create_index("ix_digital_twin_snapshots_twin", "digital_twin_snapshots", ["twin_id"])

    # ── 3: strategic_plans ───────────────────────────────────────────────────
    op.create_table(
        "strategic_plans",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("planning_horizon", sa.String(10), nullable=False),
        sa.Column("baseline_snapshot_id", sa.String(36), nullable=True),
        sa.Column("target_snapshot_id", sa.String(36), nullable=True),
        sa.Column("plan_owner", sa.String(36), nullable=True),
        sa.Column("plan_status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("objectives_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_approved", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_strategic_plans_org", "strategic_plans", ["organization_id"])

    # ── 4: strategic_objectives (child of strategic_plans) ───────────────────
    op.create_table(
        "strategic_objectives",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "plan_id", sa.String(36),
            sa.ForeignKey("strategic_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("objective_type", sa.String(30), nullable=False),
        sa.Column("linked_esg_objective_id", sa.String(36), nullable=True),
        sa.Column("linked_financial_kpi_id", sa.String(36), nullable=True),
        sa.Column("linked_risk_id", sa.String(36), nullable=True),
        sa.Column("current_value", sa.Float, nullable=True),
        sa.Column("target_value", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("target_year", sa.Integer, nullable=True),
        sa.Column("progress_pct", sa.Float, nullable=True),
    )
    op.create_index("ix_strategic_objectives_org", "strategic_objectives", ["organization_id"])
    op.create_index("ix_strategic_objectives_plan", "strategic_objectives", ["plan_id"])

    # ── 5: strategy_scenarios ────────────────────────────────────────────────
    op.create_table(
        "strategy_scenarios",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("scenario_type", sa.String(30), nullable=False),
        sa.Column("scenario_status", sa.String(20), nullable=False, server_default="Draft"),
        sa.Column("baseline_twin_id", sa.String(36), nullable=True),
        sa.Column("time_horizon_years", sa.Integer, nullable=False, server_default="5"),
        sa.Column("created_by_user", sa.String(36), nullable=True),
        sa.Column("is_template", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_strategy_scenarios_org", "strategy_scenarios", ["organization_id"])

    # ── 6: scenario_assumptions (child of strategy_scenarios) ────────────────
    op.create_table(
        "scenario_assumptions",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "scenario_id", sa.String(36),
            sa.ForeignKey("strategy_scenarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("assumption_key", sa.String(100), nullable=False),
        sa.Column("assumption_label", sa.String(255), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("assumption_year", sa.Integer, nullable=True),
    )
    op.create_index("ix_scenario_assumptions_org", "scenario_assumptions", ["organization_id"])
    op.create_index("ix_scenario_assumptions_scenario", "scenario_assumptions", ["scenario_id"])

    # ── 7: scenario_executions (child of strategy_scenarios) ─────────────────
    op.create_table(
        "scenario_executions",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "scenario_id", sa.String(36),
            sa.ForeignKey("strategy_scenarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("twin_id", sa.String(36), nullable=True),
        sa.Column("execution_status", sa.String(20), nullable=False, server_default="Pending"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("projected_kpis", sa.JSON, nullable=True),
        sa.Column("projected_risks", sa.JSON, nullable=True),
        sa.Column("projected_emissions", sa.JSON, nullable=True),
        sa.Column("projected_financial", sa.JSON, nullable=True),
        sa.Column("execution_metadata", sa.JSON, nullable=True),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_scenario_executions_org", "scenario_executions", ["organization_id"])
    op.create_index("ix_scenario_executions_scenario", "scenario_executions", ["scenario_id"])

    # ── 8: climate_stress_tests ───────────────────────────────────────────────
    op.create_table(
        "climate_stress_tests",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("test_name", sa.String(255), nullable=False),
        sa.Column("stress_type", sa.String(30), nullable=False),
        sa.Column("scenario_id", sa.String(36), nullable=True),
        sa.Column("carbon_price_shock_pct", sa.Float, nullable=True),
        sa.Column("physical_risk_multiplier", sa.Float, nullable=True),
        sa.Column("regulatory_intensity_score", sa.Float, nullable=True),
        sa.Column("transition_cost_pct", sa.Float, nullable=True),
        sa.Column("risk_impact", sa.JSON, nullable=True),
        sa.Column("emissions_impact", sa.JSON, nullable=True),
        sa.Column("financial_impact", sa.JSON, nullable=True),
        sa.Column("test_methodology", sa.Text, nullable=True),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_climate_stress_tests_org", "climate_stress_tests", ["organization_id"])

    # ── 9: supplier_shock_scenarios ───────────────────────────────────────────
    op.create_table(
        "supplier_shock_scenarios",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("scenario_name", sa.String(255), nullable=False),
        sa.Column("shock_type", sa.String(30), nullable=False),
        sa.Column("affected_supplier_ids", sa.JSON, nullable=True),
        sa.Column("affected_region", sa.String(100), nullable=True),
        sa.Column("shock_severity", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("propagation_model", sa.String(20), nullable=False, server_default="LINEAR"),
        sa.Column("supply_chain_impact", sa.JSON, nullable=True),
        sa.Column("financial_impact", sa.JSON, nullable=True),
        sa.Column("esg_impact", sa.JSON, nullable=True),
        sa.Column("recovery_timeline_months", sa.Integer, nullable=True),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_supplier_shock_scenarios_org", "supplier_shock_scenarios", ["organization_id"])

    # ── 10: financial_stress_tests ────────────────────────────────────────────
    op.create_table(
        "financial_stress_tests",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("test_name", sa.String(255), nullable=False),
        sa.Column("stress_type", sa.String(30), nullable=False),
        sa.Column("financing_cost_increase_bps", sa.Float, nullable=True),
        sa.Column("green_revenue_decline_pct", sa.Float, nullable=True),
        sa.Column("carbon_tax_increase_pct", sa.Float, nullable=True),
        sa.Column("transition_delay_months", sa.Integer, nullable=True),
        sa.Column("financial_impact", sa.JSON, nullable=True),
        sa.Column("esg_impact", sa.JSON, nullable=True),
        sa.Column("recovery_pathway", sa.Text, nullable=True),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_financial_stress_tests_org", "financial_stress_tests", ["organization_id"])

    # ── 11: transition_pathways ───────────────────────────────────────────────
    op.create_table(
        "transition_pathways",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("pathway_name", sa.String(255), nullable=False),
        sa.Column("pathway_type", sa.String(20), nullable=False),
        sa.Column("baseline_emissions_tco2e", sa.Float, nullable=True),
        sa.Column("target_year", sa.Integer, nullable=False),
        sa.Column("target_emissions_tco2e", sa.Float, nullable=True),
        sa.Column("reduction_pct", sa.Float, nullable=True),
        sa.Column("milestones", sa.JSON, nullable=True),
        sa.Column("strategic_plan_id", sa.String(36), nullable=True),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_transition_pathways_org", "transition_pathways", ["organization_id"])

    # ── 12: net_zero_pathways (child of transition_pathways) ─────────────────
    op.create_table(
        "net_zero_pathways",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "pathway_id", sa.String(36),
            sa.ForeignKey("transition_pathways.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("net_zero_year", sa.Integer, nullable=False),
        sa.Column("interim_targets", sa.JSON, nullable=True),
        sa.Column("assumptions", sa.JSON, nullable=True),
        sa.Column("abatement_cost", sa.Float, nullable=True),
        sa.Column("methodology", sa.String(100), nullable=True),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_net_zero_pathways_org", "net_zero_pathways", ["organization_id"])
    op.create_index("ix_net_zero_pathways_pathway", "net_zero_pathways", ["pathway_id"])

    # ── 13: strategic_risk_projections ────────────────────────────────────────
    op.create_table(
        "strategic_risk_projections",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("risk_id", sa.String(36), nullable=True),
        sa.Column("risk_name", sa.String(255), nullable=False),
        sa.Column("projection_year", sa.Integer, nullable=False),
        sa.Column("likelihood_pct", sa.Float, nullable=False, server_default="0"),
        sa.Column("impact_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("velocity_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("projected_financial_impact", sa.Float, nullable=True),
        sa.Column("scenario_id", sa.String(36), nullable=True),
        sa.Column("methodology", sa.Text, nullable=True),
    )
    op.create_index("ix_strategic_risk_projections_org", "strategic_risk_projections", ["organization_id"])

    # ── 14: portfolio_optimizations ───────────────────────────────────────────
    op.create_table(
        "portfolio_optimizations",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("optimization_name", sa.String(255), nullable=False),
        sa.Column("optimization_objective", sa.String(40), nullable=False),
        sa.Column("total_budget", sa.Float, nullable=True),
        sa.Column("constraint_definitions", sa.JSON, nullable=True),
        sa.Column("initiative_pool", sa.JSON, nullable=True),
        sa.Column("optimal_portfolio", sa.JSON, nullable=True),
        sa.Column("projected_value", sa.Float, nullable=True),
        sa.Column("projected_risk_reduction", sa.Float, nullable=True),
        sa.Column("projected_emissions_reduction", sa.Float, nullable=True),
        sa.Column("methodology", sa.Text, nullable=True),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_portfolio_optimizations_org", "portfolio_optimizations", ["organization_id"])

    # ── 15: investment_scenarios (child of portfolio_optimizations) ───────────
    op.create_table(
        "investment_scenarios",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "optimization_id", sa.String(36),
            sa.ForeignKey("portfolio_optimizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("scenario_name", sa.String(255), nullable=False),
        sa.Column("investment_amount", sa.Float, nullable=False),
        sa.Column("investment_type", sa.String(30), nullable=False),
        sa.Column("projected_value", sa.Float, nullable=True),
        sa.Column("projected_emissions_reduction_tco2e", sa.Float, nullable=True),
        sa.Column("projected_roi_pct", sa.Float, nullable=True),
        sa.Column("time_horizon_years", sa.Integer, nullable=True),
        sa.Column("assumptions", sa.JSON, nullable=True),
        sa.Column("methodology", sa.Text, nullable=True),
    )
    op.create_index("ix_investment_scenarios_org", "investment_scenarios", ["organization_id"])
    op.create_index("ix_investment_scenarios_opt", "investment_scenarios", ["optimization_id"])

    # ── 16: forecast_methodology_records ─────────────────────────────────────
    op.create_table(
        "forecast_methodology_records",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("methodology_name", sa.String(255), nullable=False),
        sa.Column("methodology_version", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("algorithm_type", sa.String(40), nullable=False),
        sa.Column("parameters_schema", sa.JSON, nullable=True),
        sa.Column("explainability_notes", sa.Text, nullable=True),
        sa.Column("is_approved", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column("review_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_forecast_methodology_records_org", "forecast_methodology_records", ["organization_id"])

    # ── 17: forecast_models (child of forecast_methodology_records) ───────────
    op.create_table(
        "forecast_models",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("methodology", sa.String(40), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("parameters", sa.JSON, nullable=True),
        sa.Column("model_version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("is_approved", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("approved_by", sa.String(36), nullable=True),
        sa.Column(
            "methodology_record_id", sa.String(36),
            sa.ForeignKey("forecast_methodology_records.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_forecast_models_org", "forecast_models", ["organization_id"])
    op.create_index("ix_forecast_models_methodology_rec", "forecast_models", ["methodology_record_id"])

    # ── 18: forecast_results (child of forecast_models) ──────────────────────
    op.create_table(
        "forecast_results",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column(
            "forecast_model_id", sa.String(36),
            sa.ForeignKey("forecast_models.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("forecast_type", sa.String(30), nullable=False),
        sa.Column("target_metric", sa.String(100), nullable=False),
        sa.Column("forecast_year", sa.Integer, nullable=False),
        sa.Column("baseline_value", sa.Float, nullable=True),
        sa.Column("forecast_value", sa.Float, nullable=True),
        sa.Column("lower_bound", sa.Float, nullable=True),
        sa.Column("upper_bound", sa.Float, nullable=True),
        sa.Column("confidence_level", sa.Float, nullable=True),
        sa.Column("scenario_id", sa.String(36), nullable=True),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_forecast_results_org", "forecast_results", ["organization_id"])
    op.create_index("ix_forecast_results_model", "forecast_results", ["forecast_model_id"])

    # ── 19: board_simulations ─────────────────────────────────────────────────
    op.create_table(
        "board_simulations",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("simulation_name", sa.String(255), nullable=False),
        sa.Column("scenario_a_id", sa.String(36), nullable=True),
        sa.Column("scenario_b_id", sa.String(36), nullable=True),
        sa.Column("scenario_c_id", sa.String(36), nullable=True),
        sa.Column("comparison_dimensions", sa.JSON, nullable=True),
        sa.Column("scenario_a_results", sa.JSON, nullable=True),
        sa.Column("scenario_b_results", sa.JSON, nullable=True),
        sa.Column("scenario_c_results", sa.JSON, nullable=True),
        sa.Column("recommendation", sa.Text, nullable=True),
        sa.Column("simulated_by", sa.String(36), nullable=True),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_board_simulations_org", "board_simulations", ["organization_id"])

    # ── 20: strategic_forecast_summaries ─────────────────────────────────────
    op.create_table(
        "strategic_forecast_summaries",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("summary_period", sa.String(20), nullable=False),
        sa.Column("forecast_esg_score", sa.Float, nullable=True),
        sa.Column("forecast_emissions_tco2e", sa.Float, nullable=True),
        sa.Column("forecast_green_revenue", sa.Float, nullable=True),
        sa.Column("forecast_risk_exposure", sa.Float, nullable=True),
        sa.Column("forecast_value_creation", sa.Float, nullable=True),
        sa.Column("forecast_taxonomy_alignment_pct", sa.Float, nullable=True),
        sa.Column("data_sources", sa.JSON, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_strategic_forecast_summaries_org", "strategic_forecast_summaries", ["organization_id"])

    # ── 21: strategic_scenario_reports ───────────────────────────────────────
    op.create_table(
        "strategic_scenario_reports",
        *_base(),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("report_title", sa.String(255), nullable=False),
        sa.Column("report_period", sa.String(50), nullable=False),
        sa.Column("included_scenarios", sa.JSON, nullable=True),
        sa.Column("assumptions_snapshot", sa.JSON, nullable=True),
        sa.Column("forecasts_snapshot", sa.JSON, nullable=True),
        sa.Column("stress_tests_snapshot", sa.JSON, nullable=True),
        sa.Column("pathway_outcomes", sa.JSON, nullable=True),
        sa.Column("board_comparison", sa.JSON, nullable=True),
        sa.Column("report_methodology", sa.Text, nullable=True),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_by", sa.String(36), nullable=True),
    )
    op.create_index("ix_strategic_scenario_reports_org", "strategic_scenario_reports", ["organization_id"])


def downgrade() -> None:
    # Drop in reverse FK dependency order (children before parents)

    # Leaf tables (no children)
    op.drop_index("ix_strategic_scenario_reports_org", table_name="strategic_scenario_reports")
    op.drop_table("strategic_scenario_reports")

    op.drop_index("ix_strategic_forecast_summaries_org", table_name="strategic_forecast_summaries")
    op.drop_table("strategic_forecast_summaries")

    op.drop_index("ix_board_simulations_org", table_name="board_simulations")
    op.drop_table("board_simulations")

    # forecast_results (child of forecast_models)
    op.drop_index("ix_forecast_results_model", table_name="forecast_results")
    op.drop_index("ix_forecast_results_org", table_name="forecast_results")
    op.drop_table("forecast_results")

    # forecast_models (child of forecast_methodology_records)
    op.drop_index("ix_forecast_models_methodology_rec", table_name="forecast_models")
    op.drop_index("ix_forecast_models_org", table_name="forecast_models")
    op.drop_table("forecast_models")

    op.drop_index("ix_forecast_methodology_records_org", table_name="forecast_methodology_records")
    op.drop_table("forecast_methodology_records")

    # investment_scenarios (child of portfolio_optimizations)
    op.drop_index("ix_investment_scenarios_opt", table_name="investment_scenarios")
    op.drop_index("ix_investment_scenarios_org", table_name="investment_scenarios")
    op.drop_table("investment_scenarios")

    op.drop_index("ix_portfolio_optimizations_org", table_name="portfolio_optimizations")
    op.drop_table("portfolio_optimizations")

    op.drop_index("ix_strategic_risk_projections_org", table_name="strategic_risk_projections")
    op.drop_table("strategic_risk_projections")

    # net_zero_pathways (child of transition_pathways)
    op.drop_index("ix_net_zero_pathways_pathway", table_name="net_zero_pathways")
    op.drop_index("ix_net_zero_pathways_org", table_name="net_zero_pathways")
    op.drop_table("net_zero_pathways")

    op.drop_index("ix_transition_pathways_org", table_name="transition_pathways")
    op.drop_table("transition_pathways")

    op.drop_index("ix_financial_stress_tests_org", table_name="financial_stress_tests")
    op.drop_table("financial_stress_tests")

    op.drop_index("ix_supplier_shock_scenarios_org", table_name="supplier_shock_scenarios")
    op.drop_table("supplier_shock_scenarios")

    op.drop_index("ix_climate_stress_tests_org", table_name="climate_stress_tests")
    op.drop_table("climate_stress_tests")

    # scenario_executions and scenario_assumptions (children of strategy_scenarios)
    op.drop_index("ix_scenario_executions_scenario", table_name="scenario_executions")
    op.drop_index("ix_scenario_executions_org", table_name="scenario_executions")
    op.drop_table("scenario_executions")

    op.drop_index("ix_scenario_assumptions_scenario", table_name="scenario_assumptions")
    op.drop_index("ix_scenario_assumptions_org", table_name="scenario_assumptions")
    op.drop_table("scenario_assumptions")

    op.drop_index("ix_strategy_scenarios_org", table_name="strategy_scenarios")
    op.drop_table("strategy_scenarios")

    # strategic_objectives (child of strategic_plans)
    op.drop_index("ix_strategic_objectives_plan", table_name="strategic_objectives")
    op.drop_index("ix_strategic_objectives_org", table_name="strategic_objectives")
    op.drop_table("strategic_objectives")

    op.drop_index("ix_strategic_plans_org", table_name="strategic_plans")
    op.drop_table("strategic_plans")

    # digital_twin_snapshots (child of enterprise_digital_twins)
    op.drop_index("ix_digital_twin_snapshots_twin", table_name="digital_twin_snapshots")
    op.drop_index("ix_digital_twin_snapshots_org", table_name="digital_twin_snapshots")
    op.drop_table("digital_twin_snapshots")

    op.drop_index("ix_enterprise_digital_twins_org", table_name="enterprise_digital_twins")
    op.drop_table("enterprise_digital_twins")
