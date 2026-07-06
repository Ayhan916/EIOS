import apiClient from "./client";

export interface RegulatorySource {
  id: string;
  organization_id: string | null;
  name: string;
  url: string;
  description: string;
  relevance_score: number;
  country_code: string | null;
  rss_feed_url: string | null;
  is_active: boolean;
  last_fetched_at: string | null;
}

export interface RegulatoryChange {
  id: string;
  organization_id: string;
  title: string;
  source_name: string;
  url: string | null;
  effective_date: string | null;
  summary: string;
  affected_articles: string[];
  status: string;
  action_required: string;
  action_description: string;
  impact_modules: string[];
  estimated_effort_days: number;
  due_date: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface RadarDashboard {
  total: number;
  new: number;
  action_required: number;
  implemented: number;
  not_relevant: number;
}

export interface ChangeCreate {
  title: string;
  source_name?: string;
  summary?: string;
  url?: string;
  effective_date?: string;
  affected_articles?: string[];
  action_required?: string;
  action_description?: string;
  impact_modules?: string[];
  estimated_effort_days?: number;
  due_date?: string;
}

export interface ChangeUpdate {
  status?: string;
  action_required?: string;
  action_description?: string;
  impact_modules?: string[];
  estimated_effort_days?: number;
  due_date?: string;
}

const BASE = "/regulatory-radar";

export async function getRadarDashboard(): Promise<RadarDashboard> {
  const { data } = await apiClient.get(`${BASE}/dashboard`);
  return data;
}

export async function listSources(): Promise<RegulatorySource[]> {
  const { data } = await apiClient.get(`${BASE}/sources`);
  return data;
}

export async function seedSources(): Promise<{ seeded: number }> {
  const { data } = await apiClient.post(`${BASE}/sources/seed`);
  return data;
}

export async function listChanges(params?: { status?: string; action_required?: string }): Promise<RegulatoryChange[]> {
  const { data } = await apiClient.get(`${BASE}/changes`, { params });
  return data;
}

export async function createChange(body: ChangeCreate): Promise<RegulatoryChange> {
  const { data } = await apiClient.post(`${BASE}/changes`, body);
  return data;
}

export async function updateChange(id: string, body: ChangeUpdate): Promise<RegulatoryChange> {
  const { data } = await apiClient.patch(`${BASE}/changes/${id}`, body);
  return data;
}
