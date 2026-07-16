import apiClient from "./client";

export interface LlmModelSettings {
  classification: string;
  analysis: string;
  extraction: string;
}

export const MODEL_OPTIONS = [
  { value: "anthropic:claude-sonnet-4-6",        label: "Claude Sonnet 4.6",  note: "Höchste Qualität",    free: false },
  { value: "anthropic:claude-haiku-4-5-20251001", label: "Claude Haiku 4.5",  note: "Gute Qualität, günstig", free: false },
  { value: "groq:llama-3.3-70b-versatile",        label: "Llama 3.3 70B",     note: "Solide, kostenlos",   free: true },
  { value: "groq:llama-3.1-8b-instant",           label: "Llama 3.1 8B",      note: "Schnell, kostenlos",  free: true },
] as const;

export const PIPELINE_JOB_LABELS: Record<string, { label: string; desc: string; section?: string }> = {
  classification: {
    label:   "Klassifizierung",
    desc:    "Erkennt doc_type, Unternehmen und Berichtsjahr",
    section: "Pipeline",
  },
  analysis: {
    label:   "Analyse",
    desc:    "Extrahiert KPIs, Risiken, Ziele und Summary",
    section: "Pipeline",
  },
  extraction: {
    label:   "Metriken-Extraktion",
    desc:    "Liest ESG- und Finanzkennzahlen aus dem Text",
    section: "Pipeline",
  },
  copilot: {
    label:   "Copilot-Test",
    desc:    "Beantwortet Testfragen direkt aus diesem Dokument",
    section: "Copilot",
  },
};

export async function getLlmModelSettings(): Promise<LlmModelSettings> {
  const r = await apiClient.get("/organizations/me/llm-models");
  return r.data;
}

export async function updateLlmModelSettings(settings: Partial<LlmModelSettings>): Promise<{ updated: boolean }> {
  const r = await apiClient.put("/organizations/me/llm-models", settings);
  return r.data;
}
