import apiClient from "./client";

export interface SMEProfile {
  id: string;
  organization_id: string;
  supplier_id: string;
  classification: "micro" | "small" | "medium" | "large";
  employee_count: number | null;
  annual_revenue_eur: number | null;
  is_confirmed: boolean;
  confirmed_by: string | null;
  confirmed_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SupportProgram {
  id: string;
  organization_id: string;
  supplier_id: string;
  title: string;
  description: string;
  status: "draft" | "active" | "completed" | "cancelled";
  start_date: string | null;
  end_date: string | null;
  responsible_user: string | null;
  total_budget_eur: number | null;
  spent_budget_eur: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface SupportMeasure {
  id: string;
  organization_id: string;
  program_id: string;
  title: string;
  support_type: string;
  status: "planned" | "in_progress" | "completed" | "cancelled";
  description: string | null;
  due_date: string | null;
  completed_at: string | null;
  cost_eur: number | null;
  impact_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SMESummary {
  total: number;
  sme_count: number;
  confirmed: number;
  by_classification: Record<string, number>;
}

export interface AnnualReport {
  year: number;
  programs_total: number;
  programs_completed: number;
  total_invested_eur: number;
  sme_suppliers_supported: number;
}

// SME Profiles
export async function listProfiles(smeOnly = true): Promise<SMEProfile[]> {
  const res = await apiClient.get<SMEProfile[]>("/sme-support/profiles/", {
    params: { sme_only: smeOnly },
  });
  return res.data;
}

export async function getProfileSummary(): Promise<SMESummary> {
  const res = await apiClient.get<SMESummary>("/sme-support/profiles/summary");
  return res.data;
}

export async function upsertProfile(data: {
  supplier_id: string;
  employee_count?: number | null;
  annual_revenue_eur?: number | null;
  notes?: string | null;
}): Promise<SMEProfile> {
  const res = await apiClient.post<SMEProfile>("/sme-support/profiles/", data);
  return res.data;
}

export async function confirmProfile(supplier_id: string): Promise<SMEProfile> {
  const res = await apiClient.post<SMEProfile>(`/sme-support/profiles/${supplier_id}/confirm`);
  return res.data;
}

// Support Programs
export async function listPrograms(params?: {
  supplier_id?: string;
  status?: string;
}): Promise<SupportProgram[]> {
  const res = await apiClient.get<SupportProgram[]>("/sme-support/programs/", { params });
  return res.data;
}

export async function createProgram(data: {
  supplier_id: string;
  title: string;
  description?: string;
  start_date?: string | null;
  end_date?: string | null;
  responsible_user?: string | null;
  total_budget_eur?: number | null;
}): Promise<SupportProgram> {
  const res = await apiClient.post<SupportProgram>("/sme-support/programs/", data);
  return res.data;
}

export async function activateProgram(id: string): Promise<SupportProgram> {
  const res = await apiClient.post<SupportProgram>(`/sme-support/programs/${id}/activate`);
  return res.data;
}

export async function completeProgram(id: string): Promise<SupportProgram> {
  const res = await apiClient.post<SupportProgram>(`/sme-support/programs/${id}/complete`);
  return res.data;
}

// Measures
export async function listMeasures(programId: string): Promise<SupportMeasure[]> {
  const res = await apiClient.get<SupportMeasure[]>(`/sme-support/programs/${programId}/measures/`);
  return res.data;
}

export async function addMeasure(
  programId: string,
  data: {
    title: string;
    support_type: string;
    description?: string | null;
    due_date?: string | null;
    cost_eur?: number | null;
  }
): Promise<SupportMeasure> {
  const res = await apiClient.post<SupportMeasure>(`/sme-support/programs/${programId}/measures/`, data);
  return res.data;
}

export async function completeMeasure(id: string, impact_notes?: string): Promise<SupportMeasure> {
  const res = await apiClient.post<SupportMeasure>(`/sme-support/measures/${id}/complete`, {
    impact_notes: impact_notes ?? null,
  });
  return res.data;
}

export async function updateMeasureStatus(id: string, status: string): Promise<SupportMeasure> {
  const res = await apiClient.patch<SupportMeasure>(`/sme-support/measures/${id}/status`, { status });
  return res.data;
}

// Annual report
export async function getAnnualReport(year: number): Promise<AnnualReport> {
  const res = await apiClient.get<AnnualReport>("/sme-support/annual-report", { params: { year } });
  return res.data;
}
