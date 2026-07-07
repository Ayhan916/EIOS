import apiClient from "./client";

export interface DocumentSource {
  id: string;
  organization_id: string;
  supplier_id: string | null;
  company_name: string | null;
  doc_type: string;
  source_url: string;
  schedule: string;
  is_active: boolean;
  last_fetched_at: string | null;
  last_status: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentFile {
  id: string;
  organization_id: string;
  source_id: string;
  supplier_id: string | null;
  doc_type: string;
  title: string | null;
  company_name: string | null;
  report_year: number | null;
  language: string | null;
  file_url: string | null;
  pages: number | null;
  chunks_count: number | null;
  esg_score: number | null;
  summary: string | null;
  extracted_risks: string[] | null;
  extracted_targets: string[] | null;
  extracted_commitments: string[] | null;
  extracted_kpis: Record<string, string> | null;
  status: string;
  error_msg: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentSourceCreate {
  supplier_id?: string;
  company_name?: string;
  doc_type: string;
  source_url: string;
  schedule?: string;
}

export interface DocumentSourceUpdate {
  company_name?: string;
  source_url?: string;
  schedule?: string;
  is_active?: boolean;
}

export interface IngestStats {
  ingested?: number;
  skipped?: number;
  errors?: number;
  new_files?: number;
  [key: string]: unknown;
}

export async function listSources(): Promise<DocumentSource[]> {
  const r = await apiClient.get("/documents/sources");
  return r.data;
}

export async function createSource(payload: DocumentSourceCreate): Promise<DocumentSource> {
  const r = await apiClient.post("/documents/sources", payload);
  return r.data;
}

export async function updateSource(
  id: string,
  payload: DocumentSourceUpdate,
): Promise<DocumentSource> {
  const r = await apiClient.patch(`/documents/sources/${id}`, payload);
  return r.data;
}

export async function deleteSource(id: string): Promise<void> {
  await apiClient.delete(`/documents/sources/${id}`);
}

export async function triggerIngest(sourceId: string): Promise<{ source_id: string; stats: IngestStats }> {
  const r = await apiClient.post(`/documents/sources/${sourceId}/ingest`, null, { timeout: 120_000 });
  return r.data;
}

export async function listFiles(params?: {
  doc_type?: string;
  supplier_id?: string;
  status?: string;
}): Promise<DocumentFile[]> {
  const r = await apiClient.get("/documents/files", { params });
  return r.data;
}

export async function getFile(id: string): Promise<DocumentFile> {
  const r = await apiClient.get(`/documents/files/${id}`);
  return r.data;
}

export async function ingestAll(): Promise<{ organization_id: string; stats: IngestStats }> {
  const r = await apiClient.post("/documents/ingest-all", null, { timeout: 300_000 });
  return r.data;
}
