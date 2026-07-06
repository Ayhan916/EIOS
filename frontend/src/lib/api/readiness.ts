import apiClient from "./client";

export interface ArticleScore {
  article: string;
  title: string;
  earned_points: number;
  max_points: number;
  score_pct: number;
  level: "not_ready" | "partial" | "ready" | "fully_ready";
  gaps: string[];
}

export interface ReadinessSnapshot {
  id: string;
  organization_id: string;
  overall_score_pct: number;
  overall_level: "not_ready" | "partial" | "ready" | "fully_ready";
  article_scores: ArticleScore[];
  computed_at: string;
  computed_by: string | null;
}

export interface HistoryEntry {
  id: string;
  overall_score_pct: number;
  overall_level: string;
  computed_at: string;
  computed_by: string | null;
}

export async function computeScore(): Promise<ReadinessSnapshot> {
  const res = await apiClient.post<ReadinessSnapshot>("/readiness/compute");
  return res.data;
}

export async function getLatestScore(): Promise<ReadinessSnapshot> {
  const res = await apiClient.get<ReadinessSnapshot>("/readiness/latest");
  return res.data;
}

export async function getScoreHistory(limit = 12): Promise<HistoryEntry[]> {
  const res = await apiClient.get<HistoryEntry[]>("/readiness/history", { params: { limit } });
  return res.data;
}
