import apiClient from "./client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AIModel {
  id: string;
  organization_id: string;
  name: string;
  provider: string;
  model_type: string;
  model_version: string | null;
  purpose: string | null;
  owner_user_id: string | null;
  ai_status: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AIUseCase {
  id: string;
  model_id: string;
  organization_id: string;
  title: string;
  description: string | null;
  business_owner: string | null;
  technical_owner: string | null;
  risk_level: string;
  approval_status: string;
  created_at: string;
}

export interface WorkflowStage {
  id: string;
  model_id: string;
  stage: string;
  stage_status: string;
  stage_order: number;
  approver_user_id: string | null;
  notes: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface PromptTemplate {
  id: string;
  organization_id: string;
  model_id: string | null;
  name: string;
  prompt_version: number;
  is_approved: boolean;
  approved_by: string | null;
  approved_at: string | null;
  is_active: boolean;
  owner_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AIIncident {
  id: string;
  model_id: string;
  organization_id: string;
  incident_type: string;
  severity: string;
  description: string;
  reported_by: string | null;
  is_resolved: boolean;
  resolved_at: string | null;
  esg_action_id: string | null;
  strategic_risk_id: string | null;
  created_at: string;
}

export interface DriftAlert {
  id: string;
  model_id: string;
  alert_type: string;
  severity: string;
  description: string;
  detected_at: string;
  is_resolved: boolean;
  resolved_at: string | null;
}

export interface AssuranceReport {
  id: string;
  organization_id: string;
  title: string;
  report_period_start: string;
  report_period_end: string;
  model_count: number;
  use_case_count: number;
  control_count: number;
  incident_count: number;
  approval_count: number;
  overall_status: string;
  generated_by: string | null;
  report_data: Record<string, unknown>;
  created_at: string;
}

export interface AIGovernanceDashboard {
  organization_id: string;
  total_models: number;
  active_models: number;
  draft_models: number;
  total_use_cases: number;
  pending_approvals: number;
  open_incidents: number;
  unresolved_drift_alerts: number;
  active_policies: number;
  last_report_status: string | null;
}

// ── API calls ─────────────────────────────────────────────────────────────────

const BASE = (orgId: string) => `/ai-governance/${orgId}`;

export async function getDashboard(orgId: string): Promise<AIGovernanceDashboard> {
  const { data } = await apiClient.get(`${BASE(orgId)}/dashboard`);
  return data;
}

// Models
export async function listModels(orgId: string): Promise<AIModel[]> {
  const { data } = await apiClient.get(`${BASE(orgId)}/models`);
  return data;
}

export async function registerModel(
  orgId: string,
  payload: {
    name: string;
    provider: string;
    model_type: string;
    model_version?: string;
    purpose?: string;
  }
): Promise<AIModel> {
  const { data } = await apiClient.post(`${BASE(orgId)}/models`, payload);
  return data;
}

export async function updateModelStatus(
  orgId: string,
  modelId: string,
  ai_status: string
): Promise<AIModel> {
  const { data } = await apiClient.patch(
    `${BASE(orgId)}/models/${modelId}/status`,
    { ai_status }
  );
  return data;
}

// Workflow
export async function getWorkflowStages(
  orgId: string,
  modelId: string
): Promise<WorkflowStage[]> {
  const { data } = await apiClient.get(
    `${BASE(orgId)}/models/${modelId}/workflow`
  );
  return data;
}

export async function advanceWorkflowStage(
  orgId: string,
  modelId: string,
  stage: string,
  approved: boolean,
  notes?: string
): Promise<WorkflowStage> {
  const { data } = await apiClient.post(
    `${BASE(orgId)}/models/${modelId}/workflow/advance`,
    { stage, approved, notes }
  );
  return data;
}

// Use Cases
export async function listUseCases(
  orgId: string,
  modelId: string
): Promise<AIUseCase[]> {
  const { data } = await apiClient.get(
    `${BASE(orgId)}/models/${modelId}/use-cases`
  );
  return data;
}

// Prompts
export async function listPrompts(orgId: string): Promise<PromptTemplate[]> {
  const { data } = await apiClient.get(`${BASE(orgId)}/prompts`);
  return data;
}

export async function createPrompt(
  orgId: string,
  payload: { name: string; prompt_text: string; model_id?: string }
): Promise<PromptTemplate> {
  const { data } = await apiClient.post(`${BASE(orgId)}/prompts`, payload);
  return data;
}

export async function approvePrompt(
  orgId: string,
  promptId: string
): Promise<PromptTemplate> {
  const { data } = await apiClient.post(
    `${BASE(orgId)}/prompts/${promptId}/approve`,
    {}
  );
  return data;
}

// Incidents
export async function listIncidents(
  orgId: string,
  unresolvedOnly = false
): Promise<AIIncident[]> {
  const { data } = await apiClient.get(`${BASE(orgId)}/incidents`, {
    params: { unresolved_only: unresolvedOnly },
  });
  return data;
}

export async function reportIncident(
  orgId: string,
  modelId: string,
  payload: { incident_type: string; severity: string; description: string }
): Promise<AIIncident> {
  const { data } = await apiClient.post(
    `${BASE(orgId)}/models/${modelId}/incidents`,
    payload
  );
  return data;
}

export async function resolveIncident(
  orgId: string,
  incidentId: string
): Promise<AIIncident> {
  const { data } = await apiClient.post(
    `${BASE(orgId)}/incidents/${incidentId}/resolve`,
    {}
  );
  return data;
}

// Drift alerts
export async function listDriftAlerts(
  orgId: string,
  modelId: string,
  unresolvedOnly = false
): Promise<DriftAlert[]> {
  const { data } = await apiClient.get(
    `${BASE(orgId)}/models/${modelId}/drift-alerts`,
    { params: { unresolved_only: unresolvedOnly } }
  );
  return data;
}

// Assurance reports
export async function listAssuranceReports(
  orgId: string
): Promise<AssuranceReport[]> {
  const { data } = await apiClient.get(`${BASE(orgId)}/assurance-reports`);
  return data;
}

export async function generateAssuranceReport(
  orgId: string,
  payload: { title: string; period_start: string; period_end: string }
): Promise<AssuranceReport> {
  const { data } = await apiClient.post(
    `${BASE(orgId)}/assurance-reports`,
    payload
  );
  return data;
}
