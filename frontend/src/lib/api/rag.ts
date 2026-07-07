import apiClient from "./client";

export interface RagSource {
  rank: number;
  doc_type: string;
  content_preview: string;
  severity: string | null;
  source_name: string | null;
  published_at: string | null;
  similarity: number;
}

export interface RagAnalyzeResponse {
  answer: string;
  sources: RagSource[];
  chunks_found: number;
  model: string;
  query: string;
}

export interface RagIngestResponse {
  news_articles: number;
  intelligence_events: number;
  total_new: number;
  message: string;
}

export interface RagStatsResponse {
  total_documents: number;
  news_articles: number;
  intelligence_events: number;
  suppliers_covered: number;
}

export async function ragAnalyze(params: {
  query: string;
  supplier_id?: string;
  supplier_name?: string;
  top_k?: number;
}): Promise<RagAnalyzeResponse> {
  const r = await apiClient.post("/rag/analyze", params, { timeout: 30_000 });
  return r.data;
}

export interface AffectedRight {
  right_id: string;
  right_name: string;
  baseline: number;
  adjusted: number;
  delta: number;
}

export interface RagSimulateResponse {
  scenario_type: string;
  scenario_name: string;
  supplier_name: string;
  narrative: string;
  top_affected_rights: AffectedRight[];
  deterministic_ok: boolean;
  sources: RagSource[];
  chunks_found: number;
  model: string;
}

export async function ragSimulate(params: {
  scenario_type: string;
  supplier_id: string;
  supplier_name: string;
}): Promise<RagSimulateResponse> {
  const r = await apiClient.post("/rag/simulate", params, { timeout: 45_000 });
  return r.data;
}

export async function ragIngest(supplier_id?: string): Promise<RagIngestResponse> {
  const r = await apiClient.post("/rag/ingest", null, {
    params: supplier_id ? { supplier_id } : undefined,
    timeout: 120_000,
  });
  return r.data;
}

export async function ragStats(): Promise<RagStatsResponse> {
  const r = await apiClient.get("/rag/stats");
  return r.data;
}

export interface HistoricalEntry {
  id: string;
  supplier_id: string | null;
  event_description: string;
  event_type: string;
  event_severity: string | null;
  countermeasure_description: string;
  countermeasure_type: string;
  outcome_description: string;
  outcome_category: string;
  health_delta: number | null;
  csddd_right: string | null;
  twin_dimension: string | null;
  reference_date: string | null;
  similarity?: number;
}

export interface HistoricalResponse {
  entries: HistoricalEntry[];
  total: number;
}

export interface HistoricalIngestResponse {
  timeline_events_new: number;
  timeline_events_skipped: number;
  cap_findings_new: number;
  cap_findings_skipped: number;
  total_new: number;
  message: string;
}

export async function ragIngestHistory(): Promise<HistoricalIngestResponse> {
  const r = await apiClient.post("/rag/ingest-history", null, { timeout: 120_000 });
  return r.data;
}

export async function ragHistory(params: {
  supplier_id?: string;
  csddd_right?: string;
  query?: string;
  limit?: number;
}): Promise<HistoricalResponse> {
  const r = await apiClient.get("/rag/history", { params, timeout: 30_000 });
  return r.data;
}
