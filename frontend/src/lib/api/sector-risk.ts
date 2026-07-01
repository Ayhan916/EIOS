import apiClient from "./client";

export interface SectorListItem {
  nace_code: string;
  nace_section: string;
  sector_name: string;
  is_calibrated: boolean;
  highest_probability: number;
  highest_right: string | null;
  average_probability: number;
  rights_above_7: number;
}

export interface RightScore {
  right_id: string;
  right_name: string;
  probability: number;
  is_calibrated: boolean;
  scenario: ScenarioDelta | null;
}

export interface ScenarioDelta {
  type: string;
  name: string;
  adjusted_probability: number;
  delta: number;
  factor: number;
  explanation: string;
}

export interface SectorBaseline {
  nace_code: string;
  nace_section: string;
  sector_name: string;
  calibration_version: string;
  calibration_date: string;
  is_fully_calibrated: boolean;
  rights: RightScore[];
}

export interface ScenarioTemplate {
  scenario_type: string;
  name: string;
  description: string;
  affected_nace_sections: string[];
  sources: string[];
  affected_rights_count: number;
}

export interface SimulationSummary {
  rights_increased: number;
  rights_above_7_baseline: number;
  rights_above_7_scenario: number;
  highest_risk_right: string | null;
  highest_risk_score: number;
}

export interface SimulationResult {
  nace_code: string;
  sector_name: string;
  scenario_type: string;
  scenario_name: string;
  calibration_version: string;
  simulated_at: string;
  rights: RightScore[];
  summary: SimulationSummary;
}

export interface CalibrationSuggestion {
  id: string;
  nace_code: string;
  csddd_right: string;
  suggested_probability: number;
  confidence: string;
  reasoning: string;
  sources: string[];
  status: string;
  created_at: string;
}

export interface ScenarioSuggestion {
  id: string;
  scenario_type: string;
  affected_nace_codes: string[];
  trigger_article_count: number;
  trigger_keywords_matched: string[];
  sample_headlines: string[];
  status: string;
  created_at: string;
  expires_at: string | null;
}

const BASE = "/api/v1/sector-risk-register";

export const sectorRiskApi = {
  listSectors: (calibratedOnly = false): Promise<SectorListItem[]> =>
    apiClient.get(`${BASE}/?calibrated_only=${calibratedOnly}`).then((r) => r.data),

  getSector: (nace: string): Promise<SectorBaseline> =>
    apiClient.get(`${BASE}/${nace}`).then((r) => r.data),

  simulate: (nace: string, scenario: string): Promise<SimulationResult> =>
    apiClient.get(`${BASE}/${nace}/simulate?scenario=${scenario}`).then((r) => r.data),

  listTemplates: (): Promise<ScenarioTemplate[]> =>
    apiClient.get(`${BASE}/scenarios/templates`).then((r) => r.data),

  // Calibration
  startCalibration: (nace_code: string, right: string): Promise<CalibrationSuggestion> =>
    apiClient.post(`${BASE}/calibrate`, { nace_code, right }).then((r) => r.data),

  listCalibrationSuggestions: (status?: string): Promise<CalibrationSuggestion[]> => {
    const qs = status ? `?status=${status}` : "";
    return apiClient.get(`${BASE}/calibrate/suggestions${qs}`).then((r) => r.data);
  },

  approveCalibration: (id: string): Promise<{ approved: boolean }> =>
    apiClient.post(`${BASE}/calibrate/${id}/approve`).then((r) => r.data),

  rejectCalibration: (id: string, reason: string): Promise<{ rejected: boolean }> =>
    apiClient.post(`${BASE}/calibrate/${id}/reject`, { reason }).then((r) => r.data),

  // Scenario suggestions
  detectScenarios: (organizationId: string): Promise<ScenarioSuggestion[]> =>
    apiClient
      .post(`${BASE}/scenarios/detect`, { organization_id: organizationId, lookback_days: 7 })
      .then((r) => r.data),

  listScenarioSuggestions: (status?: string): Promise<ScenarioSuggestion[]> => {
    const qs = status ? `?status=${status}` : "";
    return apiClient.get(`${BASE}/scenarios/suggestions${qs}`).then((r) => r.data);
  },

  activateScenario: (id: string): Promise<{ activated: boolean }> =>
    apiClient.post(`${BASE}/scenarios/suggestions/${id}/activate`).then((r) => r.data),

  dismissScenario: (id: string): Promise<{ dismissed: boolean }> =>
    apiClient.post(`${BASE}/scenarios/suggestions/${id}/dismiss`).then((r) => r.data),
};
