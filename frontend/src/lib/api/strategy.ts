import apiClient from "./client";

const BASE = (orgId: string) => `/strategy/${orgId}`;

// ── Types ─────────────────────────────────────────────────────────────────────

export interface DigitalTwin {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  twin_version: string;
  snapshot_date: string;
  supplier_count: number;
  kpi_count: number;
  risk_count: number;
  emissions_baseline_tco2e: number | null;
  financial_baseline: Record<string, unknown> | null;
  assumptions: Record<string, unknown> | null;
  is_active: boolean;
  is_final: boolean;
  created_at: string;
  updated_at: string;
}

export interface TwinSnapshot {
  id: string;
  organization_id: string;
  twin_id: string;
  snapshot_type: string;
  snapshot_period: string;
  sustainability_state: Record<string, unknown> | null;
  financial_esg_state: Record<string, unknown> | null;
  hierarchy_state: Record<string, unknown> | null;
  climate_risk_state: Record<string, unknown> | null;
  captured_at: string;
  is_final: boolean;
  created_at: string;
}

export interface StrategicPlan {
  id: string;
  organization_id: string;
  title: string;
  planning_horizon: string;
  description: string | null;
  plan_status: string;
  objectives_count: number;
  is_approved: boolean;
  created_at: string;
  updated_at: string;
}

export interface StrategicObjective {
  id: string;
  organization_id: string;
  plan_id: string;
  title: string;
  objective_type: string;
  current_value: number | null;
  target_value: number | null;
  confidence: number | null;
  unit: string | null;
  target_year: number | null;
  progress_pct: number | null;
  created_at: string;
}

export interface Scenario {
  id: string;
  organization_id: string;
  name: string;
  scenario_type: string;
  scenario_status: string;
  description: string | null;
  time_horizon_years: number;
  is_template: boolean;
  created_at: string;
  updated_at: string;
}

export interface ScenarioAssumption {
  id: string;
  scenario_id: string;
  assumption_key: string;
  assumption_label: string;
  value: number;
  unit: string | null;
  rationale: string | null;
  source: string | null;
  assumption_year: number | null;
  created_at: string;
}

export interface ScenarioExecution {
  id: string;
  scenario_id: string;
  twin_id: string | null;
  execution_status: string;
  executed_at: string | null;
  projected_kpis: Record<string, unknown> | null;
  projected_risks: Record<string, unknown> | null;
  projected_emissions: Record<string, unknown> | null;
  projected_financial: Record<string, unknown> | null;
  execution_metadata: Record<string, unknown> | null;
  is_final: boolean;
  created_at: string;
}

export interface ClimateStressTest {
  id: string;
  test_name: string;
  stress_type: string;
  carbon_price_shock_pct: number | null;
  physical_risk_multiplier: number | null;
  regulatory_intensity_score: number | null;
  transition_cost_pct: number | null;
  risk_impact: Record<string, unknown> | null;
  emissions_impact: Record<string, unknown> | null;
  financial_impact: Record<string, unknown> | null;
  is_final: boolean;
  created_at: string;
}

export interface SupplierShock {
  id: string;
  scenario_name: string;
  shock_type: string;
  shock_severity: number;
  affected_region: string | null;
  propagation_model: string;
  supply_chain_impact: Record<string, unknown> | null;
  financial_impact: Record<string, unknown> | null;
  esg_impact: Record<string, unknown> | null;
  recovery_timeline_months: number | null;
  is_final: boolean;
  created_at: string;
}

export interface FinancialStressTest {
  id: string;
  test_name: string;
  stress_type: string;
  financing_cost_increase_bps: number | null;
  green_revenue_decline_pct: number | null;
  carbon_tax_increase_pct: number | null;
  transition_delay_months: number | null;
  financial_impact: Record<string, unknown> | null;
  esg_impact: Record<string, unknown> | null;
  is_final: boolean;
  created_at: string;
}

export interface TransitionPathway {
  id: string;
  pathway_name: string;
  pathway_type: string;
  target_year: number;
  baseline_emissions_tco2e: number | null;
  target_emissions_tco2e: number | null;
  reduction_pct: number | null;
  milestones: Record<string, unknown> | null;
  is_primary: boolean;
  is_final: boolean;
  created_at: string;
}

export interface NetZeroPathway {
  id: string;
  pathway_id: string;
  net_zero_year: number;
  interim_targets: Record<string, unknown> | null;
  abatement_cost: number | null;
  methodology: string | null;
  is_final: boolean;
  created_at: string;
}

export interface ForecastModel {
  id: string;
  model_name: string;
  methodology: string;
  description: string | null;
  parameters: Record<string, unknown> | null;
  model_version: string;
  is_approved: boolean;
  created_at: string;
}

export interface ForecastResult {
  id: string;
  forecast_model_id: string;
  forecast_type: string;
  target_metric: string;
  forecast_year: number;
  baseline_value: number | null;
  forecast_value: number | null;
  lower_bound: number | null;
  upper_bound: number | null;
  confidence_level: number | null;
  is_final: boolean;
  created_at: string;
}

export interface BoardSimulation {
  id: string;
  simulation_name: string;
  scenario_a_id: string | null;
  scenario_b_id: string | null;
  scenario_c_id: string | null;
  comparison_dimensions: Record<string, unknown> | null;
  scenario_a_results: Record<string, unknown> | null;
  scenario_b_results: Record<string, unknown> | null;
  scenario_c_results: Record<string, unknown> | null;
  recommendation: string | null;
  simulated_by: string | null;
  is_final: boolean;
  created_at: string;
}

export interface StrategicReport {
  id: string;
  report_title: string;
  report_period: string;
  included_scenarios: Record<string, unknown> | null;
  assumptions_snapshot: Record<string, unknown> | null;
  forecasts_snapshot: Record<string, unknown> | null;
  stress_tests_snapshot: Record<string, unknown> | null;
  pathway_outcomes: Record<string, unknown> | null;
  board_comparison: Record<string, unknown> | null;
  report_methodology: string | null;
  is_final: boolean;
  finalized_at: string | null;
  created_at: string;
}

export interface StrategyRollup {
  organization_id: string;
  digital_twins: number;
  scenarios: number;
  scenario_executions: number;
  climate_stress_tests: number;
  financial_stress_tests: number;
  total_stress_tests: number;
  forecasts: number;
  board_simulations: number;
  transition_pathways: number;
  finalized_reports: number;
  avg_forecast_value: number | null;
  avg_forecast_emissions: number | null;
  avg_pathway_reduction_pct: number | null;
  scenario_templates: number;
  stress_test_templates: number;
  strategy_methodologies: number;
  scenario_comparisons: number;
}

// M44.1 types

export interface ScenarioTemplate {
  id: string;
  organization_id: string;
  template_name: string;
  template_type: string;
  description: string | null;
  default_assumptions: Record<string, unknown> | null;
  default_time_horizon_years: number;
  scenario_type: string;
  usage_count: number;
  is_approved: boolean;
  created_at: string;
}

export interface StressTestTemplate {
  id: string;
  organization_id: string;
  template_name: string;
  template_type: string;
  default_assumptions: Record<string, unknown> | null;
  methodology: string | null;
  severity_level: string;
  usage_count: number;
  created_at: string;
}

export interface StrategyMethodology {
  id: string;
  organization_id: string;
  methodology_name: string;
  methodology_version: string;
  formula_description: string | null;
  assumptions: Record<string, unknown> | null;
  applicable_to: Record<string, unknown> | null;
  approval_status: string;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
}

export interface ScenarioComparison {
  id: string;
  organization_id: string;
  comparison_name: string;
  scenario_ids: Record<string, unknown> | null;
  kpi_delta: Record<string, unknown> | null;
  emissions_delta: Record<string, unknown> | null;
  risk_delta: Record<string, unknown> | null;
  value_delta: Record<string, unknown> | null;
  comparison_methodology: string | null;
  is_final: boolean;
  created_at: string;
}

// ── API functions ─────────────────────────────────────────────────────────────

export const listDigitalTwins = (orgId: string) =>
  apiClient.get<DigitalTwin[]>(`${BASE(orgId)}/digital-twin`).then((r) => r.data);

export interface CreateDigitalTwinPayload {
  name: string;
  description?: string;
  twin_version?: string;
  supplier_count?: number;
  kpi_count?: number;
  risk_count?: number;
  emissions_baseline_tco2e?: number;
  financial_baseline?: Record<string, unknown>;
  assumptions?: Record<string, unknown>;
  business_units?: Record<string, unknown>;
  legal_entities?: Record<string, unknown>;
  regions?: Record<string, unknown>;
}

export const createDigitalTwin = (orgId: string, payload: CreateDigitalTwinPayload) =>
  apiClient.post<DigitalTwin>(`${BASE(orgId)}/digital-twin`, payload).then((r) => r.data);

export const listSnapshots = (orgId: string, twinId: string) =>
  apiClient.get<TwinSnapshot[]>(`${BASE(orgId)}/digital-twin/${twinId}/snapshots`).then((r) => r.data);

export const listPlans = (orgId: string) =>
  apiClient.get<StrategicPlan[]>(`${BASE(orgId)}/plans`).then((r) => r.data);

export const listObjectives = (orgId: string, planId: string) =>
  apiClient.get<StrategicObjective[]>(`${BASE(orgId)}/plans/${planId}/objectives`).then((r) => r.data);

export const listScenarios = (orgId: string) =>
  apiClient.get<Scenario[]>(`${BASE(orgId)}/scenarios`).then((r) => r.data);

export interface CreateScenarioPayload {
  name: string;
  scenario_type: string;
  description?: string;
  baseline_twin_id?: string;
  time_horizon_years?: number;
  is_template?: boolean;
}

export const createScenario = (orgId: string, payload: CreateScenarioPayload) =>
  apiClient.post<Scenario>(`${BASE(orgId)}/scenarios`, payload).then((r) => r.data);

export const listAssumptions = (orgId: string, scenarioId: string) =>
  apiClient.get<ScenarioAssumption[]>(`${BASE(orgId)}/scenarios/${scenarioId}/assumptions`).then((r) => r.data);

export const listExecutions = (orgId: string) =>
  apiClient.get<ScenarioExecution[]>(`${BASE(orgId)}/executions`).then((r) => r.data);

export const listClimateStressTests = (orgId: string) =>
  apiClient.get<ClimateStressTest[]>(`${BASE(orgId)}/stress-tests/climate`).then((r) => r.data);

export const listSupplierShocks = (orgId: string) =>
  apiClient.get<SupplierShock[]>(`${BASE(orgId)}/stress-tests/supplier-shock`).then((r) => r.data);

export const listFinancialStressTests = (orgId: string) =>
  apiClient.get<FinancialStressTest[]>(`${BASE(orgId)}/stress-tests/financial`).then((r) => r.data);

export interface CreateClimateStressTestPayload {
  test_name: string;
  stress_type: string;
  scenario_id?: string;
  carbon_price_shock_pct?: number;
  physical_risk_multiplier?: number;
  regulatory_intensity_score?: number;
  transition_cost_pct?: number;
  test_methodology?: string;
}
export const createClimateStressTest = (orgId: string, p: CreateClimateStressTestPayload) =>
  apiClient.post<ClimateStressTest>(`${BASE(orgId)}/stress-tests/climate`, p).then((r) => r.data);

export interface CreateSupplierShockPayload {
  scenario_name: string;
  shock_type: string;
  shock_severity: number;
  affected_region?: string;
  propagation_model?: string;
  recovery_timeline_months?: number;
}
export const createSupplierShock = (orgId: string, p: CreateSupplierShockPayload) =>
  apiClient.post<SupplierShock>(`${BASE(orgId)}/stress-tests/supplier-shock`, p).then((r) => r.data);

export interface CreateFinancialStressTestPayload {
  test_name: string;
  stress_type: string;
  financing_cost_increase_bps?: number;
  green_revenue_decline_pct?: number;
  carbon_tax_increase_pct?: number;
  transition_delay_months?: number;
  recovery_pathway?: string;
}
export const createFinancialStressTest = (orgId: string, p: CreateFinancialStressTestPayload) =>
  apiClient.post<FinancialStressTest>(`${BASE(orgId)}/stress-tests/financial`, p).then((r) => r.data);

export const listPathways = (orgId: string) =>
  apiClient.get<TransitionPathway[]>(`${BASE(orgId)}/pathways`).then((r) => r.data);

export interface CreatePathwayPayload {
  pathway_name: string;
  pathway_type: string;
  target_year: number;
  baseline_emissions_tco2e?: number;
  target_emissions_tco2e?: number;
  is_primary?: boolean;
  milestone_frequency?: string;
}

export const createPathway = (orgId: string, payload: CreatePathwayPayload) =>
  apiClient.post<TransitionPathway>(`${BASE(orgId)}/pathways`, payload).then((r) => r.data);

export const listNetZeroPathways = (orgId: string, pathwayId: string) =>
  apiClient.get<NetZeroPathway[]>(`${BASE(orgId)}/pathways/${pathwayId}/net-zero`).then((r) => r.data);

export const listForecastModels = (orgId: string) =>
  apiClient.get<ForecastModel[]>(`${BASE(orgId)}/forecasts/models`).then((r) => r.data);

export const listForecastResults = (orgId: string) =>
  apiClient.get<ForecastResult[]>(`${BASE(orgId)}/forecasts/results`).then((r) => r.data);

export interface CreateForecastModelPayload {
  model_name: string;
  methodology: string;
  description?: string;
  model_version?: string;
}
export const createForecastModel = (orgId: string, p: CreateForecastModelPayload) =>
  apiClient.post<ForecastModel>(`${BASE(orgId)}/forecasts/models`, p).then((r) => r.data);

export interface RunForecastPayload {
  forecast_model_id: string;
  forecast_type: string;
  target_metric: string;
  forecast_year: number;
  baseline_value: number;
  scenario_id?: string;
}
export const runForecast = (orgId: string, p: RunForecastPayload) =>
  apiClient.post<ForecastResult>(`${BASE(orgId)}/forecasts/run`, p).then((r) => r.data);

export const listBoardSimulations = (orgId: string) =>
  apiClient.get<BoardSimulation[]>(`${BASE(orgId)}/board-simulations`).then((r) => r.data);

export interface CreateBoardSimulationPayload {
  simulation_name: string;
  scenario_a_id?: string;
  scenario_b_id?: string;
  scenario_c_id?: string;
  recommendation?: string;
}
export const createBoardSimulation = (orgId: string, p: CreateBoardSimulationPayload) =>
  apiClient.post<BoardSimulation>(`${BASE(orgId)}/board-simulations`, p).then((r) => r.data);

export const listReports = (orgId: string) =>
  apiClient.get<StrategicReport[]>(`${BASE(orgId)}/reports`).then((r) => r.data);

export interface CreateReportPayload {
  report_title: string;
  report_period: string;
  included_scenario_ids?: string[];
  report_methodology?: string;
}
export const createReport = (orgId: string, p: CreateReportPayload) =>
  apiClient.post<StrategicReport>(`${BASE(orgId)}/reports`, p).then((r) => r.data);

export const getStrategyRollup = (orgId: string) =>
  apiClient.get<StrategyRollup>(`${BASE(orgId)}/rollup`).then((r) => r.data);

// M44.1 API functions

export const listScenarioTemplates = (orgId: string) =>
  apiClient.get<ScenarioTemplate[]>(`${BASE(orgId)}/templates/scenarios`).then((r) => r.data);

export interface CreateScenarioTemplatePayload {
  template_name: string;
  template_type: string;
  scenario_type: string;
  description?: string;
  default_time_horizon_years?: number;
}
export const createScenarioTemplate = (orgId: string, p: CreateScenarioTemplatePayload) =>
  apiClient.post<ScenarioTemplate>(`${BASE(orgId)}/templates/scenarios`, p).then((r) => r.data);

export const listStressTestTemplates = (orgId: string) =>
  apiClient.get<StressTestTemplate[]>(`${BASE(orgId)}/templates/stress-tests`).then((r) => r.data);

export interface CreateStressTestTemplatePayload {
  template_name: string;
  template_type: string;
  methodology?: string;
  severity_level?: string;
}
export const createStressTestTemplate = (orgId: string, p: CreateStressTestTemplatePayload) =>
  apiClient.post<StressTestTemplate>(`${BASE(orgId)}/templates/stress-tests`, p).then((r) => r.data);

export const listMethodologies = (orgId: string) =>
  apiClient.get<StrategyMethodology[]>(`${BASE(orgId)}/methodologies`).then((r) => r.data);

export const listComparisons = (orgId: string) =>
  apiClient.get<ScenarioComparison[]>(`${BASE(orgId)}/comparisons`).then((r) => r.data);

export const runScenario = (orgId: string, scenarioId: string) =>
  apiClient
    .post<ScenarioExecution>(`${BASE(orgId)}/scenarios/${scenarioId}/execute`, {})
    .then((r) => r.data);
