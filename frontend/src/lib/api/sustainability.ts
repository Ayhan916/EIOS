import apiClient from "./client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SustainabilityDashboard {
  organization_id: string;
  total_objectives: number;
  active_objectives: number;
  completed_objectives: number;
  total_kpis: number;
  active_kpis: number;
  total_emissions_tco2e: number | null;
  latest_inventory_year: number | null;
  open_alerts: number;
  active_initiatives: number;
  latest_overall_score: number | null;
  active_sbts: number;
}

export interface ESGObjective {
  id: string;
  organization_id: string;
  title: string;
  description: string | null;
  category: string;
  owner_user_id: string | null;
  start_date: string | null;
  target_date: string | null;
  objective_status: string;
  program_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ESGTarget {
  id: string;
  organization_id: string;
  objective_id: string;
  metric_name: string;
  baseline_value: number;
  target_value: number;
  target_unit: string | null;
  current_value: number | null;
  progress_percent: number;
  measurement_frequency: string;
  target_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ESGKPI {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  category: string;
  formula: string | null;
  unit: string | null;
  frequency: string;
  target_value: number | null;
  alert_threshold: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface KPIMeasurement {
  id: string;
  kpi_id: string;
  organization_id: string;
  period_start: string;
  period_end: string;
  measured_value: number;
  source: string | null;
  confidence: string | null;
  notes: string | null;
  recorded_by: string;
  created_at: string;
}

export interface KPIAlert {
  id: string;
  kpi_id: string;
  organization_id: string;
  alert_type: string;
  triggered_value: number;
  threshold_value: number | null;
  message: string | null;
  is_resolved: boolean;
  resolved_at: string | null;
  created_at: string;
}

export interface CarbonInventory {
  id: string;
  organization_id: string;
  reporting_year: number;
  period_start: string;
  period_end: string;
  scope1_emissions: number;
  scope2_emissions: number;
  scope3_emissions: number;
  total_emissions: number;
  unit: string;
  inventory_status: string;
  finalized_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmissionSource {
  id: string;
  organization_id: string;
  name: string;
  scope: string;
  category: string | null;
  activity_data: number;
  emission_factor: number;
  calculated_emissions: number;
  reporting_year: number;
  created_at: string;
}

export interface DecarbonizationInitiative {
  id: string;
  organization_id: string;
  name: string;
  initiative_type: string;
  expected_reduction: number;
  actual_reduction: number | null;
  initiative_status: string;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
}

export interface NetZeroRoadmap {
  id: string;
  organization_id: string;
  name: string;
  baseline_year: number;
  target_year: number;
  baseline_emissions: number;
  target_reduction_percent: number;
  target_emissions: number;
  roadmap_status: string;
  created_at: string;
}

export interface SustainabilityReport {
  id: string;
  organization_id: string;
  title: string;
  period_start: string;
  period_end: string;
  report_type: string;
  kpi_summary: Record<string, unknown>;
  emissions_summary: Record<string, unknown>;
  target_progress: Record<string, unknown>;
  objective_status: Record<string, unknown>;
  overall_status: string;
  generated_by: string;
  is_final: boolean;
  finalized_at: string | null;
  created_at: string;
}

export interface SustainabilityScorecard {
  id: string;
  organization_id: string;
  period_start: string;
  period_end: string;
  environmental_score: number;
  social_score: number;
  governance_score: number;
  overall_score: number;
  calculation_method: string | null;
  created_at: string;
}

// ── API Functions ──────────────────────────────────────────────────────────────

const BASE = (org: string) => `/api/v1/sustainability/${org}`;

export async function getDashboard(org: string): Promise<SustainabilityDashboard> {
  const r = await apiClient.get(`${BASE(org)}/dashboard`);
  return r.data;
}

export async function listObjectives(org: string): Promise<ESGObjective[]> {
  const r = await apiClient.get(`${BASE(org)}/objectives`);
  return r.data;
}

export async function createObjective(
  org: string,
  body: { title: string; category: string; description?: string }
): Promise<ESGObjective> {
  const r = await apiClient.post(`${BASE(org)}/objectives`, body);
  return r.data;
}

export async function updateObjectiveStatus(
  org: string,
  id: string,
  status: string
): Promise<ESGObjective> {
  const r = await apiClient.patch(`${BASE(org)}/objectives/${id}/status`, { status });
  return r.data;
}

export async function listTargets(org: string, objectiveId: string): Promise<ESGTarget[]> {
  const r = await apiClient.get(`${BASE(org)}/objectives/${objectiveId}/targets`);
  return r.data;
}

export async function listKPIs(org: string): Promise<ESGKPI[]> {
  const r = await apiClient.get(`${BASE(org)}/kpis`);
  return r.data;
}

export async function createKPI(
  org: string,
  body: { name: string; category: string; unit?: string; target_value?: number; alert_threshold?: number }
): Promise<ESGKPI> {
  const r = await apiClient.post(`${BASE(org)}/kpis`, body);
  return r.data;
}

export async function listAlerts(org: string): Promise<KPIAlert[]> {
  const r = await apiClient.get(`${BASE(org)}/alerts`);
  return r.data;
}

export async function recordMeasurement(
  org: string,
  kpiId: string,
  body: { measured_value: number; period_start: string; period_end: string; notes?: string }
): Promise<KPIMeasurement> {
  const r = await apiClient.post(`${BASE(org)}/kpis/${kpiId}/measurements`, body);
  return r.data;
}

export async function listMeasurements(org: string, kpiId: string, limit = 12): Promise<KPIMeasurement[]> {
  const r = await apiClient.get(`${BASE(org)}/kpis/${kpiId}/measurements?limit=${limit}`);
  return r.data;
}

export async function listInventories(org: string): Promise<CarbonInventory[]> {
  const r = await apiClient.get(`${BASE(org)}/inventory`);
  return r.data;
}

export async function listEmissionSources(org: string, year?: number): Promise<EmissionSource[]> {
  const params = year ? `?reporting_year=${year}` : "";
  const r = await apiClient.get(`${BASE(org)}/emissions${params}`);
  return r.data;
}

export async function addEmissionSource(
  org: string,
  body: {
    name: string;
    scope: "SCOPE1" | "SCOPE2" | "SCOPE3";
    activity_data: number;
    emission_factor: number;
    period_start: string;
    period_end: string;
    reporting_year: number;
    category?: string;
    activity_unit?: string;
    emission_factor_unit?: string;
    source_reference?: string;
  }
): Promise<EmissionSource> {
  const r = await apiClient.post(`${BASE(org)}/emissions`, body);
  return r.data;
}

export async function recalculateInventory(
  org: string,
  inventoryId: string
): Promise<CarbonInventory> {
  const r = await apiClient.post(`${BASE(org)}/inventory/${inventoryId}/recalculate`, {});
  return r.data;
}

export async function finalizeInventory(
  org: string,
  inventoryId: string
): Promise<CarbonInventory> {
  const r = await apiClient.post(`${BASE(org)}/inventory/${inventoryId}/finalize`, {});
  return r.data;
}

export async function listInitiatives(org: string): Promise<DecarbonizationInitiative[]> {
  const r = await apiClient.get(`${BASE(org)}/initiatives`);
  return r.data;
}

export async function updateInitiativeProgress(
  org: string,
  initiativeId: string,
  body: { actual_reduction: number; status: string },
): Promise<DecarbonizationInitiative> {
  const r = await apiClient.patch(`${BASE(org)}/initiatives/${initiativeId}/progress`, body);
  return r.data;
}

export async function listRoadmaps(org: string): Promise<NetZeroRoadmap[]> {
  const r = await apiClient.get(`${BASE(org)}/roadmaps`);
  return r.data;
}

export async function listReports(org: string): Promise<SustainabilityReport[]> {
  const r = await apiClient.get(`${BASE(org)}/reports`);
  return r.data;
}

export async function finalizeReport(
  org: string,
  reportId: string
): Promise<SustainabilityReport> {
  const r = await apiClient.post(`${BASE(org)}/reports/${reportId}/finalize`, {});
  return r.data;
}

export async function listScorecards(org: string): Promise<SustainabilityScorecard[]> {
  const r = await apiClient.get(`${BASE(org)}/scorecards`);
  return r.data;
}

export interface ScienceBasedTarget {
  id: string;
  organization_id: string;
  name: string;
  scope: string;
  target_year: number;
  baseline_year: number;
  target_reduction_percent: number;
  sbt_status: string;
  sbt_type: string;
  sbt_framework: string;
  commitment_date: string | null;
  approval_date: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface RollupEmissions {
  total_emissions: number;
  scope1: number;
  scope2: number;
  scope3: number;
  inventories_count: number;
}

export interface RollupObjectives {
  total: number;
  active: number;
  completed: number;
  completion_percent: number;
}

export interface RollupTargets {
  total: number;
  with_measurements: number;
  attainment_percent: number;
}

export interface RollupKPIs {
  total: number;
  active: number;
}

export interface RollupScores {
  avg_overall_score: number | null;
  avg_environmental_score: number | null;
  avg_social_score: number | null;
  avg_governance_score: number | null;
  scorecard_count: number;
}

export interface RollupClimateRisks {
  avg_overall_risk: number | null;
  avg_transition_risk: number | null;
  avg_physical_risk: number | null;
  avg_regulatory_risk: number | null;
  assessment_count: number;
}

export interface RollupSummary {
  entity_type: string;
  entity_id: string;
  organization_ids: string[];
  computed_at: string;
  emissions: RollupEmissions;
  objectives: RollupObjectives;
  targets: RollupTargets;
  kpis: RollupKPIs;
  scores: RollupScores;
  climate_risks: RollupClimateRisks;
}

export async function listAllTargets(org: string): Promise<ESGTarget[]> {
  const r = await apiClient.get(`${BASE(org)}/targets`);
  return r.data;
}

export async function listScienceBasedTargets(org: string): Promise<ScienceBasedTarget[]> {
  const r = await apiClient.get(`${BASE(org)}/sbts`);
  return r.data;
}

export async function getEnterpriseRollup(entityId: string): Promise<RollupSummary> {
  const r = await apiClient.get(`/api/v1/sustainability/rollups/enterprise/${entityId}`);
  return r.data;
}

export async function getBusinessUnitRollup(entityId: string): Promise<RollupSummary> {
  const r = await apiClient.get(`/api/v1/sustainability/rollups/business-unit/${entityId}`);
  return r.data;
}
