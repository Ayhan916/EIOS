import apiClient from "./client";

export interface ScopingConfig {
  id: string;
  organization_id: string;
  version: number;
  risk_score_threshold_p1: number;
  risk_score_threshold_p2: number;
  high_risk_countries: string[];
  high_risk_sectors: string[];
  revenue_threshold_pct: number;
  notes: string;
  created_by: string;
  created_at: string;
}

export interface ScopingResult {
  supplier_id: string;
  supplier_name: string;
  country: string;
  industry: string;
  risk_score: number;
  risk_band: string;
  priority: "priority_1" | "priority_2" | "priority_3";
  reasons: string[];
  manually_overridden: boolean;
  override_reason: string | null;
}

export interface AnalysisResponse {
  results: ScopingResult[];
  summary: {
    total: number;
    priority_1: number;
    priority_2: number;
    priority_3: number;
  };
  config_version: number;
}

export interface ScopingStudy {
  id: string;
  organization_id: string;
  title: string;
  report_year: number;
  config_id: string;
  status: "draft" | "submitted" | "approved";
  results_snapshot: ScopingResult[];
  methodology_notes: string;
  submitted_at: string | null;
  submitted_by: string | null;
  approved_at: string | null;
  approved_by: string | null;
  next_review_due: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewStatus {
  status: "no_study" | "current" | "due_soon" | "overdue";
  latest_approved_year: number | null;
  next_review_due: string | null;
  overdue: boolean;
  days_until_review: number | null;
}

// ── API functions ─────────────────────────────────────────────────────────────

export async function getLatestConfig(): Promise<ScopingConfig> {
  const res = await apiClient.get<ScopingConfig>("/scoping/config/");
  return res.data;
}

export async function getConfigHistory(): Promise<ScopingConfig[]> {
  const res = await apiClient.get<ScopingConfig[]>("/scoping/config/history");
  return res.data;
}

export async function createConfig(data: Partial<ScopingConfig>): Promise<ScopingConfig> {
  const res = await apiClient.post<ScopingConfig>("/scoping/config/", data);
  return res.data;
}

export async function createDefaultConfig(): Promise<ScopingConfig> {
  const res = await apiClient.post<ScopingConfig>("/scoping/config/default");
  return res.data;
}

export async function runAnalysis(configId: string): Promise<AnalysisResponse> {
  const res = await apiClient.post<AnalysisResponse>(`/scoping/analyze?config_id=${configId}`);
  return res.data;
}

export async function listStudies(): Promise<ScopingStudy[]> {
  const res = await apiClient.get<ScopingStudy[]>("/scoping/studies/");
  return res.data;
}

export async function getStudy(id: string): Promise<ScopingStudy> {
  const res = await apiClient.get<ScopingStudy>(`/scoping/studies/${id}`);
  return res.data;
}

export async function createStudy(data: {
  title: string;
  report_year: number;
  config_id: string;
  methodology_notes?: string;
  results: ScopingResult[];
}): Promise<ScopingStudy> {
  const res = await apiClient.post<ScopingStudy>("/scoping/studies/", data);
  return res.data;
}

export async function updateStudyNotes(id: string, notes: string): Promise<ScopingStudy> {
  const res = await apiClient.patch<ScopingStudy>(`/scoping/studies/${id}/notes`, { methodology_notes: notes });
  return res.data;
}

export async function submitStudy(id: string): Promise<ScopingStudy> {
  const res = await apiClient.post<ScopingStudy>(`/scoping/studies/${id}/submit`);
  return res.data;
}

export async function approveStudy(id: string): Promise<ScopingStudy> {
  const res = await apiClient.post<ScopingStudy>(`/scoping/studies/${id}/approve`);
  return res.data;
}

export async function cloneStudy(id: string): Promise<ScopingStudy> {
  const res = await apiClient.post<ScopingStudy>(`/scoping/studies/${id}/clone`);
  return res.data;
}

export async function getScopingReviewStatus(): Promise<ReviewStatus> {
  const res = await apiClient.get<ReviewStatus>("/scoping/review-status");
  return res.data;
}
