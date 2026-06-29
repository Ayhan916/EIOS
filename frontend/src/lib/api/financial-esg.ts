import apiClient from "./client";

const BASE = (orgId: string) => `/financial-esg/${orgId}`;

// ── Types ─────────────────────────────────────────────────────────────────────

export interface FinancialKPI {
  id: string;
  organization_id: string;
  name: string;
  category: string;
  formula: string | null;
  unit: string | null;
  frequency: string;
  owner_user_id: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface KPIMeasurement {
  id: string;
  organization_id: string;
  kpi_id: string;
  period: string;
  value: number;
  source: string | null;
  confidence: number | null;
  calculated_at: string;
  notes: string | null;
  created_at: string;
}

export interface CarbonCostModel {
  id: string;
  organization_id: string;
  name: string;
  assessment_year: number;
  total_emissions: number;
  internal_carbon_price: number;
  regulatory_carbon_price: number;
  avoided_emissions: number;
  avoided_cost: number;
  total_carbon_cost: number;
  regulatory_exposure: number;
  formula: Record<string, unknown> | null;
  currency: string;
  created_at: string;
}

export interface CostOfRisk {
  id: string;
  organization_id: string;
  name: string;
  assessment_date: string;
  supplier_risk_score: number;
  climate_risk_score: number;
  compliance_risk_score: number;
  operational_risk_score: number;
  exposure_base: number;
  composite_risk_score: number;
  estimated_financial_exposure: number;
  expected_loss: number;
  risk_adjusted_exposure: number;
  methodology: Record<string, unknown> | null;
  currency: string;
  created_at: string;
}

export interface ValueInitiative {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  investment_amount: number;
  expected_value: number;
  realized_value: number;
  roi_percent: number | null;
  payback_period_months: number | null;
  initiative_status: string;
  start_date: string | null;
  end_date: string | null;
  currency: string;
  category: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinanceInstrument {
  id: string;
  organization_id: string;
  name: string;
  instrument_type: string;
  amount: number;
  currency: string;
  maturity_date: string | null;
  covenant_status: string;
  issuer: string | null;
  counterparty: string | null;
  description: string | null;
  kpi_linkage: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface LinkedKPI {
  id: string;
  organization_id: string;
  instrument_id: string;
  esg_target_id: string | null;
  kpi_name: string;
  kpi_description: string | null;
  threshold_value: number | null;
  threshold_direction: string;
  covenant_status: string;
  last_assessed_at: string | null;
  current_value: number | null;
  created_at: string;
}

export interface TransitionPlan {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  baseline_state: Record<string, unknown> | null;
  target_state: Record<string, unknown> | null;
  financing_needs: number;
  funding_sources: Record<string, unknown> | null;
  plan_status: string;
  start_date: string | null;
  target_date: string | null;
  currency: string;
  created_at: string;
  updated_at: string;
}

export interface TaxonomyAssessment {
  id: string;
  organization_id: string;
  taxonomy_framework: string;
  assessment_year: number;
  eligible_activities: Record<string, unknown> | null;
  aligned_activities: Record<string, unknown> | null;
  eligible_percent: number;
  aligned_percent: number;
  justification: string | null;
  assessment_status: string;
  total_revenue: number | null;
  total_capex: number | null;
  total_opex: number | null;
  created_at: string;
  updated_at: string;
}

export interface GreenRevenue {
  id: string;
  organization_id: string;
  revenue_stream: string;
  taxonomy_category: string | null;
  amount: number;
  currency: string;
  period: string;
  alignment_status: string;
  total_revenue: number;
  green_revenue_percent: number;
  notes: string | null;
  created_at: string;
}

export interface GreenCapex {
  id: string;
  organization_id: string;
  project_name: string;
  taxonomy_category: string | null;
  amount: number;
  currency: string;
  alignment_percent: number;
  period: string;
  notes: string | null;
  created_at: string;
}

export interface GreenOpex {
  id: string;
  organization_id: string;
  description: string;
  category: string | null;
  amount: number;
  currency: string;
  alignment_percent: number;
  period: string;
  notes: string | null;
  created_at: string;
}

export interface CapitalMarketsAssessment {
  id: string;
  organization_id: string;
  disclosure_readiness: string;
  assurance_readiness: string;
  taxonomy_readiness: string;
  kpi_readiness: string;
  overall_readiness: string;
  assessment_notes: Record<string, unknown> | null;
  assessed_at: string;
  created_at: string;
}

export interface DisclosurePackage {
  id: string;
  organization_id: string;
  title: string;
  description: string | null;
  period_start: string;
  period_end: string;
  esg_kpi_snapshot: Record<string, unknown> | null;
  taxonomy_snapshot: Record<string, unknown> | null;
  climate_metrics_snapshot: Record<string, unknown> | null;
  assurance_status_snapshot: Record<string, unknown> | null;
  sustainability_targets_snapshot: Record<string, unknown> | null;
  is_final: boolean;
  finalized_at: string | null;
  finalized_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClimateFinanceAnalysis {
  id: string;
  organization_id: string;
  analysis_name: string;
  analysis_year: number;
  transition_investment: number;
  emissions_reduction: number;
  cost_per_ton_reduced: number | null;
  roi_percent: number | null;
  methodology: Record<string, unknown> | null;
  currency: string;
  notes: string | null;
  created_at: string;
}

export interface SustainabilityValuation {
  id: string;
  organization_id: string;
  valuation_name: string;
  valuation_year: number;
  risk_reduction_value: number;
  carbon_reduction_value: number;
  operational_efficiency_value: number;
  total_sustainability_value: number;
  methodology: Record<string, unknown> | null;
  currency: string;
  created_at: string;
}

export interface ScenarioAnalysis {
  id: string;
  organization_id: string;
  scenario_name: string;
  scenario_type: string;
  inputs: Record<string, unknown> | null;
  assumptions: Record<string, unknown> | null;
  outputs: Record<string, unknown> | null;
  notes: string | null;
  created_at: string;
}

export interface ESGCorrelation {
  id: string;
  organization_id: string;
  scorecard_id: string | null;
  correlation_period: string;
  esg_score: number;
  risk_reduction: number;
  cost_reduction: number;
  financial_performance: number;
  correlation_coefficient: number | null;
  methodology: string | null;
  assumptions: Record<string, unknown> | null;
  created_at: string;
}

export interface FinancialESGReport {
  id: string;
  organization_id: string;
  title: string;
  report_period_start: string;
  report_period_end: string;
  value_creation_snapshot: Record<string, unknown> | null;
  carbon_economics_snapshot: Record<string, unknown> | null;
  taxonomy_snapshot: Record<string, unknown> | null;
  green_revenue_snapshot: Record<string, unknown> | null;
  sustainable_finance_snapshot: Record<string, unknown> | null;
  readiness_snapshot: Record<string, unknown> | null;
  overall_status: string;
  is_final: boolean;
  finalized_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinancialRollup {
  entity_type: string;
  entity_id: string;
  organization_ids: string[];
  computed_at: string;
  carbon_economics: {
    total_carbon_cost: number;
    total_regulatory_exposure: number;
    total_avoided_cost: number;
    model_count: number;
  };
  green_revenue: {
    total_green_amount: number;
    avg_green_percent: number;
    record_count: number;
  };
  taxonomy: {
    avg_aligned_percent: number | null;
    avg_eligible_percent: number | null;
    assessment_count: number;
  };
  finance: {
    total_exposure: number;
    instrument_count: number;
    breached_count: number;
  };
  value_creation: {
    total_investment: number;
    total_realized_value: number;
    initiative_count: number;
    avg_roi_percent: number | null;
  };
}

// ── API functions ─────────────────────────────────────────────────────────────

export const listKPIs = async (orgId: string): Promise<FinancialKPI[]> =>
  (await apiClient.get<FinancialKPI[]>(`${BASE(orgId)}/kpis`)).data;

export const listCarbonCostModels = async (orgId: string): Promise<CarbonCostModel[]> =>
  (await apiClient.get<CarbonCostModel[]>(`${BASE(orgId)}/carbon-cost`)).data;

export const listRiskAssessments = async (orgId: string): Promise<CostOfRisk[]> =>
  (await apiClient.get<CostOfRisk[]>(`${BASE(orgId)}/risk`)).data;

export const listValueInitiatives = async (orgId: string): Promise<ValueInitiative[]> =>
  (await apiClient.get<ValueInitiative[]>(`${BASE(orgId)}/value-creation`)).data;

export const listFinanceInstruments = async (orgId: string): Promise<FinanceInstrument[]> =>
  (await apiClient.get<FinanceInstrument[]>(`${BASE(orgId)}/finance`)).data;

export const listTaxonomyAssessments = async (orgId: string): Promise<TaxonomyAssessment[]> =>
  (await apiClient.get<TaxonomyAssessment[]>(`${BASE(orgId)}/taxonomy`)).data;

export const listGreenRevenue = async (orgId: string): Promise<GreenRevenue[]> =>
  (await apiClient.get<GreenRevenue[]>(`${BASE(orgId)}/revenue`)).data;

export const listGreenCapex = async (orgId: string): Promise<GreenCapex[]> =>
  (await apiClient.get<GreenCapex[]>(`${BASE(orgId)}/capex`)).data;

export const listGreenOpex = async (orgId: string): Promise<GreenOpex[]> =>
  (await apiClient.get<GreenOpex[]>(`${BASE(orgId)}/opex`)).data;

export const listCapitalMarketsAssessments = async (orgId: string): Promise<CapitalMarketsAssessment[]> =>
  (await apiClient.get<CapitalMarketsAssessment[]>(`${BASE(orgId)}/readiness`)).data;

export const listDisclosurePackages = async (orgId: string): Promise<DisclosurePackage[]> =>
  (await apiClient.get<DisclosurePackage[]>(`${BASE(orgId)}/disclosure-packages`)).data;

export const listClimateFinance = async (orgId: string): Promise<ClimateFinanceAnalysis[]> =>
  (await apiClient.get<ClimateFinanceAnalysis[]>(`${BASE(orgId)}/climate-finance`)).data;

export const listValuations = async (orgId: string): Promise<SustainabilityValuation[]> =>
  (await apiClient.get<SustainabilityValuation[]>(`${BASE(orgId)}/valuation`)).data;

export const listScenarios = async (orgId: string): Promise<ScenarioAnalysis[]> =>
  (await apiClient.get<ScenarioAnalysis[]>(`${BASE(orgId)}/scenarios`)).data;

export const listCorrelations = async (orgId: string): Promise<ESGCorrelation[]> =>
  (await apiClient.get<ESGCorrelation[]>(`${BASE(orgId)}/correlations`)).data;

export const listReports = async (orgId: string): Promise<FinancialESGReport[]> =>
  (await apiClient.get<FinancialESGReport[]>(`${BASE(orgId)}/reports`)).data;

export const getEnterpriseFinancialRollup = async (entityId: string): Promise<FinancialRollup> =>
  (await apiClient.get<FinancialRollup>(`/financial-esg/rollups/enterprise/${entityId}`)).data;
