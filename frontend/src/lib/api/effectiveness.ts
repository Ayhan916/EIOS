import apiClient from "./client";

export interface EffectivenessIndicator {
  id: string;
  organization_id: string | null;
  name: string;
  description: string | null;
  indicator_type: "quantitative" | "qualitative";
  unit: string;
  data_source: "automatic" | "manual";
  csddd_article: string;
  risk_category: string | null;
  is_active: boolean;
  created_at: string;
}

export interface IndicatorCreate {
  name: string;
  description?: string;
  indicator_type?: string;
  unit?: string;
  data_source?: string;
  csddd_article?: string;
  risk_category?: string;
}

export interface ReviewLine {
  id: string;
  review_id: string;
  indicator_id: string;
  indicator_name: string;
  measured_value: number | null;
  measured_text: string | null;
  comment: string | null;
  auto_populated: boolean;
}

export interface EffectivenessReview {
  id: string;
  organization_id: string;
  title: string;
  period_start: string;
  period_end: string;
  overall_rating: number | null;
  key_findings: string | null;
  improvement_actions: string | null;
  status: "draft" | "submitted" | "approved" | "closed";
  submitted_at: string | null;
  submitted_by: string | null;
  approved_at: string | null;
  approved_by: string | null;
  lines: ReviewLine[];
  created_at: string;
  updated_at: string;
}

export interface ReviewCreate {
  title: string;
  period_start: string;
  period_end: string;
  overall_rating?: number;
  key_findings?: string;
  improvement_actions?: string;
}

export interface EffectivenessDashboard {
  open_caps: number;
  overdue_caps: number;
  closed_caps_12m: number;
  avg_risk_delta: number | null;
  stakeholder_consultations_12m: number;
  remedy_cases_closed_12m: number;
  escalation_needed: boolean;
  generated_at: string;
}

export interface CAPSnapshot {
  cap_id: string;
  baseline_score: number | null;
  closed_score: number | null;
  risk_delta: number | null;
  snapshot_taken_at: string | null;
}

// ── API functions ─────────────────────────────────────────────────────────────

export async function listIndicators(risk_category?: string): Promise<EffectivenessIndicator[]> {
  const params: Record<string, string> = {};
  if (risk_category) params.risk_category = risk_category;
  const res = await apiClient.get<EffectivenessIndicator[]>("/effectiveness/indicators/", { params });
  return res.data;
}

export async function createIndicator(data: IndicatorCreate): Promise<EffectivenessIndicator> {
  const res = await apiClient.post<EffectivenessIndicator>("/effectiveness/indicators/", data);
  return res.data;
}

export async function listReviews(): Promise<EffectivenessReview[]> {
  const res = await apiClient.get<EffectivenessReview[]>("/effectiveness/reviews/");
  return res.data;
}

export async function getReview(id: string): Promise<EffectivenessReview> {
  const res = await apiClient.get<EffectivenessReview>(`/effectiveness/reviews/${id}`);
  return res.data;
}

export async function createReview(data: ReviewCreate): Promise<EffectivenessReview> {
  const res = await apiClient.post<EffectivenessReview>("/effectiveness/reviews/", data);
  return res.data;
}

export async function updateReview(id: string, data: Partial<ReviewCreate>): Promise<EffectivenessReview> {
  const res = await apiClient.patch<EffectivenessReview>(`/effectiveness/reviews/${id}`, data);
  return res.data;
}

export async function upsertLine(reviewId: string, data: {
  indicator_id: string;
  indicator_name: string;
  measured_value?: number;
  measured_text?: string;
  comment?: string;
}): Promise<ReviewLine> {
  const res = await apiClient.post<ReviewLine>(`/effectiveness/reviews/${reviewId}/lines`, data);
  return res.data;
}

export async function submitReview(id: string): Promise<EffectivenessReview> {
  const res = await apiClient.post<EffectivenessReview>(`/effectiveness/reviews/${id}/submit`);
  return res.data;
}

export async function closeReview(id: string): Promise<EffectivenessReview> {
  const res = await apiClient.post<EffectivenessReview>(`/effectiveness/reviews/${id}/close`);
  return res.data;
}

export async function getEffectivenessDashboard(): Promise<EffectivenessDashboard> {
  const res = await apiClient.get<EffectivenessDashboard>("/effectiveness/dashboard");
  return res.data;
}

export async function getCAPSnapshot(capId: string): Promise<CAPSnapshot> {
  const res = await apiClient.get<CAPSnapshot>(`/effectiveness/cap/${capId}/snapshot`);
  return res.data;
}
