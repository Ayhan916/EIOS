"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Minus,
  TrendingDown,
  TrendingUp,
  XCircle,
} from "lucide-react";
import {
  LineChart,
  Line,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  benchmarkApi,
  ModuleComparisonEntry,
} from "@/lib/api/benchmark-comparison";
import { useLanguage } from "@/lib/i18n/context";
import { formatDate } from "@/lib/utils";

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_CONFIG = {
  green:   { color: "text-emerald-600", bg: "bg-emerald-100", icon: CheckCircle2 },
  yellow:  { color: "text-amber-600",   bg: "bg-amber-100",   icon: AlertTriangle },
  red:     { color: "text-red-600",     bg: "bg-red-100",     icon: XCircle },
  unknown: { color: "text-gray-400",    bg: "bg-gray-100",    icon: Activity },
};

const MODULE_LABEL_KEYS: Record<string, string> = {
  source_credibility: "benchmarks.moduleSourceCredibility",
  prioritization:     "benchmarks.modulePrioritization",
  lksg_statement:     "benchmarks.moduleLksgStatement",
  regulatory_changes: "benchmarks.moduleRegulatoryChanges",
};

function pct(v: number) {
  return `${(v * 100).toFixed(1)}%`;
}

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) return <span className="text-gray-300">—</span>;
  if (delta === 0)
    return (
      <span className="flex items-center gap-0.5 text-xs text-gray-400">
        <Minus className="h-3 w-3" /> 0%
      </span>
    );
  const positive = delta > 0;
  return (
    <span
      className={`flex items-center gap-0.5 text-xs font-medium ${
        positive ? "text-emerald-600" : "text-red-500"
      }`}
    >
      {positive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
      {positive ? "+" : ""}
      {pct(delta)}
    </span>
  );
}

// ── Sparkline ─────────────────────────────────────────────────────────────────

function Sparkline({ data, status }: { data: { pass_rate: number }[]; status: string }) {
  const color =
    status === "green" ? "#10b981" : status === "yellow" ? "#f59e0b" : "#ef4444";
  return (
    <ResponsiveContainer width={80} height={28}>
      <LineChart data={data}>
        <Line
          type="monotone"
          dataKey="pass_rate"
          stroke={color}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
        <Tooltip
          formatter={(v: number) => pct(v)}
          contentStyle={{ fontSize: 10, padding: "2px 6px" }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ── Module row ────────────────────────────────────────────────────────────────

function ModuleRow({ entry }: { entry: ModuleComparisonEntry }) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const cfg = STATUS_CONFIG[entry.status] ?? STATUS_CONFIG.unknown;
  const Icon = cfg.icon;
  const statusLabels: Record<string, string> = {
    green: t("benchmarks.passing"),
    yellow: t("benchmarks.warning"),
    red: t("benchmarks.failing"),
    unknown: t("benchmarks.unknown"),
  };

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      {/* Summary row */}
      <div
        className="flex items-center gap-3 p-3 cursor-pointer select-none"
        onClick={() => setExpanded((v) => !v)}
      >
        {/* Expand toggle */}
        <span className="text-gray-400 shrink-0">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </span>

        {/* Status badge */}
        <span
          className={`shrink-0 flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${cfg.bg} ${cfg.color}`}
        >
          <Icon className="h-3 w-3" />
          {statusLabels[entry.status] ?? entry.status}
        </span>

        {/* Module name */}
        <span className="flex-1 text-sm font-medium text-gray-900 dark:text-white">
          {MODULE_LABEL_KEYS[entry.module] ? t(MODULE_LABEL_KEYS[entry.module] as Parameters<typeof t>[0]) : entry.module}
        </span>

        {/* Pass rate */}
        <span className={`text-sm font-bold tabular-nums ${cfg.color}`}>
          {pct(entry.current_pass_rate)}
        </span>

        {/* Delta */}
        <div className="w-14 text-right">
          <DeltaBadge delta={entry.delta} />
        </div>

        {/* Baseline gap */}
        <span
          className={`text-xs tabular-nums w-14 text-right ${
            entry.current_pass_rate < entry.baseline ? "text-red-500" : "text-gray-400"
          }`}
        >
          {entry.current_pass_rate < entry.baseline
            ? `-${pct(entry.baseline - entry.current_pass_rate)} ${t("benchmarks.vsBaseline")}`
            : t("benchmarks.atBaseline")}
        </span>

        {/* Sparkline */}
        <div className="shrink-0">
          <Sparkline data={entry.trend} status={entry.status} />
        </div>

        {/* Case count */}
        <span className="text-xs text-gray-400 shrink-0 w-16 text-right">
          {t("benchmarks.cases").replace("{passed}", String(entry.passed_cases)).replace("{total}", String(entry.total_cases))}
        </span>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-gray-100 dark:border-gray-800 px-4 pb-4 pt-3 space-y-3">
          {/* Trend table */}
          <div>
            <p className="text-xs font-semibold text-gray-400 mb-1.5 uppercase tracking-wide">
              {t("benchmarks.runHistory")}
            </p>
            <div className="flex gap-2 flex-wrap">
              {entry.trend.map((tr, i) => (
                <div
                  key={tr.run_id}
                  className="text-center rounded border border-gray-200 dark:border-gray-700 px-2 py-1"
                >
                  <p className="text-xs text-gray-400">
                    {tr.computed_at
                      ? formatDate(tr.computed_at)
                      : `Run ${i + 1}`}
                  </p>
                  <p
                    className={`text-sm font-bold tabular-nums ${
                      tr.pass_rate >= 0.9
                        ? "text-emerald-600"
                        : tr.pass_rate >= 0.7
                        ? "text-amber-500"
                        : "text-red-500"
                    }`}
                  >
                    {pct(tr.pass_rate)}
                  </p>
                  <p className="text-xs text-gray-400">
                    {tr.passed}/{tr.total}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Failing cases */}
          {entry.failing_cases.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-red-500 mb-1.5 uppercase tracking-wide">
                {t("benchmarks.failingLatest")}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {entry.failing_cases.map((fc) => (
                  <span
                    key={fc}
                    className="rounded bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 px-2 py-0.5 text-xs text-red-600 font-mono"
                  >
                    {fc}
                  </span>
                ))}
              </div>
            </div>
          )}

          {entry.failing_cases.length === 0 && (
            <p className="text-xs text-emerald-600">{t("benchmarks.allPassing")}</p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function BenchmarksPage() {
  const { t } = useLanguage();
  const [limitRuns, setLimitRuns] = useState(5);

  const { data, isLoading } = useQuery({
    queryKey: ["benchmark-comparison", limitRuns],
    queryFn: () => benchmarkApi.getComparison(limitRuns),
  });

  const redCount   = data?.modules.filter((m) => m.status === "red").length ?? 0;
  const yellowCount = data?.modules.filter((m) => m.status === "yellow").length ?? 0;
  const greenCount  = data?.modules.filter((m) => m.status === "green").length ?? 0;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-sky-100 dark:bg-sky-900/30 p-2">
            <Activity className="h-6 w-6 text-sky-600 dark:text-sky-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              {t("benchmarks.title")}
            </h1>
            <p className="text-xs text-gray-500">
              {t("benchmarks.subtitle")}
            </p>
          </div>
        </div>

        {/* Run window selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">{t("benchmarks.runs")}:</span>
          {[3, 5, 10].map((n) => (
            <button
              key={n}
              onClick={() => setLimitRuns(n)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                limitRuns === n
                  ? "bg-sky-600 text-white"
                  : "bg-gray-100 text-gray-500 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700"
              }`}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      {/* Summary pills */}
      {data && (
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-xs text-gray-400">
            {t("benchmarks.latest")}: {data.latest_computed_at ? formatDate(data.latest_computed_at) : "—"}{" "}
            · {t("benchmarks.runsAnalysed").replace("{n}", String(data.run_count))}
          </span>
          <div className="flex gap-2 ml-auto">
            <span className="rounded-full bg-red-100 text-red-600 text-xs font-semibold px-2.5 py-0.5">
              {redCount} {t("benchmarks.failing")}
            </span>
            <span className="rounded-full bg-amber-100 text-amber-600 text-xs font-semibold px-2.5 py-0.5">
              {yellowCount} {t("benchmarks.warning")}
            </span>
            <span className="rounded-full bg-emerald-100 text-emerald-600 text-xs font-semibold px-2.5 py-0.5">
              {greenCount} {t("benchmarks.passing")}
            </span>
          </div>
        </div>
      )}

      {/* Module list */}
      {isLoading ? (
        <div className="py-12 text-center text-sm text-gray-400">{t("benchmarks.loading")}</div>
      ) : !data || data.modules.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 py-16 text-center">
          <Activity className="mx-auto h-8 w-8 text-gray-300 mb-3" />
          <p className="text-sm text-gray-400">
            {t("benchmarks.noData")}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {data.modules.map((entry) => (
            <ModuleRow key={entry.module} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
