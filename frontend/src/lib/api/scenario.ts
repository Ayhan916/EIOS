import apiClient from "./client";

export interface SupplierExposure {
  supplier_id: string;
  supplier_name: string;
  exposure_level: "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
  exposure_reason: string;
  recommended_action: string;
  urgency: "IMMEDIATE" | "SHORT_TERM" | "MONITOR";
}

export interface ScenarioAnalysis {
  event_summary: string;
  financial_assessment: string;
  sector_impact: string;
  suppliers: SupplierExposure[];
  overall_risk_level: "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
  data_sources: string[];
}

export interface ScenarioResult {
  company_name: string;
  sector: string;
  signal_text: string;
  suppliers_found: number;
  financial_data: Record<string, unknown>;
  news_headlines: string[];
  analysis: ScenarioAnalysis;
}

export interface SectorSupplier {
  id: string;
  name: string;
  industry: string;
  country: string;
}

export const SECTOR_OPTIONS = [
  { value: "automotive",    label: "Automobilindustrie" },
  { value: "technology",    label: "Technologie / IT" },
  { value: "energy",        label: "Energie" },
  { value: "finance",       label: "Finanzwesen" },
  { value: "chemical",      label: "Chemie / Pharma" },
  { value: "steel",         label: "Stahl / Metall" },
  { value: "logistics",     label: "Logistik / Transport" },
  { value: "retail",        label: "Handel / Retail" },
  { value: "construction",  label: "Bau / Immobilien" },
  { value: "textile",       label: "Textil / Mode" },
];

export async function analyzeScenario(payload: {
  signal_text: string;
  company_name: string;
  sector: string;
}): Promise<ScenarioResult> {
  const r = await apiClient.post("/scenario/analyze", payload, { timeout: 120_000 });
  return r.data;
}

export async function detectSector(text: string): Promise<{ sector: string | null; detected: boolean }> {
  const r = await apiClient.get("/scenario/detect-sector", { params: { text } });
  return r.data;
}

export async function getSectorSuppliers(sector: string): Promise<{ sector: string; count: number; suppliers: SectorSupplier[] }> {
  const r = await apiClient.get("/scenario/sector-suppliers", { params: { sector } });
  return r.data;
}
