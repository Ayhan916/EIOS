"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bot,
  CheckCircle2,
  DollarSign,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  XCircle,
  Zap,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { evaluationApi, BenchmarkResult, EvaluationRun } from "@/lib/api/evaluation";
import apiClient from "@/lib/api/client";
import { FounderChat } from "@/components/founder-chat";
import { useLanguage } from "@/lib/i18n/context";
import { formatDate } from "@/lib/utils";

// ── Agent monitoring types ────────────────────────────────────────────────────

interface MonitoringAgent {
  id: string;
  agent_type: string;
  name: string;
  status: string;
  enabled: boolean;
  run_count: number;
  success_count: number;
  failure_count: number;
  last_run_at: string | null;
}

async function fetchAgents(): Promise<MonitoringAgent[]> {
  const res = await apiClient.get("/agent-monitoring/");
  return res.data;
}

// ── Color helpers ─────────────────────────────────────────────────────────────

const HEALTH_COLOR = (s: number) =>
  s >= 80 ? "text-emerald-500" : s >= 60 ? "text-amber-500" : "text-red-500";

const BM_BADGE: Record<string, string> = {
  green:   "bg-emerald-100 text-emerald-800 border border-emerald-300",
  yellow:  "bg-amber-100 text-amber-800 border border-amber-300",
  red:     "bg-red-100 text-red-800 border border-red-300",
  unknown: "bg-gray-100 text-gray-600 border border-gray-200",
};

const AGENT_DOT: Record<string, string> = {
  ACTIVE:   "bg-emerald-400",
  IDLE:     "bg-gray-400",
  ERROR:    "bg-red-500",
  DISABLED: "bg-gray-300",
};

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({
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
  color?: "blue" | "green" | "amber" | "red" | "purple" | "slate";
}) {
  const bg: Record<string, string> = {
    blue:   "bg-blue-50 dark:bg-blue-900/20 text-blue-600",
    green:  "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600",
    amber:  "bg-amber-50 dark:bg-amber-900/20 text-amber-600",
    red:    "bg-red-50 dark:bg-red-900/20 text-red-600",
    purple: "bg-purple-50 dark:bg-purple-900/20 text-purple-600",
    slate:  "bg-slate-50 dark:bg-slate-900/20 text-slate-500",
  };
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-2">
      <div className="flex items-center gap-2">
        <div className={`rounded-lg p-1.5 ${bg[color]}`}>
          <Icon className="h-3.5 w-3.5" />
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900 dark:text-white leading-none">{value}</p>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </div>
  );
}

// ── Health gauge (large) ──────────────────────────────────────────────────────

function HealthGauge({ score }: { score: number }) {
  const { t } = useLanguage();
  const c = HEALTH_COLOR(score);
  const label = score >= 80 ? t("missionControl.healthy") : score >= 60 ? t("missionControl.fair") : t("missionControl.needsAttention");
  return (
    <div className="flex flex-col items-center justify-center gap-1 py-4">
      <span className={`text-6xl font-black tabular-nums ${c}`}>{score.toFixed(0)}</span>
      <span className="text-xs text-gray-400 font-mono">/100</span>
      <span className={`text-xs font-bold tracking-widest ${c}`}>{label}</span>
    </div>
  );
}

// ── Trend chart (multi-line) ──────────────────────────────────────────────────

function TrendChart({ runs, metrics }: {
  runs: EvaluationRun[];
  metrics: { key: keyof EvaluationRun; label: string; color: string; format?: (v: number) => string }[];
}) {
  const data = [...runs]
    .reverse()
    .map((r, i) => ({
      name: r.computed_at ? formatDate(r.computed_at) : `Run ${i + 1}`,
      ...Object.fromEntries(metrics.map((m) => [m.key, Number(r[m.key] ?? 0)])),
    }));

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.15} />
        <XAxis dataKey="name" tick={{ fontSize: 10 }} />
        <YAxis tick={{ fontSize: 10 }} domain={[0, "auto"]} />
        <Tooltip
          formatter={(v: number, name: string) => {
            const m = metrics.find((x) => x.key === name);
            return m?.format ? m.format(v) : v.toFixed(3);
          }}
          contentStyle={{ fontSize: 11 }}
        />
        <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
        {metrics.map((m) => (
          <Line
            key={String(m.key)}
            type="monotone"
            dataKey={String(m.key)}
            name={m.label}
            stroke={m.color}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

// ── Benchmark module summary ──────────────────────────────────────────────────

function BenchmarkModuleSummary({ results }: { results: BenchmarkResult[] }) {
  const byModule: Record<string, { passed: number; total: number }> = {};
  for (const r of results) {
    if (!byModule[r.module]) byModule[r.module] = { passed: 0, total: 0 };
    byModule[r.module].total++;
    if (r.passed) byModule[r.module].passed++;
  }
  return (
    <div className="space-y-2">
      {Object.entries(byModule).map(([mod, { passed, total }]) => (
        <div key={mod} className="flex items-center gap-3">
          {passed === total
            ? <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
            : <XCircle className="h-4 w-4 text-red-500 shrink-0" />}
          <span className="font-mono text-xs text-gray-600 dark:text-gray-300 flex-1">{mod}</span>
          <span className="text-xs text-gray-400 tabular-nums">{passed}/{total}</span>
        </div>
      ))}
    </div>
  );
}

// ── Agent status grid ─────────────────────────────────────────────────────────

function AgentStatusGrid({ agents }: { agents: MonitoringAgent[] }) {
  const { t } = useLanguage();
  if (agents.length === 0) return (
    <p className="text-xs text-gray-400 text-center py-4">{t("missionControl.noAgents")}</p>
  );
  return (
    <div className="grid grid-cols-1 gap-2">
      {agents.map((a) => (
        <div key={a.id} className="flex items-center gap-3 rounded-lg border border-gray-100 dark:border-gray-800 px-3 py-2">
          <div className={`h-2 w-2 rounded-full shrink-0 ${AGENT_DOT[a.status] ?? "bg-gray-400"}`} />
          <span className="flex-1 text-xs font-medium text-gray-700 dark:text-gray-300 truncate">{a.name || a.agent_type}</span>
          <span className="text-xs text-gray-400 tabular-nums">{t("missionControl.agentRuns").replace("{n}", String(a.run_count))}</span>
          {a.failure_count > 0 && (
            <span className="rounded-full bg-red-100 text-red-700 text-xs px-1.5 py-0.5">{t("missionControl.agentErrors").replace("{n}", String(a.failure_count))}</span>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function MissionControlPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [windowDays, setWindowDays] = useState(30);
  const [activeChart, setActiveChart] = useState<"quality" | "cost">("quality");

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ["eval-system-status"],
    queryFn: () => evaluationApi.getSystemStatus(),
    refetchInterval: 60_000,
  });

  const { data: trends } = useQuery({
    queryKey: ["evaluation-trends", 12],
    queryFn: () => evaluationApi.getTrends(12),
  });

  const { data: benchmarks } = useQuery({
    queryKey: ["evaluation-benchmarks", status?.latest_run_id],
    queryFn: () => evaluationApi.getBenchmarks(status!.latest_run_id!),
    enabled: !!status?.latest_run_id,
  });

  const { data: agents = [] } = useQuery({
    queryKey: ["agent-monitoring-list"],
    queryFn: () => fetchAgents(),
  });

  const runMutation = useMutation({
    mutationFn: () => evaluationApi.triggerRun(windowDays),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["eval-system-status"] });
      qc.invalidateQueries({ queryKey: ["evaluation-trends"] });
    },
  });

  const trendRuns = trends?.runs ?? [];

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-indigo-100 dark:bg-indigo-900/30 p-2">
            <Zap className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">{t("missionControl.title")}</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {t("missionControl.subtitle")}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={windowDays}
            onChange={(e) => setWindowDays(Number(e.target.value))}
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm"
          >
            <option value={7}>{t("evaluation.windowDays").replace("{n}", "7")}</option>
            <option value={30}>{t("evaluation.windowDays").replace("{n}", "30")}</option>
            <option value={90}>{t("evaluation.windowDays").replace("{n}", "90")}</option>
          </select>
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${runMutation.isPending ? "animate-spin" : ""}`} />
            {runMutation.isPending ? t("missionControl.running") : t("missionControl.runEval")}
          </button>
        </div>
      </div>

      {statusLoading ? (
        <div className="py-10 text-center text-sm text-gray-400">{t("missionControl.loading")}</div>
      ) : !status || status.platform_health_score === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 py-16 text-center text-gray-400">
          {t("missionControl.noData")}
        </div>
      ) : (
        <>
          {/* Hero row: health + benchmark + agent summary */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Health gauge */}
            <div className="md:col-span-1 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 flex flex-col items-center">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">{t("missionControl.platformHealth")}</p>
              <HealthGauge score={status.platform_health_score} />
              <div className="flex items-center gap-2 mt-2">
                <span className={`rounded-full border px-3 py-0.5 text-xs font-bold uppercase ${BM_BADGE[status.benchmark_status]}`}>
                  {status.benchmark_status}
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {t("missionControl.benchmarks").replace("{passed}", String(status.benchmark_passed)).replace("{total}", String(status.benchmark_total))}
              </p>
            </div>

            {/* Metric grid */}
            <div className="md:col-span-3 grid grid-cols-2 md:grid-cols-3 gap-3">
              <StatCard
                label={t("missionControl.accuracy")}
                value={`${(status.accuracy_score * 100).toFixed(1)}%`}
                sub={t("missionControl.accuracySub")}
                icon={BarChart3}
                color="blue"
              />
              <StatCard
                label={t("missionControl.confidence")}
                value={`${(status.confidence_score * 100).toFixed(1)}%`}
                sub={t("missionControl.confidenceSub")}
                icon={TrendingUp}
                color="green"
              />
              <StatCard
                label={t("missionControl.hallucination")}
                value={`${(status.hallucination_rate * 100).toFixed(2)}%`}
                sub={t("missionControl.hallucinationSub")}
                icon={AlertTriangle}
                color={status.hallucination_rate > 0.05 ? "red" : "green"}
              />
              <StatCard
                label={t("missionControl.errorRate")}
                value={`${(status.error_rate * 100).toFixed(2)}%`}
                sub={t("missionControl.errorRateSub").replace("{n}", String(status.agent_run_count))}
                icon={Activity}
                color={status.error_rate > 0.1 ? "red" : "slate"}
              />
              <StatCard
                label={t("missionControl.cost7d")}
                value={`$${status.cost_usd_last_7d.toFixed(4)}`}
                icon={DollarSign}
                color="purple"
              />
              <StatCard
                label={t("missionControl.cost30d")}
                value={`$${status.cost_usd_last_30d.toFixed(4)}`}
                icon={DollarSign}
                color="purple"
              />
            </div>
          </div>

          {/* Trend charts */}
          {trendRuns.length > 1 && (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                  {t("missionControl.trends").replace("{n}", String(trendRuns.length))}
                </p>
                <div className="flex gap-1">
                  {(["quality", "cost"] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveChart(tab)}
                      className={`rounded px-3 py-1 text-xs font-medium ${
                        activeChart === tab
                          ? "bg-indigo-600 text-white"
                          : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
                      }`}
                    >
                      {tab === "quality" ? t("missionControl.qualityMetrics") : t("missionControl.cost")}
                    </button>
                  ))}
                </div>
              </div>

              {activeChart === "quality" ? (
                <TrendChart
                  runs={trendRuns}
                  metrics={[
                    { key: "accuracy_score",      label: t("missionControl.trendAccuracy"),      color: "#3b82f6", format: (v) => `${(v * 100).toFixed(1)}%` },
                    { key: "confidence_score",    label: t("missionControl.trendConfidence"),    color: "#10b981", format: (v) => `${(v * 100).toFixed(1)}%` },
                    { key: "hallucination_rate",  label: t("missionControl.trendHallucination"), color: "#ef4444", format: (v) => `${(v * 100).toFixed(2)}%` },
                  ]}
                />
              ) : (
                <TrendChart
                  runs={trendRuns}
                  metrics={[
                    { key: "cost_usd_last_7d",  label: t("missionControl.cost7dLabel"),  color: "#a855f7", format: (v) => `$${v.toFixed(4)}` },
                    { key: "cost_usd_last_30d", label: t("missionControl.cost30dLabel"), color: "#6366f1", format: (v) => `$${v.toFixed(4)}` },
                  ]}
                />
              )}
            </div>
          )}

          {/* Benchmark details + Agent status */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Benchmark breakdown */}
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-indigo-500" />
                <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                  {t("missionControl.benchmarkSuite")}
                </p>
              </div>
              {benchmarks && benchmarks.length > 0 ? (
                <BenchmarkModuleSummary results={benchmarks} />
              ) : (
                <p className="text-xs text-gray-400">{t("missionControl.runForBenchmarks")}</p>
              )}
            </div>

            {/* Agent status */}
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="h-4 w-4 text-sky-500" />
                  <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                    {t("missionControl.agentStatus")}
                  </p>
                </div>
                {status.agents.total > 0 && (
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <span className="h-2 w-2 rounded-full bg-emerald-400 inline-block" />
                      {t("missionControl.agentsActive").replace("{n}", String(status.agents.active))}
                    </span>
                    {status.agents.error > 0 && (
                      <span className="flex items-center gap-1 text-red-500 font-semibold">
                        <span className="h-2 w-2 rounded-full bg-red-500 inline-block" />
                        {t("missionControl.agentsError").replace("{n}", String(status.agents.error))}
                      </span>
                    )}
                  </div>
                )}
              </div>
              <AgentStatusGrid agents={agents} />
            </div>
          </div>

          {/* Last updated */}
          {status.computed_at && (
            <p className="text-xs text-gray-400">
              {t("missionControl.lastEval")}: {formatDate(status.computed_at)} ·{" "}
              {t("missionControl.autoRefresh")}
            </p>
          )}
        </>
      )}

      {/* Founder Chat — always visible (no data prompts to run evaluation first) */}
      <div>
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">
          {t("missionControl.founderChat")}
        </h2>
        <FounderChat />
      </div>
    </div>
  );
}
