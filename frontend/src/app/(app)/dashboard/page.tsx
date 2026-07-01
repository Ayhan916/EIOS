"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Briefcase,
  CheckCircle2,
  Clock,
  DollarSign,
  FileText,
  Flame,
  GitPullRequest,
  Leaf,
  ListChecks,
  Plus,
  Radio,
  ShieldAlert,
  ShieldCheck,
  Target,
  TrendingUp,
  Zap,
} from "lucide-react";
import type { TranslationKey } from "@/lib/i18n/context";
import { useLanguage } from "@/lib/i18n/context";

// ── #108 Onboarding checklist ─────────────────────────────────────────────────

const SETUP_TASK_KEY = "eios_setup_tasks";

const CHECKLIST_ITEMS: Array<{ key: string; labelKey: TranslationKey; href: string }> = [
  { key: "added_supplier",         labelKey: "dashboard.addSupplier",          href: "/suppliers" },
  { key: "ran_assessment",         labelKey: "dashboard.runAssessment",         href: "/assessments/new" },
  { key: "reviewed_finding",       labelKey: "dashboard.reviewFinding",         href: "/findings" },
  { key: "configured_integration", labelKey: "dashboard.configureIntegration",  href: "/settings/integrations" },
  { key: "set_objective",          labelKey: "dashboard.setObjective",           href: "/sustainability/objectives" },
  { key: "uploaded_evidence",      labelKey: "dashboard.uploadEvidence",         href: "/evidence" },
  { key: "set_notifications",      labelKey: "dashboard.setNotifications",       href: "/settings/notifications" },
  { key: "viewed_reports",         labelKey: "dashboard.viewReports",            href: "/reports" },
];

function OnboardingChecklist() {
  const { t } = useLanguage();
  const [done, setDone] = useState<Set<string>>(new Set());
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = localStorage.getItem(SETUP_TASK_KEY);
      setDone(new Set(raw ? JSON.parse(raw) : []));
      if (localStorage.getItem("eios_checklist_dismissed")) setDismissed(true);
    } catch { /* ignore */ }
  }, []);

  function markDone(key: string) {
    setDone((prev) => {
      const next = new Set(prev);
      next.add(key);
      localStorage.setItem(SETUP_TASK_KEY, JSON.stringify([...next]));
      return next;
    });
  }

  function dismiss() {
    localStorage.setItem("eios_checklist_dismissed", "1");
    setDismissed(true);
  }

  const completedCount = CHECKLIST_ITEMS.filter((i) => done.has(i.key)).length;
  if (dismissed || completedCount === CHECKLIST_ITEMS.length) return null;
  const pct = Math.round((completedCount / CHECKLIST_ITEMS.length) * 100);

  return (
    <Card className="border-blue-200 bg-blue-50/40">
      <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-base flex items-center gap-2">
            <ListChecks className="h-4 w-4 text-blue-600" />
            {t("dashboard.gettingStartedTitle")}
          </CardTitle>
          <p className="text-xs text-muted-foreground mt-0.5">
            {completedCount} {t("common.of")} {CHECKLIST_ITEMS.length} {t("dashboard.tasksComplete")} · {pct}%
          </p>
        </div>
        <button onClick={dismiss} className="text-xs text-muted-foreground hover:text-foreground">
          {t("dashboard.dismiss")}
        </button>
      </CardHeader>
      <CardContent>
        <div className="mb-3 h-1.5 rounded-full bg-blue-100 overflow-hidden">
          <div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${pct}%` }} />
        </div>
        <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
          {CHECKLIST_ITEMS.map((item) => {
            const isChecked = done.has(item.key);
            return (
              <div key={item.key} className="flex items-center gap-2">
                <button
                  onClick={() => markDone(item.key)}
                  className={`flex h-4 w-4 flex-shrink-0 items-center justify-center rounded border transition-colors ${
                    isChecked ? "border-blue-500 bg-blue-500" : "border-slate-300 bg-white"
                  }`}
                  aria-label={isChecked ? t("common.confirm") : t("common.confirm")}
                >
                  {isChecked && <CheckCircle2 className="h-3 w-3 text-white" />}
                </button>
                <Link
                  href={item.href}
                  onClick={() => markDone(item.key)}
                  className={`text-sm hover:underline ${isChecked ? "text-muted-foreground line-through" : "text-foreground"}`}
                >
                  {t(item.labelKey)}
                </Link>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
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

// ── Risk Heatmap Widget ───────────────────────────────────────────────────────

function RiskHeatmapCard({ risks }: { risks: Array<{ risk_level: string }> }) {
  const router = useRouter();
  const { t } = useLanguage();
  const counts: Record<string, number> = { Critical: 0, High: 0, Medium: 0, Low: 0 };
  for (const r of risks) {
    if (r.risk_level in counts) counts[r.risk_level]++;
  }

  type Cell = { label: string; riskLevel: string; count: number; bg: string; text: string } | null;
  const grid: Cell[][] = [
    [null, null, { label: t("findings.critical"), riskLevel: "Critical", count: counts.Critical, bg: "bg-red-500 hover:bg-red-600", text: "text-white" }],
    [null, { label: t("findings.medium"), riskLevel: "Medium", count: counts.Medium, bg: "bg-amber-400 hover:bg-amber-500", text: "text-white" }, { label: t("findings.high"), riskLevel: "High", count: counts.High, bg: "bg-orange-500 hover:bg-orange-600", text: "text-white" }],
    [{ label: t("findings.low"), riskLevel: "Low", count: counts.Low, bg: "bg-emerald-500 hover:bg-emerald-600", text: "text-white" }, null, null],
  ];
  const rowLabels = [t("findings.high"), t("findings.medium"), t("findings.low")];
  const colLabels = [t("dashboard.lowImpact"), t("dashboard.mediumImpact"), t("dashboard.highImpact")];
  const total = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <Card>
      <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-base flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-orange-500" />
            {t("dashboard.riskHeatmap")}
          </CardTitle>
          <CardDescription>{total} {t("dashboard.risksClickFilter")}</CardDescription>
        </div>
        <button
          onClick={() => router.push("/risks")}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {t("dashboard.viewAll")} <ArrowRight className="h-3 w-3" />
        </button>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <div className="min-w-[320px]">
            <div className="flex mb-1 pl-16">
              {colLabels.map((c) => (
                <div key={c} className="flex-1 text-center text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
                  {c}
                </div>
              ))}
            </div>
            {grid.map((row, ri) => (
              <div key={ri} className="flex items-center mb-1">
                <div className="w-16 text-[10px] font-semibold text-muted-foreground uppercase tracking-wide flex-shrink-0 text-right pr-2">
                  {rowLabels[ri]}
                </div>
                {row.map((cell, ci) =>
                  cell ? (
                    <button
                      key={ci}
                      onClick={() => router.push(`/risks?risk_level=${cell.riskLevel}`)}
                      className={`flex-1 mx-0.5 h-14 rounded-lg ${cell.bg} ${cell.text} transition-colors flex flex-col items-center justify-center cursor-pointer`}
                    >
                      <span className="text-xl font-bold leading-none">{cell.count}</span>
                      <span className="text-[10px] font-medium mt-0.5 opacity-90">{cell.label}</span>
                    </button>
                  ) : (
                    <div key={ci} className="flex-1 mx-0.5 h-14 rounded-lg bg-muted/30 border border-dashed border-muted-foreground/20" />
                  )
                )}
              </div>
            ))}
            <div className="text-center text-[10px] text-muted-foreground mt-1 pl-16">
              {t("dashboard.impactAxis")}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Compliance Gap Widget ─────────────────────────────────────────────────────

function ComplianceGapCard({ readiness }: { readiness: Record<string, number> }) {
  const { t } = useLanguage();
  const entries = Object.entries(readiness).sort((a, b) => a[1] - b[1]);
  if (entries.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-base flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-blue-500" />
            {t("dashboard.complianceCoverage")}
          </CardTitle>
          <CardDescription>{t("dashboard.frameworkCoverage")}</CardDescription>
        </div>
        <Link href="/operating-system/compliance-operations" className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
          {t("common.details")} <ArrowRight className="h-3 w-3" />
        </Link>
      </CardHeader>
      <CardContent className="space-y-3">
        {entries.map(([framework, pct]) => {
          const color = pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-400" : "bg-red-500";
          const textColor = pct >= 80 ? "text-emerald-600" : pct >= 50 ? "text-amber-600" : "text-red-600";
          return (
            <div key={framework}>
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs font-medium">{framework}</span>
                <span className={`text-xs font-bold ${textColor}`}>{Math.round(pct)}%</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${Math.min(pct, 100)}%` }} />
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

// ── Financial ESG Widget ──────────────────────────────────────────────────────

interface FinancialTile {
  label: string;
  value: string;
  icon: React.ElementType;
  colorClass: string;
  href: string;
}

function FinancialEsgCard({
  taxonomyPct,
  greenRevenuePct,
  carbonCost,
}: {
  taxonomyPct: number | null;
  greenRevenuePct: number | null;
  carbonCost: number | null;
}) {
  const { t } = useLanguage();
  const tiles: FinancialTile[] = [
    {
      label: t("dashboard.taxonomyAlignment"),
      value: taxonomyPct != null ? `${taxonomyPct.toFixed(1)}%` : "—",
      icon: Leaf,
      colorClass: taxonomyPct != null && taxonomyPct >= 30 ? "text-emerald-600" : "text-amber-600",
      href: "/financial-esg/taxonomy",
    },
    {
      label: t("dashboard.greenRevenue"),
      value: greenRevenuePct != null ? `${greenRevenuePct.toFixed(1)}%` : "—",
      icon: TrendingUp,
      colorClass: greenRevenuePct != null && greenRevenuePct >= 20 ? "text-emerald-600" : "text-slate-600",
      href: "/financial-esg",
    },
    {
      label: t("dashboard.carbonCostExposure"),
      value: carbonCost != null ? `€${(carbonCost / 1000).toFixed(0)}k` : "—",
      icon: Zap,
      colorClass: carbonCost != null && carbonCost > 0 ? "text-orange-600" : "text-slate-600",
      href: "/financial-esg/carbon-economics",
    },
  ];

  return (
    <Card>
      <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-base flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-emerald-600" />
            {t("dashboard.financialEsgTitle")}
          </CardTitle>
          <CardDescription>{t("dashboard.taxonomyGreenCarbon")}</CardDescription>
        </div>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/financial-esg" className="gap-1 text-xs">
            {t("common.details")} <ArrowRight className="h-3 w-3" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          {tiles.map((tile) => (
            <Link key={tile.label} href={tile.href} className="group text-center rounded-lg border p-3 hover:bg-muted/50 transition-colors">
              <tile.icon className={`mx-auto mb-1.5 h-5 w-5 ${tile.colorClass}`} />
              <p className={`text-xl font-bold ${tile.colorClass}`}>{tile.value}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{tile.label}</p>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Pending Decisions Widget ──────────────────────────────────────────────────

interface PendingDecision {
  id: string;
  title: string;
  priority: string;
  due_date: string | null;
}

function PendingDecisionsCard({
  decisions,
  count,
}: {
  decisions: PendingDecision[];
  count: number;
}) {
  const router = useRouter();
  const { t } = useLanguage();
  const priorityBadge = (p: string) => {
    if (p === "Critical") return "bg-red-100 text-red-700";
    if (p === "High") return "bg-orange-100 text-orange-700";
    if (p === "Medium") return "bg-amber-100 text-amber-700";
    return "bg-slate-100 text-slate-600";
  };

  return (
    <Card>
      <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-base flex items-center gap-2">
            <ListChecks className="h-4 w-4 text-blue-500" />
            {t("dashboard.pendingDecisions")}
          </CardTitle>
          <CardDescription>
            {count} {t("dashboard.recommendationsAwaitingAction")}
          </CardDescription>
        </div>
        <button
          onClick={() => router.push("/recommendations")}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {t("dashboard.viewAll")} <ArrowRight className="h-3 w-3" />
        </button>
      </CardHeader>
      <CardContent>
        {decisions.length === 0 ? (
          <div className="py-6 text-center text-sm text-muted-foreground">
            {t("dashboard.noOpenDecisions")}
          </div>
        ) : (
          <div className="space-y-2">
            {decisions.map((d) => (
              <div
                key={d.id}
                className="flex items-start justify-between gap-3 rounded-lg border border-border px-3 py-2.5 hover:bg-muted/40 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{d.title}</p>
                  {d.due_date && (
                    <p className="mt-0.5 text-xs text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {t("dashboard.due")} {formatDate(d.due_date)}
                    </p>
                  )}
                </div>
                <span
                  className={`flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${priorityBadge(d.priority)}`}
                >
                  {d.priority}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── External Signal Feed Widget ───────────────────────────────────────────────

interface RiskSignal {
  id: string;
  signal_type: string;
  severity: string;
  description: string;
  source_name: string;
  observed_at: string;
  supplier_id: string;
  country_code: string;
}

function SignalFeedCard({ signals }: { signals: RiskSignal[] }) {
  const { t } = useLanguage();
  const sevColor: Record<string, string> = {
    Critical: "bg-red-100 text-red-700",
    High: "bg-orange-100 text-orange-700",
    Medium: "bg-amber-100 text-amber-700",
    Low: "bg-slate-100 text-slate-600",
  };

  return (
    <Card>
      <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-base flex items-center gap-2">
            <Radio className="h-4 w-4 text-blue-500 animate-pulse" />
            {t("dashboard.externalRiskSignals")}
          </CardTitle>
          <CardDescription>{signals.length} {t("dashboard.activeSignals")}</CardDescription>
        </div>
        <Link href="/surveillance" className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
          {t("dashboard.viewAll")} <ArrowRight className="h-3 w-3" />
        </Link>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {signals.map((s) => (
            <div
              key={s.id}
              className="flex items-start gap-3 rounded-lg border border-border px-3 py-2.5"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium line-clamp-1">{s.description}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {s.signal_type.replace(/_/g, " ")} · {s.source_name}
                  {s.country_code ? ` · ${s.country_code}` : ""}
                  {" · "}{formatDate(s.observed_at)}
                </p>
              </div>
              <span className={`flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${sevColor[s.severity] ?? "bg-slate-100 text-slate-600"}`}>
                {s.severity}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── #110 Demo data seeder ─────────────────────────────────────────────────────

const DEMO_KEY = "eios_demo_seeded";

function DemoDataButton() {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined" && localStorage.getItem(DEMO_KEY)) setDone(true);
  }, []);

  async function seed() {
    setLoading(true);
    try {
      await apiClient.post("/demo/seed");
      localStorage.setItem(DEMO_KEY, "1");
      setDone(true);
      window.location.reload();
    } catch {
      setLoading(false);
    }
  }

  if (done) return null;

  return (
    <button
      onClick={seed}
      disabled={loading}
      className="flex items-center gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 transition-colors disabled:opacity-50"
    >
      {loading ? (
        <span className="h-3 w-3 rounded-full border border-slate-400 border-t-transparent animate-spin" />
      ) : (
        <Zap className="h-3 w-3" />
      )}
      {loading ? t("dashboard.loadingDemoData") : t("dashboard.loadDemoData")}
    </button>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { user } = useAuth();
  const { t } = useLanguage();

  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
    staleTime: 30_000,
  });

  const { data: cc } = useQuery({
    queryKey: ["command-center-dashboard"],
    queryFn: async () => {
      const res = await apiClient.get("/executive/command-center");
      return res.data;
    },
    staleTime: 300_000,
  });

  const { data: orgRisks } = useQuery({
    queryKey: ["org-risks-heatmap"],
    queryFn: async () => {
      const res = await apiClient.get("/executive/risks?limit=500");
      return res.data as Array<{ risk_level: string }>;
    },
    staleTime: 120_000,
  });

  const { data: riskSignals } = useQuery({
    queryKey: ["dashboard-risk-signals"],
    queryFn: async () => {
      const res = await apiClient.get("/external-intelligence/signals?limit=7");
      return (res.data as { signals: RiskSignal[]; total: number }).signals;
    },
    staleTime: 120_000,
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
        {t("dashboard.failedToLoad")}
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
    ...data.assessments_over_time.map((m: { count: number }) => m.count),
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
            {t("dashboard.welcome")}, {user?.display_name?.split(" ")[0]}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("dashboard.portfolioSubtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DemoDataButton />
          <Button asChild>
            <Link href="/assessments/new">
              <Plus className="h-4 w-4" />
              {t("dashboard.newAssessment")}
            </Link>
          </Button>
        </div>
      </div>

      {/* ── KPI strip ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
        <KpiCard
          label={t("dashboard.totalAssessments")}
          value={data.total_assessments}
          icon={FileText}
          sub={t("dashboard.inYourOrganisation")}
        />
        <KpiCard
          label={t("dashboard.avgQualityScore")}
          value={avgQualityPct}
          icon={TrendingUp}
          valueClass={qualityClass(data.avg_quality_score)}
          sub={t("dashboard.acrossAllAssessments")}
        />
        <KpiCard
          label={t("dashboard.openActionsKpi")}
          value={data.open_actions}
          icon={Clock}
          sub={`${data.closed_actions_pct}% ${t("findings.resolved").toLowerCase()}`}
        />
        <KpiCard
          label={t("dashboard.overdue")}
          value={data.overdue_actions}
          icon={AlertTriangle}
          valueClass={data.overdue_actions > 0 ? "text-red-600" : "text-foreground"}
          accent={data.overdue_actions > 0 ? "bg-red-500" : undefined}
          sub={t("dashboard.pastDueDate")}
        />
        <KpiCard
          label={t("dashboard.highRiskFindings")}
          value={data.high_risk_finding_count + data.critical_finding_count}
          icon={ShieldAlert}
          valueClass={
            data.critical_finding_count > 0 ? "text-red-600" : "text-foreground"
          }
          sub={`${data.critical_finding_count} ${t("findings.critical").toLowerCase()}`}
        />
        <KpiCard
          label={t("dashboard.esgHealth")}
          value={cc ? `${cc.esg_health_score}/100` : "—"}
          icon={Target}
          valueClass={
            !cc ? "text-muted-foreground"
            : cc.esg_health_score >= 80 ? "text-emerald-600"
            : cc.esg_health_score >= 65 ? "text-blue-600"
            : cc.esg_health_score >= 50 ? "text-amber-600"
            : "text-red-600"
          }
          sub={cc?.health_label ?? ""}
        />
        <KpiCard
          label={t("dashboard.carbonIntensity")}
          value={
            cc?.cso?.latest_emissions_tco2e != null
              ? `${cc.cso.latest_emissions_tco2e.toLocaleString()} t`
              : "—"
          }
          icon={Flame}
          valueClass={cc?.cso?.latest_emissions_tco2e != null ? "text-orange-600" : "text-muted-foreground"}
          sub={t("dashboard.tco2eLatestYear")}
        />
      </div>

      {/* #108 Onboarding checklist */}
      <OnboardingChecklist />

      {/* ── Pending Decisions ──────────────────────────────────────────────── */}
      {cc && cc.pending_decisions_count > 0 && (
        <PendingDecisionsCard
          decisions={cc.pending_decisions}
          count={cc.pending_decisions_count}
        />
      )}

      {/* ── Financial ESG summary ──────────────────────────────────────────── */}
      {cc?.cfo && (cc.cfo.taxonomy_alignment_pct != null || cc.cfo.green_revenue_pct != null) && (
        <FinancialEsgCard
          taxonomyPct={cc.cfo.taxonomy_alignment_pct}
          greenRevenuePct={cc.cfo.green_revenue_pct}
          carbonCost={null}
        />
      )}

      {/* ── Risk Heatmap + Compliance Gap ─────────────────────────────────── */}
      {orgRisks && orgRisks.length > 0 && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <RiskHeatmapCard risks={orgRisks} />
          {cc?.esg_summary?.compliance_readiness && Object.keys(cc.esg_summary.compliance_readiness).length > 0 && (
            <ComplianceGapCard readiness={cc.esg_summary.compliance_readiness} />
          )}
        </div>
      )}

      {/* ── Middle row: Action breakdown + Findings breakdown ──────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Action status breakdown */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">{t("dashboard.actionStatus")}</CardTitle>
            <CardDescription>{t("dashboard.recommendationLifecycle")}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              {[
                { key: "open",        label: t("findings.open"),       cls: "bg-slate-100 text-slate-700" },
                { key: "in_progress", label: t("findings.inProgress"), cls: "bg-blue-100 text-blue-700" },
                { key: "resolved",    label: t("findings.resolved"),   cls: "bg-amber-100 text-amber-700" },
                { key: "verified",    label: t("findings.verified"),   cls: "bg-emerald-100 text-emerald-700" },
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
                  <span>{t("dashboard.closureRate")}</span>
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
            <CardTitle className="text-base">{t("dashboard.findingsBreakdown")}</CardTitle>
            <CardDescription>
              {totalFindings} {t("dashboard.totalFindingsDesc")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                {t("dashboard.bySeverity")}
              </p>
              <div className="space-y-2">
                <HBar label={t("findings.critical")} count={data.findings_by_severity["Critical"] ?? 0} max={maxSeverity} colorClass="bg-red-500" />
                <HBar label={t("findings.high")}     count={data.findings_by_severity["High"] ?? 0}     max={maxSeverity} colorClass="bg-orange-400" />
                <HBar label={t("findings.medium")}   count={data.findings_by_severity["Medium"] ?? 0}   max={maxSeverity} colorClass="bg-amber-400" />
                <HBar label={t("findings.low")}      count={data.findings_by_severity["Low"] ?? 0}      max={maxSeverity} colorClass="bg-slate-300" />
              </div>
            </div>
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                {t("dashboard.byEsgCategory")}
              </p>
              <div className="space-y-2">
                <HBar label={t("dashboard.environmental")} count={data.findings_by_category["E"] ?? 0}     max={maxCategory} colorClass="bg-emerald-500" />
                <HBar label={t("dashboard.social")}        count={data.findings_by_category["S"] ?? 0}     max={maxCategory} colorClass="bg-blue-500" />
                <HBar label={t("dashboard.governance")}    count={data.findings_by_category["G"] ?? 0}     max={maxCategory} colorClass="bg-purple-500" />
                {(data.findings_by_category["Other"] ?? 0) > 0 && (
                  <HBar label={t("materials.other")} count={data.findings_by_category["Other"]} max={maxCategory} colorClass="bg-slate-400" />
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Review Queue ───────────────────────────────────────────────────── */}
      {(data.awaiting_review > 0 || data.reviews_overdue > 0) && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                <GitPullRequest className="h-4 w-4 text-blue-500" />
                {t("dashboard.reviewQueue")}
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("dashboard.reviewQueueDesc")}
              </p>
            </div>
            <div className="flex items-center gap-3">
              {data.awaiting_review > 0 && (
                <span className="rounded-full bg-blue-100 text-blue-700 px-3 py-0.5 text-xs font-semibold">
                  {data.awaiting_review} {t("dashboard.awaitingReview")}
                </span>
              )}
              {data.reviews_overdue > 0 && (
                <span className="rounded-full bg-red-100 text-red-700 px-3 py-0.5 text-xs font-semibold">
                  {data.reviews_overdue} {t("dashboard.overdueReview")}
                </span>
              )}
            </div>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {data.review_queue.map((item: { id: string; title: string; review_status: string; review_due_date: string | null; is_overdue: boolean }) => (
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
                    {item.review_status === "InReview" ? t("dashboard.inReview") : t("dashboard.changesRequested")}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3 flex-shrink-0" />
                  {item.review_due_date ? (
                    <span className={item.is_overdue ? "text-red-600 font-medium" : ""}>
                      {t("dashboard.due")} {formatDate(item.review_due_date)}
                      {item.is_overdue && ` · ${t("dashboard.overdueLabel")}`}
                    </span>
                  ) : (
                    <span>{t("dashboard.noDueDate")}</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* ── Supplier Portfolio ─────────────────────────────────────────────── */}
      {data.total_suppliers > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                <Briefcase className="h-4 w-4 text-blue-500" />
                {t("dashboard.supplierPortfolio")}
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {t("dashboard.supplierPortfolioDesc")}
              </p>
            </div>
            <Link href="/suppliers">
              <Button variant="ghost" size="sm" className="gap-1 text-xs">
                {t("dashboard.viewAll")} <ArrowRight className="h-3 w-3" />
              </Button>
            </Link>
          </div>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <KpiCard
              label={t("suppliers.title")}
              value={data.total_suppliers}
              icon={Briefcase}
              sub={`${data.active_suppliers} ${t("common.active").toLowerCase()}`}
            />
            <KpiCard
              label={t("dashboard.withCriticalRisks")}
              value={data.suppliers_with_critical_risks}
              icon={ShieldAlert}
              valueClass={data.suppliers_with_critical_risks > 0 ? "text-red-600" : "text-foreground"}
              accent={data.suppliers_with_critical_risks > 0 ? "bg-red-500" : undefined}
              sub={t("dashboard.haveCriticalFindings")}
            />
            <KpiCard
              label={t("dashboard.suppliersNoAssessments")}
              value={data.suppliers_without_assessments}
              icon={AlertTriangle}
              valueClass={data.suppliers_without_assessments > 0 ? "text-amber-600" : "text-foreground"}
              sub={t("dashboard.needFirstAssessment")}
            />
            <KpiCard
              label={t("common.active")}
              value={data.active_suppliers}
              icon={CheckCircle2}
              valueClass="text-emerald-600"
              sub={t("dashboard.suppliersInScope")}
            />
          </div>

          {data.supplier_watchlist.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">{t("dashboard.supplierWatchlist")}</CardTitle>
                <p className="text-xs text-muted-foreground">{t("dashboard.rankedByCritical")}</p>
              </CardHeader>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/30">
                      <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">{t("assessments.supplier")}</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">{t("common.country")}</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">{t("suppliers.tier")}</th>
                      <th className="px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">{t("findings.critical")}</th>
                      <th className="px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">{t("findings.high")}</th>
                      <th className="px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">{t("dashboard.colOpenActions")}</th>
                      <th className="px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">{t("dashboard.overdue")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.supplier_watchlist.map((s: { id: string; name: string; country: string; supplier_tier: string; critical_findings: number; high_findings: number; open_actions: number; overdue_actions: number }) => (
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

      {/* ── External Risk Signals ──────────────────────────────────────────── */}
      {riskSignals && riskSignals.length > 0 && (
        <SignalFeedCard signals={riskSignals} />
      )}

      {/* ── Bottom row: Recent assessments + Timeline ──────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Recent assessments — 2/3 width */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
            <div>
              <CardTitle className="text-base">{t("dashboard.recentAssessments")}</CardTitle>
              <CardDescription>{t("dashboard.latestEsgEvaluations")}</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/assessments" className="gap-1 text-xs">
                {t("dashboard.viewAll")} <ArrowRight className="h-3 w-3" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {!data.recent_assessments.length ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                {t("dashboard.noAssessmentsYet")}{" "}
                <Link href="/assessments/new" className="text-primary underline">
                  {t("dashboard.runFirstAssessment")}
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
                            <span>{a.finding_count} {t("dashboard.findingsLabel")}</span>
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
            <CardTitle className="text-base">{t("dashboard.assessmentVolume")}</CardTitle>
            <CardDescription>{t("dashboard.assessmentsPerMonth")}</CardDescription>
          </CardHeader>
          <CardContent>
            {!data.assessments_over_time.length ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                {t("dashboard.noTimelineData")}
              </p>
            ) : (
              <div className="space-y-2">
                {data.assessments_over_time.map((m: { month: string; count: number }) => (
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
