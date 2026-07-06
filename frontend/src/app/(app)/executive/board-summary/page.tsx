"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock,
  Leaf,
  Shield,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import Link from "next/link";
import { useLanguage } from "@/lib/i18n/context";
import { getCommandCenter } from "@/lib/api/executive";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

// ── #125 Board Summary — condensed 5-metric view ──────────────────────────────

function MetricPillar({
  icon: Icon,
  label,
  value,
  sub,
  status,
  href,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  status: "green" | "amber" | "red" | "neutral";
  href: string;
}) {
  const { t } = useLanguage();
  const statusBar: Record<string, string> = {
    green:   "bg-emerald-500",
    amber:   "bg-amber-400",
    red:     "bg-red-500",
    neutral: "bg-slate-300",
  };
  const statusText: Record<string, string> = {
    green:   "text-emerald-600",
    amber:   "text-amber-600",
    red:     "text-red-600",
    neutral: "text-slate-500",
  };
  const statusBg: Record<string, string> = {
    green:   "bg-emerald-50 border-emerald-100",
    amber:   "bg-amber-50 border-amber-100",
    red:     "bg-red-50 border-red-100",
    neutral: "bg-slate-50 border-slate-100",
  };

  return (
    <Link href={href} className="group block">
      <Card className={`border ${statusBg[status]} hover:shadow-md transition-all`}>
        <CardContent className="pt-6 pb-5">
          <div className={`mb-4 h-1.5 rounded-full ${statusBar[status]}`} />
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-white p-2 shadow-sm">
              <Icon className="h-5 w-5 text-slate-600" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
              <p className={`mt-1 text-4xl font-bold tabular-nums ${statusText[status]}`}>{value}</p>
              {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
            </div>
          </div>
          <p className="mt-3 text-xs text-muted-foreground group-hover:text-foreground transition-colors">
            {t("exec.viewDetails")} →
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}

export default function BoardSummaryPage() {
  const { t } = useLanguage();
  const { data: cc, isLoading } = useQuery({
    queryKey: ["executive-command-center"],
    queryFn: getCommandCenter,
    staleTime: 60_000,
  });

  return (
    <div className="min-h-screen bg-slate-50 p-8 print:p-4">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">{t("exec.boardSummaryTitle")}</p>
          <h1 className="mt-1 text-3xl font-bold text-slate-900">{t("exec.esgPortfolioOverview")}</h1>
          <p className="mt-1 text-sm text-slate-500">{t("exec.condensedBoardView")} · {new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" })}</p>
        </div>
        <div className="flex gap-2 print:hidden">
          <button
            onClick={() => window.print()}
            className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
          >
            {t("exec.printPdf")}
          </button>
          <Link
            href="/executive"
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            {t("exec.fullDashboard")} →
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : !cc ? (
        <p className="text-center text-muted-foreground py-20">{t("exec.noExecutiveData")}</p>
      ) : (
        <>
          {/* ── 5 pillars ────────────────────────────────────────────────── */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-5">
            <MetricPillar
              icon={ShieldAlert}
              label={t("exec.pillarRisk")}
              value={cc.ceo.critical_risk_suppliers}
              sub={t("exec.criticalRiskSuppliersCount")}
              status={cc.ceo.critical_risk_suppliers === 0 ? "green" : cc.ceo.critical_risk_suppliers <= 3 ? "amber" : "red"}
              href="/risks?risk_level=Critical"
            />
            <MetricPillar
              icon={TrendingUp}
              label={t("exec.pillarEsgScore")}
              value={cc.yoy.current_avg_esg != null ? `${cc.yoy.current_avg_esg.toFixed(0)}` : "—"}
              sub={cc.yoy.avg_esg_delta != null ? `${cc.yoy.avg_esg_delta >= 0 ? "+" : ""}${cc.yoy.avg_esg_delta.toFixed(1)} YoY` : t("exec.avgAcrossPortfolio")}
              status={cc.yoy.current_avg_esg != null ? (cc.yoy.current_avg_esg >= 70 ? "green" : cc.yoy.current_avg_esg >= 50 ? "amber" : "red") : "neutral"}
              href="/suppliers"
            />
            <MetricPillar
              icon={Shield}
              label={t("exec.pillarCompliance")}
              value={cc.cco.soc2_readiness_pct != null ? `${cc.cco.soc2_readiness_pct.toFixed(0)}%` : "—"}
              sub={t("exec.soc2Readiness")}
              status={cc.cco.soc2_readiness_pct != null ? (cc.cco.soc2_readiness_pct >= 80 ? "green" : cc.cco.soc2_readiness_pct >= 60 ? "amber" : "red") : "neutral"}
              href="/compliance/center"
            />
            <MetricPillar
              icon={Leaf}
              label={t("exec.pillarStrategy")}
              value={cc.cso.kpi_on_track}
              sub={t("exec.kpisOnTrackSub")}
              status={cc.cso.kpi_missed > 0 ? "amber" : cc.cso.kpi_on_track > 0 ? "green" : "neutral"}
              href="/strategy"
            />
            <MetricPillar
              icon={Clock}
              label={t("exec.pillarDecisions")}
              value={cc.pending_decisions_count}
              sub={t("exec.pendingApproval")}
              status={cc.pending_decisions_count === 0 ? "green" : cc.pending_decisions_count <= 3 ? "amber" : "red"}
              href="/recommendations"
            />
          </div>

          {/* ── ESG Health Score ──────────────────────────────────────────── */}
          <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t("exec.overallEsgHealth")}</p>
                <p className={`mt-1 text-5xl font-bold tabular-nums ${
                  cc.esg_health_score >= 80 ? "text-emerald-600"
                  : cc.esg_health_score >= 65 ? "text-blue-600"
                  : cc.esg_health_score >= 50 ? "text-amber-600"
                  : "text-red-600"
                }`}>{cc.esg_health_score}<span className="text-2xl font-medium text-muted-foreground">/100</span></p>
                <p className="mt-1 text-sm text-muted-foreground">{cc.health_label}</p>
              </div>
              <div className="text-right space-y-1">
                <div className="flex items-center gap-2 justify-end text-sm">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <span>{t("exec.scoredSuppliersCount").replace("{n}", String(cc.ceo.total_scored_suppliers))}</span>
                </div>
                <div className="flex items-center gap-2 justify-end text-sm">
                  <BarChart3 className="h-4 w-4 text-blue-500" />
                  <span>{t("exec.taxonomyAlignedPct").replace("{n}", cc.cfo.taxonomy_alignment_pct?.toFixed(1) ?? "—")}</span>
                </div>
                <div className="flex items-center gap-2 justify-end text-sm">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  <span>{t("exec.criticalFindingsOpen").replace("{n}", String(cc.cco.open_critical_findings))}</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
