import apiClient from "./client";
import axios from "axios";

const BACKEND_ORIGIN =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const PUBLIC_BASE = `${BACKEND_ORIGIN}/api/v1`;

export interface GrievanceSubmitRequest {
  organization_id: string;
  title: string;
  description: string;
  category: string;
  submitted_by_email?: string;
  submitted_by_name?: string;
  related_supplier_name?: string;
}

export interface GrievanceSubmitResponse {
  reference_code: string;
  message: string;
  status: string;
}

export interface GrievanceStatusCheckResponse {
  reference_code: string;
  status: string;
  category: string;
  submitted_at: string;
  last_updated: string;
}

export interface GrievanceReportResponse {
  id: string;
  organization_id: string;
  category: string;
  grievance_status: string;
  title: string;
  description: string;
  is_anonymous: boolean;
  anonymized_reference_code: string;
  related_supplier_id: string | null;
  assigned_to_user_id: string | null;
  reviewer_notes: string | null;
  resolution_notes: string | null;
  resolved_at: string | null;
  regulation_refs: string;
  linked_finding_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface GrievanceStatusUpdate {
  grievance_status: string;
  reviewer_notes?: string;
  resolution_notes?: string;
  assigned_to_user_id?: string;
}

export interface GrievanceSummary {
  total: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
}

// ── Public (no auth) ──────────────────────────────────────────────────────────

export async function submitGrievance(
  body: GrievanceSubmitRequest
): Promise<GrievanceSubmitResponse> {
  const r = await axios.post(`${PUBLIC_BASE}/grievances/submit`, body);
  return r.data;
}

export async function checkGrievanceStatus(
  referenceCode: string
): Promise<GrievanceStatusCheckResponse> {
  const r = await axios.get(
    `${PUBLIC_BASE}/grievances/status/${referenceCode}`
  );
  return r.data;
}

// ── Internal (auth required) ──────────────────────────────────────────────────

export async function listGrievances(opts: {
  status_filter?: string;
  category_filter?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<GrievanceReportResponse[]> {
  const params = new URLSearchParams();
  if (opts.status_filter) params.set("status_filter", opts.status_filter);
  if (opts.category_filter) params.set("category_filter", opts.category_filter);
  if (opts.limit) params.set("limit", String(opts.limit));
  if (opts.offset) params.set("offset", String(opts.offset));
  const r = await apiClient.get(`/grievances/?${params.toString()}`);
  return r.data;
}

export async function getGrievance(id: string): Promise<GrievanceReportResponse> {
  const r = await apiClient.get(`/grievances/${id}`);
  return r.data;
}

export async function updateGrievanceStatus(
  id: string,
  body: GrievanceStatusUpdate
): Promise<GrievanceReportResponse> {
  const r = await apiClient.patch(`/grievances/${id}/status`, body);
  return r.data;
}

export async function getGrievanceSummary(): Promise<GrievanceSummary> {
  const r = await apiClient.get("/grievances/summary");
  return r.data;
}
