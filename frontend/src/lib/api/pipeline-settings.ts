import apiClient from "./client";

export interface PipelineSettings {
  parse_engine:         "docling" | "pymupdf" | "pdfplumber";
  ocr_enabled:          boolean;
  extract_tables:       "markdown" | "plain";
  chunk_size:           number;
  chunk_overlap:        number;
  chunk_strategy:       "sliding_window" | "semantic" | "by_section";
  retrieval_mode:       "dense" | "hybrid";
  similarity_threshold: number;
  top_k:                number;
}

export const PIPELINE_DEFAULTS: PipelineSettings = {
  parse_engine:         "docling",
  ocr_enabled:          false,
  extract_tables:       "markdown",
  chunk_size:           800,
  chunk_overlap:        80,
  chunk_strategy:       "sliding_window",
  retrieval_mode:       "dense",
  similarity_threshold: 0.25,
  top_k:                8,
};

export const PARSE_ENGINE_OPTIONS = [
  { value: "docling",    label: "Docling",    note: "Höchste Qualität, Standard" },
  { value: "pymupdf",    label: "PyMuPDF",    note: "Schneller, weniger präzise" },
  { value: "pdfplumber", label: "pdfplumber", note: "Optimal für Tabellen" },
] as const;

export const CHUNK_STRATEGY_OPTIONS = [
  { value: "sliding_window", label: "Sliding Window", note: "Standard, gleichmäßige Chunks" },
  { value: "semantic",       label: "Semantisch",     note: "Nach Sinnabschnitten" },
  { value: "by_section",     label: "Nach Kapitel",   note: "Folgt Dokumentstruktur" },
] as const;

export const CHUNK_SIZE_OPTIONS = [400, 600, 800, 1000, 1200, 1600];
export const CHUNK_OVERLAP_OPTIONS = [40, 60, 80, 100, 120, 160];
export const SIMILARITY_OPTIONS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40];
export const TOP_K_OPTIONS = [3, 5, 8, 10, 12, 15, 20];

export async function getPipelineSettings(): Promise<PipelineSettings> {
  const r = await apiClient.get("/organizations/me/pipeline-settings");
  return r.data;
}

export async function updatePipelineSettings(s: Partial<PipelineSettings>): Promise<{ updated: boolean }> {
  const r = await apiClient.put("/organizations/me/pipeline-settings", s);
  return r.data;
}
