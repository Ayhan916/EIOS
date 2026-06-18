"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock,
  Globe,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import {
  getExecutiveDashboard,
  getKPITrends,
  getRiskRegister,
  getExecutiveHeatmap,
  getActionEffectiveness,
  getGovernanceMetrics,
} from "@/lib/api/executive";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import Link from "next/link";

// ── Helpers ───────────────────────────────────────────────────────────────────

function bandColor(band: string) {
  switch (band) {
    case "Critical":
      return "bg-red-100 text-red-800";
    case "High":
      return "bg-orange-100 text-orange-800";
    case "Moderate":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-emerald-100 text-emerald-800";
  }
}

function trendIcon(trend: string) {
  if (trend === "Improving")
    return <TrendingUp className="h-4 w-4 text-emerald-600" />;
  if (trend === "Deteriorating")
    return <TrendingDown className="h-4 w-4 text-red-600" />;
  return <span className="text-muted-foreground text-xs">—</span>;
}

function fmt(n: number | null, decimals = 1) {
  if (n === null || n === undefined) return "—";
  return n.toFixed(decimals);
}

// ── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  accent?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className={`mt-1 text-3xl font-semibold ${accent ?? ""}`}>
              {value}
            </p>
            {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
          </div>
          <div className="rounded-lg bg-slate-100 p-2">
            <Icon className="h-5 w-5 text-slate-600" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Trend tab ─────────────────────────────────────────────────────────────────

type Period = 30 | 90 | 365;

function KPITrendSection() {
  const [period, setPeriod] = useState<Period>(90);
  const { data, isLoading } = useQuery({
    queryKey: ["executive-kpi-trends", period],
    queryFn: () => getKPITrends(period),
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base">Portfolio KPI Trends</CardTitle>
        <div className="flex gap-1">
          {([30, 90, 365] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                period === p
                  ? "bg-slate-800 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {p === 365 ? "1Y" : `${p}D`}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        ) : !data || data.data_points.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No trend data for this period yet.
          </p>
        ) : (
          <>
            <div className="mb-4 flex gap-6">
              <div>
                <p className="text-xs text-muted-foreground">ESG Delta</p>
                <p
                  className={`text-lg font-semibold ${
                    (data.esg_delta ?? 0) >= 0
                      ? "text-emerald-600"
                      : "text-red-600"
                  }`}
                >
                  {data.esg_delta !== null
                    ? `${data.esg_delta >= 0 ? "+" : ""}${data.esg_delta}`
                    : "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Risk Delta</p>
                <p
                  className={`text-lg font-semibold ${
                    (data.risk_delta ?? 0) <= 0
                      ? "text-emerald-600"
                      : "text-red-600"
                  }`}
                >
                  {data.risk_delta !== null
                    ? `${data.risk_delta >= 0 ? "+" : ""}${data.risk_delta}`
                    : "—"}
                </p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-xs text-muted-foreground">
                    <th className="pb-2 text-left">Month</th>
                    <th className="pb-2 text-right">Suppliers</th>
                    <th className="pb-2 text-right">Avg ESG</th>
                    <th className="pb-2 text-right">Avg Risk</th>
                    <th className="pb-2 text-right">High+Critical</th>
                  </tr>
                </thead>
                <tbody>
                  {data.data_points.map((dp) => (
                    <tr key={dp.month} className="border-b last:border-0">
                      <td className="py-2 font-mono text-xs">{dp.month}</td>
                      <td className="py-2 text-right">{dp.supplier_count}</td>
                      <td className="py-2 text-right">
                        {fmt(dp.avg_esg_score)}
                      </td>
                      <td className="py-2 text-right">
                        {fmt(dp.avg_risk_score)}
                      </td>
                      <td className="py-2 text-right">
                        {dp.high_risk_count + dp.critical_risk_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ── Risk Register preview ─────────────────────────────────────────────────────

function RiskRegisterPreview() {
  const { data, isLoading } = useQuery({
    queryKey: ["executive-risk-register-preview"],
    queryFn: () => getRiskRegister({ limit: 10, sort_by: "risk_score" }),
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base">Top Risk Suppliers</CardTitle>
        <Link
          href="/executive/risk-register"
          className="text-xs text-blue-600 hover:underline"
        >
          View all →
        </Link>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-6">
            <Spinner />
          </div>
        ) : !data || data.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No scored suppliers yet.
          </p>
        ) : (
          <div className="space-y-2">
            {data.map((e) => (
              <div
                key={e.supplier_id}
                className="flex items-center justify-between rounded-lg border px-3 py-2"
              >
                <div className="flex items-center gap-3">
                  <span className="w-5 text-center text-xs font-mono text-muted-foreground">
                    {e.rank}
                  </span>
                  <div>
                    <p className="text-sm font-medium">{e.supplier_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {e.country} · {e.industry}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {trendIcon(e.trend)}
                  <span className="text-sm font-mono">
                    {fmt(e.risk_score)}
                  </span>
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium ${bandColor(e.risk_band)}`}
                  >
                    {e.risk_band}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Heatmap preview ───────────────────────────────────────────────────────────

function HeatmapPreview() {
  const [view, setView] = useState<"country" | "sector" | "tier">("country");
  const { data, isLoading } = useQuery({
    queryKey: ["executive-heatmap-preview", view],
    queryFn: () => getExecutiveHeatmap(view),
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base">Risk Heatmap</CardTitle>
        <div className="flex gap-1">
          {(["country", "sector", "tier"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`rounded px-2 py-1 text-xs font-medium capitalize transition-colors ${
                view === v
                  ? "bg-slate-800 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-6">
            <Spinner />
          </div>
        ) : !data || data.buckets.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            No data available.
          </p>
        ) : (
          <div className="space-y-2">
            {data.buckets.slice(0, 8).map((b) => (
              <div key={b.label} className="flex items-center gap-3">
                <p className="w-32 truncate text-sm font-medium">{b.label}</p>
                <div className="flex-1">
                  <div className="h-2 rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full bg-orange-400"
                      style={{
                        width: `${Math.min(100, b.avg_risk_score)}%`,
                      }}
                    />
                  </div>
                </div>
                <span className="w-10 text-right text-xs font-mono text-muted-foreground">
                  {b.avg_risk_score.toFixed(0)}
                </span>
                <span className="w-16 text-right text-xs text-muted-foreground">
                  {b.supplier_count} supplier{b.supplier_count !== 1 ? "s" : ""}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Action & Governance summary ───────────────────────────────────────────────

function ActionGovernanceSection() {
  const { data: ae } = useQuery({
    queryKey: ["executive-action-effectiveness"],
    queryFn: () => getActionEffectiveness(30),
  });
  const { data: gov } = useQuery({
    queryKey: ["executive-governance-metrics"],
    queryFn: () => getGovernanceMetrics(30),
  });

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Action Effectiveness (30d)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Open actions</span>
            <span className="font-medium">{ae?.total_open ?? "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Overdue</span>
            <span
              className={`font-medium ${
                (ae?.total_overdue ?? 0) > 0 ? "text-red-600" : ""
              }`}
            >
              {ae?.total_overdue ?? "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Closed this period</span>
            <span className="font-medium">{ae?.closed_this_period ?? "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Resolution rate</span>
            <span className="font-medium">
              {ae?.resolution_rate !== null && ae?.resolution_rate !== undefined
                ? `${(ae.resolution_rate * 100).toFixed(0)}%`
                : "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Avg resolution</span>
            <span className="font-medium">
              {ae?.avg_resolution_days != null
                ? `${ae.avg_resolution_days}d`
                : "—"}
            </span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Governance Metrics (30d)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Total decisions</span>
            <span className="font-medium">
              {gov?.total_review_decisions ?? "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Approved</span>
            <span className="font-medium text-emerald-600">
              {gov?.approved ?? "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Rejected</span>
            <span className="font-medium text-red-600">
              {gov?.rejected ?? "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Approval rate</span>
            <span className="font-medium">
              {gov?.approval_rate !== null && gov?.approval_rate !== undefined
                ? `${(gov.approval_rate * 100).toFixed(0)}%`
                : "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Avg review time</span>
            <span className="font-medium">
              {gov?.avg_review_days != null
                ? `${gov.avg_review_days}d`
                : "—"}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ExecutiveDashboardPage() {
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ["executive-dashboard"],
    queryFn: getExecutiveDashboard,
  });

  const ps = dashboard?.portfolio_summary;
  const as_ = dashboard?.action_summary;
  const gs = dashboard?.governance_summary;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Executive Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Board-level ESG portfolio intelligence
          </p>
        </div>
        <Link
          href="/executive/reports"
          className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          Board Reports →
        </Link>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : (
        <>
          {/* KPI strip */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <KpiCard
              label="Total Suppliers"
              value={ps?.total_suppliers ?? 0}
              icon={Globe}
            />
            <KpiCard
              label="Scored"
              value={ps?.scored_suppliers ?? 0}
              sub={
                ps
                  ? `${ps.total_suppliers > 0 ? Math.round((ps.scored_suppliers / ps.total_suppliers) * 100) : 0}%`
                  : undefined
              }
              icon={BarChart3}
            />
            <KpiCard
              label="Avg ESG Score"
              value={fmt(ps?.avg_esg_score ?? null)}
              icon={TrendingUp}
              accent={
                (ps?.avg_esg_score ?? 0) >= 70
                  ? "text-emerald-600"
                  : "text-red-600"
              }
            />
            <KpiCard
              label="Critical Risk"
              value={ps?.critical_risk_suppliers ?? 0}
              icon={AlertTriangle}
              accent={
                (ps?.critical_risk_suppliers ?? 0) > 0 ? "text-red-600" : ""
              }
            />
            <KpiCard
              label="Overdue Actions"
              value={as_?.overdue_actions ?? 0}
              icon={Clock}
              accent={
                (as_?.overdue_actions ?? 0) > 0 ? "text-red-600" : ""
              }
            />
            <KpiCard
              label="Awaiting Review"
              value={gs?.assessments_awaiting_review ?? 0}
              icon={CheckCircle2}
            />
          </div>

          {/* Risk distribution */}
          {ps && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Risk Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4">
                  {(
                    [
                      ["Critical", ps.critical_risk_suppliers, "bg-red-500"],
                      ["High", ps.high_risk_suppliers, "bg-orange-500"],
                      ["Moderate", ps.moderate_risk_suppliers, "bg-amber-400"],
                      ["Low", ps.low_risk_suppliers, "bg-emerald-500"],
                    ] as [string, number, string][]
                  ).map(([label, count, color]) => (
                    <div key={label} className="flex-1 text-center">
                      <div
                        className={`mx-auto h-12 w-full max-w-[60px] rounded ${color}`}
                        style={{
                          opacity: ps.scored_suppliers
                            ? 0.3 +
                              0.7 * (count / ps.scored_suppliers)
                            : 0.3,
                        }}
                      />
                      <p className="mt-1 text-lg font-semibold">{count}</p>
                      <p className="text-xs text-muted-foreground">{label}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex gap-6 text-sm text-muted-foreground">
                  <span>
                    Improving:{" "}
                    <strong className="text-emerald-600">
                      {ps.improving_suppliers}
                    </strong>
                  </span>
                  <span>
                    Deteriorating:{" "}
                    <strong className="text-red-600">
                      {ps.deteriorating_suppliers}
                    </strong>
                  </span>
                  {ps.avg_risk_score !== null && (
                    <span>
                      Avg Risk:{" "}
                      <strong>{fmt(ps.avg_risk_score)}</strong>
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Trend + heatmap row */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <KPITrendSection />
            <HeatmapPreview />
          </div>

          {/* Risk register preview */}
          <RiskRegisterPreview />

          {/* Action + governance */}
          <ActionGovernanceSection />
        </>
      )}
    </div>
  );
}
