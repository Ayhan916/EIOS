"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BookOpen,
  CheckCircle2,
  Clock,
  Globe,
  Leaf,
  Shield,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import Link from "next/link";
import {
  AreaChart, Area,
  LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import {
  getExecutiveDashboard,
  getKPITrends,
  getRiskRegister,
  getExecutiveHeatmap,
  getActionEffectiveness,
  getGovernanceMetrics,
  getCommandCenter,
  type CommandCenterData,
  type PriorityAction,
  type PendingDecision,
} from "@/lib/api/executive";
import apiClient from "@/lib/api/client";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

// ── Types ─────────────────────────────────────────────────────────────────────

type Persona = "CEO" | "CFO" | "CSO" | "CCO";

// ── Helpers ───────────────────────────────────────────────────────────────────

function bandColor(band: string) {
  switch (band) {
    case "Critical": return "bg-red-100 text-red-800";
    case "High":     return "bg-orange-100 text-orange-800";
    case "Moderate": return "bg-amber-100 text-amber-800";
    default:         return "bg-emerald-100 text-emerald-800";
  }
}

function trendIcon(trend: string) {
  if (trend === "Improving") return <TrendingUp className="h-4 w-4 text-emerald-600" />;
  if (trend === "Deteriorating") return <TrendingDown className="h-4 w-4 text-red-600" />;
  return <span className="text-muted-foreground text-xs">—</span>;
}

function fmt(n: number | null | undefined, dec = 1) {
  if (n == null) return "—";
  return n.toFixed(dec);
}

// ── ESG Health Score card ─────────────────────────────────────────────────────

function HealthScoreRing({ score, label }: { score: number; label: string }) {
  const r = 42;
  const circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  const color =
    score >= 80 ? "stroke-emerald-500"
    : score >= 65 ? "stroke-blue-500"
    : score >= 50 ? "stroke-amber-500"
    : "stroke-red-500";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative flex h-28 w-28 items-center justify-center">
        <svg viewBox="0 0 100 100" className="h-28 w-28 -rotate-90">
          <circle cx="50" cy="50" r={r} fill="none" strokeWidth="9" className="stroke-muted" />
          <circle
            cx="50" cy="50" r={r} fill="none" strokeWidth="9"
            strokeDasharray={`${filled} ${circ}`}
            className={`transition-all ${color}`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute text-center">
          <p className="text-2xl font-bold tabular-nums leading-none">{score.toFixed(0)}</p>
          <p className="text-[10px] text-muted-foreground">/100</p>
        </div>
      </div>
      <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
        score >= 80 ? "bg-emerald-100 text-emerald-700"
        : score >= 65 ? "bg-blue-100 text-blue-700"
        : score >= 50 ? "bg-amber-100 text-amber-700"
        : "bg-red-100 text-red-700"
      }`}>{label}</span>
    </div>
  );
}

// ── Priority Actions ──────────────────────────────────────────────────────────

const PRIORITY_ICONS: Record<string, React.ElementType> = {
  overdue_actions:    Clock,
  critical_findings:  AlertTriangle,
  critical_risks:     ShieldAlert,
  assessments_pending: CheckCircle2,
};

const SEVERITY_STYLES: Record<string, string> = {
  critical: "border-red-200 bg-red-50 text-red-800",
  high:     "border-orange-200 bg-orange-50 text-orange-800",
  medium:   "border-amber-200 bg-amber-50 text-amber-800",
};

function PriorityActionsPanel({ actions }: { actions: PriorityAction[] }) {
  const { t } = useLanguage();
  if (!actions.length) {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
        <CheckCircle2 className="h-4 w-4" /> No urgent actions required
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {actions.map((a, i) => {
        const Icon = PRIORITY_ICONS[a.type] ?? AlertTriangle;
        return (
          <Link
            key={i}
            href={a.href}
            className={`flex items-center gap-3 rounded-lg border px-4 py-3 transition-colors hover:opacity-80 ${SEVERITY_STYLES[a.severity]}`}
          >
            <Icon className="h-4 w-4 flex-shrink-0" />
            <span className="text-sm font-medium flex-1">{a.title}</span>
            <span className="text-xs opacity-70">{t("common.view")} →</span>
          </Link>
        );
      })}
    </div>
  );
}

// ── Pending Decisions Panel ───────────────────────────────────────────────────

const PRIORITY_COLORS: Record<string, string> = {
  Critical: "text-red-600",
  High:     "text-orange-600",
  Medium:   "text-amber-600",
  Low:      "text-slate-500",
};

function PendingDecisionsPanel({ decisions }: { decisions: PendingDecision[] }) {
  const { t } = useLanguage();
  if (!decisions.length) {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
        <CheckCircle2 className="h-4 w-4" /> No decisions awaiting approval
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {decisions.map((d) => (
        <Link
          key={d.id}
          href="/recommendations"
          className="flex items-center justify-between rounded-lg border px-4 py-2.5 hover:bg-muted/50 transition-colors"
        >
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">{d.title}</p>
            {d.due_date && (
              <p className="text-xs text-muted-foreground">{t("dashboard.due")} {d.due_date.slice(0, 10)}</p>
            )}
          </div>
          <span className={`ml-3 flex-shrink-0 text-xs font-semibold ${PRIORITY_COLORS[d.priority] ?? "text-slate-500"}`}>
            {d.priority}
          </span>
        </Link>
      ))}
      <Link href="/recommendations" className="block text-center text-xs text-blue-600 hover:underline pt-1">
        View all recommendations →
      </Link>
    </div>
  );
}

// ── Upcoming Deadlines Panel ──────────────────────────────────────────────────

function UpcomingDeadlinesPanel() {
  const { data } = useQuery({
    queryKey: ["upcoming-deadlines"],
    queryFn: async () => {
      const res = await apiClient.get(
        "/operating-system/calendar-events?event_status=SCHEDULED&limit=5"
      );
      return res.data as { id: string; title: string; event_type: string; scheduled_at: string }[];
    },
    staleTime: 300_000,
  });

  const deadlines = (data ?? []).filter((e) =>
    ["COMPLIANCE_DEADLINE", "AUDIT_DEADLINE", "REPORTING_DEADLINE"].includes(e.event_type)
  );

  if (!deadlines.length) {
    return <p className="text-sm text-muted-foreground py-2">No upcoming deadlines.</p>;
  }

  const daysUntil = (date: string) => {
    const diff = new Date(date).getTime() - Date.now();
    return Math.ceil(diff / 86_400_000);
  };

  return (
    <div className="space-y-2">
      {deadlines.map((d) => {
        const days = daysUntil(d.scheduled_at);
        return (
          <Link
            key={d.id}
            href="/operating-system/calendar"
            className="flex items-center justify-between rounded-lg border px-3 py-2 hover:bg-muted/50 transition-colors"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{d.title}</p>
              <p className="text-xs text-muted-foreground">{d.event_type.replace(/_/g, " ")}</p>
            </div>
            <span className={`ml-3 flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${
              days <= 7 ? "bg-red-100 text-red-700"
              : days <= 30 ? "bg-amber-100 text-amber-700"
              : "bg-slate-100 text-slate-600"
            }`}>
              {days <= 0 ? "Today" : `${days}d`}
            </span>
          </Link>
        );
      })}
      <Link href="/operating-system/calendar" className="block text-center text-xs text-blue-600 hover:underline pt-1">
        View calendar →
      </Link>
    </div>
  );
}

// ── #140 Executive alert banner ───────────────────────────────────────────────

function ExecutiveAlertBanner({ actions }: { actions: PriorityAction[] }) {
  const criticals = actions.filter((a) => a.severity === "critical");
  if (criticals.length === 0) return null;
  return (
    <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-5 py-3">
      <AlertCircle className="h-4 w-4 flex-shrink-0 text-red-600 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-red-800">
          {criticals.length} critical item{criticals.length > 1 ? "s" : ""} require immediate attention
        </p>
        <div className="mt-1 flex flex-wrap gap-2">
          {criticals.map((a, i) => (
            <Link key={i} href={a.href} className="text-xs text-red-700 underline hover:text-red-900">
              {a.title}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  sub,
  delta,
  icon: Icon,
  accent,
  href,
}: {
  label: string;
  value: string | number;
  sub?: string;
  delta?: number | null;
  icon: React.ElementType;
  accent?: string;
  href?: string;  // #131 drill-down
}) {
  const inner = (
    <CardContent className="pt-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className={`mt-1 text-3xl font-semibold ${accent ?? ""}`}>{value}</p>
          {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
          {delta != null && (
            <p className={`mt-1 text-xs font-medium ${delta >= 0 ? "text-emerald-600" : "text-red-600"}`}>
              {delta >= 0 ? "+" : ""}{delta.toFixed(1)} vs. prior year
            </p>
          )}
        </div>
        <div className="rounded-lg bg-slate-100 p-2">
          <Icon className="h-5 w-5 text-slate-600" />
        </div>
      </div>
      {href && (
        <p className="mt-2 flex items-center gap-0.5 text-[10px] text-muted-foreground">
          View details <ArrowRight className="h-2.5 w-2.5" />
        </p>
      )}
    </CardContent>
  );
  if (href) {
    return (
      <Card className="hover:border-primary/40 hover:shadow-sm transition-all cursor-pointer">
        <Link href={href}>{inner}</Link>
      </Card>
    );
  }
  return <Card>{inner}</Card>;
}

// ── Persona panels ────────────────────────────────────────────────────────────

function CEOPanel({ cc, dashboard }: { cc: CommandCenterData; dashboard: any }) {
  const { t } = useLanguage();
  const ps = dashboard?.portfolio_summary;
  return (
    <div className="space-y-6">
      {/* #121 6 KPI cards with drill-down (#131) */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <KpiCard
          label="Avg ESG Score"
          value={fmt(cc.yoy.current_avg_esg, 0)}
          delta={cc.yoy.avg_esg_delta}
          icon={TrendingUp}
          href="/suppliers"
          accent={(cc.yoy.current_avg_esg ?? 0) >= 70 ? "text-emerald-600" : "text-red-600"}
        />
        <KpiCard
          label="Scored Suppliers"
          value={cc.ceo.total_scored_suppliers}
          sub="with ESG score"
          icon={Globe}
          href="/suppliers"
        />
        <KpiCard
          label="Critical Risk"
          value={cc.ceo.critical_risk_suppliers}
          icon={ShieldAlert}
          href="/risks?risk_level=Critical"
          accent={cc.ceo.critical_risk_suppliers > 0 ? "text-red-600" : ""}
        />
        <KpiCard
          label="Total Emissions"
          value={cc.cso.latest_emissions_tco2e != null ? `${(cc.cso.latest_emissions_tco2e / 1000).toFixed(1)}k` : "—"}
          sub="tCO₂e latest year"
          icon={Leaf}
          href="/sustainability/carbon"
          accent={cc.cso.latest_emissions_tco2e != null && cc.cso.latest_emissions_tco2e > 100_000 ? "text-red-600" : "text-emerald-600"}
        />
        <KpiCard
          label="Overdue Actions"
          value={cc.ceo.overdue_actions}
          icon={Clock}
          href="/recommendations"
          accent={cc.ceo.overdue_actions > 0 ? "text-red-600" : ""}
        />
        <KpiCard
          label={t("dashboard.criticalFindings")}
          value={cc.cco.open_critical_findings}
          icon={AlertTriangle}
          href="/findings?severity=Critical"
          accent={cc.cco.open_critical_findings > 0 ? "text-red-600" : ""}
        />
      </div>
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
                        ? 0.3 + 0.7 * (count / ps.scored_suppliers)
                        : 0.3,
                    }}
                  />
                  <p className="mt-1 text-lg font-semibold">{count}</p>
                  <p className="text-xs text-muted-foreground">{label}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pending Decisions */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Clock className="h-4 w-4 text-amber-500" />
              {t("exec.pendingDecisions")}
              {cc.pending_decisions_count > 0 && (
                <span className="ml-auto rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">
                  {cc.pending_decisions_count}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <PendingDecisionsPanel decisions={cc.pending_decisions ?? []} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Clock className="h-4 w-4 text-blue-500" />
              Upcoming Deadlines
            </CardTitle>
          </CardHeader>
          <CardContent>
            <UpcomingDeadlinesPanel />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function CFOPanel({ cc }: { cc: CommandCenterData }) {
  const { taxonomy_alignment_pct, green_revenue_pct } = cc.cfo;
  const bondEligible = taxonomy_alignment_pct != null && taxonomy_alignment_pct >= 30;
  return (
    <div className="space-y-6">
      {/* #122 4-metric CFO view */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard
          label="EU Taxonomy Alignment"
          value={taxonomy_alignment_pct != null ? `${taxonomy_alignment_pct.toFixed(1)}%` : "—"}
          sub="of revenue aligned"
          icon={BarChart3}
          href="/financial-esg/taxonomy"
          accent={taxonomy_alignment_pct != null && taxonomy_alignment_pct >= 30 ? "text-emerald-600" : "text-amber-600"}
        />
        <KpiCard
          label="Green Revenue"
          value={green_revenue_pct != null ? `${green_revenue_pct.toFixed(1)}%` : "—"}
          sub="share of total revenue"
          icon={Leaf}
          href="/financial-esg/green-revenue"
          accent={green_revenue_pct != null && green_revenue_pct >= 20 ? "text-emerald-600" : "text-slate-600"}
        />
        <KpiCard
          label="Carbon Cost Exposure"
          value={cc.cso.latest_emissions_tco2e != null ? `€${((cc.cso.latest_emissions_tco2e * 0.065) / 1000).toFixed(0)}k` : "—"}
          sub="@ €65/tCO₂e (ETS)"
          icon={Zap}
          href="/financial-esg/carbon-economics"
          accent="text-orange-600"
        />
        <Card className={`${bondEligible ? "border-emerald-200 bg-emerald-50/40" : "border-amber-200 bg-amber-50/40"}`}>
          <CardContent className="pt-5">
            <p className="text-xs text-muted-foreground">ESG Bond Eligibility</p>
            <p className={`mt-1 text-2xl font-bold ${bondEligible ? "text-emerald-600" : "text-amber-600"}`}>
              {bondEligible ? "Eligible" : "Not Yet"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {bondEligible ? "≥30% taxonomy aligned" : `Need ${30 - (taxonomy_alignment_pct ?? 0)}% more`}
            </p>
            <Link href="/financial-esg/taxonomy" className="mt-1 flex items-center gap-0.5 text-[10px] text-muted-foreground">
              View details <ArrowRight className="h-2.5 w-2.5" />
            </Link>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardContent className="py-4 text-sm text-muted-foreground">
          For detailed carbon economics and ESG disclosure packages, visit{" "}
          <Link href="/financial-esg" className="text-blue-600 hover:underline">Financial ESG</Link>{" "}
          and <Link href="/reports" className="text-blue-600 hover:underline">Reports Center</Link>.
        </CardContent>
      </Card>
    </div>
  );
}

function CSOPanel({ cc }: { cc: CommandCenterData }) {
  const { latest_emissions_tco2e, kpi_on_track, kpi_at_risk, kpi_missed } = cc.cso;
  const total = kpi_on_track + kpi_at_risk + kpi_missed;

  const { data: sustDash } = useQuery({
    queryKey: ["sustainability-dashboard-cso"],
    queryFn: async () => { const r = await apiClient.get("/sustainability/dashboard/default"); return r.data; },
    staleTime: 300_000,
  });

  const sbtAlignment = sustDash?.active_sbts != null && sustDash?.total_sbts != null && sustDash.total_sbts > 0
    ? Math.round((sustDash.active_sbts / sustDash.total_sbts) * 100)
    : null;

  return (
    <div className="space-y-6">
      {/* #123 CSO: emissions + SBTi + KPIs + reporting */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard
          label="Total Emissions"
          value={latest_emissions_tco2e != null ? `${(latest_emissions_tco2e / 1000).toFixed(1)}k` : "—"}
          sub="tCO₂e (latest year)"
          icon={Leaf}
          href="/sustainability/carbon"
        />
        <KpiCard
          label="SBTi Alignment"
          value={sbtAlignment != null ? `${sbtAlignment}%` : sustDash?.active_sbts != null ? `${sustDash.active_sbts} active` : "—"}
          sub="science-based targets"
          icon={CheckCircle2}
          href="/sustainability/science-based-targets"
          accent={sbtAlignment != null && sbtAlignment >= 75 ? "text-emerald-600" : "text-amber-600"}
        />
        <KpiCard
          label="KPIs On Track"
          value={kpi_on_track}
          sub={total > 0 ? `${Math.round(kpi_on_track / total * 100)}% on track` : "—"}
          icon={TrendingUp}
          href="/sustainability/kpis"
          accent={kpi_on_track > 0 ? "text-emerald-600" : ""}
        />
        <Card className="border-blue-100 bg-blue-50/30">
          <CardContent className="pt-5">
            <p className="text-xs text-muted-foreground">Reporting Status</p>
            <p className="mt-1 text-xl font-bold text-blue-700">Active</p>
            <p className="mt-1 text-xs text-muted-foreground">TCFD · GRI · CDP</p>
            <Link href="/reports" className="mt-1 flex items-center gap-0.5 text-[10px] text-muted-foreground">
              Generate reports <ArrowRight className="h-2.5 w-2.5" />
            </Link>
          </CardContent>
        </Card>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <CardContent className="py-4 text-sm">
            <Link href="/sustainability/carbon" className="text-blue-600 hover:underline">View Carbon Inventory →</Link>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-sm">
            <Link href="/strategy/pathways" className="text-blue-600 hover:underline">View Transition Pathways →</Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function CCOPanel({ cc }: { cc: CommandCenterData }) {
  const { t } = useLanguage();
  const { soc2_readiness_pct, soc2_implemented, soc2_total, open_critical_findings } = cc.cco;
  const pct = soc2_readiness_pct ?? 0;
  const r = 42;
  const circ = 2 * Math.PI * r;
  const filled = (pct / 100) * circ;
  const ringColor = pct >= 80 ? "stroke-emerald-500" : pct >= 60 ? "stroke-amber-500" : "stroke-red-500";

  return (
    <div className="space-y-6">
      {/* #124 / #135 Prominent audit readiness ring + metrics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Audit readiness ring */}
        <Card className="flex items-center justify-center p-6">
          <div className="flex flex-col items-center gap-2 text-center">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Audit Readiness</p>
            <div className="relative flex h-28 w-28 items-center justify-center">
              <svg viewBox="0 0 100 100" className="h-28 w-28 -rotate-90">
                <circle cx="50" cy="50" r={r} fill="none" strokeWidth="9" className="stroke-muted" />
                <circle cx="50" cy="50" r={r} fill="none" strokeWidth="9"
                  strokeDasharray={`${filled} ${circ}`}
                  className={`transition-all ${ringColor}`}
                  strokeLinecap="round" />
              </svg>
              <div className="absolute text-center">
                <p className="text-2xl font-bold tabular-nums">{pct.toFixed(0)}</p>
                <p className="text-[10px] text-muted-foreground">%</p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">{soc2_implemented}/{soc2_total} controls</p>
            <Link href="/compliance/center" className="text-xs text-blue-600 hover:underline">View details →</Link>
          </div>
        </Card>
        <KpiCard
          label={t("dashboard.criticalFindings")}
          value={open_critical_findings}
          sub="require immediate action"
          icon={AlertTriangle}
          href="/findings?severity=Critical"
          accent={open_critical_findings > 0 ? "text-red-600" : ""}
        />
        <Card>
          <CardContent className="pt-6 text-sm">
            <p className="text-muted-foreground mb-2 text-xs font-medium uppercase tracking-wide">Quick Links</p>
            <div className="space-y-1">
              <Link href="/findings" className="block text-blue-600 hover:underline text-xs">Open Findings →</Link>
              <Link href="/reports" className="block text-blue-600 hover:underline text-xs">Regulatory Reports →</Link>
              <Link href="/enterprise/audit" className="block text-blue-600 hover:underline text-xs">Audit Trail →</Link>
              <Link href="/compliance/center" className="block text-blue-600 hover:underline text-xs">Compliance Center →</Link>
            </div>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Clock className="h-4 w-4 text-blue-500" />
            Upcoming Regulatory Deadlines
          </CardTitle>
        </CardHeader>
        <CardContent>
          <UpcomingDeadlinesPanel />
        </CardContent>
      </Card>
    </div>
  );
}

// ── KPI Trend section (shared) ────────────────────────────────────────────────

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
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : !data || data.data_points.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">No trend data yet.</p>
        ) : (
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
                    <td className="py-2 text-right">{fmt(dp.avg_esg_score)}</td>
                    <td className="py-2 text-right">{fmt(dp.avg_risk_score)}</td>
                    <td className="py-2 text-right">{dp.high_risk_count + dp.critical_risk_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── #137 Risk Trend Chart ─────────────────────────────────────────────────────

function RiskTrendChart() {
  const { data, isLoading } = useQuery({
    queryKey: ["executive-kpi-trends-risk", 365],
    queryFn: () => getKPITrends(365),
    staleTime: 300_000,
  });

  const chartData = (data?.data_points ?? []).map((dp) => ({
    month: dp.month,
    "High+Critical": dp.high_risk_count + dp.critical_risk_count,
    Critical: dp.critical_risk_count,
  }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-orange-500" />
          Risk Trend (12 months)
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : chartData.length < 2 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">Not enough trend data yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area type="monotone" dataKey="High+Critical" stroke="#f97316" fill="#fed7aa" strokeWidth={2} />
              <Area type="monotone" dataKey="Critical" stroke="#ef4444" fill="#fecaca" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

// ── #138 Emissions Trend Chart ────────────────────────────────────────────────

function EmissionsTrendChart() {
  const { data, isLoading } = useQuery({
    queryKey: ["executive-emissions-trend"],
    queryFn: async () => {
      const r = await apiClient.get("/sustainability/carbon-inventory/default?limit=12");
      return r.data;
    },
    staleTime: 300_000,
  });

  const inventories = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
  const chartData = inventories
    .slice()
    .sort((a: any, b: any) => a.year - b.year)
    .map((inv: any) => ({
      year: String(inv.year),
      "tCO₂e": Math.round(inv.total_tco2e ?? 0),
    }));

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Leaf className="h-4 w-4 text-emerald-500" />
          Emissions Trend
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : chartData.length < 2 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">No multi-year inventory data yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="year" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Line type="monotone" dataKey="tCO₂e" stroke="#22c55e" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

// ── Risk Register preview (shared) ───────────────────────────────────────────

function RiskRegisterPreview() {
  const { data, isLoading } = useQuery({
    queryKey: ["executive-risk-register-preview"],
    queryFn: () => getRiskRegister({ limit: 8, sort_by: "risk_score" }),
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base">Top Risk Suppliers</CardTitle>
        <Link href="/suppliers" className="text-xs text-blue-600 hover:underline">View all →</Link>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-6"><Spinner /></div>
        ) : !data || data.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">No scored suppliers yet.</p>
        ) : (
          <div className="space-y-2">
            {data.map((e) => (
              <Link
                key={e.supplier_id}
                href={`/suppliers/${e.supplier_id}`}
                className="flex items-center justify-between rounded-lg border px-3 py-2 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="w-5 text-center text-xs font-mono text-muted-foreground">{e.rank}</span>
                  <div>
                    <p className="text-sm font-medium">{e.supplier_name}</p>
                    <p className="text-xs text-muted-foreground">{e.country} · {e.industry}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {trendIcon(e.trend)}
                  <span className="text-sm font-mono">{fmt(e.risk_score)}</span>
                  <span className={`rounded px-2 py-0.5 text-xs font-medium ${bandColor(e.risk_band)}`}>
                    {e.risk_band}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Heatmap (shared) ──────────────────────────────────────────────────────────

function HeatmapPreview() {
  const { t } = useLanguage();
  const [view, setView] = useState<"country" | "sector" | "tier">("sector");
  const { data, isLoading } = useQuery({
    queryKey: ["executive-heatmap-preview", view],
    queryFn: () => getExecutiveHeatmap(view),
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base">{t("dashboard.riskHeatmap")}</CardTitle>
        <div className="flex gap-1">
          {(["country", "sector", "tier"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`rounded px-2 py-1 text-xs font-medium capitalize transition-colors ${
                view === v ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-6"><Spinner /></div>
        ) : !data || data.buckets.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">No data available.</p>
        ) : (
          <div className="space-y-2">
            {data.buckets.slice(0, 8).map((b) => {
              const filterParam = view === "country"
                ? `country=${encodeURIComponent(b.label)}`
                : view === "sector"
                ? `industry=${encodeURIComponent(b.label)}`
                : `tier=${encodeURIComponent(b.label)}`;
              return (
                <Link
                  key={b.label}
                  href={`/suppliers?${filterParam}`}
                  className="flex items-center gap-3 rounded-md px-2 py-1 hover:bg-muted/40 transition-colors -mx-2"
                >
                  <p className="w-32 truncate text-sm font-medium">{b.label}</p>
                  <div className="flex-1">
                    <div className="h-2 rounded-full bg-slate-100">
                      <div className="h-2 rounded-full bg-orange-400" style={{ width: `${Math.min(100, b.avg_risk_score)}%` }} />
                    </div>
                  </div>
                  <span className="w-10 text-right text-xs font-mono text-muted-foreground">{b.avg_risk_score.toFixed(0)}</span>
                  <span className="w-16 text-right text-xs text-muted-foreground">{b.supplier_count} supplier{b.supplier_count !== 1 ? "s" : ""}</span>
                </Link>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Action + Governance (shared) ──────────────────────────────────────────────

function ActionGovernanceSection() {
  const { t } = useLanguage();
  const { data: ae } = useQuery({ queryKey: ["executive-action-effectiveness"], queryFn: () => getActionEffectiveness(30) });
  const { data: gov } = useQuery({ queryKey: ["executive-governance-metrics"], queryFn: () => getGovernanceMetrics(30) });

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Action Effectiveness (30d)</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-muted-foreground">Open actions</span><span className="font-medium">{ae?.total_open ?? "—"}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">{t("dashboard.overdue")}</span><span className={`font-medium ${(ae?.total_overdue ?? 0) > 0 ? "text-red-600" : ""}`}>{ae?.total_overdue ?? "—"}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Closed this period</span><span className="font-medium">{ae?.closed_this_period ?? "—"}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Resolution rate</span><span className="font-medium">{ae?.resolution_rate != null ? `${(ae.resolution_rate * 100).toFixed(0)}%` : "—"}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Avg resolution</span><span className="font-medium">{ae?.avg_resolution_days != null ? `${ae.avg_resolution_days}d` : "—"}</span></div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Governance Metrics (30d)</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-muted-foreground">Total decisions</span><span className="font-medium">{gov?.total_review_decisions ?? "—"}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Approved</span><span className="font-medium text-emerald-600">{gov?.approved ?? "—"}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Rejected</span><span className="font-medium text-red-600">{gov?.rejected ?? "—"}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Approval rate</span><span className="font-medium">{gov?.approval_rate != null ? `${(gov.approval_rate * 100).toFixed(0)}%` : "—"}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Avg review time</span><span className="font-medium">{gov?.avg_review_days != null ? `${gov.avg_review_days}d` : "—"}</span></div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

const PERSONAS: { id: Persona; label: string; icon: React.ElementType }[] = [
  { id: "CEO", label: "CEO", icon: Zap },
  { id: "CFO", label: "CFO", icon: BarChart3 },
  { id: "CSO", label: "CSO", icon: Leaf },
  { id: "CCO", label: "CCO", icon: Shield },
];

export default function ExecutiveDashboardPage() {
  const { t } = useLanguage();
  const [persona, setPersona] = useState<Persona>("CEO");

  const { data: cc, isLoading: ccLoading } = useQuery({
    queryKey: ["executive-command-center"],
    queryFn: getCommandCenter,
    staleTime: 60_000,
  });

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["executive-dashboard"],
    queryFn: getExecutiveDashboard,
  });

  const isLoading = ccLoading || dashLoading;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{t("exec.commandCenter")}</h1>
          <p className="text-sm text-muted-foreground">
            Board-level ESG portfolio intelligence
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/reports"
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium hover:bg-muted transition-colors"
          >
            Reports Center →
          </Link>
          <Link
            href="/executive/reports"
            className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            Board Reports →
          </Link>
          {/* #116 Generate Board Pack */}
          <Link
            href="/executive/reports"
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 transition-colors shadow-sm"
          >
            <BookOpen className="h-4 w-4" />
            Generate Board Pack
          </Link>
        </div>
      </div>

      {/* #140 Executive alert banner */}
      {cc && <ExecutiveAlertBanner actions={cc.priority_actions} />}

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : (
        <>
          {/* ── Command Center Top Row ─────────────────────────────────────── */}
          {cc && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              {/* ESG Health Score */}
              <Card className="flex items-center justify-center p-6">
                <div className="flex flex-col items-center gap-3 text-center">
                  <p className="text-sm font-medium text-muted-foreground">{t("exec.esgHealth")}</p>
                  <HealthScoreRing score={cc.esg_health_score} label={cc.health_label} />
                  {cc.yoy.avg_esg_delta != null && (
                    <p className={`text-xs font-medium ${cc.yoy.avg_esg_delta >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {cc.yoy.avg_esg_delta >= 0 ? "+" : ""}{cc.yoy.avg_esg_delta.toFixed(1)} avg ESG vs. prior year
                    </p>
                  )}
                </div>
              </Card>

              {/* Priority Actions */}
              <Card className="lg:col-span-2">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                    {t("exec.priorityActions")}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <PriorityActionsPanel actions={cc.priority_actions} />
                </CardContent>
              </Card>
            </div>
          )}

          {/* ── Persona selector ──────────────────────────────────────────── */}
          <div className="flex gap-2 border-b border-border pb-4">
            {PERSONAS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setPersona(id)}
                className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                  persona === id
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
            <div className="flex-1" />
            <span className="self-center text-xs text-muted-foreground">
              {persona === "CEO" ? `${t("exec.ceo")} view`
               : persona === "CFO" ? `${t("exec.cfo")} view`
               : persona === "CSO" ? `${t("exec.cso")} view`
               : `${t("exec.cco")} view`}
            </span>
          </div>

          {/* ── Persona-specific metrics ──────────────────────────────────── */}
          {cc && (
            persona === "CEO" ? <CEOPanel cc={cc} dashboard={dashboard} />
            : persona === "CFO" ? <CFOPanel cc={cc} />
            : persona === "CSO" ? <CSOPanel cc={cc} />
            : <CCOPanel cc={cc} />
          )}

          {/* ── #137 #138 Trend charts ────────────────────────────────────── */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <RiskTrendChart />
            <EmissionsTrendChart />
          </div>

          {/* ── Shared analytics (always visible) ────────────────────────── */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <KPITrendSection />
            <HeatmapPreview />
          </div>

          <RiskRegisterPreview />
          <ActionGovernanceSection />
        </>
      )}
    </div>
  );
}
