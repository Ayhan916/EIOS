"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Briefcase,
  CheckCircle2,
  Clock,
  FileText,
  GitPullRequest,
  Plus,
  Radio,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import { getDashboard } from "@/lib/api/dashboard";
import apiClient from "@/lib/api/client";
import { formatDate, formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";

// ── Helpers ──────────────────────────────────────────────────────────────────

function qualityClass(score: number | null) {
  if (score == null) return "text-muted-foreground";
  if (score >= 0.7) return "text-emerald-600";
  if (score >= 0.4) return "text-amber-600";
  return "text-red-600";
}

function qualityBg(score: number | null) {
  if (score == null) return "bg-slate-100 text-slate-600";
  if (score >= 0.7) return "bg-emerald-50 text-emerald-700";
  if (score >= 0.4) return "bg-amber-50 text-amber-700";
  return "bg-red-50 text-red-700";
}

// ── Sub-components ────────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  sub,
  icon: Icon,
  valueClass,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  valueClass?: string;
  accent?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-5 pb-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {label}
            </p>
            <p className={`mt-1 text-3xl font-bold ${valueClass ?? "text-foreground"}`}>
              {value}
            </p>
            {sub && (
              <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>
            )}
          </div>
          <div className={`rounded-full p-2.5 flex-shrink-0 ${accent ?? "bg-primary/10"}`}>
            <Icon className={`h-5 w-5 ${accent ? "text-white" : "text-primary"}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function HBar({
  label,
  count,
  max,
  colorClass,
}: {
  label: string;
  count: number;
  max: number;
  colorClass: string;
}) {
  const pct = max > 0 ? Math.round((count / max) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="w-20 text-xs text-muted-foreground text-right flex-shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${colorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-7 text-xs font-semibold text-right flex-shrink-0">{count}</span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

const SEVERITY_SIGNAL: Record<string, string> = {
  Critical: "bg-red-100 text-red-800",
  High:     "bg-orange-100 text-orange-800",
  Medium:   "bg-amber-100 text-amber-800",
  Low:      "bg-slate-100 text-slate-600",
};

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function DashboardPage() {
  const { user } = useAuth();

  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
    staleTime: 30_000,
  });

  const { data: signals } = useQuery({
    queryKey: ["dashboard-signals"],
    queryFn: async () => {
      const r = await apiClient.get("/api/v1/surveillance/signals?limit=7&signal_status=ACTIVE");
      return r.data as Array<{
        id: string; title: string; severity: string; signal_type: string;
        source_type: string; supplier_id: string | null; detected_at: string;
      }>;
    },
    staleTime: 60_000,
  });

  const { data: findingTrend } = useQuery({
    queryKey: ["dashboard-finding-trend"],
    queryFn: async () => {
      const r = await apiClient.get("/api/v1/executive/findings/trend?months=6");
      return r.data as Array<{ month: string; opened: number }>;
    },
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="py-24 text-center text-muted-foreground">
        Failed to load dashboard.
      </div>
    );
  }

  const totalFindings = Object.values(data.findings_by_severity).reduce(
    (a, b) => a + b,
    0
  );
  const maxSeverity = Math.max(...Object.values(data.findings_by_severity), 1);
  const maxCategory = Math.max(...Object.values(data.findings_by_category), 1);
  const maxMonthly = Math.max(
    ...data.assessments_over_time.map((m) => m.count),
    1
  );

  const avgQualityPct =
    data.avg_quality_score != null
      ? `${Math.round(data.avg_quality_score * 100)}%`
      : "—";

  return (
    <div className="space-y-8">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Welcome back, {user?.display_name?.split(" ")[0]}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Portfolio Dashboard · ESG Due Diligence & Risk Intelligence
          </p>
        </div>
        <Button asChild>
          <Link href="/assessments/new">
            <Plus className="h-4 w-4" />
            New Assessment
          </Link>
        </Button>
      </div>

      {/* ── KPI strip ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <KpiCard
          label="Total Assessments"
          value={data.total_assessments}
          icon={FileText}
          sub="in your organisation"
        />
        <KpiCard
          label="Avg Quality Score"
          value={avgQualityPct}
          icon={TrendingUp}
          valueClass={qualityClass(data.avg_quality_score)}
          sub="across all assessments"
        />
        <KpiCard
          label="Open Actions"
          value={data.open_actions}
          icon={Clock}
          sub={`${data.closed_actions_pct}% closed`}
        />
        <KpiCard
          label="Overdue"
          value={data.overdue_actions}
          icon={AlertTriangle}
          valueClass={data.overdue_actions > 0 ? "text-red-600" : "text-foreground"}
          accent={data.overdue_actions > 0 ? "bg-red-500" : undefined}
          sub="past due date"
        />
        <KpiCard
          label="High-Risk Findings"
          value={data.high_risk_finding_count + data.critical_finding_count}
          icon={ShieldAlert}
          valueClass={
            data.critical_finding_count > 0 ? "text-red-600" : "text-foreground"
          }
          sub={`${data.critical_finding_count} critical`}
        />
      </div>

      {/* ── Middle row: Action breakdown + Findings breakdown ──────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Action status breakdown */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Action Status</CardTitle>
            <CardDescription>Recommendation lifecycle across portfolio</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              {[
                { key: "open", label: "Open", cls: "bg-slate-100 text-slate-700" },
                { key: "in_progress", label: "In Progress", cls: "bg-blue-100 text-blue-700" },
                { key: "resolved", label: "Resolved", cls: "bg-amber-100 text-amber-700" },
                { key: "verified", label: "Verified", cls: "bg-emerald-100 text-emerald-700" },
              ].map(({ key, label, cls }) => (
                <div
                  key={key}
                  className={`rounded-lg p-4 text-center ${cls}`}
                >
                  <p className="text-2xl font-bold">
                    {data.action_status_breakdown[key] ?? 0}
                  </p>
                  <p className="text-xs font-medium mt-0.5">{label}</p>
                </div>
              ))}
            </div>
            {data.open_actions > 0 && (
              <div className="mt-4">
                <div className="flex justify-between text-xs text-muted-foreground mb-1">
                  <span>Closure rate</span>
                  <span className="font-medium">{data.closed_actions_pct}%</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full"
                    style={{ width: `${data.closed_actions_pct}%` }}
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Findings breakdown */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Findings Breakdown</CardTitle>
            <CardDescription>
              {totalFindings} total findings across all assessments
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* By severity */}
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                By Severity
              </p>
              <div className="space-y-2">
                <HBar label="Critical" count={data.findings_by_severity["Critical"] ?? 0} max={maxSeverity} colorClass="bg-red-500" />
                <HBar label="High" count={data.findings_by_severity["High"] ?? 0} max={maxSeverity} colorClass="bg-orange-400" />
                <HBar label="Medium" count={data.findings_by_severity["Medium"] ?? 0} max={maxSeverity} colorClass="bg-amber-400" />
                <HBar label="Low" count={data.findings_by_severity["Low"] ?? 0} max={maxSeverity} colorClass="bg-slate-300" />
              </div>
            </div>
            {/* By ESG category */}
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                By ESG Category
              </p>
              <div className="space-y-2">
                <HBar label="Environmental" count={data.findings_by_category["E"] ?? 0} max={maxCategory} colorClass="bg-emerald-500" />
                <HBar label="Social" count={data.findings_by_category["S"] ?? 0} max={maxCategory} colorClass="bg-blue-500" />
                <HBar label="Governance" count={data.findings_by_category["G"] ?? 0} max={maxCategory} colorClass="bg-purple-500" />
                {(data.findings_by_category["Other"] ?? 0) > 0 && (
                  <HBar label="Other" count={data.findings_by_category["Other"]} max={maxCategory} colorClass="bg-slate-400" />
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Review Queue (shown only when there are items pending) ─────────── */}
      {(data.awaiting_review > 0 || data.reviews_overdue > 0) && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                <GitPullRequest className="h-4 w-4 text-blue-500" />
                Review Queue
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Assessments awaiting formal governance review
              </p>
            </div>
            <div className="flex items-center gap-3">
              {data.awaiting_review > 0 && (
                <span className="rounded-full bg-blue-100 text-blue-700 px-3 py-0.5 text-xs font-semibold">
                  {data.awaiting_review} awaiting
                </span>
              )}
              {data.reviews_overdue > 0 && (
                <span className="rounded-full bg-red-100 text-red-700 px-3 py-0.5 text-xs font-semibold">
                  {data.reviews_overdue} overdue
                </span>
              )}
            </div>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {data.review_queue.map((item) => (
              <Link
                key={item.id}
                href={`/assessments/${item.id}`}
                className="flex flex-col gap-2 rounded-lg border border-border bg-card px-4 py-3 transition-colors hover:bg-muted/50"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="truncate text-sm font-medium text-foreground leading-snug">
                    {item.title}
                  </p>
                  <span className={`flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                    item.review_status === "InReview"
                      ? "bg-blue-100 text-blue-700"
                      : "bg-amber-100 text-amber-700"
                  }`}>
                    {item.review_status === "InReview" ? "In Review" : "Changes Requested"}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3 flex-shrink-0" />
                  {item.review_due_date ? (
                    <span className={item.is_overdue ? "text-red-600 font-medium" : ""}>
                      Due {formatDate(item.review_due_date)}
                      {item.is_overdue && " · Overdue"}
                    </span>
                  ) : (
                    <span>No due date</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* ── Supplier KPIs (M27) ────────────────────────────────────────────── */}
      {data.total_suppliers > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                <Briefcase className="h-4 w-4 text-blue-500" />
                Supplier Portfolio
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                ESG due diligence subjects under management
              </p>
            </div>
            <Link href="/suppliers">
              <Button variant="ghost" size="sm" className="gap-1 text-xs">
                View all <ArrowRight className="h-3 w-3" />
              </Button>
            </Link>
          </div>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <KpiCard
              label="Total Suppliers"
              value={data.total_suppliers}
              icon={Briefcase}
              sub={`${data.active_suppliers} active`}
            />
            <KpiCard
              label="With Critical Risks"
              value={data.suppliers_with_critical_risks}
              icon={ShieldAlert}
              valueClass={data.suppliers_with_critical_risks > 0 ? "text-red-600" : "text-foreground"}
              accent={data.suppliers_with_critical_risks > 0 ? "bg-red-500" : undefined}
              sub="have critical findings"
            />
            <KpiCard
              label="No Assessments"
              value={data.suppliers_without_assessments}
              icon={AlertTriangle}
              valueClass={data.suppliers_without_assessments > 0 ? "text-amber-600" : "text-foreground"}
              sub="need first assessment"
            />
            <KpiCard
              label="Active"
              value={data.active_suppliers}
              icon={CheckCircle2}
              valueClass="text-emerald-600"
              sub="suppliers in scope"
            />
          </div>

          {data.supplier_watchlist.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Supplier Risk Watchlist</CardTitle>
                <p className="text-xs text-muted-foreground">Ranked by critical findings</p>
              </CardHeader>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/30">
                      <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Supplier</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Country</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">Tier</th>
                      <th className="px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">Critical</th>
                      <th className="px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">High</th>
                      <th className="px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">Open Actions</th>
                      <th className="px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">Overdue</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.supplier_watchlist.map((s) => (
                      <tr key={s.id} className="hover:bg-muted/20 transition-colors">
                        <td className="px-4 py-2.5">
                          <Link
                            href={`/suppliers/${s.id}`}
                            className="font-medium hover:text-blue-600 hover:underline"
                          >
                            {s.name}
                          </Link>
                        </td>
                        <td className="px-4 py-2.5 text-muted-foreground">{s.country || "—"}</td>
                        <td className="px-4 py-2.5">
                          <span className="text-xs font-medium text-muted-foreground">{s.supplier_tier}</span>
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <span className={`font-semibold ${s.critical_findings > 0 ? "text-red-600" : "text-muted-foreground"}`}>
                            {s.critical_findings}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <span className={`font-semibold ${s.high_findings > 0 ? "text-orange-500" : "text-muted-foreground"}`}>
                            {s.high_findings}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-right text-muted-foreground">
                          {s.open_actions}
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <span className={s.overdue_actions > 0 ? "text-red-600 font-medium" : "text-muted-foreground"}>
                            {s.overdue_actions}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ── Signal Feed + Finding Trend ───────────────────────────────────── */}
      {((signals && signals.length > 0) || (findingTrend && findingTrend.length > 0)) && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* External Signal Feed */}
          {signals && signals.length > 0 && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Radio className="h-4 w-4 text-blue-500" />
                    Live Signal Feed
                  </CardTitle>
                  <CardDescription>Active external intelligence signals</CardDescription>
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/surveillance" className="gap-1 text-xs">
                    All signals <ArrowRight className="h-3 w-3" />
                  </Link>
                </Button>
              </CardHeader>
              <CardContent className="p-0">
                <ul className="divide-y divide-border">
                  {signals.map((s) => (
                    <li key={s.id} className="flex items-start gap-3 px-4 py-3 hover:bg-muted/30 transition-colors">
                      <span className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${SEVERITY_SIGNAL[s.severity] ?? "bg-slate-100 text-slate-600"}`}>
                        {s.severity}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium line-clamp-1">{s.title}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {s.signal_type.replace(/_/g, " ")} · {timeAgo(s.detected_at)}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Finding Trend */}
          {findingTrend && findingTrend.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-orange-500" />
                  Finding Trend
                </CardTitle>
                <CardDescription>New findings per month (last 6 months)</CardDescription>
              </CardHeader>
              <CardContent>
                {(() => {
                  const maxOpened = Math.max(...findingTrend.map((r) => r.opened), 1);
                  return (
                    <div className="space-y-2">
                      {findingTrend.map((r) => (
                        <div key={r.month} className="flex items-center gap-3">
                          <span className="w-16 text-xs text-muted-foreground flex-shrink-0">{r.month}</span>
                          <div className="flex-1 h-5 bg-muted rounded overflow-hidden">
                            <div
                              className="h-full bg-orange-400/70 rounded"
                              style={{ width: `${Math.round((r.opened / maxOpened) * 100)}%` }}
                            />
                          </div>
                          <Link
                            href={`/findings`}
                            className="w-7 text-xs font-semibold text-right flex-shrink-0 hover:text-orange-600"
                          >
                            {r.opened}
                          </Link>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ── Bottom row: Recent assessments + Timeline ──────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Recent assessments — 2/3 width */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
            <div>
              <CardTitle className="text-base">Recent Assessments</CardTitle>
              <CardDescription>Latest ESG evaluations</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/assessments" className="gap-1 text-xs">
                View all <ArrowRight className="h-3 w-3" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {!data.recent_assessments.length ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No assessments yet.{" "}
                <Link href="/assessments/new" className="text-primary underline">
                  Run your first assessment
                </Link>
              </div>
            ) : (
              <div className="space-y-1">
                {data.recent_assessments.map((a) => (
                  <Link
                    key={a.id}
                    href={`/assessments/${a.id}`}
                    className="flex items-center gap-3 rounded-md px-3 py-2.5 transition-colors hover:bg-muted/60"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-foreground">
                        {a.title}
                      </p>
                      <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{formatDateTime(a.created_at)}</span>
                        {a.assessment_type && (
                          <>
                            <span>·</span>
                            <span className="capitalize">{a.assessment_type.replace(/_/g, " ")}</span>
                          </>
                        )}
                        {a.finding_count > 0 && (
                          <>
                            <span>·</span>
                            <span>{a.finding_count} findings</span>
                          </>
                        )}
                      </div>
                    </div>
                    <div
                      className={`flex-shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ${qualityBg(a.quality_score)}`}
                    >
                      {a.quality_score != null
                        ? `${Math.round(a.quality_score * 100)}%`
                        : a.status}
                    </div>
                    <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-muted-foreground/40" />
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Assessment timeline — 1/3 width */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Assessment Volume</CardTitle>
            <CardDescription>Assessments per month</CardDescription>
          </CardHeader>
          <CardContent>
            {!data.assessments_over_time.length ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                No timeline data yet.
              </p>
            ) : (
              <div className="space-y-2">
                {data.assessments_over_time.map((m) => (
                  <div key={m.month} className="flex items-center gap-3">
                    <span className="w-16 text-xs text-muted-foreground flex-shrink-0">
                      {m.month}
                    </span>
                    <div className="flex-1 h-5 bg-muted rounded overflow-hidden">
                      <div
                        className="h-full bg-primary/70 rounded"
                        style={{
                          width: `${Math.round((m.count / maxMonthly) * 100)}%`,
                        }}
                      />
                    </div>
                    <span className="w-4 text-xs font-semibold text-right flex-shrink-0">
                      {m.count}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
