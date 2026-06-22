"""M44 — Digital Twin, Strategic Planning & Scenario Intelligence ORM Models.

21 new tables:
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
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel

# ── Enum constants ─────────────────────────────────────────────────────────────

SNAPSHOT_TYPES = ("MONTHLY", "QUARTERLY", "ANNUAL")

PLANNING_HORIZONS = ("1Y", "3Y", "5Y", "10Y")
PLAN_STATUSES = ("Draft", "Active", "Approved", "Archived")

OBJECTIVE_TYPES = ("ESG", "FINANCIAL", "RISK", "EMISSIONS", "COMBINED")

SCENARIO_TYPES = ("CLIMATE", "REGULATORY", "FINANCIAL", "SUPPLY_CHAIN", "COMBINED")
SCENARIO_STATUSES = ("Draft", "Active", "Archived")

CLIMATE_STRESS_TYPES = (
    "TRANSITION_SHOCK", "PHYSICAL_RISK", "CARBON_PRICE", "REGULATORY",
)
SUPPLIER_SHOCK_TYPES = (
    "SUPPLIER_FAILURE", "REGIONAL_DISRUPTION", "SANCTIONS", "ESG_INCIDENT",
)
PROPAGATION_MODELS = ("LINEAR", "NETWORK")

FINANCIAL_STRESS_TYPES = (
    "FINANCING_COST", "GREEN_REVENUE_DECLINE", "CARBON_TAX", "TRANSITION_DELAY",
)

PATHWAY_TYPES = ("CONSERVATIVE", "EXPECTED", "ACCELERATED", "CUSTOM")

OPTIMIZATION_OBJECTIVES = (
    "MAXIMIZE_VALUE", "MINIMIZE_RISK", "MAXIMIZE_EMISSIONS_REDUCTION",
)
INVESTMENT_TYPES = ("ESG_INITIATIVE", "DECARBONIZATION", "RISK_REDUCTION")

FORECAST_METHODOLOGIES = (
    "LINEAR_TREND", "WEIGHTED_MOVING_AVERAGE", "SCENARIO_PROJECTION",
)
FORECAST_TYPES = (
    "KPI", "EMISSIONS", "TARGETS", "GREEN_REVENUE", "TAXONOMY",
)

# M44.1 additions
MILESTONE_FREQUENCIES = ("ANNUAL", "SEMIANNUAL", "QUARTERLY")
SCENARIO_TEMPLATE_TYPES = (
    "NET_ZERO", "CARBON_PRICE_SHOCK", "SUPPLIER_FAILURE",
    "REGULATORY_TIGHTENING", "TAXONOMY_EXPANSION", "CLIMATE_DISASTER",
)
METHODOLOGY_APPROVAL_STATUSES = ("DRAFT", "APPROVED", "DEPRECATED")
STRESS_TEST_TEMPLATE_TYPES = ("CLIMATE", "FINANCIAL", "REGULATORY", "SUPPLY_CHAIN")
SEVERITY_LEVELS = ("LOW", "MEDIUM", "HIGH", "EXTREME")
TREND_DIRECTIONS = ("IMPROVING", "STABLE", "DECLINING")


# ── Section 1: Enterprise Digital Twin ────────────────────────────────────────

class EnterpriseDigitalTwinModel(BaseModel):
    __tablename__ = "enterprise_digital_twins"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    twin_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    business_units: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    legal_entities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    regions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    supplier_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    esg_programs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    kpi_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    emissions_baseline_tco2e: Mapped[float | None] = mapped_column(Float, nullable=True)
    financial_baseline: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assumptions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_config_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 2: Digital Twin Snapshot ─────────────────────────────────────────

class DigitalTwinSnapshotModel(BaseModel):
    __tablename__ = "digital_twin_snapshots"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    twin_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("enterprise_digital_twins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_type: Mapped[str] = mapped_column(String(20), nullable=False)
    snapshot_period: Mapped[str] = mapped_column(String(20), nullable=False)
    sustainability_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    financial_esg_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hierarchy_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    climate_risk_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 3: Strategic Plan ─────────────────────────────────────────────────

class StrategicPlanModel(BaseModel):
    __tablename__ = "strategic_plans"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    planning_horizon: Mapped[str] = mapped_column(String(10), nullable=False)
    baseline_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    target_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    plan_owner: Mapped[str | None] = mapped_column(String(36), nullable=True)
    plan_status: Mapped[str] = mapped_column(String(20), nullable=False, default="Draft")
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    objectives_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 4: Strategic Objective ───────────────────────────────────────────

class StrategicObjectiveModel(BaseModel):
    __tablename__ = "strategic_objectives"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("strategic_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective_type: Mapped[str] = mapped_column(String(30), nullable=False)
    linked_esg_objective_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    linked_financial_kpi_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    linked_risk_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    progress_pct: Mapped[float | None] = mapped_column(Float, nullable=True)


# ── Section 5: Scenario ───────────────────────────────────────────────────────

class StrategyScenarioModel(BaseModel):
    __tablename__ = "strategy_scenarios"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scenario_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scenario_status: Mapped[str] = mapped_column(String(20), nullable=False, default="Draft")
    baseline_twin_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    time_horizon_years: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    created_by_user: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_template: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 6: Scenario Assumption ───────────────────────────────────────────

class ScenarioAssumptionModel(BaseModel):
    __tablename__ = "scenario_assumptions"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("strategy_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assumption_key: Mapped[str] = mapped_column(String(100), nullable=False)
    assumption_label: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assumption_year: Mapped[int | None] = mapped_column(Integer, nullable=True)


# ── Section 7: Scenario Execution ────────────────────────────────────────────

class ScenarioExecutionModel(BaseModel):
    __tablename__ = "scenario_executions"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("strategy_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    twin_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    execution_status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending")
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    projected_kpis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    projected_risks: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    projected_emissions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    projected_financial: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    execution_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 8: Climate Stress Test ───────────────────────────────────────────

class ClimateStressTestModel(BaseModel):
    __tablename__ = "climate_stress_tests"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stress_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scenario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    carbon_price_shock_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    physical_risk_multiplier: Mapped[float | None] = mapped_column(Float, nullable=True)
    regulatory_intensity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    transition_cost_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_impact: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    emissions_impact: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    financial_impact: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    test_methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 9: Supplier Shock Scenario ───────────────────────────────────────

class SupplierShockScenarioModel(BaseModel):
    __tablename__ = "supplier_shock_scenarios"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    shock_type: Mapped[str] = mapped_column(String(30), nullable=False)
    affected_supplier_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    affected_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shock_severity: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    propagation_model: Mapped[str] = mapped_column(String(20), nullable=False, default="LINEAR")
    supply_chain_impact: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    financial_impact: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    esg_impact: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recovery_timeline_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 10: Financial Stress Test ────────────────────────────────────────

class FinancialStressTestModel(BaseModel):
    __tablename__ = "financial_stress_tests"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stress_type: Mapped[str] = mapped_column(String(30), nullable=False)
    financing_cost_increase_bps: Mapped[float | None] = mapped_column(Float, nullable=True)
    green_revenue_decline_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbon_tax_increase_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    transition_delay_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    financial_impact: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    esg_impact: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recovery_pathway: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 11: Transition Pathway ───────────────────────────────────────────

class TransitionPathwayModel(BaseModel):
    __tablename__ = "transition_pathways"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    pathway_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pathway_type: Mapped[str] = mapped_column(String(20), nullable=False)
    baseline_emissions_tco2e: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    target_emissions_tco2e: Mapped[float | None] = mapped_column(Float, nullable=True)
    reduction_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    milestones: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    strategic_plan_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    milestone_frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="ANNUAL")
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 12: Net Zero Pathway ─────────────────────────────────────────────

class NetZeroPathwayRecord(BaseModel):
    __tablename__ = "net_zero_pathways"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    pathway_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transition_pathways.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    net_zero_year: Mapped[int] = mapped_column(Integer, nullable=False)
    interim_targets: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assumptions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    abatement_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    methodology: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 13: Strategic Risk Projection ────────────────────────────────────

class StrategicRiskProjectionModel(BaseModel):
    __tablename__ = "strategic_risk_projections"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    risk_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    risk_name: Mapped[str] = mapped_column(String(255), nullable=False)
    projection_year: Mapped[int] = mapped_column(Integer, nullable=False)
    likelihood_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    velocity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    projected_financial_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    scenario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Section 14: Portfolio Optimization ───────────────────────────────────────

class PortfolioOptimizationModel(BaseModel):
    __tablename__ = "portfolio_optimizations"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    optimization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    optimization_objective: Mapped[str] = mapped_column(String(40), nullable=False)
    total_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    constraint_definitions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    initiative_pool: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    optimal_portfolio: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    projected_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    projected_risk_reduction: Mapped[float | None] = mapped_column(Float, nullable=True)
    projected_emissions_reduction: Mapped[float | None] = mapped_column(Float, nullable=True)
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 15: Investment Scenario ──────────────────────────────────────────

class InvestmentScenarioModel(BaseModel):
    __tablename__ = "investment_scenarios"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    optimization_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("portfolio_optimizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    investment_amount: Mapped[float] = mapped_column(Float, nullable=False)
    investment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    projected_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    projected_emissions_reduction_tco2e: Mapped[float | None] = mapped_column(Float, nullable=True)
    projected_roi_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_horizon_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assumptions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── Section 16: Forecast Methodology Record (AI Governance) ──────────────────

class ForecastMethodologyRecordModel(BaseModel):
    __tablename__ = "forecast_methodology_records"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    methodology_name: Mapped[str] = mapped_column(String(255), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    algorithm_type: Mapped[str] = mapped_column(String(40), nullable=False)
    parameters_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    explainability_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Section 17: Forecast Model ────────────────────────────────────────────────

class ForecastModelRecord(BaseModel):
    __tablename__ = "forecast_models"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    methodology: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    methodology_record_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("forecast_methodology_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


# ── Section 18: Forecast Result ───────────────────────────────────────────────

class ForecastResultModel(BaseModel):
    __tablename__ = "forecast_results"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    forecast_model_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("forecast_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    forecast_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_metric: Mapped[str] = mapped_column(String(100), nullable=False)
    forecast_year: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    lower_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    scenario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 19: Board Simulation ──────────────────────────────────────────────

class BoardSimulationModel(BaseModel):
    __tablename__ = "board_simulations"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    simulation_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_a_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    scenario_b_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    scenario_c_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    comparison_dimensions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scenario_a_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scenario_b_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scenario_c_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    simulated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 20: Strategic Forecast Summary ────────────────────────────────────

class StrategicForecastSummaryModel(BaseModel):
    __tablename__ = "strategic_forecast_summaries"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    summary_period: Mapped[str] = mapped_column(String(20), nullable=False)
    forecast_esg_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_emissions_tco2e: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_green_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_risk_exposure: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_value_creation: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_taxonomy_alignment_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_sources: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trend_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    forecast_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    pathway_progress_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    scenario_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── Section 21: Strategic Scenario Report ────────────────────────────────────

class StrategicScenarioReportModel(BaseModel):
    __tablename__ = "strategic_scenario_reports"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    report_title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_period: Mapped[str] = mapped_column(String(50), nullable=False)
    included_scenarios: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assumptions_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    forecasts_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stress_tests_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pathway_outcomes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    board_comparison: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    report_methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    methodology_appendix: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    assumption_appendix: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sensitivity_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    comparison_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)


# ── M44.1 Section 22: Scenario Template ──────────────────────────────────────

class ScenarioTemplateModel(BaseModel):
    __tablename__ = "scenario_templates"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_assumptions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    default_time_horizon_years: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    scenario_type: Mapped[str] = mapped_column(String(20), nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── M44.1 Section 23: Strategy Methodology ───────────────────────────────────

class StrategyMethodologyModel(BaseModel):
    __tablename__ = "strategy_methodologies"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    methodology_name: Mapped[str] = mapped_column(String(255), nullable=False)
    methodology_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    formula_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assumptions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    applicable_to: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approval_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── M44.1 Section 24: Scenario Comparison ────────────────────────────────────

class ScenarioComparisonModel(BaseModel):
    __tablename__ = "scenario_comparisons"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    comparison_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    kpi_delta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    emissions_delta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    risk_delta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    value_delta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    comparison_methodology: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ── M44.1 Section 25: Stress Test Template ───────────────────────────────────

class StressTestTemplateModel(BaseModel):
    __tablename__ = "stress_test_templates"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[str] = mapped_column(String(20), nullable=False)
    default_assumptions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity_level: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# ── M44.1 Section 26: Forecast Window Policy ─────────────────────────────────

class ForecastWindowPolicyModel(BaseModel):
    __tablename__ = "forecast_window_policies"

    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    min_window: Mapped[int] = mapped_column(Integer, nullable=False)
    max_window: Mapped[int] = mapped_column(Integer, nullable=False)
    default_window: Mapped[int] = mapped_column(Integer, nullable=False)
    applicable_methodology: Mapped[str] = mapped_column(
        String(40), nullable=False, default="WEIGHTED_MOVING_AVERAGE"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
