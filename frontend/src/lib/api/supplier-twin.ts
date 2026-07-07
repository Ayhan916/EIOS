import apiClient from "./client";

export interface HealthDimension {
  name: string;
  label: string;
  score: number;
  status: "CRITICAL" | "AT_RISK" | "MODERATE" | "HEALTHY";
}

export interface SupplierDigitalTwin {
  id: string;
  supplier_id: string;
  organization_id: string;
  esg_health: number;
  compliance_health: number;
  financial_health: number;
  geopolitical_health: number;
  cyber_health: number;
  human_rights_health: number;
  environmental_health: number;
  operational_health: number;
  overall_health: number;
  health_trend: "IMPROVING" | "STABLE" | "DETERIORATING";
  ai_confidence: number;
  open_recommendations: number;
  open_actions: number;
  event_count: number;
  critical_event_count: number;
  last_event_at: string | null;
  last_updated_at: string;
  twin_version: number;
  dimensions: HealthDimension[];
}

export interface IntelligenceTimelineEvent {
  id: string;
  supplier_id: string;
  organization_id: string;
  event_type: string;
  event_category: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
  title: string;
  summary: string;
  why_important: string;
  regulatory_impact: string;
  recommended_action: string;
  source_type: string;
  source_name: string;
  source_url: string;
  evidence_ids: string;
  regulation_ids: string;
  risk_ids: string;
  signal_id: string;
  twin_dimension_affected: string;
  health_delta: number;
  confidence: number;
  credibility_level: "High" | "Medium" | "Low";
  credibility_reason: string;
  occurred_at: string;
  processed_at: string;
  is_active: boolean;
}

export interface TimelineListResponse {
  events: IntelligenceTimelineEvent[];
  total: number;
  supplier_id: string;
}

export interface ProcessSignalsResponse {
  supplier_id: string;
  events_created: number;
  twin_updated: boolean;
  message: string;
}

export async function getSupplierTwin(supplierId: string): Promise<SupplierDigitalTwin> {
  const r = await apiClient.get(`/suppliers/${supplierId}/twin`);
  return r.data;
}

export async function getSupplierTwinTimeline(
  supplierId: string,
  opts: { limit?: number; offset?: number; severity?: string; category?: string } = {}
): Promise<TimelineListResponse> {
  const params = new URLSearchParams();
  if (opts.limit) params.set("limit", String(opts.limit));
  if (opts.offset) params.set("offset", String(opts.offset));
  if (opts.severity) params.set("severity", opts.severity);
  if (opts.category) params.set("category", opts.category);
  const r = await apiClient.get(
    `/suppliers/${supplierId}/twin/timeline?${params.toString()}`
  );
  return r.data;
}

export async function processSupplierSignals(supplierId: string): Promise<ProcessSignalsResponse> {
  const r = await apiClient.post(`/suppliers/${supplierId}/twin/process`);
  return r.data;
}

export interface CollectIntelligenceResponse {
  sources_attempted: number;
  sources_ok: number;
  entities_checked: number;
  suppliers_matched: number;
  signals_created: number;
  twins_updated: number;
  events_created: number;
  duration_seconds: number;
  errors: string[];
  message: string;
}

export async function collectIntelligence(): Promise<CollectIntelligenceResponse> {
  // Multi-source collection can take 40-90 s — override the default 30 s client timeout
  const r = await apiClient.post("/intelligence/collect", undefined, { timeout: 120_000 });
  return r.data;
}

export async function collectIntelligenceForSupplier(supplierId: string): Promise<CollectIntelligenceResponse> {
  const r = await apiClient.post(`/suppliers/${supplierId}/intelligence/collect`, undefined, { timeout: 120_000 });
  return r.data;
}

export async function collectIntelligenceBatch(supplierIds: string[]): Promise<CollectIntelligenceResponse> {
  const r = await apiClient.post("/intelligence/collect/batch", supplierIds, { timeout: 120_000 });
  return r.data;
}
