"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BarChart3,
  Minus,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

// ── Types ─────────────────────────────────────────────────────────────────────

interface PortfolioAnalytics {
  total_suppliers: number;
  scored_suppliers: number;
  critical_risk_suppliers: number;
  high_risk_suppliers: number;
  improving_suppliers: number;
  deteriorating_suppliers: number;
  avg_esg_score: number | null;
  avg_risk_score: number | null;
  risk_distribution: Record<string, number>;
}

interface WatchlistEntry {
  supplier_id: string;
  supplier_name: string;
  country: string;
  industry: string;
  supplier_tier: string;
  risk_score: number;
  risk_band: string;
  trend: string;
  trend_delta: number;
  critical_findings: number;
  overdue_actions: number;
  alert_reasons: string[];
}

interface RankingEntry {
  rank: number;
  supplier_id: string;
  supplier_name: string;
  country: string;
  industry: string;
  supplier_tier: string;
  risk_score: number;
  risk_band: string;
  esg_score: number;
  trend: string;
  trend_delta: number;
  critical_findings: number;
  overdue_actions: number;
}

interface HeatmapCell {
  pillar: string;
  severity: string;
  count: number;
}

interface RiskHeatmap {
  cells: HeatmapCell[];
  total_findings: number;
  supplier_id: string | null;
}

// ── Styling helpers ───────────────────────────────────────────────────────────

function bandColor(band: string): string {
  switch (band) {
    case "Critical": return "bg-red-100 text-red-800";
    case "High":     return "bg-orange-100 text-orange-800";
    case "Moderate": return "bg-amber-100 text-amber-800";
    case "Low":      return "bg-emerald-100 text-emerald-800";
    default:         return "bg-slate-100 text-slate-600";
  }
}

function bandBar(band: string): string {
  switch (band) {
    case "Critical": return "bg-red-500";
    case "High":     return "bg-orange-400";
    case "Moderate": return "bg-amber-400";
    case "Low":      return "bg-emerald-500";
    default:         return "bg-slate-300";
  }
}

function heatColor(count: number, max: number): string {
  if (count === 0 || max === 0) return "bg-slate-50 text-slate-300";
  const ratio = count / max;
  if (ratio > 0.7) return "bg-red-500 text-white";
  if (ratio > 0.4) return "bg-orange-400 text-white";
  if (ratio > 0.15) return "bg-amber-300 text-slate-800";
  return "bg-amber-100 text-slate-700";
}

function TrendIcon({ trend }: { trend: string }) {
  if (trend === "Improving")    return <ArrowUpRight className="h-3.5 w-3.5 text-emerald-600" />;
  if (trend === "Deteriorating") return <ArrowDownRight className="h-3.5 w-3.5 text-red-500" />;
  return <Minus className="h-3.5 w-3.5 text-slate-400" />;
}

// ── Tab: Portfolio ────────────────────────────────────────────────────────────

function PortfolioTab() {
  const { t } = useLanguage();

  const { data, isLoading } = useQuery<PortfolioAnalytics>({
    queryKey: ["supplier-portfolio"],
    queryFn: async () => {
      const res = await apiClient.get("/suppliers/analytics/portfolio");
      return res.data;
    },
  });

  if (isLoading) return <div className="flex justify-center py-16"><Spinner size="lg" /></div>;
  if (!data) return null;

  const BANDS = ["Critical", "High", "Moderate", "Low"];
  const distMax = Math.max(...BANDS.map((b) => data.risk_distribution[b] ?? 0), 1);

  const kpis = [
    { label: t("analytics.totalSuppliers"),  value: data.total_suppliers,           icon: "🏢", color: "text-slate-900" },
    { label: t("analytics.scoredSuppliers"), value: data.scored_suppliers,           icon: "✓",  color: "text-blue-700" },
    { label: t("analytics.criticalRisk"),    value: data.critical_risk_suppliers,    icon: "🔴", color: "text-red-700" },
    { label: t("analytics.highRisk"),        value: data.high_risk_suppliers,        icon: "🟠", color: "text-orange-700" },
    { label: t("analytics.improving"),       value: data.improving_suppliers,        icon: "↑",  color: "text-emerald-700" },
    { label: t("analytics.deteriorating"),   value: data.deteriorating_suppliers,    icon: "↓",  color: "text-red-600" },
  ];

  return (
    <div className="space-y-6 mt-4">
      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {kpis.map((k) => (
          <Card key={k.label}>
            <CardContent className="pt-4 pb-4 text-center">
              <p className="text-xs text-slate-500 mb-1">{k.label}</p>
              <p className={`text-3xl font-bold ${k.color}`}>{k.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        {/* ESG / Risk avg */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">{t("analytics.avgEsgScore")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold text-blue-700">
              {data.avg_esg_score !== null ? data.avg_esg_score.toFixed(1) : "—"}
            </p>
            <p className="text-xs text-slate-400 mt-1">out of 100</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">{t("analytics.avgRiskScore")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-4xl font-bold text-orange-600">
              {data.avg_risk_score !== null ? data.avg_risk_score.toFixed(1) : "—"}
            </p>
            <p className="text-xs text-slate-400 mt-1">out of 100 (higher = worse)</p>
          </CardContent>
        </Card>

        {/* Risk distribution */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">{t("analytics.riskDistribution")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {BANDS.map((band) => {
              const count = data.risk_distribution[band] ?? 0;
              const pct = distMax > 0 ? Math.round((count / distMax) * 100) : 0;
              return (
                <div key={band}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-600">{band}</span>
                    <span className="font-semibold text-slate-800">{count}</span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${bandBar(band)}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Tab: Watchlist ────────────────────────────────────────────────────────────

function WatchlistTab() {
  const { t } = useLanguage();

  const { data = [], isLoading } = useQuery<WatchlistEntry[]>({
    queryKey: ["supplier-watchlist"],
    queryFn: async () => {
      const res = await apiClient.get("/suppliers/analytics/watchlist", { params: { limit: 50 } });
      return res.data;
    },
  });

  if (isLoading) return <div className="flex justify-center py-16"><Spinner size="lg" /></div>;

  if (data.length === 0) {
    return (
      <div className="mt-4 rounded-lg border border-dashed p-12 text-center text-sm text-slate-400">
        <TrendingUp className="mx-auto mb-3 h-8 w-8 text-emerald-400" />
        {t("analytics.watchlistEmpty")}
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-xl border border-slate-200 bg-white overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            <th className="px-4 py-3">{t("analytics.supplier")}</th>
            <th className="px-4 py-3">Country</th>
            <th className="px-4 py-3">{t("analytics.tier")}</th>
            <th className="px-4 py-3">{t("analytics.riskScore")}</th>
            <th className="px-4 py-3">{t("analytics.trend")}</th>
            <th className="px-4 py-3">{t("analytics.criticalFindings")}</th>
            <th className="px-4 py-3">{t("analytics.overdueActions")}</th>
            <th className="px-4 py-3">{t("analytics.alertReasons")}</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {data.map((entry) => (
            <tr key={entry.supplier_id} className="border-b border-slate-50 last:border-0 hover:bg-red-50/30">
              <td className="px-4 py-3 font-medium text-slate-900">{entry.supplier_name}</td>
              <td className="px-4 py-3 text-slate-500">{entry.country || "—"}</td>
              <td className="px-4 py-3 text-xs text-slate-500 capitalize">{entry.supplier_tier}</td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1.5">
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${bandColor(entry.risk_band)}`}>
                    {entry.risk_band}
                  </span>
                  <span className="text-xs font-mono text-slate-600">{entry.risk_score.toFixed(1)}</span>
                </div>
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1 text-xs">
                  <TrendIcon trend={entry.trend} />
                  <span className={entry.trend === "Improving" ? "text-emerald-600" : entry.trend === "Deteriorating" ? "text-red-600" : "text-slate-400"}>
                    {entry.trend}
                  </span>
                </div>
              </td>
              <td className="px-4 py-3">
                {entry.critical_findings > 0
                  ? <span className="font-semibold text-red-600">{entry.critical_findings}</span>
                  : <span className="text-slate-300">0</span>}
              </td>
              <td className="px-4 py-3">
                {entry.overdue_actions > 0
                  ? <span className="font-semibold text-orange-600">{entry.overdue_actions}</span>
                  : <span className="text-slate-300">0</span>}
              </td>
              <td className="px-4 py-3 max-w-xs">
                <div className="flex flex-wrap gap-1">
                  {entry.alert_reasons.map((r) => (
                    <span key={r} className="rounded bg-red-100 px-1.5 py-0.5 text-[10px] font-medium text-red-700">
                      {r}
                    </span>
                  ))}
                </div>
              </td>
              <td className="px-4 py-3">
                <Link
                  href={`/suppliers/${entry.supplier_id}`}
                  className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                >
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Tab: Rankings ─────────────────────────────────────────────────────────────

const SORT_OPTIONS = [
  { value: "risk_score",       label: "Risk Score" },
  { value: "esg_score",        label: "ESG Score" },
  { value: "overdue_actions",  label: "Overdue Actions" },
  { value: "critical_findings", label: "Critical Findings" },
] as const;

const BANDS = ["Critical", "High", "Moderate", "Low"];
const TIERS = ["tier1", "tier2", "tier3"];

function RankingsTab() {
  const { t } = useLanguage();
  const [sortBy, setSortBy] = useState<string>("risk_score");
  const [filterBand, setFilterBand] = useState("");
  const [filterTier, setFilterTier] = useState("");

  const { data = [], isLoading } = useQuery<RankingEntry[]>({
    queryKey: ["supplier-rankings", sortBy, filterBand, filterTier],
    queryFn: async () => {
      const params: Record<string, string> = { sort_by: sortBy, limit: "50" };
      if (filterBand) params.risk_band = filterBand;
      if (filterTier) params.supplier_tier = filterTier;
      const res = await apiClient.get("/suppliers/analytics/rankings", { params });
      return res.data;
    },
  });

  return (
    <div className="mt-4 space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">{t("analytics.sortBy")}:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="rounded-md border border-slate-200 px-2.5 py-1.5 text-sm outline-none focus:ring-2 focus:ring-blue-400"
          >
            {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">{t("analytics.filterBand")}:</span>
          <select
            value={filterBand}
            onChange={(e) => setFilterBand(e.target.value)}
            className="rounded-md border border-slate-200 px-2.5 py-1.5 text-sm outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="">All</option>
            {BANDS.map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">{t("analytics.filterTier")}:</span>
          <select
            value={filterTier}
            onChange={(e) => setFilterTier(e.target.value)}
            className="rounded-md border border-slate-200 px-2.5 py-1.5 text-sm outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="">All</option>
            {TIERS.map((t_) => <option key={t_} value={t_}>{t_.replace("tier", "Tier ")}</option>)}
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : data.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-sm text-slate-400">
          {t("analytics.rankingsEmpty")}
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3 w-10">{t("analytics.rank")}</th>
                <th className="px-4 py-3">{t("analytics.supplier")}</th>
                <th className="px-4 py-3">Country</th>
                <th className="px-4 py-3">{t("analytics.tier")}</th>
                <th className="px-4 py-3">{t("analytics.riskScore")}</th>
                <th className="px-4 py-3">{t("analytics.esgScore")}</th>
                <th className="px-4 py-3">{t("analytics.trend")}</th>
                <th className="px-4 py-3">{t("analytics.criticalFindings")}</th>
                <th className="px-4 py-3">{t("analytics.overdueActions")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {data.map((entry) => (
                <tr key={entry.supplier_id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-3 font-bold text-slate-400 text-center">#{entry.rank}</td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-900">{entry.supplier_name}</p>
                    <p className="text-[11px] text-slate-400">{entry.industry}</p>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{entry.country || "—"}</td>
                  <td className="px-4 py-3 text-xs text-slate-500 capitalize">{entry.supplier_tier}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${bandColor(entry.risk_band)}`}>
                      {entry.risk_score.toFixed(1)}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-sm text-blue-700">{entry.esg_score.toFixed(1)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <TrendIcon trend={entry.trend} />
                      <span className="text-xs text-slate-500">
                        {entry.trend_delta > 0 ? "+" : ""}{entry.trend_delta.toFixed(1)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {entry.critical_findings > 0
                      ? <span className="font-semibold text-red-600">{entry.critical_findings}</span>
                      : <span className="text-slate-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {entry.overdue_actions > 0
                      ? <span className="font-semibold text-orange-600">{entry.overdue_actions}</span>
                      : <span className="text-slate-300">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/suppliers/${entry.supplier_id}`}
                      className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                    >
                      <ArrowRight className="h-3 w-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Tab: Heatmap ──────────────────────────────────────────────────────────────

const PILLARS = ["Environmental", "Social", "Governance"];
const SEVERITIES = ["Critical", "High", "Medium", "Low"];

const PILLAR_COLORS: Record<string, string> = {
  Environmental: "text-emerald-700",
  Social:        "text-blue-700",
  Governance:    "text-violet-700",
};

function HeatmapTab() {
  const { t } = useLanguage();

  const { data, isLoading } = useQuery<RiskHeatmap>({
    queryKey: ["supplier-heatmap"],
    queryFn: async () => {
      const res = await apiClient.get("/suppliers/analytics/heatmap");
      return res.data;
    },
  });

  if (isLoading) return <div className="flex justify-center py-16"><Spinner size="lg" /></div>;
  if (!data) return null;

  const cellMap = new Map<string, number>();
  for (const cell of data.cells) {
    cellMap.set(`${cell.pillar}|${cell.severity}`, cell.count);
  }
  const maxCount = Math.max(...data.cells.map((c) => c.count), 1);

  if (data.total_findings === 0) {
    return (
      <div className="mt-4 rounded-lg border border-dashed p-12 text-center text-sm text-slate-400">
        <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-slate-300" />
        {t("analytics.noHeatmapData")}
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-900">{t("analytics.heatmapTitle")}</h3>
          <p className="text-xs text-slate-500 mt-0.5">{t("analytics.heatmapDesc")}</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-slate-900">{data.total_findings}</p>
          <p className="text-xs text-slate-400">{t("analytics.totalFindings")}</p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-slate-50">
              <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400 w-36">
                Pillar
              </th>
              {SEVERITIES.map((sev) => (
                <th key={sev} className="px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                  {sev}
                </th>
              ))}
              <th className="px-4 py-3 text-center text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Total
              </th>
            </tr>
          </thead>
          <tbody>
            {PILLARS.map((pillar) => {
              const rowTotal = SEVERITIES.reduce((sum, sev) => sum + (cellMap.get(`${pillar}|${sev}`) ?? 0), 0);
              return (
                <tr key={pillar} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-4">
                    <span className={`font-semibold text-sm ${PILLAR_COLORS[pillar] ?? "text-slate-700"}`}>
                      {pillar}
                    </span>
                  </td>
                  {SEVERITIES.map((sev) => {
                    const count = cellMap.get(`${pillar}|${sev}`) ?? 0;
                    return (
                      <td key={sev} className="px-4 py-4 text-center">
                        <div
                          className={`mx-auto flex h-14 w-14 items-center justify-center rounded-lg text-lg font-bold ${heatColor(count, maxCount)}`}
                        >
                          {count}
                        </div>
                      </td>
                    );
                  })}
                  <td className="px-4 py-4 text-center">
                    <span className="font-semibold text-slate-700">{rowTotal}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr className="border-t border-slate-200 bg-slate-50">
              <td className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400">Total</td>
              {SEVERITIES.map((sev) => {
                const colTotal = PILLARS.reduce((sum, p) => sum + (cellMap.get(`${p}|${sev}`) ?? 0), 0);
                return (
                  <td key={sev} className="px-4 py-3 text-center font-semibold text-slate-700">{colTotal}</td>
                );
              })}
              <td className="px-4 py-3 text-center font-bold text-slate-900">{data.total_findings}</td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 text-xs text-slate-500">
        <span>Intensity:</span>
        {[
          { color: "bg-red-500", label: "High (>70%)" },
          { color: "bg-orange-400", label: "Medium (>40%)" },
          { color: "bg-amber-300", label: "Low (>15%)" },
          { color: "bg-amber-100", label: "Minimal" },
          { color: "bg-slate-50 border border-slate-200", label: "None" },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1">
            <div className={`h-3 w-3 rounded ${color}`} />
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type Tab = "portfolio" | "watchlist" | "rankings" | "heatmap";

const TABS: { id: Tab; labelKey: "analytics.tabPortfolio" | "analytics.tabWatchlist" | "analytics.tabRankings" | "analytics.tabHeatmap"; icon: typeof BarChart3 }[] = [
  { id: "portfolio",  labelKey: "analytics.tabPortfolio",  icon: BarChart3 },
  { id: "watchlist",  labelKey: "analytics.tabWatchlist",  icon: AlertTriangle },
  { id: "rankings",   labelKey: "analytics.tabRankings",   icon: TrendingDown },
  { id: "heatmap",    labelKey: "analytics.tabHeatmap",    icon: BarChart3 },
];

export default function SupplierAnalyticsPage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<Tab>("portfolio");

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">{t("analytics.title")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("analytics.subtitle")}</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 w-fit">
        {TABS.map((tab_) => {
          const Icon = tab_.icon;
          return (
            <button
              key={tab_.id}
              onClick={() => setActiveTab(tab_.id)}
              className={`flex items-center gap-1.5 rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
                activeTab === tab_.id
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {t(tab_.labelKey)}
            </button>
          );
        })}
      </div>

      {activeTab === "portfolio"  && <PortfolioTab />}
      {activeTab === "watchlist"  && <WatchlistTab />}
      {activeTab === "rankings"   && <RankingsTab />}
      {activeTab === "heatmap"    && <HeatmapTab />}
    </div>
  );
}
