"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
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
  Target,
} from "lucide-react";
import {
  evaluationApi,
  EvaluationRun,
  BenchmarkResult,
  CalibrationPoint,
  RecordCalibrationRequest,
} from "@/lib/api/evaluation";
import { useLanguage } from "@/lib/i18n/context";
import { formatDate } from "@/lib/utils";

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
  const { t } = useLanguage();
  const color =
    score >= 80 ? "text-emerald-500" : score >= 60 ? "text-amber-500" : "text-red-500";
  const label = score >= 80 ? t("evaluation.healthy") : score >= 60 ? t("evaluation.fair") : t("evaluation.needsAttention");
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
  const { t } = useLanguage();
  if (results.length === 0) return null;
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase text-gray-500 dark:text-gray-400">
          <tr>
            <th className="px-4 py-3 text-left">{t("evaluation.bmTest")}</th>
            <th className="px-4 py-3 text-left">{t("evaluation.bmModule")}</th>
            <th className="px-4 py-3 text-center">{t("evaluation.bmResult")}</th>
            <th className="px-4 py-3 text-center">{t("evaluation.bmScore")}</th>
            <th className="px-4 py-3 text-center">{t("evaluation.bmMs")}</th>
            <th className="px-4 py-3 text-left">{t("evaluation.bmNote")}</th>
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

// ── Calibration curve chart ───────────────────────────────────────────────────

const CALIBRATION_COLORS: Record<string, string> = {
  high: "#22c55e",
  medium: "#f59e0b",
  low: "#ef4444",
};

function CalibrationCurveChart({ points }: { points: CalibrationPoint[] }) {
  const { t } = useLanguage();
  const data = points.map((p) => ({
    name: p.confidence_level.charAt(0).toUpperCase() + p.confidence_level.slice(1),
    accuracy: p.accuracy !== null ? Math.round(p.accuracy * 100) : null,
    total: p.total,
    confirmed: p.confirmed,
    refuted: p.refuted,
    unknown: p.unknown,
    fill: CALIBRATION_COLORS[p.confidence_level] ?? "#94a3b8",
  }));

  if (data.every((d) => d.total === 0)) {
    return (
      <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
        {t("evaluation.calibNoData")}
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
          tick={{ fontSize: 11 }}
          width={40}
        />
        <Tooltip
          formatter={(value: number, _name: string, props) => {
            const item = props.payload;
            if (value === null || value === undefined) return ["—", t("evaluation.calibTooltipAccuracy")];
            return [
              `${value}% (${item.confirmed} confirmed / ${item.refuted} refuted / ${item.unknown} unknown)`,
              t("evaluation.calibTooltipAccuracy"),
            ];
          }}
          labelFormatter={(l) => `${t("evaluation.calibTooltipConfidence")}: ${l}`}
        />
        <ReferenceLine y={100} stroke="#94a3b8" strokeDasharray="4 2" label={{ value: t("evaluation.calibPerfect"), fontSize: 10, fill: "#94a3b8" }} />
        <Bar dataKey="accuracy" name={t("evaluation.calibTooltipAccuracy")} radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function RecordCalibrationForm({ onSuccess }: { onSuccess: () => void }) {
  const { t } = useLanguage();
  const [form, setForm] = useState<RecordCalibrationRequest>({
    entity_type: "finding",
    entity_id: "",
    predicted_confidence: "high",
    actual_outcome: "confirmed",
  });

  const mutation = useMutation({
    mutationFn: () => evaluationApi.recordCalibrationEvent(form),
    onSuccess: () => {
      onSuccess();
      setForm({ entity_type: "finding", entity_id: "", predicted_confidence: "high", actual_outcome: "confirmed" });
    },
  });

  return (
    <div className="rounded-xl border border-border bg-slate-50/60 p-4 space-y-3">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
        {t("evaluation.recordOutcome")}
      </p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">{t("evaluation.entityType")}</label>
          <select
            className="h-8 w-full rounded-md border border-input bg-white px-2 text-xs"
            value={form.entity_type}
            onChange={(e) => setForm((f) => ({ ...f, entity_type: e.target.value as RecordCalibrationRequest["entity_type"] }))}
          >
            <option value="finding">Finding</option>
            <option value="risk">Risk</option>
            <option value="recommendation">Recommendation</option>
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">{t("evaluation.entityId")}</label>
          <input
            className="h-8 w-full rounded-md border border-input bg-white px-2 text-xs"
            placeholder="UUID"
            value={form.entity_id}
            onChange={(e) => setForm((f) => ({ ...f, entity_id: e.target.value }))}
          />
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">{t("evaluation.predictedConf")}</label>
          <select
            className="h-8 w-full rounded-md border border-input bg-white px-2 text-xs"
            value={form.predicted_confidence}
            onChange={(e) => setForm((f) => ({ ...f, predicted_confidence: e.target.value as RecordCalibrationRequest["predicted_confidence"] }))}
          >
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">{t("evaluation.actualOutcome")}</label>
          <select
            className="h-8 w-full rounded-md border border-input bg-white px-2 text-xs"
            value={form.actual_outcome}
            onChange={(e) => setForm((f) => ({ ...f, actual_outcome: e.target.value as RecordCalibrationRequest["actual_outcome"] }))}
          >
            <option value="confirmed">Confirmed</option>
            <option value="refuted">Refuted</option>
            <option value="unknown">Unknown</option>
          </select>
        </div>
      </div>
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending || !form.entity_id.trim()}
        className="flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
      >
        {mutation.isPending ? t("evaluation.saving") : t("evaluation.saveOutcome")}
      </button>
      {mutation.isError && (
        <p className="text-xs text-red-500">{t("evaluation.saveError")}</p>
      )}
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
            title={`${r.platform_health_score.toFixed(0)} — ${r.computed_at ? formatDate(r.computed_at) : ""}`}
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
  const { t } = useLanguage();
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

  const { data: calibrationData, refetch: refetchCalibration } = useQuery({
    queryKey: ["calibration-curve"],
    queryFn: () => evaluationApi.getCalibrationCurve(),
  });

  const run = latest;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-purple-100 dark:bg-purple-900/30 p-2">
            <Activity className="h-6 w-6 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              {t("evaluation.title")}
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {t("evaluation.subtitle")}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
            {t("evaluation.window")}:
            <select
              value={windowDays}
              onChange={(e) => setWindowDays(Number(e.target.value))}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm"
            >
              <option value={7}>{t("evaluation.windowDays").replace("{n}", "7")}</option>
              <option value={30}>{t("evaluation.windowDays").replace("{n}", "30")}</option>
              <option value={90}>{t("evaluation.windowDays").replace("{n}", "90")}</option>
            </select>
          </label>
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white hover:bg-purple-700 disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${runMutation.isPending ? "animate-spin" : ""}`} />
            {runMutation.isPending ? t("evaluation.running") : t("evaluation.runEval")}
          </button>
        </div>
      </div>

      {latestLoading ? (
        <div className="py-10 text-center text-sm text-gray-400">{t("evaluation.loading")}</div>
      ) : !run ? (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 py-16 text-center text-gray-400">
          {t("evaluation.noRun")}
        </div>
      ) : (
        <>
          {/* Health + benchmark status */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-1 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 flex flex-col items-center justify-center gap-2">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{t("evaluation.platformHealth")}</span>
              <HealthGauge score={run.platform_health_score} />
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-gray-400">{t("evaluation.benchmark")}:</span>
                <BmBadge status={run.benchmark_status} />
              </div>
              <p className="text-xs text-gray-400 text-center">
                {t("evaluation.testsPassed").replace("{passed}", String(run.benchmark_passed)).replace("{total}", String(run.benchmark_total))}
              </p>
            </div>

            <div className="md:col-span-2 grid grid-cols-2 gap-3">
              <MetricCard
                label={t("evaluation.accuracy")}
                value={`${(run.accuracy_score * 100).toFixed(1)}%`}
                sub={t("evaluation.accuracySub")}
                icon={BarChart3}
                color="blue"
              />
              <MetricCard
                label={t("evaluation.confidence")}
                value={`${(run.confidence_score * 100).toFixed(1)}%`}
                sub={t("evaluation.confidenceSub")}
                icon={TrendingUp}
                color="green"
              />
              <MetricCard
                label={t("evaluation.hallucinationRate")}
                value={`${(run.hallucination_rate * 100).toFixed(2)}%`}
                sub={t("evaluation.hallucinationSub")}
                icon={AlertTriangle}
                color={run.hallucination_rate > 0.05 ? "red" : "green"}
              />
              <MetricCard
                label={t("evaluation.errorRate")}
                value={`${(run.error_rate * 100).toFixed(2)}%`}
                sub={t("evaluation.errorRateSub").replace("{n}", String(run.agent_run_count)).replace("{d}", String(run.window_days))}
                icon={Cpu}
                color={run.error_rate > 0.1 ? "red" : "green"}
              />
            </div>
          </div>

          {/* Cost */}
          <div className="grid grid-cols-3 gap-4">
            <MetricCard
              label={t("evaluation.costTotal")}
              value={`$${run.cost_usd_total.toFixed(4)}`}
              sub={t("evaluation.dayWindow").replace("{n}", String(run.window_days))}
              icon={DollarSign}
              color="purple"
            />
            <MetricCard
              label={t("evaluation.cost7d")}
              value={`$${run.cost_usd_last_7d.toFixed(4)}`}
              icon={DollarSign}
              color="purple"
            />
            <MetricCard
              label={t("evaluation.cost30d")}
              value={`$${run.cost_usd_last_30d.toFixed(4)}`}
              icon={DollarSign}
              color="purple"
            />
          </div>

          {/* Trend */}
          {trends && trends.runs.length > 1 && (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                {t("evaluation.trendTitle").replace("{n}", String(trends.runs.length))}
              </p>
              <TrendBars runs={trends.runs} />
              <p className="text-xs text-gray-400">{t("evaluation.trendLegend")}</p>
            </div>
          )}

          {/* Confidence Calibration Curve — GAP-27 */}
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-4">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 p-1.5">
                <Target className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                  {t("evaluation.calibTitle")}
                </p>
                <p className="text-xs text-gray-400">
                  {t("evaluation.calibSubtitle")}
                </p>
              </div>
              {calibrationData && (
                <span className="ml-auto text-xs text-gray-400">
                  {t("evaluation.calibEvents").replace("{n}", String(calibrationData.total_events))}
                </span>
              )}
            </div>

            {calibrationData && (
              <CalibrationCurveChart points={calibrationData.points} />
            )}

            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              {calibrationData?.points.map((p) => (
                <div
                  key={p.confidence_level}
                  className="rounded-lg border border-border bg-slate-50/60 p-2 space-y-0.5"
                >
                  <p className="font-semibold capitalize text-gray-700 dark:text-gray-300">
                    {p.confidence_level}
                  </p>
                  <p className="text-muted-foreground">
                    {p.accuracy !== null ? t("evaluation.calibCorrect").replace("{n}", (p.accuracy * 100).toFixed(0)) : "—"}
                  </p>
                  <p className="text-[10px] text-muted-foreground">
                    {p.confirmed}✓ {p.refuted}✗ {p.unknown}?
                  </p>
                </div>
              ))}
            </div>

            <RecordCalibrationForm onSuccess={() => refetchCalibration()} />
          </div>

          {/* Benchmarks */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                {t("evaluation.benchmarkResults")}
              </p>
              <button
                onClick={() => setSelectedRunId(run.id)}
                className="text-xs text-blue-500 hover:underline"
              >
                {t("evaluation.loadForRun")}
              </button>
            </div>
            {benchmarks ? (
              <BenchmarkTable results={benchmarks} />
            ) : (
              <p className="text-xs text-gray-400">{t("evaluation.loadForRunHint")}</p>
            )}
          </div>

          {/* Last evaluated */}
          <p className="text-xs text-gray-400">
            {t("evaluation.lastEvaluated")}:{" "}
            {run.computed_at ? formatDate(run.computed_at) : "—"} ·{" "}
            {t("evaluation.runType")}: {run.run_type}
          </p>
        </>
      )}
    </div>
  );
}
