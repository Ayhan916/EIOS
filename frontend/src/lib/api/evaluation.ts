import apiClient from "./client";

export interface EvaluationRun {
  id: string;
  run_type: string;
  window_days: number;
  agent_run_count: number;
  accuracy_score: number;
  precision_score: number;
  recall_score: number;
  confidence_score: number;
  hallucination_rate: number;
  error_rate: number;
  cost_usd_total: number;
  cost_usd_last_7d: number;
  cost_usd_last_30d: number;
  benchmark_status: "green" | "yellow" | "red" | "unknown";
  benchmark_passed: number;
  benchmark_total: number;
  platform_health_score: number;
  raw_metrics: Record<string, unknown>;
  computed_at: string | null;
  created_at: string;
}

export interface BenchmarkResult {
  id: string;
  evaluation_run_id: string;
  benchmark_name: string;
  module: string;
  dimension: string;
  passed: boolean;
  score: number;
  expected_output: string;
  actual_output: string;
  failure_reason: string;
  duration_ms: number;
  created_at: string;
}

export interface TriggerResponse {
  evaluation_run: EvaluationRun;
  benchmark_results: BenchmarkResult[];
}

export interface AgentStatusSummary {
  active: number;
  idle: number;
  error: number;
  disabled: number;
  total: number;
}

export interface SystemStatus {
  platform_health_score: number;
  benchmark_status: "green" | "yellow" | "red" | "unknown";
  benchmark_passed: number;
  benchmark_total: number;
  accuracy_score: number;
  confidence_score: number;
  hallucination_rate: number;
  error_rate: number;
  cost_usd_last_7d: number;
  cost_usd_last_30d: number;
  agent_run_count: number;
  latest_run_id: string | null;
  computed_at: string | null;
  agents: AgentStatusSummary;
}

export interface CalibrationPoint {
  confidence_level: "high" | "medium" | "low";
  total: number;
  confirmed: number;
  refuted: number;
  unknown: number;
  accuracy: number | null;
}

export interface CalibrationCurveResponse {
  points: CalibrationPoint[];
  total_events: number;
}

export interface RecordCalibrationRequest {
  entity_type: "finding" | "risk" | "recommendation";
  entity_id: string;
  predicted_confidence: "high" | "medium" | "low";
  actual_outcome: "confirmed" | "refuted" | "unknown";
}

export interface CalibrationEventResponse {
  id: string;
  entity_type: string;
  entity_id: string;
  predicted_confidence: string;
  actual_outcome: string;
  recorded_by: string | null;
  recorded_at: string | null;
  created_at: string;
}

export const evaluationApi = {
  triggerRun: async (windowDays = 30): Promise<TriggerResponse> => {
    const res = await apiClient.post(`/evaluation/run?window_days=${windowDays}`);
    return res.data;
  },

  getLatest: async (): Promise<EvaluationRun | null> => {
    const res = await apiClient.get("/evaluation/latest");
    return res.data;
  },

  getTrends: async (limit = 12): Promise<{ runs: EvaluationRun[] }> => {
    const res = await apiClient.get(`/evaluation/trends?limit=${limit}`);
    return res.data;
  },

  getBenchmarks: async (runId: string): Promise<BenchmarkResult[]> => {
    const res = await apiClient.get(`/evaluation/benchmarks/${runId}`);
    return res.data;
  },

  getSystemStatus: async (): Promise<SystemStatus> => {
    const res = await apiClient.get("/evaluation/system-status");
    return res.data;
  },

  getCalibrationCurve: async (): Promise<CalibrationCurveResponse> => {
    const res = await apiClient.get("/evaluation/calibration/curve");
    return res.data;
  },

  recordCalibrationEvent: async (
    body: RecordCalibrationRequest
  ): Promise<CalibrationEventResponse> => {
    const res = await apiClient.post("/evaluation/calibration/events", body);
    return res.data;
  },
};
