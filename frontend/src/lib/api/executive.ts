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

// ── M50: Command Center ───────────────────────────────────────────────────────

export interface PriorityAction {
  type: string;
  title: string;
  severity: "critical" | "high" | "medium";
  href: string;
  count: number;
}

export interface PendingDecision {
  id: string;
  title: string;
  priority: string;
  due_date: string | null;
}

export interface CommandCenterData {
  esg_health_score: number;
  health_label: "Excellent" | "Good" | "Needs Attention" | "Critical";
  priority_actions: PriorityAction[];
  pending_decisions: PendingDecision[];
  pending_decisions_count: number;
  yoy: {
    avg_esg_delta: number | null;
    prior_avg_esg: number | null;
    current_avg_esg: number | null;
  };
  ceo: {
    total_scored_suppliers: number;
    critical_risk_suppliers: number;
    open_findings: number;
    overdue_actions: number;
  };
  cfo: {
    taxonomy_alignment_pct: number | null;
    green_revenue_pct: number | null;
  };
  cso: {
    latest_emissions_tco2e: number | null;
    kpi_on_track: number;
    kpi_at_risk: number;
    kpi_missed: number;
  };
  cco: {
    soc2_readiness_pct: number | null;
    soc2_implemented: number;
    soc2_total: number;
    open_critical_findings: number;
  };
}

export async function getCommandCenter(): Promise<CommandCenterData> {
  return request(`${BASE}/command-center`);
}

// ── M50: Board Portal (public) ────────────────────────────────────────────────

export async function getBoardPortalData(token: string): Promise<{
  report_id: string;
  title: string;
  period_start: string;
  period_end: string;
  generated_at: string | null;
  report_version: string;
  executive_summary: string;
  allowed_sections: string[];
  expires_at: string;
  shared_with_email: string | null;
  supplier_snapshot: Record<string, unknown> | null;
  sections: Record<string, Record<string, unknown> | null>;
}> {
  const res = await fetch(`/api/v1/board/${token}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? res.statusText);
  }
  return res.json();
}

export function createShareLink(reportId: string, body: {
  expires_in_hours?: number;
  allowed_sections?: string[];
  shared_with_email?: string | null;
}): Promise<{ token: string; expires_at: string; report_id: string; board_url: string }> {
  return request(`/api/v1/executive/reports/${reportId}/share-link`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
