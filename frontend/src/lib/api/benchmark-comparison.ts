import apiClient from "./client";

export interface BenchmarkTrendPoint {
  run_id: string;
  computed_at: string | null;
  pass_rate: number;
  passed: number;
  total: number;
}

export interface ModuleComparisonEntry {
  module: string;
  current_pass_rate: number;
  prev_pass_rate: number | null;
  delta: number | null;
  status: "green" | "yellow" | "red" | "unknown";
  baseline: number;
  total_cases: number;
  passed_cases: number;
  trend: BenchmarkTrendPoint[];
  failing_cases: string[];
}

export interface BenchmarkComparisonResponse {
  modules: ModuleComparisonEntry[];
  run_count: number;
  latest_run_id: string | null;
  latest_computed_at: string | null;
}

export const benchmarkApi = {
  getComparison: async (limitRuns = 5): Promise<BenchmarkComparisonResponse> => {
    const res = await apiClient.get("/evaluation/benchmarks/comparison", {
      params: { limit_runs: limitRuns },
    });
    return res.data;
  },
};
