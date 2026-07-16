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

export interface YearChange {
  year_from: number;
  year_to: number;
  value_from: number;
  value_to: number;
  pct_change: number;
  unit: string;
}

export interface TrendAlert {
  company_name: string;
  metric_type: string;
  unit: string;
  alert_type: "consecutive" | "spike";
  direction: "up" | "down";
  sentiment: "positive" | "negative" | "neutral";
  severity: "critical" | "high" | "medium" | "low";
  year_start: number;
  year_end: number;
  avg_pct_change: number;
  description: string;
  changes: YearChange[];
  reference_source: string | null;
  reference_url: string | null;
  verification_note: string | null;
}

export interface VerifyResult {
  verified: number;
  discrepant: number;
  not_found: number;
  total: number;
}

export async function detectContradictions(params?: {
  company_name?: string;
}): Promise<{ contradictions?: number; total_contradictions?: number; companies_checked?: number }> {
  const r = await apiClient.post("/intelligence/detect-contradictions", null, { params, timeout: 300_000 });
  return r.data;
}

export async function verifyMetrics(params?: {
  company_name?: string;
  metric_types?: string;
}): Promise<VerifyResult> {
  const r = await apiClient.post("/intelligence/verify-metrics", null, { params, timeout: 300_000 });
  return r.data;
}

export async function listTrends(params?: {
  company_name?: string;
  supplier_id?: string;
  min_consecutive?: number;
  spike_threshold?: number;
}): Promise<TrendAlert[]> {
  const r = await apiClient.get("/intelligence/trends", { params });
  return r.data;
}

export async function getDocQuality(): Promise<DocQuality[]> {
  const r = await apiClient.get("/intelligence/doc-quality");
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

// ── Cross-Source Intelligence ─────────────────────────────────────────────────

export interface CrossAffectedSupplier {
  id: string;
  name: string;
  nace_code: string;
  country: string | null;
  supplier_tier: number | null;
  relation: "sector_stress" | "upstream_pressure" | "downstream_risk" | "indirect";
}

export interface CrossAlert {
  id: string;
  trigger_company: string;
  trigger_nace: string | null;
  trigger_signal_type: string;
  trigger_description: string;
  impact_type: string;
  severity: "critical" | "high" | "medium" | "low";
  affected_nace_codes: Record<string, string>;
  affected_suppliers: CrossAffectedSupplier[];
  reasoning: string;
  recommended_actions: string[];
  status: "open" | "acknowledged" | "resolved";
  created_at: string;
}

export interface CrossAnalyzeRequest {
  trigger_company: string;
  trigger_signal_type: string;
  trigger_description: string;
  trigger_nace?: string;
  trigger_signal_id?: string;
}

export async function crossAnalyze(req: CrossAnalyzeRequest): Promise<CrossAlert & { alert_id: string }> {
  const r = await apiClient.post("/intelligence/cross-analyze", req);
  return r.data;
}

export async function listCrossAlerts(params?: {
  status?: string;
  severity?: string;
  supplier_id?: string;
  limit?: number;
}): Promise<{ alerts: CrossAlert[]; total: number }> {
  const r = await apiClient.get("/intelligence/cross-alerts", { params });
  return r.data;
}

export interface DocQuality {
  doc_file_id: string;
  doc_id: string;
  doc_type: string;
  title: string | null;
  company_name: string | null;
  supplier_id: string | null;
  report_year: number | null;
  metric_count: number;
  metrics_count: number;
  metric_types: string[];
  years: number[];
  confidence_dist: Record<string, number>;
  quality_score: number;
  missing_core: string[];
  found_core: number;
  total_core: number;
}

export async function listDocQuality(params?: { supplier_id?: string }): Promise<DocQuality[]> {
  const r = await apiClient.get("/intelligence/doc-quality", { params });
  return r.data;
}

export async function listExternalSignalsForSupplier(supplierId: string): Promise<{ signals: any[]; total: number }> {
  const r = await apiClient.get(`/external-intelligence/signals/supplier/${supplierId}?active_only=false`);
  return r.data;
}

export async function updateCrossAlertStatus(alertId: string, status: "open" | "acknowledged" | "resolved"): Promise<void> {
  await apiClient.patch(`/intelligence/cross-alerts/${alertId}/status`, { status });
}

export const NACE_LABELS: Record<string, string> = {
  C29: "Automobil", C27: "Elektrische Ausrüstung", C26: "Elektronik/Halbleiter",
  C24: "Stahl/Metall", C25: "Metallteile", C28: "Maschinenbau",
  C20: "Chemie", C22: "Gummi/Kunststoff", B07: "Metallerzbergbau",
  B05: "Kohlenbergbau", D35: "Energie", H49: "Landtransport",
  C17: "Papier/Verpackung", C19: "Mineralölverarbeitung", C30: "Sonstiger Fahrzeugbau",
};

export const RELATION_LABELS: Record<string, string> = {
  sector_stress: "Gleicher Sektor",
  upstream_pressure: "Upstream-Lieferant",
  downstream_risk: "Downstream-Abnehmer",
  indirect: "Indirekt",
};

export const IMPACT_TYPE_LABELS: Record<string, string> = {
  supply_disruption: "Lieferunterbrechung",
  supply_loss: "Lieferantenausfall",
  capacity_reduction: "Kapazitätsabbau",
  delivery_risk: "Lieferrisiko",
  financial_contagion: "Finanzielle Ansteckung",
  reputational_spillover: "Reputationsübertragung",
  regulatory_spillover: "Regulatorische Übertragung",
  commitment_risk: "Commitment-Risiko",
  trend_risk: "Trendrisiko",
  sector_risk: "Sektorrisiko",
};
