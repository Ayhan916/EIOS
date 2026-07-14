import apiClient from "./client";

export interface CompanyMetric {
  id: string;
  company_name: string;
  supplier_id: string | null;
  metric_type: string;
  value: number;
  unit: string;
  year: number;
  period: string;
  source_doc_id: string | null;
  confidence: string;
  created_at: string;
}

export interface CompanySignal {
  id: string;
  company_name: string;
  supplier_id: string | null;
  signal_type: string;
  dimension: string;
  direction: string;
  severity: string;
  description: string;
  year: number | null;
  event_date: string | null;
  source_doc_id: string | null;
  created_at: string;
}

export interface ExtractAllResult {
  processed: number;
  total_metrics: number;
  total_signals: number;
  details: unknown[];
}

export async function listMetrics(params?: {
  company_name?: string;
  metric_type?: string;
  year_from?: number;
  year_to?: number;
  supplier_id?: string;
}): Promise<CompanyMetric[]> {
  const r = await apiClient.get("/intelligence/metrics", { params });
  return r.data;
}

export async function listSignals(params?: {
  company_name?: string;
  dimension?: string;
  direction?: string;
  year_from?: number;
  year_to?: number;
  supplier_id?: string;
}): Promise<CompanySignal[]> {
  const r = await apiClient.get("/intelligence/signals", { params });
  return r.data;
}

export async function extractAllIntelligence(): Promise<ExtractAllResult> {
  const r = await apiClient.post("/intelligence/extract-all", null, { timeout: 600_000 });
  return r.data;
}

export interface RagFilterOptions {
  companies: string[];
  doc_classes: string[];
  years: number[];
}

export async function getRagFilterOptions(): Promise<RagFilterOptions> {
  const r = await apiClient.get("/copilot/rag-filter-options");
  return r.data;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

export const METRIC_LABELS: Record<string, string> = {
  revenue:              "Umsatz",
  ebitda:               "EBITDA",
  ebitda_margin:        "EBITDA-Marge",
  net_income:           "Jahresüberschuss",
  employees:            "Mitarbeiter",
  capex:                "CapEx",
  free_cashflow:        "Free Cashflow",
  debt_ratio:           "Verschuldungsgrad",
  roce:                 "ROCE",
  eps:                  "EPS",
  co2_scope1:           "CO₂ Scope 1",
  co2_scope2:           "CO₂ Scope 2",
  co2_scope3:           "CO₂ Scope 3",
  water_m3:             "Wasserverbrauch",
  energy_gwh:           "Energieverbrauch",
  renewable_energy_pct: "Erneuerbare Energie",
  women_leadership_pct: "Frauen in Führung",
  supplier_audited_pct: "Lieferanten auditiert",
  employees_total:      "Mitarbeiter gesamt",
  esg_score:            "ESG-Score",
  lost_time_injury_rate:"Unfallrate",
  supplier_count:       "Lieferantenanzahl",
};

export const UNIT_LABELS: Record<string, string> = {
  EUR_M:  "Mio. €",
  EUR_B:  "Mrd. €",
  EUR:    "€",
  PCT:    "%",
  COUNT:  "",
  tCO2:   "tCO₂",
  tCO2_M: "Mio. tCO₂",
  GWh:    "GWh",
  MWh:    "MWh",
  m3:     "m³",
};

export function formatValue(value: number, unit: string): string {
  const label = UNIT_LABELS[unit] ?? unit;
  const formatted = value >= 1_000_000
    ? (value / 1_000_000).toFixed(1) + "M"
    : value >= 1_000
    ? (value / 1_000).toFixed(1) + "K"
    : value % 1 === 0
    ? value.toLocaleString("de-DE")
    : value.toFixed(2);
  return label ? `${formatted} ${label}` : formatted;
}

export const FINANCIAL_METRICS = ["revenue", "ebitda", "ebitda_margin", "net_income", "employees", "capex", "free_cashflow", "debt_ratio", "roce", "eps"];
export const ESG_METRICS = ["co2_scope1", "co2_scope2", "co2_scope3", "water_m3", "energy_gwh", "renewable_energy_pct", "women_leadership_pct", "supplier_audited_pct", "employees_total", "esg_score"];

export const DIMENSION_LABELS: Record<string, string> = {
  financial:    "Finanzen",
  esg:          "ESG",
  governance:   "Governance",
  supply_chain: "Lieferkette",
  regulatory:   "Regulatorisch",
  reputation:   "Reputation",
};

export const SEVERITY_ORDER: Record<string, number> = {
  critical: 0, high: 1, medium: 2, low: 3,
};
