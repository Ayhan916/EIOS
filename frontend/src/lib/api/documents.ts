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
  review_status: string;
  copilot_hidden: boolean;
  classification_confidence: number | null;
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

export async function reclassifyFile(id: string, model?: string): Promise<ReclassifyResult> {
  const params: Record<string, string> = {};
  if (model) params.model = model;
  const r = await apiClient.post(`/documents/files/${id}/reclassify`, null, { params, timeout: 60_000 });
  return r.data;
}

export async function reanalyzeFile(id: string, model?: string, extraContext?: string): Promise<{ doc_file_id: string; has_summary: boolean; kpi_count: number }> {
  const params: Record<string, string> = {};
  if (model) params.model = model;
  const body = extraContext ? { extra_context: extraContext } : {};
  const r = await apiClient.post(`/documents/files/${id}/reanalyze`, body, { params, timeout: 120_000 });
  return r.data;
}

export async function processFile(id: string): Promise<{ queued: number; doc_file_id: string }> {
  const r = await apiClient.post(`/documents/files/${id}/process`, null, { timeout: 30_000 });
  return r.data;
}

export async function reparseFile(
  id: string,
  parseEngine?: string,
  ocrEnabled?: boolean,
  extractTables?: boolean,
  describePictures?: boolean,
): Promise<{ doc_file_id: string; pages: number; chars: number }> {
  const params: Record<string, string | boolean> = {};
  if (parseEngine) params.parse_engine = parseEngine;
  if (ocrEnabled !== undefined) params.ocr_enabled = ocrEnabled;
  if (extractTables !== undefined) params.extract_tables = extractTables;
  if (describePictures !== undefined) params.describe_pictures = describePictures;
  const r = await apiClient.post(`/documents/files/${id}/reparse`, null, { params, timeout: 300_000 });
  return r.data;
}

export async function rechunkFile(id: string, chunkSize?: number, chunkOverlap?: number, chunkStrategy?: string): Promise<{ doc_file_id: string; chunks_added: number }> {
  const params: Record<string, number | string> = {};
  if (chunkSize) params.chunk_size = chunkSize;
  if (chunkOverlap) params.chunk_overlap = chunkOverlap;
  if (chunkStrategy) params.chunk_strategy = chunkStrategy;
  const r = await apiClient.post(`/documents/files/${id}/rechunk`, null, { params, timeout: 180_000 });
  return r.data;
}

export async function reextractMetrics(id: string, model?: string): Promise<{ doc_file_id: string; metrics: number; signals: number }> {
  const params: Record<string, string> = {};
  if (model) params.model = model;
  const r = await apiClient.post(`/documents/files/${id}/reextract-metrics`, null, { params, timeout: 180_000 });
  return r.data;
}

export async function excludeChunk(chunkId: string): Promise<{ excluded: boolean; chunk_id: string }> {
  const r = await apiClient.patch(`/documents/chunks/${chunkId}/exclude`);
  return r.data;
}

export async function toggleCopilotVisibility(fileId: string): Promise<{ copilot_hidden: boolean; file_id: string }> {
  const r = await apiClient.patch(`/documents/files/${fileId}/copilot-visibility`);
  return r.data;
}

export async function updateMetric(
  metricId: string,
  payload: { value?: number; unit?: string; year?: number; period?: string; confidence?: string },
): Promise<{ id: string; updated: boolean }> {
  const r = await apiClient.patch(`/documents/metrics/${metricId}`, payload);
  return r.data;
}

export async function deleteMetric(metricId: string): Promise<void> {
  await apiClient.delete(`/documents/metrics/${metricId}`);
}

export async function addMetric(
  fileId: string,
  payload: { metric_type: string; value: number; unit: string; year: number; period?: string; confidence?: string },
): Promise<ReviewMetric> {
  const r = await apiClient.post(`/documents/files/${fileId}/metrics`, payload);
  return r.data;
}

// ── Review API ────────────────────────────────────────────────────────────────

export interface ReviewChunk {
  id: string;
  content: string;
  chunk_level: string;
  doc_class: string | null;
  page_number?: number | null;
  excluded_from_index?: boolean;
}

export interface ReviewMetric {
  id: string;
  metric_type: string;
  value: number;
  unit: string;
  year: number;
  period: string;
  confidence: string;
  confidence_pct: number | null;
  page_number: number | null;
  scope: string | null;
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
  copilot_hidden: boolean;
  classification_confidence: number | null;
  classification_alternatives: { doc_type: string; confidence: number }[] | null;
  classification_evidence: string[] | null;
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

export async function unapproveDocument(fileId: string): Promise<{ review_status: string }> {
  const r = await apiClient.post(`/documents/files/${fileId}/unapprove`, {});
  return r.data;
}

export interface SandboxChunk {
  chunk_id: string;
  content: string;
  page_number: number | null;
  excluded_from_index: boolean;
  similarity: number;
}

export interface CorpusSimilarChunk {
  chunk_id: string;
  content: string;
  page_number: number | null;
  similarity: number;
  doc_id: string;
  company_name: string | null;
  title: string | null;
  report_year: number | null;
  doc_type: string;
}

export interface SandboxResult {
  query: string;
  answer: string | null;
  chunks: SandboxChunk[];
  corpus_similar: CorpusSimilarChunk[];
}

export async function runCopilotSandbox(fileId: string, query: string): Promise<SandboxResult> {
  const r = await apiClient.post(`/documents/files/${fileId}/sandbox`, { query }, { timeout: 60_000 });
  return r.data;
}

export interface LayoutElement {
  type: "text" | "table" | "figure" | "unknown";
  l: number; t: number; r: number; b: number;
  page_h: number | null;
}

export interface ParseLayout {
  file_id: string;
  pages: number | null;
  layout: Record<string, LayoutElement[]>;
}

export async function getParseLayout(fileId: string): Promise<ParseLayout> {
  const r = await apiClient.get(`/documents/files/${fileId}/parse-layout`);
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

export interface SupplierAuditEntry {
  id: string;
  doc_file_id: string;
  doc_title: string;
  doc_type: string;
  report_year: number | null;
  user_id: string;
  action: string;
  field: string | null;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

export async function getSupplierAuditLog(supplierId: string, limit = 200): Promise<SupplierAuditEntry[]> {
  const r = await apiClient.get(`/documents/suppliers/${supplierId}/audit-log`, { params: { limit } });
  return r.data;
}

export async function splitChunk(
  chunkId: string,
  splitAt: number,
): Promise<{ split: boolean; chunk_a_id: string; chunk_b_id: string }> {
  const r = await apiClient.post(`/documents/chunks/${chunkId}/split`, { split_at: splitAt });
  return r.data;
}

export async function mergeChunks(
  chunkId: string,
  otherChunkId: string,
): Promise<{ merged: boolean; surviving_chunk_id: string; deleted_chunk_id: string }> {
  const r = await apiClient.post(`/documents/chunks/${chunkId}/merge`, { other_chunk_id: otherChunkId });
  return r.data;
}

// ── Chunk Comments (P2-D) ─────────────────────────────────────────────────────

export interface ChunkComment {
  id: string;
  user_id: string | null;
  comment: string;
  created_at: string;
}

export async function listChunkComments(chunkId: string): Promise<ChunkComment[]> {
  const r = await apiClient.get(`/documents/chunks/${chunkId}/comments`);
  return r.data;
}

export async function createChunkComment(chunkId: string, comment: string): Promise<{ id: string; chunk_id: string; comment: string }> {
  const r = await apiClient.post(`/documents/chunks/${chunkId}/comments`, { comment });
  return r.data;
}

export async function deleteChunkComment(chunkId: string, commentId: string): Promise<void> {
  await apiClient.delete(`/documents/chunks/${chunkId}/comments/${commentId}`);
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
