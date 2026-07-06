import apiClient from "./client";

export interface CompanyProfile {
  id: string;
  organization_id: string;
  fiscal_year: number;
  employee_count_worldwide: number;
  net_revenue_eur_millions: number;
  headquarters_country: string;
  sector: string;
  non_eu_company: boolean;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface ThresholdStatus {
  fiscal_year: number;
  level: string;
  employee_count: number;
  net_revenue_eur_millions: number;
  tier1: { employee_met: boolean; revenue_met: boolean; deadline: string };
  tier2: { employee_met: boolean; revenue_met: boolean; deadline: string };
  is_borderline: boolean;
  borderline_message: string;
  recommendation: string;
}

export interface ThresholdInfo {
  tier_1: { employees: number; revenue_eur_millions: number; deadline: string; obligations: string[] };
  tier_2: { employees: number; revenue_eur_millions: number; deadline: string; obligations: string[] };
  borderline_pct: number;
  source: string;
}

export interface ProfileUpsert {
  fiscal_year: number;
  employee_count_worldwide: number;
  net_revenue_eur_millions: number;
  headquarters_country?: string;
  sector?: string;
  non_eu_company?: boolean;
  notes?: string;
}

const BASE = "/threshold";

export async function getThresholdInfo(): Promise<ThresholdInfo> {
  const { data } = await apiClient.get(`${BASE}/info`);
  return data;
}

export async function getThresholdStatus(): Promise<ThresholdStatus> {
  const { data } = await apiClient.get(`${BASE}/status`);
  return data;
}

export async function listProfiles(): Promise<CompanyProfile[]> {
  const { data } = await apiClient.get(`${BASE}/profiles`);
  return data;
}

export async function upsertProfile(body: ProfileUpsert): Promise<CompanyProfile> {
  const { data } = await apiClient.post(`${BASE}/profiles`, body);
  return data;
}
