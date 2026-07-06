import apiClient from "./client";

export interface ESAPSubmission {
  id: string;
  organization_id: string;
  report_year: number;
  export_format: string;
  status: string;
  submitted_at: string | null;
  submitted_by: string | null;
  confirmation_reference: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface TaxonomyMapping {
  schema_version: string;
  note: string;
  mapping: Record<string, { xbrl_concept: string; csddd_article: string; mandatory: boolean; data_type: string; eios_source: string }>;
}

export interface ValidationChecklist {
  report_year: number;
  is_valid: boolean;
  missing_count: number;
  checklist: { field: string; xbrl_concept: string; csddd_article: string; mandatory: boolean; status: "ok" | "missing" }[];
  esap_note: string;
}

const BASE = "/esap";

export async function getTaxonomy(): Promise<TaxonomyMapping> {
  const { data } = await apiClient.get(`${BASE}/taxonomy`);
  return data;
}

export async function exportReport(reportYear: number, format: "json" | "xml"): Promise<string> {
  const { data } = await apiClient.get(`${BASE}/export`, { params: { report_year: reportYear, format } });
  return typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

export async function validateReport(reportYear: number): Promise<ValidationChecklist> {
  const { data } = await apiClient.get(`${BASE}/validate`, { params: { report_year: reportYear } });
  return data;
}

export async function listSubmissions(): Promise<ESAPSubmission[]> {
  const { data } = await apiClient.get(`${BASE}/submissions`);
  return data;
}

export async function createSubmission(reportYear: number, format: string, notes: string): Promise<ESAPSubmission> {
  const { data } = await apiClient.post(`${BASE}/submissions`, { report_year: reportYear, export_format: format, notes });
  return data;
}

export async function markReady(id: string): Promise<ESAPSubmission> {
  const { data } = await apiClient.post(`${BASE}/submissions/${id}/ready`);
  return data;
}

export async function recordSubmission(id: string, submittedBy: string, confirmationReference: string): Promise<ESAPSubmission> {
  const { data } = await apiClient.post(`${BASE}/submissions/${id}/submit`, { submitted_by: submittedBy, confirmation_reference: confirmationReference });
  return data;
}
