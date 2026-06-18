import type {
  ActionEffectivenessResponse,
  BoardReportDetail,
  BoardReportRequest,
  BoardReportSummary,
  ExecutiveDashboard,
  ExecutiveHeatmapResponse,
  GovernanceMetricsResponse,
  KPITrendResponse,
  ReportScheduleRequest,
  ReportScheduleResponse,
  RiskRegisterEntry,
} from "@/types/api";

const BASE = "/api/v1/executive";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function getExecutiveDashboard(): Promise<ExecutiveDashboard> {
  return request(`${BASE}/dashboard`);
}

export async function getKPITrends(
  period: 30 | 90 | 365 = 90,
): Promise<KPITrendResponse> {
  return request(`${BASE}/kpi-trends?period=${period}`);
}

export async function getRiskRegister(params?: {
  limit?: number;
  sort_by?: string;
  risk_band?: string;
  country?: string;
  supplier_tier?: string;
}): Promise<RiskRegisterEntry[]> {
  const qs = new URLSearchParams();
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.sort_by) qs.set("sort_by", params.sort_by);
  if (params?.risk_band) qs.set("risk_band", params.risk_band);
  if (params?.country) qs.set("country", params.country);
  if (params?.supplier_tier) qs.set("supplier_tier", params.supplier_tier);
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return request(`${BASE}/risk-register${query}`);
}

export async function getExecutiveHeatmap(
  view: "country" | "sector" | "tier" = "country",
): Promise<ExecutiveHeatmapResponse> {
  return request(`${BASE}/heatmaps?view=${view}`);
}

export async function getActionEffectiveness(
  period: number = 30,
): Promise<ActionEffectivenessResponse> {
  return request(`${BASE}/action-effectiveness?period=${period}`);
}

export async function getGovernanceMetrics(
  period: number = 30,
): Promise<GovernanceMetricsResponse> {
  return request(`${BASE}/governance-metrics?period=${period}`);
}

export async function generateBoardReport(
  body: BoardReportRequest,
): Promise<BoardReportDetail> {
  return request(`${BASE}/reports`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function listBoardReports(
  limit = 20,
): Promise<BoardReportSummary[]> {
  return request(`${BASE}/reports?limit=${limit}`);
}

export async function getBoardReport(id: string): Promise<BoardReportDetail> {
  return request(`${BASE}/reports/${id}`);
}

export async function deleteBoardReport(id: string): Promise<void> {
  const res = await fetch(`${BASE}/reports/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? res.statusText);
  }
}

export function boardReportPdfUrl(id: string): string {
  return `${BASE}/reports/${id}/pdf`;
}

export async function createReportSchedule(
  body: ReportScheduleRequest,
): Promise<ReportScheduleResponse> {
  return request(`${BASE}/schedules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function listReportSchedules(): Promise<ReportScheduleResponse[]> {
  return request(`${BASE}/schedules`);
}

export async function deleteReportSchedule(id: string): Promise<void> {
  const res = await fetch(`${BASE}/schedules/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? res.statusText);
  }
}
