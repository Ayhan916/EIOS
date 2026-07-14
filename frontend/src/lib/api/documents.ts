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

export interface ExtractedRisk {
  title: string;
  description: string;
  category: string;
  severity: "kritisch" | "hoch" | "mittel" | "niedrig" | string;
}

export interface ExtractedTarget {
  area: string;
  target: string;
  target_year: number | null;
  baseline_year: number | null;
  current_progress: string | null;
}

export interface ExtractedCommitment {
  article: string;
  commitment: string;
  status: string;
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
  extracted_risks: ExtractedRisk[] | null;
  extracted_targets: ExtractedTarget[] | null;
  extracted_commitments: ExtractedCommitment[] | null;
  extracted_kpis: Record<string, number | string | null> | null;
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

export async function deleteFile(id: string): Promise<void> {
  await apiClient.delete(`/documents/files/${id}`);
}

export interface ClassifyResult {
  filename: string;
  doc_type: string;
  report_year: number | null;
  title: string | null;
  confidence_source: "filename" | "llm" | "fallback";
}

export async function classifyDocument(file: File): Promise<ClassifyResult> {
  const form = new FormData();
  form.append("file", file);
  const r = await apiClient.post("/documents/classify", form, {
    timeout: 30_000,
  });
  return r.data;
}

export async function ingestAll(): Promise<{ organization_id: string; stats: IngestStats }> {
  const r = await apiClient.post("/documents/ingest-all", null, { timeout: 300_000 });
  return r.data;
}

export async function deleteQueuedFiles(): Promise<{ deleted: number; message: string }> {
  const r = await apiClient.delete("/documents/files/queued");
  return r.data;
}

export interface ReclassifyResult {
  doc_file_id: string;
  old_doc_type: string;
  new_doc_type: string;
  new_doc_class: string;
  new_company_name: string | null;
  new_report_year: number | null;
  changed: boolean;
}

export interface ReclassifyAllResult {
  total: number;
  changed: number;
  errors: number;
  details: (ReclassifyResult | { error: string; doc_file_id: string })[];
}

export async function processSingleFile(fileId: string): Promise<{ queued: number; doc_file_id: string }> {
  const r = await apiClient.post(`/documents/files/${fileId}/process`, null, { timeout: 10_000 });
  return r.data;
}

export async function processPending(): Promise<{ queued: number; organization_id: string }> {
  const r = await apiClient.post("/documents/process-pending", null, { timeout: 10_000 });
  return r.data;
}

export async function cancelProcessing(): Promise<{ cancelled: boolean }> {
  const r = await apiClient.post("/documents/cancel-processing", null, { timeout: 5_000 });
  return r.data;
}

export async function reclassifyAllFiles(): Promise<ReclassifyAllResult> {
  const r = await apiClient.post("/documents/files/reclassify-all", null, { timeout: 600_000 });
  return r.data;
}

export async function reclassifyFile(id: string): Promise<ReclassifyResult> {
  const r = await apiClient.post(`/documents/files/${id}/reclassify`, null, { timeout: 60_000 });
  return r.data;
}

// ── Review API ────────────────────────────────────────────────────────────────

export interface ReviewChunk {
  id: string;
  content: string;
  chunk_level: string;
  doc_class: string | null;
}

export interface ReviewMetric {
  id: string;
  metric_type: string;
  value: number;
  unit: string;
  year: number;
  period: string;
  confidence: string;
}

export interface ReviewSignal {
  id: string;
  signal_type: string;
  dimension: string;
  direction: string;
  severity: string;
  description: string;
  year: number | null;
}

export interface ReviewAuditEntry {
  id: string;
  user_id: string;
  action: string;
  field: string | null;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

export interface ReviewData {
  id: string;
  doc_type: string;
  company_name: string | null;
  report_year: number | null;
  title: string | null;
  language: string | null;
  pages: number | null;
  chunks_count: number | null;
  esg_score: number | null;
  summary: string | null;
  status: string;
  review_status: string;
  review_notes: string | null;
  parsed_text: string | null;
  extracted_kpis: Record<string, unknown> | null;
  extracted_risks: unknown[] | null;
  extracted_targets: unknown[] | null;
  extracted_commitments: unknown[] | null;
  has_pdf: boolean;
  created_at: string;
  updated_at: string;
  chunks: ReviewChunk[];
  metrics: ReviewMetric[];
  signals: ReviewSignal[];
  audit_log: ReviewAuditEntry[];
}

export async function getFileReview(fileId: string): Promise<ReviewData> {
  const r = await apiClient.get(`/documents/files/${fileId}/review`);
  return r.data;
}

export async function updateClassification(
  fileId: string,
  payload: { doc_type?: string; company_name?: string; report_year?: number },
): Promise<{ updated: number; fields: string[] }> {
  const r = await apiClient.patch(`/documents/files/${fileId}/classification`, payload);
  return r.data;
}

export async function updateKpis(
  fileId: string,
  kpis: Record<string, unknown>,
): Promise<{ updated: boolean }> {
  const r = await apiClient.patch(`/documents/files/${fileId}/kpis`, { kpis });
  return r.data;
}

export async function approveDocument(
  fileId: string,
  notes?: string,
): Promise<{ review_status: string }> {
  const r = await apiClient.post(`/documents/files/${fileId}/approve`, { notes });
  return r.data;
}

export async function deleteChunk(chunkId: string): Promise<void> {
  await apiClient.delete(`/documents/chunks/${chunkId}`);
}

export async function updateChunk(
  chunkId: string,
  content: string,
): Promise<{ updated: boolean; embedding_invalidated: boolean }> {
  const r = await apiClient.patch(`/documents/chunks/${chunkId}`, { content });
  return r.data;
}

export async function testRetrieval(
  fileId: string,
  query: string,
  topK = 5,
  minSim = 0.25,
): Promise<{ query: string; results: { chunk_id: string; similarity: number; chunk_level: string; doc_class: string | null; content_preview: string }[] }> {
  const r = await apiClient.post(`/documents/files/${fileId}/test-retrieval`, {
    query,
    top_k: topK,
    min_sim: minSim,
  });
  return r.data;
}

export function getFilePdfUrl(fileId: string): string {
  const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return `${BACKEND}/api/v1/documents/files/${fileId}/serve`;
}

export async function uploadDocument(
  sourceId: string,
  file: File,
  onProgress?: (pct: number) => void,
  reportYear?: number,
  title?: string,
  signal?: AbortSignal,
): Promise<{ source_id: string; filename: string; stats: IngestStats }> {
  const form = new FormData();
  form.append("file", file);
  if (reportYear) form.append("report_year", String(reportYear));
  if (title) form.append("title", title);

  const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const token = typeof window !== "undefined" ? localStorage.getItem("eios_access_token") : null;

  // Use native fetch — Axios sets Content-Type: application/json by default which
  // strips the multipart boundary and causes 422. fetch() lets the browser set the
  // correct Content-Type: multipart/form-data; boundary=... automatically.
  const r = await fetch(`${BACKEND}/api/v1/documents/sources/${sourceId}/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
    signal,
  });

  if (!r.ok) {
    const text = await r.text().catch(() => r.statusText);
    throw new Error(`Upload fehlgeschlagen (${r.status}): ${text}`);
  }

  return r.json();
}
