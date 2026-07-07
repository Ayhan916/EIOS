"""M44 — Strategy Platform Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ── Digital Twin ──────────────────────────────────────────────────────────────


class DigitalTwinCreate(BaseModel):
    name: str
    description: str | None = None
    twin_version: str = "1.0.0"
    supplier_count: int = 0
    kpi_count: int = 0
    risk_count: int = 0
    emissions_baseline_tco2e: float | None = None
    financial_baseline: dict[str, Any] | None = None
    assumptions: dict[str, Any] | None = None
    business_units: dict[str, Any] | None = None
    legal_entities: dict[str, Any] | None = None
    regions: dict[str, Any] | None = None


class DigitalTwinResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None = None
    twin_version: str
    snapshot_date: datetime
    supplier_count: int
    kpi_count: int
    risk_count: int
    emissions_baseline_tco2e: float | None = None
    financial_baseline: dict[str, Any] | None = None
    assumptions: dict[str, Any] | None = None
    is_active: bool
    is_final: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SnapshotCreate(BaseModel):
    snapshot_type: str
    snapshot_period: str
    sustainability_state: dict[str, Any] | None = None
    financial_esg_state: dict[str, Any] | None = None
    hierarchy_state: dict[str, Any] | None = None
    climate_risk_state: dict[str, Any] | None = None


class SnapshotResponse(BaseModel):
    id: str
    organization_id: str
    twin_id: str
    snapshot_type: str
    snapshot_period: str
    sustainability_state: dict[str, Any] | None = None
    financial_esg_state: dict[str, Any] | None = None
    hierarchy_state: dict[str, Any] | None = None
    climate_risk_state: dict[str, Any] | None = None
    captured_at: datetime
    is_final: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Strategic Plan ─────────────────────────────────────────────────────────────


class StrategicPlanCreate(BaseModel):
    title: str
    planning_horizon: str
    description: str | None = None
    baseline_snapshot_id: str | None = None
    target_snapshot_id: str | None = None
    plan_owner: str | None = None


class StrategicPlanResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    planning_horizon: str
    description: str | None = None
    plan_status: str
    baseline_snapshot_id: str | None = None
    target_snapshot_id: str | None = None
    plan_owner: str | None = None
    objectives_count: int
    is_approved: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StrategicObjectiveCreate(BaseModel):
    title: str
    objective_type: str
    linked_esg_objective_id: str | None = None
    linked_financial_kpi_id: str | None = None
    linked_risk_id: str | None = None
    current_value: float | None = None
    target_value: float | None = None
    confidence: float | None = None
    unit: str | None = None
    target_year: int | None = None


class StrategicObjectiveResponse(BaseModel):
    id: str
    organization_id: str
    plan_id: str
    title: str
    objective_type: str
    linked_esg_objective_id: str | None = None
    linked_financial_kpi_id: str | None = None
    linked_risk_id: str | None = None
    current_value: float | None = None
    target_value: float | None = None
    confidence: float | None = None
    unit: str | None = None
    target_year: int | None = None
    progress_pct: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Scenario ──────────────────────────────────────────────────────────────────


class ScenarioCreate(BaseModel):
    name: str
    scenario_type: str
    description: str | None = None
    baseline_twin_id: str | None = None
    time_horizon_years: int = 5
    is_template: bool = False


class ScenarioResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    scenario_type: str
    scenario_status: str
    description: str | None = None
    baseline_twin_id: str | None = None
    time_horizon_years: int
    is_template: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssumptionCreate(BaseModel):
    assumption_key: str
    assumption_label: str
    value: float
    unit: str | None = None
    rationale: str | None = None
    source: str | None = None
    assumption_year: int | None = None


class AssumptionResponse(BaseModel):
    id: str
    organization_id: str
    scenario_id: str
    assumption_key: str
    assumption_label: str
    value: float
    unit: str | None = None
    rationale: str | None = None
    source: str | None = None
    assumption_year: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ExecutionCreate(BaseModel):
    twin_id: str | None = None
    baseline_override: dict[str, Any] | None = None


class ExecutionResponse(BaseModel):
    id: str
    organization_id: str
    scenario_id: str
    twin_id: str | None = None
    execution_status: str
    executed_at: datetime | None = None
    projected_kpis: dict[str, Any] | None = None
    projected_risks: dict[str, Any] | None = None
    projected_emissions: dict[str, Any] | None = None
    projected_financial: dict[str, Any] | None = None
    execution_metadata: dict[str, Any] | None = None
    is_final: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Stress Tests ──────────────────────────────────────────────────────────────


class ClimateStressTestCreate(BaseModel):
    test_name: str
    stress_type: str
    scenario_id: str | None = None
    carbon_price_shock_pct: float | None = None
    physical_risk_multiplier: float | None = None
    regulatory_intensity_score: float | None = None
    transition_cost_pct: float | None = None
    test_methodology: str | None = None


class ClimateStressTestResponse(BaseModel):
    id: str
    organization_id: str
    test_name: str
    stress_type: str
    scenario_id: str | None = None
    carbon_price_shock_pct: float | None = None
    physical_risk_multiplier: float | None = None
    regulatory_intensity_score: float | None = None
    transition_cost_pct: float | None = None
    risk_impact: dict[str, Any] | None = None
    emissions_impact: dict[str, Any] | None = None
    financial_impact: dict[str, Any] | None = None
    test_methodology: str | None = None
    is_final: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SupplierShockCreate(BaseModel):
    scenario_name: str
    shock_type: str
    shock_severity: float = Field(ge=0.0, le=1.0)
    affected_supplier_ids: list[str] | None = None
    affected_region: str | None = None
    propagation_model: str = "LINEAR"
    recovery_timeline_months: int | None = None


class SupplierShockResponse(BaseModel):
    id: str
    organization_id: str
    scenario_name: str
    shock_type: str
    shock_severity: float
    affected_region: str | None = None
    propagation_model: str
    supply_chain_impact: dict[str, Any] | None = None
    financial_impact: dict[str, Any] | None = None
    esg_impact: dict[str, Any] | None = None
    recovery_timeline_months: int | None = None
    is_final: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FinancialStressTestCreate(BaseModel):
    test_name: str
    stress_type: str
    financing_cost_increase_bps: float | None = None
    green_revenue_decline_pct: float | None = None
    carbon_tax_increase_pct: float | None = None
    transition_delay_months: int | None = None
    recovery_pathway: str | None = None


class FinancialStressTestResponse(BaseModel):
    id: str
    organization_id: str
    test_name: str
    stress_type: str
    financing_cost_increase_bps: float | None = None
    green_revenue_decline_pct: float | None = None
    carbon_tax_increase_pct: float | None = None
    transition_delay_months: int | None = None
    financial_impact: dict[str, Any] | None = None
    esg_impact: dict[str, Any] | None = None
    recovery_pathway: str | None = None
    is_final: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Pathways ──────────────────────────────────────────────────────────────────


class TransitionPathwayCreate(BaseModel):
    pathway_name: str
    pathway_type: str
    target_year: int
    baseline_emissions_tco2e: float | None = None
    target_emissions_tco2e: float | None = None
    strategic_plan_id: str | None = None
    is_primary: bool = False


class TransitionPathwayResponse(BaseModel):
    id: str
    organization_id: str
    pathway_name: str
    pathway_type: str
    target_year: int
    baseline_emissions_tco2e: float | None = None
    target_emissions_tco2e: float | None = None
    reduction_pct: float | None = None
    milestones: dict[str, Any] | None = None
    is_primary: bool
    is_final: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NetZeroPathwayCreate(BaseModel):
    net_zero_year: int
    interim_targets: list[dict[str, Any]] | None = None
    assumptions: dict[str, Any] | None = None
    abatement_cost: float | None = None
    methodology: str | None = None


class NetZeroPathwayResponse(BaseModel):
    id: str
    organization_id: str
    pathway_id: str
    net_zero_year: int
    interim_targets: dict[str, Any] | None = None
    assumptions: dict[str, Any] | None = None
    abatement_cost: float | None = None
    methodology: str | None = None
    is_final: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Forecasts ─────────────────────────────────────────────────────────────────


class ForecastModelCreate(BaseModel):
    model_name: str
    methodology: str
    description: str | None = None
    parameters: dict[str, Any] | None = None
    model_version: str = "1.0.0"
    methodology_record_id: str | None = None


class ForecastModelResponse(BaseModel):
    id: str
    organization_id: str
    model_name: str
    methodology: str
    description: str | None = None
    parameters: dict[str, Any] | None = None
    model_version: str
    is_approved: bool
    methodology_record_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ForecastRunCreate(BaseModel):
    forecast_model_id: str
    forecast_type: str
    target_metric: str
    forecast_year: int
    baseline_value: float
    scenario_id: str | None = None
    parameter_overrides: dict[str, Any] | None = None


class ForecastResultResponse(BaseModel):
    id: str
    organization_id: str
    forecast_model_id: str
    forecast_type: str
    target_metric: str
    forecast_year: int
    baseline_value: float | None = None
    forecast_value: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    confidence_level: float | None = None
    scenario_id: str | None = None
    is_final: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Board Simulation ──────────────────────────────────────────────────────────


class BoardSimulationCreate(BaseModel):
    simulation_name: str
    scenario_a_id: str | None = None
    scenario_b_id: str | None = None
    scenario_c_id: str | None = None
    recommendation: str | None = None


class BoardSimulationResponse(BaseModel):
    id: str
    organization_id: str
    simulation_name: str
    scenario_a_id: str | None = None
    scenario_b_id: str | None = None
    scenario_c_id: str | None = None
    comparison_dimensions: dict[str, Any] | None = None
    scenario_a_results: dict[str, Any] | None = None
    scenario_b_results: dict[str, Any] | None = None
    scenario_c_results: dict[str, Any] | None = None
    recommendation: str | None = None
    simulated_by: str | None = None
    is_final: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Reports ───────────────────────────────────────────────────────────────────


class StrategicReportCreate(BaseModel):
    report_title: str
    report_period: str
    included_scenario_ids: list[str] | None = None
    board_comparison: dict[str, Any] | None = None
    report_methodology: str | None = None


class StrategicReportResponse(BaseModel):
    id: str
    organization_id: str
    report_title: str
    report_period: str
    included_scenarios: dict[str, Any] | None = None
    assumptions_snapshot: dict[str, Any] | None = None
    forecasts_snapshot: dict[str, Any] | None = None
    stress_tests_snapshot: dict[str, Any] | None = None
    pathway_outcomes: dict[str, Any] | None = None
    board_comparison: dict[str, Any] | None = None
    report_methodology: str | None = None
    is_final: bool
    finalized_at: datetime | None = None
    finalized_by: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Rollup ────────────────────────────────────────────────────────────────────


class StrategyRollupResponse(BaseModel):
    organization_id: str
    digital_twins: int
    scenarios: int
    scenario_executions: int
    climate_stress_tests: int
    financial_stress_tests: int
    total_stress_tests: int
    forecasts: int
    board_simulations: int
    transition_pathways: int
    finalized_reports: int
    avg_forecast_value: float | None = None
    avg_forecast_emissions: float | None = None
    avg_pathway_reduction_pct: float | None = None
    scenario_templates: int = 0
    stress_test_templates: int = 0
    strategy_methodologies: int = 0
    scenario_comparisons: int = 0


# ── M44.1: Scenario Templates ─────────────────────────────────────────────────


class ScenarioTemplateCreate(BaseModel):
    template_name: str
    template_type: str
    scenario_type: str
    description: str | None = None
    default_assumptions: dict[str, Any] | None = None
    default_time_horizon_years: int = 5


class ScenarioTemplateResponse(BaseModel):
    id: str
    organization_id: str
    template_name: str
    template_type: str
    description: str | None = None
    default_assumptions: dict[str, Any] | None = None
    default_time_horizon_years: int
    scenario_type: str
    usage_count: int
    is_approved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateInstantiateCreate(BaseModel):
    scenario_name: str
    assumption_overrides: dict[str, Any] | None = None
    time_horizon_years: int | None = None


# ── M44.1: Stress Test Templates ─────────────────────────────────────────────


class StressTestTemplateCreate(BaseModel):
    template_name: str
    template_type: str
    default_assumptions: dict[str, Any] | None = None
    methodology: str | None = None
    severity_level: str = "MEDIUM"


class StressTestTemplateResponse(BaseModel):
    id: str
    organization_id: str
    template_name: str
    template_type: str
    default_assumptions: dict[str, Any] | None = None
    methodology: str | None = None
    severity_level: str
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── M44.1: Strategy Methodologies ─────────────────────────────────────────────


class StrategyMethodologyCreate(BaseModel):
    methodology_name: str
    methodology_version: str = "1.0.0"
    formula_description: str | None = None
    assumptions: dict[str, Any] | None = None
    applicable_to: list[str] | None = None


class StrategyMethodologyResponse(BaseModel):
    id: str
    organization_id: str
    methodology_name: str
    methodology_version: str
    formula_description: str | None = None
    assumptions: dict[str, Any] | None = None
    applicable_to: dict[str, Any] | None = None
    approval_status: str
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── M44.1: Scenario Comparisons ───────────────────────────────────────────────


class ScenarioComparisonCreate(BaseModel):
    comparison_name: str
    scenario_ids: list[str]
    comparison_methodology: str = "delta_vs_baseline"


class ScenarioComparisonResponse(BaseModel):
    id: str
    organization_id: str
    comparison_name: str
    scenario_ids: dict[str, Any] | None = None
    kpi_delta: dict[str, Any] | None = None
    emissions_delta: dict[str, Any] | None = None
    risk_delta: dict[str, Any] | None = None
    value_delta: dict[str, Any] | None = None
    comparison_methodology: str | None = None
    is_final: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── M44.1: Forecast Window Policies ───────────────────────────────────────────


class ForecastWindowPolicyCreate(BaseModel):
    policy_name: str
    min_window: int
    max_window: int
    default_window: int
    applicable_methodology: str = "WEIGHTED_MOVING_AVERAGE"


class ForecastWindowPolicyResponse(BaseModel):
    id: str
    organization_id: str
    policy_name: str
    min_window: int
    max_window: int
    default_window: int
    applicable_methodology: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
