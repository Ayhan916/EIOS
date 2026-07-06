import apiClient from "./client";

export interface BoardSignoffRequest {
  id: string;
  organization_id: string;
  title: string;
  signoff_type: string;
  entity_type: string | null;
  entity_id: string | null;
  description: string;
  status: string;
  requested_by: string;
  requested_at: string;
  due_date: string | null;
  approved_at: string | null;
  approved_by: string | null;
  approved_by_role: string | null;
  rejection_reason: string | null;
  document_ref: string | null;
  created_at: string;
  updated_at: string;
}

export interface BoardDecision {
  id: string;
  request_id: string;
  decision: string;
  decided_by: string;
  decided_by_role: string;
  comment: string | null;
  decided_at: string;
}

export interface BoardDashboard {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  overdue: number;
  approval_rate_pct: number;
}

export interface CreateSignoffRequest {
  title: string;
  signoff_type: string;
  description?: string;
  entity_type?: string;
  entity_id?: string;
  due_date?: string;
  document_ref?: string;
}

export interface ApproveBody {
  approved_by: string;
  approved_by_role: string;
  comment?: string;
}

export interface RejectBody {
  rejected_by: string;
  rejected_by_role: string;
  reason: string;
}

const BASE = "/board-signoff";

export async function getBoardDashboard(): Promise<BoardDashboard> {
  const { data } = await apiClient.get(`${BASE}/dashboard`);
  return data;
}

export async function listBoardRequests(params?: {
  status?: string;
  signoff_type?: string;
}): Promise<BoardSignoffRequest[]> {
  const { data } = await apiClient.get(BASE + "/", { params });
  return data;
}

export async function createBoardRequest(body: CreateSignoffRequest): Promise<BoardSignoffRequest> {
  const { data } = await apiClient.post(BASE + "/", body);
  return data;
}

export async function getBoardRequest(id: string): Promise<BoardSignoffRequest> {
  const { data } = await apiClient.get(`${BASE}/${id}`);
  return data;
}

export async function approveRequest(id: string, body: ApproveBody): Promise<BoardSignoffRequest> {
  const { data } = await apiClient.post(`${BASE}/${id}/approve`, body);
  return data;
}

export async function rejectRequest(id: string, body: RejectBody): Promise<BoardSignoffRequest> {
  const { data } = await apiClient.post(`${BASE}/${id}/reject`, body);
  return data;
}

export async function withdrawRequest(id: string): Promise<BoardSignoffRequest> {
  const { data } = await apiClient.post(`${BASE}/${id}/withdraw`);
  return data;
}

export async function getDecisions(id: string): Promise<BoardDecision[]> {
  const { data } = await apiClient.get(`${BASE}/${id}/decisions`);
  return data;
}
