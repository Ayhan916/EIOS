import apiClient from "./client";

export interface ImpactAssessment {
  id: string;
  organization_id: string;
  title: string;
  impact_type: string;
  entity_type: string;
  entity_id: string | null;
  gravity: number;
  scope: number;
  remediability: number;
  likelihood: number;
  severity_score: number;
  priority_score: number;
  severity_level: "critical" | "high" | "medium" | "low";
  justification: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface PreviewResult {
  severity_score: number;
  priority_score: number;
  severity_level: "critical" | "high" | "medium" | "low";
}

export interface ImpactDashboard {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  avg_severity_score: number;
  by_type: Record<string, number>;
  top5_priority: Array<{
    id: string;
    title: string;
    severity_score: number;
    priority_score: number;
    severity_level: string;
    impact_type: string;
  }>;
}

export async function previewScore(dims: {
  gravity: number;
  scope: number;
  remediability: number;
  likelihood: number;
}): Promise<PreviewResult> {
  const res = await apiClient.post<PreviewResult>("/impact/preview", dims);
  return res.data;
}

export async function getImpactDashboard(): Promise<ImpactDashboard> {
  const res = await apiClient.get<ImpactDashboard>("/impact/dashboard");
  return res.data;
}

export async function listAssessments(params?: {
  severity_level?: string;
  impact_type?: string;
}): Promise<ImpactAssessment[]> {
  const res = await apiClient.get<ImpactAssessment[]>("/impact/", { params });
  return res.data;
}

export async function createAssessment(data: {
  title: string;
  impact_type: string;
  entity_type: string;
  entity_id?: string | null;
  gravity: number;
  scope: number;
  remediability: number;
  likelihood: number;
  justification?: string | null;
}): Promise<ImpactAssessment> {
  const res = await apiClient.post<ImpactAssessment>("/impact/", data);
  return res.data;
}

export async function updateAssessment(
  id: string,
  data: {
    gravity: number;
    scope: number;
    remediability: number;
    likelihood: number;
    title?: string;
    justification?: string | null;
  }
): Promise<ImpactAssessment> {
  const res = await apiClient.put<ImpactAssessment>(`/impact/${id}`, data);
  return res.data;
}

export async function deleteAssessment(id: string): Promise<void> {
  await apiClient.delete(`/impact/${id}`);
}
