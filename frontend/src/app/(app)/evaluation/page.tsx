"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  CheckCircle2,
  XCircle,
  RefreshCw,
  TrendingUp,
  AlertTriangle,
  DollarSign,
  Cpu,
  BarChart3,
} from "lucide-react";
import { evaluationApi, EvaluationRun, BenchmarkResult } from "@/lib/api/evaluation";

// ── Metric card ───────────────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  sub,
  icon: Icon,
  color = "blue",
}: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ElementType;
  color?: "blue" | "green" | "amber" | "red" | "purple";
}) {
  const colors = {
    blue:   "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400",
    green:  "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400",
    amber:  "bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400",
    red:    "bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400",
    purple: "bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400",
  };
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-2">
      <div className="flex items-center gap-2">
        <div className={`rounded-lg p-1.5 ${colors[color]}`}>
          <Icon className="h-4 w-4" />
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </div>
  );
}

// ── Health gauge ──────────────────────────────────────────────────────────────

function HealthGauge({ score }: { score: number }) {
  const color =
    score >= 80 ? "text-emerald-500" : score >= 60 ? "text-amber-500" : "text-red-500";
  const label = score >= 80 ? "Healthy" : score >= 60 ? "Fair" : "Needs Attention";
  return (
    <div className="flex flex-col items-center gap-1">
      <span className={`text-5xl font-black ${color}`}>{score.toFixed(0)}</span>
      <span className="text-xs text-gray-400 font-medium">/ 100</span>
      <span className={`text-sm font-semibold ${color}`}>{label}</span>
    </div>
  );
}

// ── Benchmark status badge ────────────────────────────────────────────────────

const BM_BADGE: Record<string, string> = {
  green:   "bg-emerald-100 text-emerald-800 border-emerald-300",
  yellow:  "bg-amber-100 text-amber-800 border-amber-300",
  red:     "bg-red-100 text-red-800 border-red-300",
  unknown: "bg-gray-100 text-gray-600 border-gray-300",
};

function BmBadge({ status }: { status: string }) {
  return (
    <span className={`rounded-full border px-3 py-0.5 text-xs font-bold uppercase ${BM_BADGE[status] ?? BM_BADGE.unknown}`}>
      {status}
    </span>
  );
}

// ── Benchmark results table ───────────────────────────────────────────────────

function BenchmarkTable({ results }: { results: BenchmarkResult[] }) {
  if (results.length === 0) return null;
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase text-gray-500 dark:text-gray-400">
          <tr>
            <th className="px-4 py-3 text-left">Test</th>
            <th className="px-4 py-3 text-left">Module</th>
            <th className="px-4 py-3 text-center">Result</th>
            <th className="px-4 py-3 text-center">Score</th>
            <th className="px-4 py-3 text-center">ms</th>
            <th className="px-4 py-3 text-left">Note</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
          {results.map((b) => (
            <tr key={b.id} className="bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/50">
              <td className="px-4 py-2.5 font-mono text-xs text-gray-700 dark:text-gray-300">
                {b.benchmark_name}
              </td>
              <td className="px-4 py-2.5 text-xs text-gray-500">{b.module}</td>
              <td className="px-4 py-2.5 text-center">
                {b.passed
                  ? <CheckCircle2 className="h-4 w-4 text-emerald-500 mx-auto" />
                  : <XCircle className="h-4 w-4 text-red-500 mx-auto" />}
              </td>
              <td className="px-4 py-2.5 text-center text-xs font-mono">
                {b.score.toFixed(2)}
              </td>
              <td className="px-4 py-2.5 text-center text-xs text-gray-400">
                {b.duration_ms.toFixed(1)}
              </td>
              <td className="px-4 py-2.5 text-xs text-gray-500 max-w-xs truncate">
                {b.failure_reason || "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Trend sparkline (simple bar chart) ───────────────────────────────────────

function TrendBars({ runs }: { runs: EvaluationRun[] }) {
  if (runs.length === 0) return null;
  const max = Math.max(...runs.map((r) => r.platform_health_score), 1);
  return (
    <div className="flex items-end gap-1 h-16">
      {[...runs].reverse().map((r) => {
        const pct = (r.platform_health_score / max) * 100;
        const color =
          r.platform_health_score >= 80
            ? "bg-emerald-400"
            : r.platform_health_score >= 60
            ? "bg-amber-400"
            : "bg-red-400";
        return (
          <div
            key={r.id}
            title={`${r.platform_health_score.toFixed(0)} — ${r.computed_at ? new Date(r.computed_at).toLocaleDateString() : ""}`}
            className={`flex-1 rounded-t ${color} transition-all`}
            style={{ height: `${pct}%`, minHeight: "4px" }}
          />
        );
      })}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function EvaluationPage() {
  const qc = useQueryClient();
  const [windowDays, setWindowDays] = useState(30);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const { data: latest, isLoading: latestLoading } = useQuery({
    queryKey: ["evaluation-latest"],
    queryFn: () => evaluationApi.getLatest(),
  });

  const { data: trends } = useQuery({
    queryKey: ["evaluation-trends"],
    queryFn: () => evaluationApi.getTrends(12),
  });

  const { data: benchmarks } = useQuery({
    queryKey: ["evaluation-benchmarks", selectedRunId],
    queryFn: () => evaluationApi.getBenchmarks(selectedRunId!),
    enabled: !!selectedRunId,
  });

  const runMutation = useMutation({
    mutationFn: () => evaluationApi.triggerRun(windowDays),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["evaluation-latest"] });
      qc.invalidateQueries({ queryKey: ["evaluation-trends"] });
      setSelectedRunId(data.evaluation_run.id);
    },
  });

  const run = latest;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-purple-100 dark:bg-purple-900/30 p-2">
            <Activity className="h-6 w-6 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              Evaluation Engine
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              FR-014 — Platform AI quality metrics: accuracy, confidence, hallucination rate, cost
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
            Window:
            <select
              value={windowDays}
              onChange={(e) => setWindowDays(Number(e.target.value))}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
            >
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
            </select>
          </label>
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white hover:bg-purple-700 disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${runMutation.isPending ? "animate-spin" : ""}`} />
            {runMutation.isPending ? "Running…" : "Run Evaluation"}
          </button>
        </div>
      </div>

      {latestLoading ? (
        <div className="py-10 text-center text-sm text-gray-400">Loading…</div>
      ) : !run ? (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 py-16 text-center text-gray-400">
          No evaluation run yet. Click "Run Evaluation" to get started.
        </div>
      ) : (
        <>
          {/* Health + benchmark status */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-1 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 flex flex-col items-center justify-center gap-2">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Platform Health</span>
              <HealthGauge score={run.platform_health_score} />
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-gray-400">Benchmark:</span>
                <BmBadge status={run.benchmark_status} />
              </div>
              <p className="text-xs text-gray-400 text-center">
                {run.benchmark_passed}/{run.benchmark_total} tests passed
              </p>
            </div>

            <div className="md:col-span-2 grid grid-cols-2 gap-3">
              <MetricCard
                label="Accuracy"
                value={`${(run.accuracy_score * 100).toFixed(1)}%`}
                sub="Benchmark pass rate"
                icon={BarChart3}
                color="blue"
              />
              <MetricCard
                label="Confidence"
                value={`${(run.confidence_score * 100).toFixed(1)}%`}
                sub="Mean agent confidence"
                icon={TrendingUp}
                color="green"
              />
              <MetricCard
                label="Hallucination Rate"
                value={`${(run.hallucination_rate * 100).toFixed(2)}%`}
                sub="High-conf errors / total"
                icon={AlertTriangle}
                color={run.hallucination_rate > 0.05 ? "red" : "green"}
              />
              <MetricCard
                label="Error Rate"
                value={`${(run.error_rate * 100).toFixed(2)}%`}
                sub={`${run.agent_run_count} runs in ${run.window_days}d window`}
                icon={Cpu}
                color={run.error_rate > 0.1 ? "red" : "green"}
              />
            </div>
          </div>

          {/* Cost */}
          <div className="grid grid-cols-3 gap-4">
            <MetricCard
              label="Cost (total)"
              value={`$${run.cost_usd_total.toFixed(4)}`}
              sub={`${run.window_days}-day window`}
              icon={DollarSign}
              color="purple"
            />
            <MetricCard
              label="Cost (last 7d)"
              value={`$${run.cost_usd_last_7d.toFixed(4)}`}
              icon={DollarSign}
              color="purple"
            />
            <MetricCard
              label="Cost (last 30d)"
              value={`$${run.cost_usd_last_30d.toFixed(4)}`}
              icon={DollarSign}
              color="purple"
            />
          </div>

          {/* Trend */}
          {trends && trends.runs.length > 1 && (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Health Score Trend (last {trends.runs.length} runs)
              </p>
              <TrendBars runs={trends.runs} />
              <p className="text-xs text-gray-400">Each bar = one evaluation run. Green ≥80, Amber ≥60, Red &lt;60.</p>
            </div>
          )}

          {/* Benchmarks */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                Benchmark Results
              </p>
              <button
                onClick={() => setSelectedRunId(run.id)}
                className="text-xs text-blue-500 hover:underline"
              >
                Load for this run
              </button>
            </div>
            {benchmarks ? (
              <BenchmarkTable results={benchmarks} />
            ) : (
              <p className="text-xs text-gray-400">Click "Load for this run" to show benchmark details.</p>
            )}
          </div>

          {/* Last evaluated */}
          <p className="text-xs text-gray-400">
            Last evaluated:{" "}
            {run.computed_at ? new Date(run.computed_at).toLocaleString() : "—"} ·{" "}
            Run type: {run.run_type}
          </p>
        </>
      )}
    </div>
  );
}
