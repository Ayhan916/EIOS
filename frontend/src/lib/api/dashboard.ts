import apiClient from "./client";
import type { ReviewQueueItem, SupplierWatchlistItem } from "@/types/api";

export interface RecentAssessmentItem {
  id: string;
  title: string;
  status: string;
  review_status: string;
  assessment_type: string | null;
  quality_score: number | null;
  finding_count: number;
  risk_count: number;
  created_at: string;
}

export interface MonthlyCount {
  month: string;
  count: number;
}

export interface DashboardData {
  total_assessments: number;
  avg_quality_score: number | null;
  action_status_breakdown: Record<string, number>;
  open_actions: number;
  overdue_actions: number;
  closed_actions_pct: number;
  findings_by_severity: Record<string, number>;
  findings_by_category: Record<string, number>;
  high_risk_finding_count: number;
  critical_finding_count: number;
  recent_assessments: RecentAssessmentItem[];
  assessments_over_time: MonthlyCount[];
  // M26 review queue
  awaiting_review: number;
  reviews_overdue: number;
  recently_approved: number;
  recently_rejected: number;
  review_queue: ReviewQueueItem[];
  // M27 supplier KPIs
  total_suppliers: number;
  active_suppliers: number;
  suppliers_with_critical_risks: number;
  suppliers_without_assessments: number;
  supplier_watchlist: SupplierWatchlistItem[];
}

export async function getDashboard(): Promise<DashboardData> {
  const res = await apiClient.get<DashboardData>("/dashboard/");
  return res.data;
}
