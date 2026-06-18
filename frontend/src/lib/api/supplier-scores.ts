import type {
  ExecutiveRankingEntry,
  PortfolioAnalytics,
  RiskHeatmap,
  SupplierBenchmark,
  SupplierScoreHistoryEntry,
  SupplierScoreResponse,
  WatchlistEntry,
} from "@/types/api";

const BASE = "/api/v1/suppliers";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function getSupplierIntelligence(
  supplierId: string,
): Promise<SupplierScoreResponse> {
  return request(`${BASE}/${supplierId}/intelligence`);
}

export async function recalculateSupplierScore(
  supplierId: string,
): Promise<SupplierScoreResponse> {
  return request(`${BASE}/${supplierId}/intelligence/recalculate`, {
    method: "POST",
  });
}

export async function getSupplierScoreHistory(
  supplierId: string,
  limit = 12,
): Promise<SupplierScoreHistoryEntry[]> {
  return request(`${BASE}/${supplierId}/intelligence/history?limit=${limit}`);
}

export async function getSupplierBenchmark(
  supplierId: string,
): Promise<SupplierBenchmark> {
  return request(`${BASE}/${supplierId}/benchmark`);
}

export async function getSupplierHeatmap(supplierId: string): Promise<RiskHeatmap> {
  return request(`${BASE}/${supplierId}/heatmap`);
}

export async function getPortfolioAnalytics(): Promise<PortfolioAnalytics> {
  return request(`${BASE}/analytics/portfolio`);
}

export async function getIntelligenceWatchlist(limit = 20): Promise<WatchlistEntry[]> {
  return request(`${BASE}/analytics/watchlist?limit=${limit}`);
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
  return request(`${BASE}/analytics/rankings${q ? `?${q}` : ""}`);
}

export async function getOrgRiskHeatmap(): Promise<RiskHeatmap> {
  return request(`${BASE}/analytics/heatmap`);
}
