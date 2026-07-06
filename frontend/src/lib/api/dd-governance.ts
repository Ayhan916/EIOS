import apiClient from "./client";

export interface DDPolicy {
  id: string;
  organization_id: string;
  title: string;
  policy_status: "draft" | "active" | "archived";
  content_text: string;
  file_url: string | null;
  approved_by: string;
  approved_role: string;
  valid_from: string | null;
  published_at: string | null;
  next_review_due: string | null;
  is_public: boolean;
  public_token: string | null;
  policy_version: number;
  parent_policy_id: string | null;
  review_status: string;
  created_at: string;
  updated_at: string;
}

export interface DDPolicyCreate {
  title: string;
  content_text?: string;
  approved_by?: string;
  approved_role?: string;
  valid_from?: string;
  is_public?: boolean;
}

export interface CodeOfConduct {
  id: string;
  organization_id: string;
  title: string;
  content_text: string;
  coc_version: number;
  valid_from: string | null;
  acceptance_validity_months: number;
  is_active: boolean;
  linked_policy_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewStatus {
  has_active_policy: boolean;
  review_status: string;
  next_review_due: string | null;
  days_until_review: number | null;
  policy_version: number | null;
  policy_title: string | null;
}

export interface GovernanceEvent {
  event_type: string;
  title: string;
  due_date: string | null;
  status: string;
  detail: string;
  reference_id: string;
}

export async function listPolicies(): Promise<DDPolicy[]> {
  const { data } = await apiClient.get<DDPolicy[]>("/governance/policies/");
  return data;
}

export async function getActivePolicy(): Promise<DDPolicy | null> {
  const { data } = await apiClient.get<DDPolicy | null>("/governance/policies/active");
  return data;
}

export async function createPolicy(body: DDPolicyCreate): Promise<DDPolicy> {
  const { data } = await apiClient.post<DDPolicy>("/governance/policies/", body);
  return data;
}

export async function updatePolicy(id: string, body: Partial<DDPolicyCreate>): Promise<DDPolicy> {
  const { data } = await apiClient.patch<DDPolicy>(`/governance/policies/${id}`, body);
  return data;
}

export async function activatePolicy(id: string): Promise<DDPolicy> {
  const { data } = await apiClient.post<DDPolicy>(`/governance/policies/${id}/activate`);
  return data;
}

export async function clonePolicy(id: string): Promise<DDPolicy> {
  const { data } = await apiClient.post<DDPolicy>(`/governance/policies/${id}/clone`);
  return data;
}

export async function archivePolicy(id: string): Promise<DDPolicy> {
  const { data } = await apiClient.post<DDPolicy>(`/governance/policies/${id}/archive`);
  return data;
}

export async function listCoCs(): Promise<CodeOfConduct[]> {
  const { data } = await apiClient.get<CodeOfConduct[]>("/governance/codes-of-conduct/");
  return data;
}

export async function createCoC(body: {
  title: string;
  content_text?: string;
  valid_from?: string;
  acceptance_validity_months?: number;
  linked_policy_id?: string;
}): Promise<CodeOfConduct> {
  const { data } = await apiClient.post<CodeOfConduct>("/governance/codes-of-conduct/", body);
  return data;
}

export async function getReviewStatus(): Promise<ReviewStatus> {
  const { data } = await apiClient.get<ReviewStatus>("/governance/review-status");
  return data;
}

export async function getCalendar(): Promise<{ events: GovernanceEvent[] }> {
  const { data } = await apiClient.get<{ events: GovernanceEvent[] }>("/governance/calendar");
  return data;
}
