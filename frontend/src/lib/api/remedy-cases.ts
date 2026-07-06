import apiClient from "./client";

export interface RemedyCase {
  id: string;
  organization_id: string;
  title: string;
  description: string | null;
  incident_date: string;
  affected_count: number;
  affected_type: string;
  rights: string[];
  remedy_types: string[];
  severity_score: number;
  impact_causation: string;
  status: "open" | "in_progress" | "completed" | "verified";
  source_grievance_id: string | null;
  co_responsible_parties: string[];
  closed_at: string | null;
  closed_by: string | null;
  closure_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface RemedyCaseCreate {
  title: string;
  description?: string;
  incident_date: string;
  affected_count?: number;
  affected_type: string;
  rights?: string[];
  remedy_types?: string[];
  severity_score?: number;
  impact_causation: string;
  source_grievance_id?: string;
  co_responsible_parties?: string[];
}

export interface RemedyCaseUpdate {
  title?: string;
  description?: string;
  incident_date?: string;
  affected_count?: number;
  affected_type?: string;
  rights?: string[];
  remedy_types?: string[];
  severity_score?: number;
  impact_causation?: string;
  co_responsible_parties?: string[];
}

export interface RemedyBeneficiary {
  id: string;
  remedy_case_id: string;
  reference: string;
  affected_type: string;
  promised_compensation: number | null;
  received_compensation: number | null;
  confirmation_date: string | null;
  created_at: string;
}

export interface RemedyAction {
  id: string;
  remedy_case_id: string;
  title: string;
  description: string | null;
  status: "todo" | "in_progress" | "done";
  responsible_party: string | null;
  due_date: string | null;
  completed_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface RemedyActionCreate {
  title: string;
  description?: string;
  responsible_party?: string;
  due_date?: string;
}

export interface AuditLog {
  id: string;
  remedy_case_id: string;
  action: string;
  performed_by: string;
  details: string | null;
  created_at: string;
}

export interface RemedySummaryReport {
  year: number;
  total: number;
  by_status: Record<string, number>;
  by_affected_type: Record<string, number>;
  total_affected_persons: number;
  avg_severity: number;
}

// ── API functions ─────────────────────────────────────────────────────────────

export async function listRemedyCases(statusFilter?: string): Promise<RemedyCase[]> {
  const params: Record<string, string> = {};
  if (statusFilter) params.status_filter = statusFilter;
  const res = await apiClient.get<RemedyCase[]>("/remedy-cases/", { params });
  return res.data;
}

export async function getRemedyCase(id: string): Promise<RemedyCase> {
  const res = await apiClient.get<RemedyCase>(`/remedy-cases/${id}`);
  return res.data;
}

export async function createRemedyCase(data: RemedyCaseCreate): Promise<RemedyCase> {
  const res = await apiClient.post<RemedyCase>("/remedy-cases/", data);
  return res.data;
}

export async function updateRemedyCase(id: string, data: RemedyCaseUpdate): Promise<RemedyCase> {
  const res = await apiClient.patch<RemedyCase>(`/remedy-cases/${id}`, data);
  return res.data;
}

export async function closeRemedyCase(id: string, closure_notes?: string): Promise<RemedyCase> {
  const res = await apiClient.patch<RemedyCase>(`/remedy-cases/${id}/close`, { closure_notes });
  return res.data;
}

export async function listBeneficiaries(caseId: string): Promise<RemedyBeneficiary[]> {
  const res = await apiClient.get<RemedyBeneficiary[]>(`/remedy-cases/${caseId}/beneficiaries`);
  return res.data;
}

export async function addBeneficiary(caseId: string, data: Partial<RemedyBeneficiary>): Promise<RemedyBeneficiary> {
  const res = await apiClient.post<RemedyBeneficiary>(`/remedy-cases/${caseId}/beneficiaries`, data);
  return res.data;
}

export async function listActions(caseId: string): Promise<RemedyAction[]> {
  const res = await apiClient.get<RemedyAction[]>(`/remedy-cases/${caseId}/actions`);
  return res.data;
}

export async function addAction(caseId: string, data: RemedyActionCreate): Promise<RemedyAction> {
  const res = await apiClient.post<RemedyAction>(`/remedy-cases/${caseId}/actions`, data);
  return res.data;
}

export async function updateAction(caseId: string, actionId: string, data: { status?: string; title?: string }): Promise<RemedyAction> {
  const res = await apiClient.patch<RemedyAction>(`/remedy-cases/${caseId}/actions/${actionId}`, data);
  return res.data;
}

export async function getAuditLog(caseId: string): Promise<AuditLog[]> {
  const res = await apiClient.get<AuditLog[]>(`/remedy-cases/${caseId}/audit-log`);
  return res.data;
}

export async function getRemedySummaryReport(year: number): Promise<RemedySummaryReport> {
  const res = await apiClient.get<RemedySummaryReport>(`/reports/remedy-summary`, { params: { year } });
  return res.data;
}
