import type {
  ExecutiveRankingEntry,
  PortfolioAnalytics,
  RiskHeatmap,
  SupplierBenchmark,
  SupplierScoreHistoryEntry,
  SupplierScoreResponse,
  WatchlistEntry,
} from "@/types/api";
import apiClient from "./client";

const BASE = "/api/v1/suppliers";

// ── Risk Score Explanation (E5-F1) ────────────────────────────────────────────

export interface FactorExplanation {
  factor: string;
  label: string;
  count: number;
  weight: number;
  contribution: number;
  pct_of_total: number;
  impact: "high" | "medium" | "low" | "none";
}

export interface RiskScoreExplanation {
  composite_score: number;
  band: string;
  formula_version: string;
  factors: FactorExplanation[];
  top_drivers: FactorExplanation[];
  confidence_level: string;
  confidence_score: number;
  confidence_basis: string;
  limitations: string[];
}

export async function getSupplierRiskScoreExplanation(
  supplierId: string,
): Promise<RiskScoreExplanation> {
  const r = await apiClient.get(`${BASE}/${supplierId}/risk-score/explanation`);
  return r.data;
}

export async function getSupplierIntelligence(
  supplierId: string,
): Promise<SupplierScoreResponse> {
  const r = await apiClient.get(`${BASE}/${supplierId}/intelligence`);
  return r.data;
}

export async function recalculateSupplierScore(
  supplierId: string,
): Promise<SupplierScoreResponse> {
  const r = await apiClient.post(`${BASE}/${supplierId}/intelligence/recalculate`);
  return r.data;
}

export async function getSupplierScoreHistory(
  supplierId: string,
  limit = 12,
): Promise<SupplierScoreHistoryEntry[]> {
  const r = await apiClient.get(`${BASE}/${supplierId}/intelligence/history?limit=${limit}`);
  return r.data;
}

export async function getSupplierBenchmark(
  supplierId: string,
): Promise<SupplierBenchmark> {
  const r = await apiClient.get(`${BASE}/${supplierId}/benchmark`);
  return r.data;
}

export async function getSupplierHeatmap(supplierId: string): Promise<RiskHeatmap> {
  const r = await apiClient.get(`${BASE}/${supplierId}/heatmap`);
  return r.data;
}

export async function getPortfolioAnalytics(): Promise<PortfolioAnalytics> {
  const r = await apiClient.get(`${BASE}/analytics/portfolio`);
  return r.data;
}

export async function getIntelligenceWatchlist(limit = 20): Promise<WatchlistEntry[]> {
  const r = await apiClient.get(`${BASE}/analytics/watchlist?limit=${limit}`);
  return r.data;
}

export async function getExecutiveRankings(params?: {
  sort_by?: string;
  limit?: number;
  risk_band?: string;
  country?: string;
  supplier_tier?: string;
}): Promise<ExecutiveRankingEntry[]> {
  const qs = new URLSearchParams();
  if (params?.sort_by) qs.set("sort_by", params.sort_by);
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.risk_band) qs.set("risk_band", params.risk_band);
  if (params?.country) qs.set("country", params.country);
  if (params?.supplier_tier) qs.set("supplier_tier", params.supplier_tier);
  const q = qs.toString();
  const r = await apiClient.get(`${BASE}/analytics/rankings${q ? `?${q}` : ""}`);
  return r.data;
}

export async function getOrgRiskHeatmap(): Promise<RiskHeatmap> {
  const r = await apiClient.get(`${BASE}/analytics/heatmap`);
  return r.data;
}
