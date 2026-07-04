"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import apiClient from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import Link from "next/link";
import {
  ChevronDown,
  ChevronRight,
  Download,
  FileText,
  AlertTriangle,
  CheckCircle,
  Clock,
  Search,
  Users,
  Shield,
  Leaf,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface KPI {
  total_suppliers: number;
  critical_suppliers: number;
  high_risk_suppliers: number;
  unresolved_hr_risks: number;
  unresolved_env_risks: number;
  overdue_actions: number;
  open_actions: number;
  remediation_completion_pct: number;
  avg_esg_score: number;
  avg_risk_score: number;
  reports_generated: number;
}

interface SupplierSummary {
  supplier_id: string;
  supplier_name: string;
  country: string;
  tier: string;
  risk_band: string;
  esg_score: number;
  risk_score: number;
  trend: string;
  critical_findings: number;
  high_findings: number;
  open_actions: number;
  overdue_actions: number;
  hr_findings: number;
  env_findings: number;
}

interface HRTopicSummary {
  topic: string;
  display_name: string;
  finding_count: number;
  critical_findings: number;
  risk_count: number;
  unresolved_risks: number;
  suppliers_impacted: number;
}

interface HRReport {
  total_hr_findings: number;
  total_hr_risks: number;
  suppliers_impacted: number;
  open_remediation_actions: number;
  overdue_actions: number;
  resolved_actions: number;
  by_topic: HRTopicSummary[];
}

interface EnvTopicSummary {
  topic: string;
  display_name: string;
  finding_count: number;
  critical_findings: number;
  risk_count: number;
  unresolved_risks: number;
  suppliers_impacted: number;
}

interface EnvReport {
  total_env_findings: number;
  total_env_risks: number;
  unresolved_risks: number;
  suppliers_impacted: number;
  mitigation_controls: number;
  effective_controls: number;
  by_topic: EnvTopicSummary[];
}

interface RemediationReport {
  total: number;
  open: number;
  in_progress: number;
  completed: number;
  overdue: number;
  closure_rate: number;
  avg_resolution_days: number | null;
  by_priority: Record<string, number>;
  top_overdue: Array<{ title: string; priority: string; overdue_days?: number }>;
}

interface PreventiveMeasuresReport {
  total_controls: number;
  preventive: number;
  detective: number;
  corrective: number;
  by_category: Array<{
    category: string;
    total: number;
    effective: number;
    measures: Array<{ id: string; title: string; control_type: string; effectiveness_status: string }>;
  }>;
}

interface ReportSummary {
  id: string;
  report_type: string;
  framework: string;
  framework_version: string;
  generated_at: string;
  generated_by: string;
  status: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const API_BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1`;

async function downloadPdf(reportId: string, filename: string) {
  const token = typeof window !== "undefined" ? localStorage.getItem("eios_access_token") : null;
  const res = await fetch(`${API_BASE}/due-diligence/reports/${reportId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

const RISK_BAND_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-green-100 text-green-700",
};

function RiskBadge({ band }: { band: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${RISK_BAND_COLORS[band] ?? "bg-slate-100 text-slate-500"}`}>
      {band}
    </span>
  );
}

function ScoreBar({ value, max = 1 }: { value: number; max?: number }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const color = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-amber-400" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 rounded-full bg-slate-100">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-500">{(value * 100).toFixed(0)}%</span>
    </div>
  );
}

// ── KPI Dashboard ─────────────────────────────────────────────────────────────

function DashboardTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";

  const { data: kpi, isLoading } = useQuery<KPI>({
    queryKey: ["dd", "kpi", orgId],
    queryFn: async () => (await apiClient.get("/due-diligence/dashboard")).data,
    staleTime: 60_000,
    enabled: !!orgId,
  });

  if (isLoading) return <div className="flex h-40 items-center justify-center"><Spinner /></div>;
  if (!kpi) return null;

  const kpiCards = [
    { label: t("dd.totalSuppliers"), value: kpi.total_suppliers, icon: Users, color: "text-blue-600 bg-blue-50" },
    { label: t("dd.criticalSuppliers"), value: kpi.critical_suppliers, icon: AlertTriangle, color: "text-red-600 bg-red-50" },
    { label: t("dd.unresolvedHrRisks"), value: kpi.unresolved_hr_risks, icon: Shield, color: "text-orange-600 bg-orange-50" },
    { label: t("dd.unresolvedEnvRisks"), value: kpi.unresolved_env_risks, icon: Leaf, color: "text-green-700 bg-green-50" },
    { label: t("dd.overdueActions"), value: kpi.overdue_actions, icon: Clock, color: "text-red-600 bg-red-50" },
    { label: t("dd.openActions"), value: kpi.open_actions, icon: FileText, color: "text-slate-600 bg-slate-50" },
    { label: t("dd.remediationPct"), value: `${kpi.remediation_completion_pct.toFixed(0)}%`, icon: CheckCircle, color: "text-green-600 bg-green-50" },
    { label: t("dd.reportsGenerated"), value: kpi.reports_generated, icon: FileText, color: "text-slate-600 bg-slate-50" },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {kpiCards.map((c) => (
          <Card key={c.label}>
            <CardContent className="pt-5">
              <div className={`mb-3 inline-flex rounded-md p-2 ${c.color}`}>
                <c.icon className="h-4 w-4" />
              </div>
              <p className="text-2xl font-bold text-slate-900">{c.value}</p>
              <p className="mt-0.5 text-xs text-slate-500">{c.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">{t("dd.avgEsgScore")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">{(kpi.avg_esg_score * 100).toFixed(1)}</p>
            <ScoreBar value={kpi.avg_esg_score} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">{t("dd.avgRiskScore")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-slate-900">{(kpi.avg_risk_score * 100).toFixed(1)}</p>
            <ScoreBar value={kpi.avg_risk_score} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Suppliers Tab ─────────────────────────────────────────────────────────────

function SuppliersTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data: suppliers, isLoading } = useQuery<SupplierSummary[]>({
    queryKey: ["dd", "suppliers", orgId],
    queryFn: async () => (await apiClient.get("/due-diligence/suppliers")).data,
    staleTime: 60_000,
    enabled: !!orgId,
  });

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ["dd", "supplier-detail", expanded],
    queryFn: async () => (await apiClient.get(`/due-diligence/suppliers/${expanded}`)).data,
    enabled: !!expanded,
    staleTime: 120_000,
  });

  if (isLoading) return <div className="flex h-40 items-center justify-center"><Spinner /></div>;

  const list = suppliers ?? [];

  if (list.length === 0) {
    return (
      <Card>
        <CardContent className="py-16 text-center">
          <Users className="mx-auto mb-3 h-10 w-10 text-slate-300" />
          <p className="font-medium text-slate-600">{t("dd.noSuppliers")}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-2">
      {list.map((s) => {
        const open = expanded === s.supplier_id;
        return (
          <Card key={s.supplier_id} className={open ? "border-blue-200" : ""}>
            <CardContent className="pt-4 pb-4">
              <button
                className="flex w-full items-start justify-between gap-4 text-left"
                onClick={() => setExpanded(open ? null : s.supplier_id)}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-slate-900">{s.supplier_name}</span>
                    <RiskBadge band={s.risk_band} />
                    <span className="text-xs text-slate-400">{s.country} · {t("dd.tier")} {s.tier}</span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-500">
                    <span>{t("dd.esgScore")}: <strong className="text-slate-700">{(s.esg_score * 100).toFixed(0)}</strong></span>
                    <span>{t("dd.criticalFindings")}: <strong className="text-red-600">{s.critical_findings}</strong></span>
                    <span>{t("dd.openActions")}: <strong className="text-slate-700">{s.open_actions}</strong></span>
                    {s.overdue_actions > 0 && (
                      <span className="text-red-600">{t("dd.overdueActions")}: <strong>{s.overdue_actions}</strong></span>
                    )}
                  </div>
                </div>
                {open ? <ChevronDown className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" /> : <ChevronRight className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />}
              </button>

              {open && (
                <div className="mt-4 border-t border-slate-100 pt-4">
                  {detailLoading ? (
                    <div className="flex h-16 items-center justify-center"><Spinner /></div>
                  ) : detail ? (
                    <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
                      <div>
                        <p className="text-xs text-slate-400">{t("dd.industry")}</p>
                        <p className="font-medium text-slate-700">{detail.industry || "—"}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400">{t("dd.envScore")}</p>
                        <p className="font-medium text-slate-700">{(detail.environmental_score * 100).toFixed(0)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400">{t("dd.socialScore")}</p>
                        <p className="font-medium text-slate-700">{(detail.social_score * 100).toFixed(0)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400">{t("dd.govScore")}</p>
                        <p className="font-medium text-slate-700">{(detail.governance_score * 100).toFixed(0)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400">{t("dd.hrFindings")}</p>
                        <p className="font-medium text-slate-700">{s.hr_findings}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400">{t("dd.envFindings")}</p>
                        <p className="font-medium text-slate-700">{s.env_findings}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400">{t("dd.highFindings")}</p>
                        <p className="font-medium text-slate-700">{s.high_findings}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400">{t("dd.trend")}</p>
                        <p className={`font-medium capitalize ${s.trend === "improving" ? "text-green-600" : s.trend === "deteriorating" ? "text-red-600" : "text-slate-600"}`}>
                          {s.trend}
                        </p>
                      </div>
                    </div>
                  ) : null}
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

// ── Human Rights Tab ──────────────────────────────────────────────────────────

function HumanRightsTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";

  const { data: report, isLoading } = useQuery<HRReport>({
    queryKey: ["dd", "human-rights", orgId],
    queryFn: async () => (await apiClient.get("/due-diligence/human-rights")).data,
    staleTime: 60_000,
    enabled: !!orgId,
  });

  if (isLoading) return <div className="flex h-40 items-center justify-center"><Spinner /></div>;
  if (!report) return null;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {[
          { label: t("dd.totalHrFindings"), value: report.total_hr_findings },
          { label: t("dd.totalHrRisks"), value: report.total_hr_risks },
          { label: t("dd.suppliersImpacted"), value: report.suppliers_impacted },
          { label: t("dd.openRemediation"), value: report.open_remediation_actions },
          { label: t("dd.overdueActions"), value: report.overdue_actions, red: true },
          { label: t("dd.resolvedActions"), value: report.resolved_actions, green: true },
        ].map((c) => (
          <Card key={c.label}>
            <CardContent className="pt-5">
              <p className={`text-2xl font-bold ${c.red ? "text-red-600" : c.green ? "text-green-600" : "text-slate-900"}`}>{c.value}</p>
              <p className="mt-0.5 text-xs text-slate-500">{c.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold">{t("dd.byTopic")}</CardTitle>
        </CardHeader>
        <CardContent>
          {report.by_topic.length === 0 ? (
            <p className="text-sm text-slate-400">{t("dd.noData")}</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {report.by_topic.map((topic) => (
                <div key={topic.topic} className="flex items-center gap-4 py-3">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-800 text-sm">{topic.display_name}</p>
                    <div className="mt-1 flex flex-wrap gap-3 text-xs text-slate-500">
                      <span>{t("dd.findings")}: <strong className="text-slate-700">{topic.finding_count}</strong></span>
                      <span className="text-red-600">{t("dd.critical")}: <strong>{topic.critical_findings}</strong></span>
                      <span>{t("dd.risks")}: <strong className="text-slate-700">{topic.risk_count}</strong></span>
                      <span>{t("dd.unresolvedRisks")}: <strong className="text-amber-700">{topic.unresolved_risks}</strong></span>
                      <span>{t("dd.suppliersImpacted")}: <strong className="text-slate-700">{topic.suppliers_impacted}</strong></span>
                    </div>
                  </div>
                  {topic.critical_findings > 0 && (
                    <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">{t("dd.critical")}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Environmental Tab ─────────────────────────────────────────────────────────

function EnvironmentalTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";

  const { data: report, isLoading } = useQuery<EnvReport>({
    queryKey: ["dd", "environmental", orgId],
    queryFn: async () => (await apiClient.get("/due-diligence/environmental")).data,
    staleTime: 60_000,
    enabled: !!orgId,
  });

  if (isLoading) return <div className="flex h-40 items-center justify-center"><Spinner /></div>;
  if (!report) return null;

  const controlEffPct = report.mitigation_controls > 0
    ? Math.round((report.effective_controls / report.mitigation_controls) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {[
          { label: t("dd.totalEnvFindings"), value: report.total_env_findings },
          { label: t("dd.totalEnvRisks"), value: report.total_env_risks },
          { label: t("dd.unresolvedRisks"), value: report.unresolved_risks, red: true },
          { label: t("dd.suppliersImpacted"), value: report.suppliers_impacted },
          { label: t("dd.mitigationControls"), value: report.mitigation_controls },
          { label: t("dd.effectiveControls"), value: `${report.effective_controls} (${controlEffPct}%)`, green: true },
        ].map((c) => (
          <Card key={c.label}>
            <CardContent className="pt-5">
              <p className={`text-2xl font-bold ${c.red ? "text-red-600" : c.green ? "text-green-600" : "text-slate-900"}`}>{c.value}</p>
              <p className="mt-0.5 text-xs text-slate-500">{c.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold">{t("dd.byTopic")}</CardTitle>
        </CardHeader>
        <CardContent>
          {report.by_topic.length === 0 ? (
            <p className="text-sm text-slate-400">{t("dd.noData")}</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {report.by_topic.map((topic) => (
                <div key={topic.topic} className="flex items-center gap-4 py-3">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-800 text-sm">{topic.display_name}</p>
                    <div className="mt-1 flex flex-wrap gap-3 text-xs text-slate-500">
                      <span>{t("dd.findings")}: <strong className="text-slate-700">{topic.finding_count}</strong></span>
                      <span className="text-red-600">{t("dd.critical")}: <strong>{topic.critical_findings}</strong></span>
                      <span>{t("dd.risks")}: <strong className="text-slate-700">{topic.risk_count}</strong></span>
                      <span>{t("dd.unresolvedRisks")}: <strong className="text-amber-700">{topic.unresolved_risks}</strong></span>
                      <span>{t("dd.suppliersImpacted")}: <strong className="text-slate-700">{topic.suppliers_impacted}</strong></span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Actions Tab (Remediation + Preventive Measures) ───────────────────────────

const PRIORITY_COLORS: Record<string, string> = {
  critical: "text-red-700 bg-red-50",
  high: "text-orange-700 bg-orange-50",
  medium: "text-amber-700 bg-amber-50",
  low: "text-slate-600 bg-slate-50",
};

function ActionsTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";

  const { data: remediation, isLoading: remLoading } = useQuery<RemediationReport>({
    queryKey: ["dd", "remediation", orgId],
    queryFn: async () => (await apiClient.get("/due-diligence/remediation")).data,
    staleTime: 60_000,
    enabled: !!orgId,
  });

  const { data: preventive, isLoading: prevLoading } = useQuery<PreventiveMeasuresReport>({
    queryKey: ["dd", "preventive", orgId],
    queryFn: async () => (await apiClient.get("/due-diligence/preventive-measures")).data,
    staleTime: 60_000,
    enabled: !!orgId,
  });

  if (remLoading || prevLoading) return <div className="flex h-40 items-center justify-center"><Spinner /></div>;

  return (
    <div className="space-y-8">
      {/* Remediation */}
      <div className="space-y-4">
        <h3 className="font-semibold text-slate-900">{t("dd.remediation")}</h3>
        {remediation && (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              {[
                { label: t("dd.total"), value: remediation.total },
                { label: t("dd.open"), value: remediation.open },
                { label: t("dd.inProgress"), value: remediation.in_progress },
                { label: t("dd.completed"), value: remediation.completed, green: true },
                { label: t("dd.overdue"), value: remediation.overdue, red: true },
              ].map((c) => (
                <Card key={c.label}>
                  <CardContent className="pt-4 pb-4 text-center">
                    <p className={`text-xl font-bold ${c.red ? "text-red-600" : c.green ? "text-green-600" : "text-slate-900"}`}>{c.value}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{c.label}</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-slate-500">{t("dd.closureRate")}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold text-slate-900">{remediation.closure_rate.toFixed(1)}%</p>
                  <div className="mt-2 h-2 w-full rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full bg-green-500"
                      style={{ width: `${Math.min(100, remediation.closure_rate)}%` }}
                    />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-xs font-medium text-slate-500">{t("dd.avgResolutionDays")}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold text-slate-900">
                    {remediation.avg_resolution_days != null ? remediation.avg_resolution_days.toFixed(1) : "—"}
                  </p>
                  <p className="text-xs text-slate-400">{t("dd.days")}</p>
                </CardContent>
              </Card>
            </div>

            {remediation.top_overdue.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold">{t("dd.topOverdue")}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="divide-y divide-slate-100">
                    {remediation.top_overdue.map((item, i) => (
                      <div key={i} className="flex items-center justify-between gap-4 py-2.5">
                        <p className="text-sm text-slate-700 flex-1 min-w-0 truncate">{item.title}</p>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${PRIORITY_COLORS[item.priority] ?? "bg-slate-50 text-slate-600"}`}>
                            {item.priority}
                          </span>
                          {item.overdue_days != null && (
                            <span className="text-xs text-red-600 font-medium">+{item.overdue_days}d</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>

      {/* Preventive Measures */}
      <div className="space-y-4">
        <h3 className="font-semibold text-slate-900">{t("dd.preventiveMeasures")}</h3>
        {preventive && (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: t("dd.totalControls"), value: preventive.total_controls },
                { label: t("dd.preventive"), value: preventive.preventive },
                { label: t("dd.detective"), value: preventive.detective },
                { label: t("dd.corrective"), value: preventive.corrective },
              ].map((c) => (
                <Card key={c.label}>
                  <CardContent className="pt-4 pb-4 text-center">
                    <p className="text-xl font-bold text-slate-900">{c.value}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{c.label}</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            {(preventive.by_category ?? []).map((cat) => (
              <Card key={cat.category}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold capitalize">{cat.category}</CardTitle>
                  <p className="text-xs text-slate-400">{cat.effective}/{cat.total} {t("dd.effective")}</p>
                </CardHeader>
                <CardContent>
                  <div className="divide-y divide-slate-100">
                    {cat.measures.map((m) => (
                      <div key={m.id} className="flex items-center justify-between gap-4 py-2">
                        <p className="text-sm text-slate-700 flex-1 min-w-0 truncate">{m.title}</p>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-xs text-slate-400 capitalize">{m.control_type}</span>
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${m.effectiveness_status === "effective" ? "bg-green-100 text-green-700" : m.effectiveness_status === "partial" ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"}`}>
                            {m.effectiveness_status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

// ── Reports Tab ───────────────────────────────────────────────────────────────

const REPORT_TYPES = [
  { value: "lksgg_annual", label: "LkSGG Annual Report" },
  { value: "csddd", label: "CSDDD Report" },
  { value: "human_rights", label: "Human Rights" },
  { value: "environmental", label: "Environmental" },
  { value: "preventive_measures", label: "Preventive Measures" },
  { value: "remediation", label: "Remediation" },
] as const;

function ReportsTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";
  const qc = useQueryClient();
  const [selectedType, setSelectedType] = useState<string>("csddd");
  const [reportingYear, setReportingYear] = useState<string>("");
  const [genError, setGenError] = useState("");
  const [downloadError, setDownloadError] = useState<Record<string, string>>({});

  const { data: reports, isLoading } = useQuery<ReportSummary[]>({
    queryKey: ["dd", "reports", orgId],
    queryFn: async () => (await apiClient.get("/due-diligence/reports")).data,
    staleTime: 30_000,
    enabled: !!orgId,
  });

  const generate = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = { report_type: selectedType };
      if (reportingYear) payload.reporting_year = parseInt(reportingYear, 10);
      const res = await apiClient.post("/due-diligence/reports/generate", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dd", "reports", orgId] });
      setGenError("");
    },
    onError: (e: Error) => setGenError(e.message),
  });

  async function handleDownload(report: ReportSummary) {
    try {
      await downloadPdf(report.id, `dd-${report.report_type}-${report.generated_at.slice(0, 10)}.pdf`);
    } catch {
      setDownloadError((prev) => ({ ...prev, [report.id]: t("dd.downloadFailed") }));
    }
  }

  return (
    <div className="space-y-6">
      <Card className="border-blue-200 bg-blue-50/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">{t("dd.generateReport")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">{t("dd.reportType")}</label>
              <select
                className="h-9 rounded-md border border-slate-200 bg-white px-3 text-sm"
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
              >
                {REPORT_TYPES.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>
            {selectedType === "lksgg_annual" && (
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">{t("dd.reportingYear")}</label>
                <input
                  type="number"
                  min="2020"
                  max="2100"
                  className="h-9 w-28 rounded-md border border-slate-200 bg-white px-3 text-sm"
                  value={reportingYear}
                  onChange={(e) => setReportingYear(e.target.value)}
                  placeholder={String(new Date().getFullYear())}
                />
              </div>
            )}
            <Button onClick={() => generate.mutate()} disabled={generate.isPending} className="gap-1.5">
              {generate.isPending ? <Spinner className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
              {t("dd.generate")}
            </Button>
          </div>
          {genError && <p className="mt-2 text-sm text-red-600">{genError}</p>}
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : !reports || reports.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileText className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="font-medium text-slate-600">{t("dd.noReports")}</p>
            <p className="mt-1 text-sm text-slate-400">{t("dd.noReportsDesc")}</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="pt-0">
            <div className="divide-y divide-slate-100">
              {reports.map((r) => (
                <div key={r.id} className="flex items-center gap-4 py-3">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-800 text-sm capitalize">{r.report_type.replace(/_/g, " ")}</p>
                    <p className="text-xs text-slate-400">
                      {r.framework} {r.framework_version} · {new Date(r.generated_at).toLocaleDateString()}
                    </p>
                    {downloadError[r.id] && <p className="text-xs text-red-600">{downloadError[r.id]}</p>}
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize shrink-0 ${r.status === "completed" ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                    {r.status}
                  </span>
                  {r.status === "completed" && (
                    <Button variant="outline" size="sm" className="gap-1 shrink-0 h-7 text-xs" onClick={() => handleDownload(r)}>
                      <Download className="h-3 w-3" /> PDF
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Assessment Findings cross-reference ───────────────────────────────────────

interface OrgFinding {
  id: string;
  title: string;
  severity: string;
  category: string;
  status: string;
  assessment_id: string;
  created_at: string | null;
  supplier_name: string;
  supplier_id: string;
}

const FINDING_SEVERITY_COLORS: Record<string, string> = {
  Critical: "bg-red-100 text-red-700",
  High:     "bg-orange-100 text-orange-700",
  Medium:   "bg-amber-100 text-amber-700",
  Low:      "bg-slate-100 text-slate-600",
};

function AssessmentFindingsTab() {
  const [search, setSearch] = useState("");

  const { data: findings = [], isLoading } = useQuery<OrgFinding[]>({
    queryKey: ["executive-findings-xref"],
    queryFn: async () => (await apiClient.get("/executive/findings")).data,
    staleTime: 120_000,
  });

  const filtered = findings.filter(
    (f) =>
      !search ||
      f.title.toLowerCase().includes(search.toLowerCase()) ||
      f.supplier_name.toLowerCase().includes(search.toLowerCase()) ||
      f.category.toLowerCase().includes(search.toLowerCase()),
  );

  const grouped = filtered.reduce<Record<string, OrgFinding[]>>((acc, f) => {
    const key = f.category || "Other";
    (acc[key] ??= []).push(f);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50/40 p-4">
        <Search className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
        <div className="text-sm text-blue-700">
          <p className="font-semibold">Assessment Findings – Querverweise</p>
          <p className="text-xs mt-0.5">
            Alle Audit-Findings aus dem Assessment-Pipeline. Zum Verknüpfen einer Beschwerde mit einem Finding
            öffne das Finding und kopiere die ID in den entsprechenden Grievance-Datensatz.
          </p>
        </div>
      </div>

      <input
        type="search"
        placeholder="Suchen nach Titel, Lieferant, Kategorie…"
        className="w-full max-w-sm rounded-lg border border-border bg-background px-3 py-1.5 text-sm"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {isLoading && <div className="flex h-40 items-center justify-center"><Spinner /></div>}

      {!isLoading && findings.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Shield className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="font-medium text-slate-600">Keine Assessment-Findings vorhanden</p>
            <p className="mt-1 text-sm text-slate-400">
              Findings entstehen im Audit-Prozess. Starte ein Assessment, um Findings zu erfassen.
            </p>
          </CardContent>
        </Card>
      )}

      {Object.entries(grouped).map(([category, items]) => (
        <div key={category}>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{category}</p>
          <div className="space-y-2">
            {items.map((f) => (
              <div key={f.id} className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3">
                <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${FINDING_SEVERITY_COLORS[f.severity] ?? "bg-slate-100 text-slate-600"}`}>
                  {f.severity}
                </span>
                <div className="flex-1 min-w-0">
                  <Link href={`/findings/${f.id}`} className="text-sm font-medium hover:text-blue-600 hover:underline truncate block">
                    {f.title}
                  </Link>
                  <p className="text-xs text-muted-foreground">
                    <Link href={`/suppliers/${f.supplier_id}`} className="hover:underline">{f.supplier_name}</Link>
                    {" · "}
                    <span className={f.status === "Open" ? "text-amber-600" : f.status === "Verified" ? "text-emerald-600" : ""}>
                      {f.status}
                    </span>
                  </p>
                </div>
                <Link
                  href={`/assessments/${f.assessment_id}`}
                  className="shrink-0 flex items-center gap-1 text-xs text-indigo-500 hover:text-indigo-700"
                >
                  Assessment <ChevronRight className="h-3 w-3" />
                </Link>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DueDiligencePage() {
  const { t } = useLanguage();

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t("dd.pageTitle")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("dd.pageSubtitle")}</p>
      </div>

      <Tabs defaultValue="dashboard">
        <TabsList>
          <TabsTrigger value="dashboard">{t("dd.tabDashboard")}</TabsTrigger>
          <TabsTrigger value="suppliers">{t("dd.tabSuppliers")}</TabsTrigger>
          <TabsTrigger value="human-rights">{t("dd.tabHumanRights")}</TabsTrigger>
          <TabsTrigger value="environmental">{t("dd.tabEnvironmental")}</TabsTrigger>
          <TabsTrigger value="actions">{t("dd.tabActions")}</TabsTrigger>
          <TabsTrigger value="reports">{t("dd.tabReports")}</TabsTrigger>
          <TabsTrigger value="assessment-findings">Assessment Findings</TabsTrigger>
        </TabsList>
        <TabsContent value="dashboard" className="mt-6"><DashboardTab /></TabsContent>
        <TabsContent value="suppliers" className="mt-6"><SuppliersTab /></TabsContent>
        <TabsContent value="human-rights" className="mt-6"><HumanRightsTab /></TabsContent>
        <TabsContent value="environmental" className="mt-6"><EnvironmentalTab /></TabsContent>
        <TabsContent value="actions" className="mt-6"><ActionsTab /></TabsContent>
        <TabsContent value="reports" className="mt-6"><ReportsTab /></TabsContent>
        <TabsContent value="assessment-findings" className="mt-6"><AssessmentFindingsTab /></TabsContent>
      </Tabs>
    </div>
  );
}
