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
};
