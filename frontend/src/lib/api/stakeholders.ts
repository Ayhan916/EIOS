import apiClient from "./client";

export interface Stakeholder {
  id: string;
  organization_id: string;
  name: string;
  stakeholder_type: string;
  contact_email: string | null;
  language: string;
  activity_chain_ids: string[];
  regions: string[];
  risk_topics: string[];
  justification: string;
  created_at: string;
  updated_at: string;
}

export interface StakeholderCreate {
  name: string;
  stakeholder_type: string;
  contact_email?: string;
  language?: string;
  activity_chain_ids?: string[];
  regions?: string[];
  risk_topics?: string[];
  justification: string;
}

export interface Consultation {
  id: string;
  organization_id: string;
  stakeholder_ids: string[];
  consultation_date: string | null;
  format: string;
  topics: string[];
  description: string;
  outcomes: string;
  barrier: string;
  barrier_notes: string;
  linked_risk_id: string | null;
  linked_finding_id: string | null;
  linked_cap_id: string | null;
  feedback_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConsultationCreate {
  stakeholder_ids: string[];
  consultation_date?: string;
  format: string;
  topics?: string[];
  description: string;
  outcomes?: string;
  barrier: string;
  barrier_notes?: string;
  linked_risk_id?: string;
  linked_finding_id?: string;
  linked_cap_id?: string;
}

export interface EngagementReport {
  total_stakeholders: number;
  stakeholders_by_type: Record<string, number>;
  total_consultations: number;
  consultations_by_format: Record<string, number>;
  barrier_summary: Record<string, number>;
  stakeholders_without_consultation_12m: number;
  consultations: Consultation[];
  stakeholders: Stakeholder[];
}

export interface MapNode {
  id: string;
  name: string;
  type: string;
  lastConsultation: string | null;
  color: "green" | "yellow" | "red";
  regions: string[];
}

export async function listStakeholders(params?: {
  stakeholder_type?: string;
  limit?: number;
  offset?: number;
}): Promise<Stakeholder[]> {
  const { data } = await apiClient.get<Stakeholder[]>("/stakeholders/", { params });
  return data;
}

export async function createStakeholder(body: StakeholderCreate): Promise<Stakeholder> {
  const { data } = await apiClient.post<Stakeholder>("/stakeholders/", body);
  return data;
}

export async function getStakeholder(id: string): Promise<Stakeholder> {
  const { data } = await apiClient.get<Stakeholder>(`/stakeholders/${id}`);
  return data;
}

export async function updateStakeholder(id: string, body: Partial<StakeholderCreate>): Promise<Stakeholder> {
  const { data } = await apiClient.patch<Stakeholder>(`/stakeholders/${id}`, body);
  return data;
}

export async function deleteStakeholder(id: string): Promise<void> {
  await apiClient.delete(`/stakeholders/${id}`);
}

export async function listConsultations(params?: {
  stakeholder_id?: string;
  limit?: number;
}): Promise<Consultation[]> {
  const { data } = await apiClient.get<Consultation[]>("/stakeholders/consultations/", { params });
  return data;
}

export async function createConsultation(body: ConsultationCreate): Promise<Consultation> {
  const { data } = await apiClient.post<Consultation>("/stakeholders/consultations/", body);
  return data;
}

export async function updateConsultation(id: string, body: Partial<ConsultationCreate>): Promise<Consultation> {
  const { data } = await apiClient.patch<Consultation>(`/stakeholders/consultations/${id}`, body);
  return data;
}

export async function getEngagementReport(): Promise<EngagementReport> {
  const { data } = await apiClient.get<EngagementReport>("/stakeholders/report/engagement");
  return data;
}

export async function getMapData(): Promise<{ nodes: MapNode[] }> {
  const { data } = await apiClient.get<{ nodes: MapNode[] }>("/stakeholders/map-data");
  return data;
}
