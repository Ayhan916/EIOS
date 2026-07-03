"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import { useAuth } from "@/lib/auth/context";
import {
  AlertCircle,
  ArrowRight,
  Calendar,
  Check,
  CheckCircle2,
  ChevronRight,
  ChevronUp,
  ChevronDown,
  Clock,
  Download,
  Eye,
  FileBarChart2,
  FileJson,
  FileText,
  Globe,
  Loader2,
  Lock,
  Plus,
  Send,
  Share2,
  Shield,
  ShieldCheck,
  Trash2,
  X,
  XCircle,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import {
  generateBoardReport,
  listBoardReports,
  deleteBoardReport,
  boardReportPdfUrl,
  createShareLink,
} from "@/lib/api/executive";
import {
  listReports as listSustainReports,
  finalizeReport,
  type SustainabilityReport,
} from "@/lib/api/sustainability";
import {
  listReports as listFinReports,
  listScenarios as listFinScenarios,
  listCorrelations,
} from "@/lib/api/financial-esg";
import {
  listReports as listStratReports,
  listScenarios as listStratScenarios,
  createReport,
  type CreateReportPayload,
} from "@/lib/api/strategy";
import { listAssuranceReports, generateAssuranceReport } from "@/lib/api/ai-governance";
import type { BoardReportRequest } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import Link from "next/link";
import { CopilotDrawer } from "@/components/copilot-drawer";

// ── Types ─────────────────────────────────────────────────────────────────────

interface DisclosurePackage {
  id: string;
  package_name: string;
  framework_codes: string[];
  publication_date: string;
  report_status: string;
  disclosure_score: number | null;
  created_at: string;
}

interface FrameworkDisclosureSummary {
  framework_id: string;
  framework_code: string;
  framework_name: string;
  total_requirements: number;
  not_started: number;
  draft: number;
  in_review: number;
  approved: number;
  published: number;
  completion_pct: number;
  critical_blockers: number;
}

interface DisclosureDashboardResponse {
  frameworks: FrameworkDisclosureSummary[];
  total_requirements: number;
  total_published: number;
  total_approved: number;
  total_draft: number;
  total_not_started: number;
  overall_completion_pct: number;
}

interface DisclosureRequirement {
  id: string;
  framework_id: string;
  reference: string;
  title: string;
  description: string;
  category: string;
  status: string;
}

interface ComplianceReportSummary {
  id: string;
  organization_id: string;
  report_type: string;
  framework_code: string;
  framework_version: string;
  generated_at: string;
  generated_by: string;
  report_hash: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const API_BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1`;

async function authenticatedDownload(url: string, filename: string) {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("eios_access_token") : null;
  const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `Download failed (${res.status})`);
  }
  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl; a.download = filename; a.click();
  URL.revokeObjectURL(blobUrl);
}

async function downloadPdf(path: string, filename: string) {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("eios_access_token") : null;
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `Download failed (${res.status})`);
  }
  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
}

function ragColor(s: string) {
  switch (s) {
    case "GREEN": return "bg-emerald-100 text-emerald-800";
    case "AMBER": return "bg-amber-100 text-amber-800";
    case "RED":   return "bg-red-100 text-red-800";
    default:      return "bg-slate-100 text-slate-600";
  }
}

function pkgStatusColor(status: string) {
  const m: Record<string, string> = {
    DRAFT: "bg-slate-100 text-slate-600",
    IN_REVIEW: "bg-blue-100 text-blue-700",
    APPROVED: "bg-emerald-100 text-emerald-700",
    PUBLISHED: "bg-green-100 text-green-700",
  };
  return m[status] ?? "bg-slate-100 text-slate-600";
}

function aiStatusColor(s: string) {
  const m: Record<string, string> = {
    COMPLIANT: "bg-emerald-100 text-emerald-800",
    PARTIALLY_COMPLIANT: "bg-amber-100 text-amber-800",
    NON_COMPLIANT: "bg-red-100 text-red-800",
    NOT_ASSESSED: "bg-slate-100 text-slate-600",
  };
  return m[s] ?? "bg-slate-100 text-slate-600";
}

// ── Disclosure wizard (existing) ───────────────────────────────────────────────

function CompleteDisclosureWizard({
  framework,
  onClose,
}: {
  framework: FrameworkDisclosureSummary;
  onClose: () => void;
}) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);

  const { data: requirements, isLoading } = useQuery<DisclosureRequirement[]>({
    queryKey: ["disclosure-requirements", framework.framework_id],
    queryFn: async () => {
      const r = await apiClient.get(
        `/reporting/frameworks/${framework.framework_id}/requirements`,
      );
      return r.data ?? [];
    },
  });

  const incomplete = (requirements ?? []).filter(
    (r) => r.status === "Not Started" || r.status === "Draft",
  );
  const inReview = (requirements ?? []).filter((r) => r.status === "In Review").length;
  const approved = (requirements ?? []).filter((r) => r.status === "Approved").length;
  const published = (requirements ?? []).filter((r) => r.status === "Published").length;

  const current = incomplete[step] ?? null;
  const total = (requirements ?? []).length;
  const done = total - incomplete.length;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  async function handleBegin(req: DisclosureRequirement) {
    setBusy(req.id);
    try {
      await apiClient.post("/reporting/responses", { requirement_id: req.id });
      qc.invalidateQueries({ queryKey: ["disclosure-requirements", framework.framework_id] });
      qc.invalidateQueries({ queryKey: ["disclosure-dashboard"] });
      if (step < incomplete.length - 1) setStep((s) => s + 1);
    } catch { /* ignore */ }
    finally { setBusy(null); }
  }

  async function handleSubmit(req: DisclosureRequirement) {
    setBusy(req.id + "-submit");
    try {
      const listR = await apiClient.get(
        `/reporting/responses?requirement_id=${req.id}&limit=1`,
      );
      const respId = listR.data?.[0]?.id;
      if (respId) {
        await apiClient.post(`/reporting/responses/${respId}/submit`, {});
        qc.invalidateQueries({ queryKey: ["disclosure-requirements", framework.framework_id] });
        qc.invalidateQueries({ queryKey: ["disclosure-dashboard"] });
        if (step < incomplete.length - 1) setStep((s) => s + 1);
      }
    } catch { /* ignore */ }
    finally { setBusy(null); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div className="w-full max-w-2xl rounded-xl bg-background border border-border shadow-2xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <p className="font-semibold">{framework.framework_name}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{t("reports.disclosureCompletion")}</p>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="px-5 py-3 border-b border-border bg-muted/30">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
            <span>{t("reports.reqComplete").replace("{done}", String(done)).replace("{total}", String(total))}</span>
            <span className="font-semibold text-foreground">{pct}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
            <div className={`h-full rounded-full transition-all ${pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-blue-500"}`} style={{ width: `${pct}%` }} />
          </div>
          <div className="mt-2 flex gap-3 text-[10px]">
            {[
              { labelKey: "reports.published", val: published, cls: "text-emerald-600" },
              { labelKey: "reports.approved", val: approved, cls: "text-blue-600" },
              { labelKey: "reports.inReview", val: inReview, cls: "text-amber-600" },
              { labelKey: "reports.remaining", val: incomplete.length, cls: "text-muted-foreground" },
            ].map(({ labelKey, val, cls }) => (
              <span key={labelKey} className={cls}><span className="font-semibold">{val}</span> {t(labelKey as Parameters<typeof t>[0])}</span>
            ))}
          </div>
        </div>
        <div className="p-5">
          {isLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : incomplete.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-500 mb-3" />
              <p className="font-medium">{t("reports.allAddressed")}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {inReview} {t("reports.inReview")} · {approved} {t("reports.approved")} · {published} {t("reports.published")}
              </p>
            </div>
          ) : current ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <button onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0} className="flex items-center gap-1 hover:text-foreground disabled:opacity-40">
                  ← {t("common.back")}
                </button>
                <span>{t("reports.requirementOf").replace("{n}", String(step + 1)).replace("{m}", String(incomplete.length))}</span>
                <button onClick={() => setStep((s) => Math.min(incomplete.length - 1, s + 1))} disabled={step === incomplete.length - 1} className="flex items-center gap-1 hover:text-foreground disabled:opacity-40">
                  {t("common.next")} →
                </button>
              </div>
              <div className="rounded-lg border border-border p-4 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-mono font-medium text-slate-600">{current.reference}</span>
                      <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700">{current.category}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${current.status === "Draft" ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-600"}`}>{current.status}</span>
                    </div>
                    <p className="font-medium text-sm">{current.title}</p>
                    {current.description && <p className="mt-1.5 text-xs text-muted-foreground line-clamp-3">{current.description}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-2 pt-1">
                  {current.status === "Not Started" ? (
                    <Button size="sm" onClick={() => handleBegin(current)} disabled={busy === current.id} className="gap-1.5 text-xs">
                      {busy === current.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ArrowRight className="h-3.5 w-3.5" />}
                      {t("reports.beginDraft")}
                    </Button>
                  ) : (
                    <Button size="sm" onClick={() => handleSubmit(current)} disabled={busy === current.id + "-submit"} className="gap-1.5 text-xs">
                      {busy === current.id + "-submit" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ChevronRight className="h-3.5 w-3.5" />}
                      {t("reports.submitReview")}
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" onClick={() => setStep((s) => Math.min(incomplete.length - 1, s + 1))} className="text-xs text-muted-foreground" disabled={step === incomplete.length - 1}>
                    {t("reports.skipForNow")}
                  </Button>
                </div>
              </div>
              {incomplete.length > 1 && (
                <div className="space-y-1">
                  <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">{t("reports.remainingRequirements")}</p>
                  <div className="max-h-32 overflow-y-auto space-y-1">
                    {incomplete.map((r, i) => (
                      <button key={r.id} onClick={() => setStep(i)} className={`w-full text-left rounded px-2 py-1.5 text-xs transition-colors flex items-center gap-2 ${i === step ? "bg-primary/10 text-primary" : "hover:bg-muted/50 text-muted-foreground"}`}>
                        <span className="font-mono text-[10px] w-16 flex-shrink-0">{r.reference}</span>
                        <span className="truncate">{r.title}</span>
                        <span className={`ml-auto flex-shrink-0 rounded-full px-1.5 py-0.5 text-[9px] ${r.status === "Draft" ? "bg-amber-50 text-amber-600" : "bg-slate-100 text-slate-500"}`}>
                          {r.status === "Not Started" ? "—" : r.status}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

// ── Disclosure gap analysis ───────────────────────────────────────────────────

function DisclosureGapAnalysis() {
  const { t } = useLanguage();
  const [wizard, setWizard] = useState<FrameworkDisclosureSummary | null>(null);

  const { data: dashboard, isLoading } = useQuery<DisclosureDashboardResponse>({
    queryKey: ["disclosure-dashboard"],
    queryFn: async () => {
      const r = await apiClient.get("/reporting/dashboard");
      return r.data;
    },
    staleTime: 60_000,
    retry: false,
  });

  if (isLoading) {
    return (
      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{t("reports.disclosureGap")}</h2>
        <Card><CardContent className="flex justify-center py-8"><Spinner /></CardContent></Card>
      </section>
    );
  }

  if (!dashboard || dashboard.frameworks.length === 0) return null;

  const overall = Math.round(dashboard.overall_completion_pct);

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{t("reports.disclosureGap")}</h2>
        <span className="text-xs text-muted-foreground">
          {t("reports.totalRequirements").replace("{n}", String(dashboard.total_requirements)).replace("{m}", String(dashboard.frameworks.length))}
        </span>
      </div>
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-6">
            <div className="text-center">
              <p className={`text-3xl font-bold ${overall >= 80 ? "text-emerald-600" : overall >= 50 ? "text-amber-600" : "text-red-600"}`}>{overall}%</p>
              <p className="text-xs text-muted-foreground mt-0.5">{t("reports.overallCoverage")}</p>
            </div>
            <div className="flex-1">
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>{t("reports.current")}</span>
                <span>{t("reports.required100")}</span>
              </div>
              <div className="h-3 w-full rounded-full bg-muted overflow-hidden">
                <div className={`h-full rounded-full transition-all ${overall >= 80 ? "bg-emerald-500" : overall >= 50 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${overall}%` }} />
              </div>
              <div className="mt-2 flex gap-4 text-[10px]">
                {[
                  { labelKey: "reports.published", val: dashboard.total_published, cls: "text-emerald-600 font-semibold" },
                  { labelKey: "reports.approved", val: dashboard.total_approved, cls: "text-blue-600" },
                  { labelKey: "reports.draft", val: dashboard.total_draft, cls: "text-amber-600" },
                  { labelKey: "reports.notStarted", val: dashboard.total_not_started, cls: "text-slate-500" },
                ].map(({ labelKey, val, cls }) => (
                  <span key={labelKey} className={cls}>{val} {t(labelKey as Parameters<typeof t>[0])}</span>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-4 pb-2">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="pb-2 text-left text-xs font-medium text-muted-foreground">{t("reports.framework")}</th>
                  <th className="pb-2 text-right text-xs font-medium text-muted-foreground">{t("reports.current")}</th>
                  <th className="pb-2 text-right text-xs font-medium text-muted-foreground">{t("reports.gap")}</th>
                  <th className="pb-2 text-left text-xs font-medium text-muted-foreground px-4">{t("reports.statusBreakdown")}</th>
                  <th className="pb-2 text-center text-xs font-medium text-muted-foreground">{t("reports.blockers")}</th>
                  <th className="pb-2 text-right text-xs font-medium text-muted-foreground" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {dashboard.frameworks.map((fw) => {
                  const pct = Math.round(fw.completion_pct);
                  const gap = 100 - pct;
                  const total = fw.total_requirements || 1;
                  const gapCls = gap === 0 ? "text-emerald-600" : gap <= 20 ? "text-amber-600" : "text-red-600";
                  return (
                    <tr key={fw.framework_id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 pr-4">
                        <p className="font-medium text-sm">{fw.framework_name}</p>
                        <p className="text-[10px] text-muted-foreground">{fw.framework_code} · {fw.total_requirements} reqs</p>
                      </td>
                      <td className="py-3 pr-2 text-right">
                        <span className={`text-sm font-semibold ${pct >= 80 ? "text-emerald-600" : pct >= 50 ? "text-amber-600" : "text-red-600"}`}>{pct}%</span>
                      </td>
                      <td className="py-3 pr-4 text-right">
                        <span className={`text-xs font-medium ${gapCls}`}>{gap === 0 ? t("reports.complete") : `−${gap}%`}</span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex h-2 w-36 rounded-full overflow-hidden gap-px">
                          {fw.published > 0 && <div className="bg-emerald-500" style={{ width: `${(fw.published / total) * 100}%` }} />}
                          {fw.approved > 0 && <div className="bg-blue-400" style={{ width: `${(fw.approved / total) * 100}%` }} />}
                          {fw.in_review > 0 && <div className="bg-amber-400" style={{ width: `${(fw.in_review / total) * 100}%` }} />}
                          {fw.draft > 0 && <div className="bg-slate-300" style={{ width: `${(fw.draft / total) * 100}%` }} />}
                          {fw.not_started > 0 && <div className="bg-slate-100" style={{ width: `${(fw.not_started / total) * 100}%` }} />}
                        </div>
                        <div className="mt-1 flex gap-2 text-[9px] text-muted-foreground">
                          {fw.published > 0 && <span className="text-emerald-600">{fw.published} pub</span>}
                          {fw.draft > 0 && <span>{fw.draft} draft</span>}
                          {fw.not_started > 0 && <span>{fw.not_started} pending</span>}
                        </div>
                      </td>
                      <td className="py-3 text-center">
                        {fw.critical_blockers > 0 ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-semibold text-red-700">
                            <AlertCircle className="h-3 w-3" /> {fw.critical_blockers}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="py-3 text-right">
                        {(fw.not_started > 0 || fw.draft > 0) && (
                          <button onClick={() => setWizard(fw)} className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 transition-colors">
                            {t("reports.beginDraft")} <ChevronRight className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
      {wizard && <CompleteDisclosureWizard framework={wizard} onClose={() => setWizard(null)} />}
    </section>
  );
}

// ── Direct regulatory reports ─────────────────────────────────────────────────

const DIRECT_REPORTS = [
  {
    id: "tcfd",
    name: "TCFD Climate Report",
    description: "Task Force on Climate-related Financial Disclosures report (JSON)",
    icon: Globe,
    color: "bg-teal-50 text-teal-700 border-teal-200",
    iconColor: "text-teal-600",
    action: async (year: number) => {
      await authenticatedDownload(`/executive/tcfd?reporting_year=${year}`, `tcfd_report_${year}.json`);
    },
  },
  {
    id: "sfdr-pai",
    name: "SFDR PAI Calculation",
    description: "Sustainable Finance Disclosure Regulation Principal Adverse Impacts",
    icon: Shield,
    color: "bg-purple-50 text-purple-700 border-purple-200",
    iconColor: "text-purple-600",
    action: async (year: number) => {
      const start = `${year}-01-01`;
      const end = `${year}-12-31`;
      await authenticatedDownload(
        `/financial-esg/sfdr/pai?reference_period_start=${start}&reference_period_end=${end}`,
        `sfdr_pai_${year}.json`,
      );
    },
  },
  {
    id: "audit-csv",
    name: "Audit Trail CSV",
    description: "Full audit event log export for compliance verification",
    icon: FileText,
    color: "bg-slate-50 text-slate-700 border-slate-200",
    iconColor: "text-slate-600",
    action: async (_year: number) => {
      await authenticatedDownload(`/audit/events/export?format=csv`, `audit_trail.csv`);
    },
  },
] as const;

function CDPModuleCard() {
  const { t } = useLanguage();
  const { data: settings } = useQuery({
    queryKey: ["org-settings-cdp"],
    queryFn: async () => {
      try { const r = await apiClient.get("/commercial/organizations/me/settings"); return r.data; }
      catch { return null; }
    },
    staleTime: 300_000,
    retry: false,
  });

  const cdpConnected = !!(settings?.cdp_api_key || settings?.sbti_integration_enabled);
  const CDP_MODULES = [
    { name: "Climate Change", complete: cdpConnected },
    { name: "Water Security", complete: false },
    { name: "Forests", complete: false },
    { name: "Supplier Engagement", complete: cdpConnected },
  ];
  const completedCount = CDP_MODULES.filter((m) => m.complete).length;
  const pct = Math.round((completedCount / CDP_MODULES.length) * 100);

  return (
    <Card className="border border-amber-200 bg-amber-50">
      <CardContent className="pt-5 space-y-3">
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-amber-50 p-2 border border-amber-200">
            <Globe className="h-5 w-5 text-amber-600" />
          </div>
          <div className="flex-1">
            <p className="font-medium text-sm">{t("reports.cdpClimate")}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{t("reports.cdpClimateDesc")}</p>
          </div>
        </div>
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-amber-800">
            <span>{t("reports.moduleCompletion")}</span>
            <span className="font-semibold">{completedCount}/{CDP_MODULES.length}</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-amber-200 overflow-hidden">
            <div className="h-full rounded-full bg-amber-500 transition-all" style={{ width: `${pct}%` }} />
          </div>
        </div>
        <div className="space-y-1">
          {CDP_MODULES.map((m) => (
            <div key={m.name} className="flex items-center gap-2 text-xs">
              {m.complete ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 flex-shrink-0" /> : <XCircle className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" />}
              <span className={m.complete ? "text-amber-900" : "text-amber-700"}>{m.name}</span>
            </div>
          ))}
        </div>
        {!cdpConnected && <p className="text-xs text-amber-700">{t("reports.connectCdp")}</p>}
      </CardContent>
    </Card>
  );
}

function DirectReportCard({ report }: { report: (typeof DIRECT_REPORTS)[number] }) {
  const { t } = useLanguage();
  const [year, setYear] = useState(new Date().getFullYear() - 1);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState<Record<string, unknown> | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  async function handleDownload() {
    setDownloading(true); setError(null); setSuccess(false);
    try {
      await report.action(year);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("reports.downloadFailed"));
    } finally { setDownloading(false); }
  }

  async function handlePreview() {
    if (previewOpen) { setPreviewOpen(false); return; }
    setPreviewLoading(true);
    try {
      const r = await apiClient.get(`/executive/tcfd?reporting_year=${year}`);
      setPreviewData(r.data);
      setPreviewOpen(true);
    } catch { setError(t("reports.previewUnavailable")); }
    finally { setPreviewLoading(false); }
  }

  return (
    <Card className={`border ${report.color}`}>
      <CardContent className="pt-5 space-y-3">
        <div className="flex items-start gap-4">
          <div className={`rounded-lg p-2 ${report.color}`}>
            <report.icon className={`h-5 w-5 ${report.iconColor}`} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm text-foreground">{report.name}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{report.description}</p>
            {error && <p className="mt-1.5 text-xs text-red-600 flex items-center gap-1"><AlertCircle className="h-3 w-3" /> {error}</p>}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {report.id !== "audit-csv" && (
              <select className="h-8 rounded-md border border-input bg-background px-2 text-xs" value={year} onChange={(e) => setYear(Number(e.target.value))}>
                {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 1 - i).map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            )}
            {report.id === "tcfd" && (
              <Button size="sm" variant="ghost" onClick={handlePreview} disabled={previewLoading} className="gap-1.5 text-xs">
                {previewLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Eye className="h-3.5 w-3.5" />}
                {previewOpen ? t("reports.hide") : t("reports.preview")}
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={handleDownload} disabled={downloading} className="gap-1.5 text-xs">
              {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : success ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> : <Download className="h-3.5 w-3.5" />}
              {success ? t("reports.downloaded") : t("common.export")}
            </Button>
          </div>
        </div>
        {previewOpen && previewData && (
          <div className="rounded-lg border border-teal-200 bg-teal-50/40 p-4 space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <p className="font-semibold text-teal-800">{t("reports.tcfdPreview").replace("{year}", String(year))}</p>
              <button onClick={() => setPreviewOpen(false)} className="text-teal-600 hover:text-teal-900">✕</button>
            </div>
            {Object.entries(previewData).slice(0, 12).map(([key, val]) => (
              <div key={key} className="flex gap-2">
                <span className="w-36 flex-shrink-0 font-medium text-teal-700 capitalize">{key.replace(/_/g, " ")}:</span>
                <span className="text-muted-foreground truncate">
                  {val == null ? "—" : typeof val === "object" ? JSON.stringify(val).slice(0, 80) + "…" : String(val)}
                </span>
              </div>
            ))}
            <p className="text-teal-600 text-[10px]">{t("reports.previewFull")}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PackageExportButtons({ pkg }: { pkg: DisclosurePackage }) {
  const { t } = useLanguage();
  const [busy, setBusy] = useState<"ixbrl" | "gri" | "json" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function doExport(format: "xbrl" | "gri" | "json") {
    setBusy(format === "xbrl" ? "ixbrl" : (format as "gri" | "json"));
    setError(null);
    try {
      const ext = format === "xbrl" ? "html" : format;
      const name = `${pkg.package_name.replace(/\s+/g, "_").toLowerCase()}_${format}.${ext}`;
      await authenticatedDownload(`/reporting/packages/${pkg.id}/export?format=${format}`, name);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("reports.exportFailed"));
    } finally { setBusy(null); }
  }

  return (
    <div className="flex items-center gap-2">
      {error && <span className="text-xs text-red-500">{error}</span>}
      <Button size="sm" variant="outline" className="gap-1 text-xs" disabled={!!busy} onClick={() => doExport("xbrl")}>
        {busy === "ixbrl" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />} iXBRL
      </Button>
      <Button size="sm" variant="outline" className="gap-1 text-xs" disabled={!!busy} onClick={() => doExport("gri")}>
        {busy === "gri" ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileJson className="h-3 w-3" />} GRI
      </Button>
      <Button size="sm" variant="outline" className="gap-1 text-xs" disabled={!!busy} onClick={() => doExport("json")}>
        {busy === "json" ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileJson className="h-3 w-3" />} JSON
      </Button>
    </div>
  );
}

function GeneratePackageForm({ onSuccess }: { onSuccess: () => void }) {
  const { t } = useLanguage();
  const [name, setName] = useState("CSRD Annual Report");
  const [frameworks, setFrameworks] = useState("CSRD,GRI");
  const [pubDate, setPubDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [error, setError] = useState<string | null>(null);

  const { mutate, isPending } = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/reporting/packages/generate", {
        package_name: name,
        framework_codes: frameworks.split(",").map((f) => f.trim()),
        publication_date: pubDate,
      });
      return res.data;
    },
    onSuccess: () => { setError(null); onSuccess(); },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <div className="rounded-lg border border-dashed border-border p-5 space-y-4">
      <p className="text-sm font-medium">{t("reports.newPackage")}</p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <Label className="text-xs">{t("reports.packageName")}</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="CSRD Annual Report" className="mt-1 h-8 text-sm" />
        </div>
        <div>
          <Label className="text-xs">{t("reports.frameworks")}</Label>
          <Input value={frameworks} onChange={(e) => setFrameworks(e.target.value)} placeholder="CSRD,GRI" className="mt-1 h-8 text-sm" />
        </div>
        <div>
          <Label className="text-xs">{t("reports.pubDate")}</Label>
          <Input type="date" value={pubDate} onChange={(e) => setPubDate(e.target.value)} className="mt-1 h-8 text-sm" />
        </div>
      </div>
      {error && <p className="text-xs text-red-600 flex items-center gap-1"><AlertCircle className="h-3 w-3" /> {error}</p>}
      <Button size="sm" disabled={isPending} onClick={() => mutate()} className="gap-1.5">
        {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
        {t("reports.generate")}
      </Button>
    </div>
  );
}

// ── TAB 1: Disclosure (existing content) ──────────────────────────────────────

function DisclosureTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const { data: packages, isLoading } = useQuery<DisclosurePackage[]>({
    queryKey: ["disclosure-packages"],
    queryFn: async () => {
      const res = await apiClient.get("/reporting/packages?limit=50");
      return res.data;
    },
  });

  return (
    <div className="space-y-8">
      <DisclosureGapAnalysis />

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{t("reports.regulatoryReports")}</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {DIRECT_REPORTS.map((r) => <DirectReportCard key={r.id} report={r} />)}
          <CDPModuleCard />
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{t("reports.disclosurePackages")}</h2>
          <Link href="/regulatory" className="text-xs text-blue-600 hover:underline">{t("reports.manageFrameworks")}</Link>
        </div>
        <GeneratePackageForm onSuccess={() => qc.invalidateQueries({ queryKey: ["disclosure-packages"] })} />
        {isLoading ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : !packages || packages.length === 0 ? (
          <div className="rounded-lg border border-dashed p-8 text-center">
            <Calendar className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">{t("reports.noReports")}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {packages.map((pkg) => {
              const hasGRI = (pkg.framework_codes ?? []).some((f) => f.toUpperCase().includes("GRI"));
              const hasIXBRL = (pkg.framework_codes ?? []).some((f) => f.toUpperCase().includes("IXBRL") || f.toUpperCase().includes("XBRL"));
              const griPct = pkg.disclosure_score != null ? Math.round(pkg.disclosure_score * 100) : null;
              const ixbrlValid = pkg.report_status === "APPROVED" || pkg.report_status === "PUBLISHED";
              return (
                <Card key={pkg.id}>
                  <CardContent className="py-4 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3 flex-1 min-w-0">
                        <FileText className="mt-0.5 h-5 w-5 shrink-0 text-slate-400" />
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-sm">{pkg.package_name}</p>
                          <div className="mt-1 flex flex-wrap items-center gap-2">
                            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${pkgStatusColor(pkg.report_status)}`}>{pkg.report_status}</span>
                            {(pkg.framework_codes ?? []).map((f) => (
                              <span key={f} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{f}</span>
                            ))}
                            {hasIXBRL && (
                              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${ixbrlValid ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                                {ixbrlValid ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                                iXBRL {ixbrlValid ? "Valid" : "Pending"}
                              </span>
                            )}
                            <span className="text-xs text-muted-foreground">{new Date(pkg.publication_date).toLocaleDateString()}</span>
                          </div>
                          {hasGRI && griPct != null && (
                            <div className="mt-2 space-y-1">
                              <div className="flex justify-between text-[10px] text-muted-foreground">
                                <span>{t("reports.griCoverage")}</span>
                                <span className="font-semibold">{griPct}%</span>
                              </div>
                              <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                                <div className={`h-full rounded-full transition-all ${griPct >= 80 ? "bg-emerald-500" : griPct >= 50 ? "bg-amber-500" : "bg-red-400"}`} style={{ width: `${griPct}%` }} />
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                      <PackageExportButtons pkg={pkg} />
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      <section>
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="flex items-center justify-between py-4">
            <div className="flex items-center gap-3">
              <Calendar className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm font-medium text-blue-900">{t("reports.regulatoryCalendar")}</p>
                <p className="text-xs text-blue-700">{t("reports.calendarDesc")}</p>
              </div>
            </div>
            <Button asChild variant="outline" size="sm" className="border-blue-300 text-blue-700 hover:bg-blue-100">
              <Link href="/regulatory">{t("reports.viewCalendar")}</Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

// ── TAB 2: Executive / Board Reports ─────────────────────────────────────────

const BOARD_SLIDES = [
  { key: "executive_summary",  label: "Executive Summary" },
  { key: "esg_health",         label: "ESG Health Score" },
  { key: "risk_heatmap",       label: "Risk Heatmap" },
  { key: "supplier_portfolio", label: "Supplier Portfolio" },
  { key: "compliance_status",  label: "Compliance Status" },
  { key: "sustainability",     label: "Sustainability KPIs" },
  { key: "financial_esg",      label: "Financial ESG" },
  { key: "pending_decisions",  label: "Pending Decisions" },
];

function BoardReportForm({ onSuccess }: { onSuccess: () => void }) {
  const { t } = useLanguage();
  const [title, setTitle] = useState("Board Report");
  const [periodStart, setPeriodStart] = useState(() => {
    const d = new Date(); d.setMonth(d.getMonth() - 1); d.setDate(1); return d.toISOString().split("T")[0];
  });
  const [periodEnd, setPeriodEnd] = useState(() => {
    const d = new Date(); d.setDate(0); return d.toISOString().split("T")[0];
  });
  const [kpiDays, setKpiDays] = useState<30 | 90 | 365>(90);
  const [selectedSlides, setSelectedSlides] = useState<Set<string>>(new Set(BOARD_SLIDES.map((s) => s.key)));
  const [error, setError] = useState<string | null>(null);

  function toggleSlide(key: string) {
    setSelectedSlides((prev) => {
      const next = new Set(prev);
      if (next.has(key)) { if (next.size > 1) next.delete(key); }
      else next.add(key);
      return next;
    });
  }

  const { mutate, isPending } = useMutation({
    mutationFn: (body: BoardReportRequest) => generateBoardReport(body),
    onSuccess: () => { setError(null); onSuccess(); },
    onError: (e: Error) => setError(e.message),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutate({ title, period_start: periodStart, period_end: periodEnd, kpi_period_days: kpiDays });
  }

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">{t("reports.newReport")}</CardTitle></CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="br-title">{t("common.title")}</Label>
            <Input id="br-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Q1 2026 Board Report" required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="br-start">Period Start</Label>
              <Input id="br-start" type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} required />
            </div>
            <div>
              <Label htmlFor="br-end">Period End</Label>
              <Input id="br-end" type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} required />
            </div>
          </div>
          <div>
            <Label>KPI Trend Window</Label>
            <div className="mt-1 flex gap-2">
              {([30, 90, 365] as const).map((d) => (
                <button key={d} type="button" onClick={() => setKpiDays(d)} className={`rounded px-3 py-1.5 text-sm font-medium transition-colors ${kpiDays === d ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}>
                  {d === 365 ? "1 Year" : `${d} Days`}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="text-sm font-medium mb-2">Slides to include</p>
            <div className="grid grid-cols-2 gap-1.5">
              {BOARD_SLIDES.map((s) => {
                const checked = selectedSlides.has(s.key);
                return (
                  <button key={s.key} type="button" onClick={() => toggleSlide(s.key)} className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs font-medium transition-colors ${checked ? "border-primary bg-primary/5 text-primary" : "border-border text-muted-foreground hover:bg-muted/50"}`}>
                    <span className={`flex h-3.5 w-3.5 flex-shrink-0 items-center justify-center rounded border ${checked ? "border-primary bg-primary" : "border-slate-300"}`}>
                      {checked && <span className="block h-1.5 w-1.5 rounded-sm bg-white" />}
                    </span>
                    {s.label}
                  </button>
                );
              })}
            </div>
            <p className="mt-1 text-[10px] text-muted-foreground">{selectedSlides.size} of {BOARD_SLIDES.length} slides selected</p>
          </div>
          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 shrink-0" /> {error}
            </div>
          )}
          <Button type="submit" disabled={isPending} className="w-full">
            {isPending ? <><Spinner className="h-4 w-4" /> {t("common.loading")}</> : <><Plus className="h-4 w-4" /> {t("reports.generate")}</>}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function ShareLinkButton({ reportId }: { reportId: string }) {
  const { t } = useLanguage();
  const [sharing, setSharing] = useState(false);
  const [copied, setCopied] = useState(false);

  async function handleShare() {
    setSharing(true);
    try {
      const res = await createShareLink(reportId, { expires_in_hours: 168 });
      const url = `${window.location.origin}${res.board_url}`;
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch { /* clipboard fallback: not critical */ }
    finally { setSharing(false); }
  }

  return (
    <button onClick={handleShare} disabled={sharing} className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-slate-50 disabled:opacity-50">
      {sharing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Share2 className="h-3.5 w-3.5" />}
      {copied ? t("common.confirm") : t("exec.shareLink")}
    </button>
  );
}

function PptxButton({ reportId, title }: { reportId: string; title: string }) {
  const [busy, setBusy] = useState(false);

  async function handleDownload() {
    setBusy(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("eios_access_token") : null;
      const res = await fetch(`/commercial/executive/reports/${reportId}/pptx`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `${title.replace(/\s+/g, "_").toLowerCase()}.pptx`; a.click();
      URL.revokeObjectURL(url);
    } catch { /* silent — PPTX may require commercial tier */ }
    finally { setBusy(false); }
  }

  return (
    <button onClick={handleDownload} disabled={busy} className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-slate-50 disabled:opacity-50">
      {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />} PPTX
    </button>
  );
}

function ExecutiveReportsTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const { data: reports, isLoading } = useQuery({
    queryKey: ["executive-reports"],
    queryFn: () => listBoardReports(50),
  });

  const { mutate: doDelete, isPending: deleting } = useMutation({
    mutationFn: deleteBoardReport,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["executive-reports"] }),
  });

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-muted-foreground">{t("exec.reportsSubtitle")}</p>
      </div>
      <BoardReportForm onSuccess={() => qc.invalidateQueries({ queryKey: ["executive-reports"] })} />
      {isLoading ? (
        <div className="flex justify-center py-10"><Spinner /></div>
      ) : !reports || reports.length === 0 ? (
        <Card><CardContent className="py-10 text-center text-sm text-muted-foreground">{t("reports.noReports")}</CardContent></Card>
      ) : (
        <div className="space-y-3">
          {reports.map((r) => (
            <Card key={r.id}>
              <CardContent className="flex items-start justify-between pt-4">
                <div className="flex gap-3">
                  <FileText className="mt-0.5 h-5 w-5 shrink-0 text-slate-400" />
                  <div>
                    <p className="font-medium">{r.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {r.period_start} → {r.period_end} · v{r.report_version} · Generated {new Date(r.generated_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                    </p>
                    <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{r.executive_summary}</p>
                  </div>
                </div>
                <div className="ml-4 flex shrink-0 gap-2 flex-wrap">
                  <PptxButton reportId={r.id} title={r.title} />
                  <a href={boardReportPdfUrl(r.id)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-slate-50">
                    <Download className="h-3.5 w-3.5" /> PDF
                  </a>
                  <ShareLinkButton reportId={r.id} />
                  {isAdmin && (
                    <button onClick={() => doDelete(r.id)} disabled={deleting} className="inline-flex items-center gap-1.5 rounded-md border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── TAB 3: Compliance Reports (CSRD/ESRS/CSDdD) ───────────────────────────────

const COMPLIANCE_REPORTS = [
  {
    id: "csrd_gap",
    path: "/compliance/reports/csrd-gap",
    filename: "csrd-gap-report.pdf",
    titleKey: "complianceReports.csrdTitle" as const,
    descKey: "complianceReports.csrdDesc" as const,
    framework: "CSRD",
    icon: FileBarChart2,
    color: "border-emerald-200 bg-emerald-50",
    iconBg: "bg-emerald-600",
    badgeColor: "bg-emerald-100 text-emerald-800",
    bullets: ["Article-level gap analysis", "Mandatory vs. voluntary obligations", "Coverage ratio per disclosure area", "Priority remediation list"],
  },
  {
    id: "esrs_readiness",
    path: "/compliance/reports/esrs-readiness",
    filename: "esrs-readiness-report.pdf",
    titleKey: "complianceReports.esrsTitle" as const,
    descKey: "complianceReports.esrsDesc" as const,
    framework: "ESRS",
    icon: ShieldCheck,
    color: "border-blue-200 bg-blue-50",
    iconBg: "bg-blue-600",
    badgeColor: "bg-blue-100 text-blue-800",
    bullets: ["E1–E5 Environmental standards", "S1–S4 Social standards", "G1 Governance standard", "Cross-cutting standards (ESRS 1 & 2)"],
  },
  {
    id: "csddd_due_diligence",
    path: "/compliance/reports/csddd-due-diligence",
    filename: "csddd-due-diligence-report.pdf",
    titleKey: "complianceReports.csdddTitle" as const,
    descKey: "complianceReports.csdddDesc" as const,
    framework: "CSDdD",
    icon: FileText,
    color: "border-violet-200 bg-violet-50",
    iconBg: "bg-violet-600",
    badgeColor: "bg-violet-100 text-violet-800",
    bullets: ["21 rights under Annex I", "Supply chain due diligence steps", "Remediation & preventive measures", "Human rights risk coverage"],
  },
] as const;

const COMPLIANCE_TYPE_LABELS: Record<string, string> = {
  csrd_gap: "CSRD Gap",
  esrs_readiness: "ESRS Readiness",
  csddd_due_diligence: "CSDdD Due Diligence",
};

function ComplianceReportCard({ report }: { report: (typeof COMPLIANCE_REPORTS)[number] }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const Icon = report.icon;

  async function generate() {
    setBusy(true); setDone(false); setError(null);
    try {
      await downloadPdf(report.path, report.filename);
      setDone(true);
      qc.invalidateQueries({ queryKey: ["compliance-reports-history"] });
      setTimeout(() => setDone(false), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("complianceReports.errorFailed"));
    } finally { setBusy(false); }
  }

  return (
    <Card className={`border-2 ${report.color} transition-shadow hover:shadow-md`}>
      <CardHeader className="pb-3">
        <div className="flex items-start gap-3">
          <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${report.iconBg} flex-shrink-0`}>
            <Icon className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <CardTitle className="text-base">{t(report.titleKey)}</CardTitle>
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${report.badgeColor}`}>{report.framework}</span>
            </div>
            <p className="mt-1 text-sm text-slate-600 leading-snug">{t(report.descKey)}</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="space-y-1">
          {report.bullets.map((b) => (
            <li key={b} className="flex items-center gap-2 text-xs text-slate-600">
              <span className="h-1.5 w-1.5 rounded-full bg-slate-400 flex-shrink-0" />{b}
            </li>
          ))}
        </ul>
        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />{error}
          </div>
        )}
        <Button onClick={generate} disabled={busy} className="w-full gap-2" variant={done ? "outline" : "default"}>
          {busy ? <><Spinner size="sm" />{t("complianceReports.generating")}</> : done ? <><CheckCircle2 className="h-4 w-4 text-emerald-600" />{t("complianceReports.download")}</> : <><Download className="h-4 w-4" />{t("complianceReports.generate")}</>}
        </Button>
      </CardContent>
    </Card>
  );
}

function ComplianceReportsTab() {
  const { t } = useLanguage();
  const [downloading, setDownloading] = useState<string | null>(null);

  const { data: history = [], isLoading } = useQuery<ComplianceReportSummary[]>({
    queryKey: ["compliance-reports-history"],
    queryFn: async () => {
      const res = await apiClient.get("/compliance/reports", { params: { limit: 50 } });
      return res.data;
    },
  });

  async function downloadHistorical(report: ComplianceReportSummary) {
    setDownloading(report.id);
    try {
      const label = COMPLIANCE_TYPE_LABELS[report.report_type] ?? report.report_type;
      const date = new Date(report.generated_at).toISOString().split("T")[0];
      await downloadPdf(`/compliance/reports/${report.id}/download`, `${label.toLowerCase().replace(/\s+/g, "-")}-${date}.pdf`);
    } catch { /* silent */ }
    finally { setDownloading(null); }
  }

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm text-muted-foreground">{t("complianceReports.subtitle")}</p>
      </div>
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        {COMPLIANCE_REPORTS.map((r) => <ComplianceReportCard key={r.id} report={r} />)}
      </div>
      <div className="space-y-4">
        <h2 className="text-base font-semibold text-slate-800">{t("complianceReports.history")}</h2>
        {isLoading ? (
          <div className="flex justify-center py-10"><Spinner size="lg" /></div>
        ) : history.length === 0 ? (
          <div className="rounded-lg border border-dashed p-10 text-center text-sm text-slate-400">{t("complianceReports.historyEmpty")}</div>
        ) : (
          <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                  <th className="px-4 py-3">{t("complianceReports.type")}</th>
                  <th className="px-4 py-3">{t("complianceReports.framework")}</th>
                  <th className="px-4 py-3">{t("complianceReports.generatedAt")}</th>
                  <th className="px-4 py-3">{t("complianceReports.hash")}</th>
                  <th className="px-4 py-3 text-right">{t("common.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {history.map((r) => (
                  <tr key={r.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <FileBarChart2 className="h-4 w-4 text-slate-400 flex-shrink-0" />
                        <span className="font-medium text-slate-800">{COMPLIANCE_TYPE_LABELS[r.report_type] ?? r.report_type}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">{r.framework_code}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5 text-slate-600">
                        <Clock className="h-3.5 w-3.5 text-slate-400" />{new Date(r.generated_at).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-[11px] text-slate-400" title={r.report_hash}>{r.report_hash.slice(0, 10)}…</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => downloadHistorical(r)} disabled={downloading === r.id} className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50 transition-colors">
                        {downloading === r.id ? <><Spinner size="sm" />{t("complianceReports.downloading")}</> : <><Download className="h-3.5 w-3.5" />{t("complianceReports.download")}</>}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ── TAB 4: Sustainability Reports ─────────────────────────────────────────────

const SUSTAIN_ORG_ID = "default";

function SustainReportCard({ report }: { report: SustainabilityReport }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const finalize = useMutation({
    mutationFn: () => finalizeReport(SUSTAIN_ORG_ID, report.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sustain-reports", SUSTAIN_ORG_ID] }),
  });

  const kpiSummary = report.kpi_summary as Record<string, unknown>;
  const emissionsSummary = report.emissions_summary as Record<string, unknown>;
  const objStatus = report.objective_status as Record<string, unknown>;

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold">{report.title}</p>
          <p className="text-xs text-muted-foreground">
            {new Date(report.period_start).toLocaleDateString()} – {new Date(report.period_end).toLocaleDateString()} · {report.report_type}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`rounded px-2 py-0.5 text-xs font-medium ${ragColor(report.overall_status)}`}>{report.overall_status}</span>
          {report.is_final && (
            <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
              <Lock className="h-3 w-3" /> Finalized
            </span>
          )}
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3 text-xs">
        {kpiSummary.total_active_kpis != null && (
          <div className="rounded bg-muted p-2">
            <p className="text-muted-foreground">{t("sustain.kpisTitle")}</p>
            <p className="font-bold">{String(kpiSummary.total_active_kpis)}</p>
          </div>
        )}
        {emissionsSummary.total_emissions != null && (
          <div className="rounded bg-muted p-2">
            <p className="text-muted-foreground">{t("scope3.totalEmissions")}</p>
            <p className="font-bold">{Number(emissionsSummary.total_emissions).toLocaleString()} tCO₂e</p>
          </div>
        )}
        {(objStatus.completion_rate_pct as number) != null && (
          <div className="rounded bg-muted p-2">
            <p className="text-muted-foreground">Obj. Completion</p>
            <p className="font-bold">{Number(objStatus.completion_rate_pct).toFixed(1)}%</p>
          </div>
        )}
      </div>
      {!report.is_final && (
        <Button size="sm" variant="outline" onClick={() => finalize.mutate()} disabled={finalize.isPending}>
          <Lock className="mr-1 h-3 w-3" />
          {finalize.isPending ? "Finalizing…" : "Finalize (Immutable)"}
        </Button>
      )}
      {report.is_final && report.finalized_at && (
        <p className="text-xs text-muted-foreground">Finalized {new Date(report.finalized_at).toLocaleDateString()} · Read-only</p>
      )}
    </div>
  );
}

function SustainabilityReportsTab() {
  const { t } = useLanguage();
  const [sendingNow, setSendingNow] = useState(false);
  const [sentNow, setSentNow] = useState(false);

  const { data: reports, isLoading } = useQuery({
    queryKey: ["sustain-reports", SUSTAIN_ORG_ID],
    queryFn: () => listSustainReports(SUSTAIN_ORG_ID),
  });

  const finalized = reports?.filter((r) => r.is_final).length ?? 0;
  const draft = (reports?.length ?? 0) - finalized;

  async function sendQuarterlyNow() {
    setSendingNow(true);
    try {
      const stored = JSON.parse(localStorage.getItem("eios_automation_rules") ?? "{}");
      await apiClient.post("/automations/trigger", {
        rule_id: "quarterly_sustainability",
        entity_type: "org",
        entity_id: SUSTAIN_ORG_ID,
        payload: {
          recipients: stored?.quarterly_sustainability?.config?.recipients ?? "",
          include_charts: stored?.quarterly_sustainability?.config?.include_charts ?? true,
          triggered_manually: true,
        },
      });
      setSentNow(true);
      setTimeout(() => setSentNow(false), 3000);
    } catch { /* silent */ }
    finally { setSendingNow(false); }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <p className="text-sm text-muted-foreground">{t("sustain.reportsSubtitle")}</p>
        <Button variant="outline" size="sm" className="gap-1.5 border-emerald-300 text-emerald-700 hover:bg-emerald-50" onClick={sendQuarterlyNow} disabled={sendingNow}>
          <Send className="h-3.5 w-3.5" />
          {sentNow ? "Sent!" : sendingNow ? "Sending…" : t("reports.generate")}
        </Button>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">{t("reports.title")}</p><p className="text-2xl font-bold">{reports?.length ?? 0}</p></CardContent></Card>
        <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">{t("dpp.draft")}</p><p className="text-2xl font-bold text-amber-600">{draft}</p></CardContent></Card>
        <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Finalized</p><p className="text-2xl font-bold text-emerald-600">{finalized}</p></CardContent></Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4" />{t("sustain.reportsTitle")}{reports ? ` (${reports.length})` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <Spinner />}
          {reports?.length === 0 && <p className="text-sm text-muted-foreground">{t("sustain.noReportsDesc")}</p>}
          <div className="space-y-3">
            {reports?.map((r) => <SustainReportCard key={r.id} report={r} />)}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── TAB 5: Financial ESG Reports ─────────────────────────────────────────────

function FinancialEsgReportsTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";

  const { data: reports, isLoading: l1 } = useQuery({ queryKey: ["fin-esg", "reports", orgId], queryFn: () => listFinReports(orgId) });
  const { data: scenarios, isLoading: l2 } = useQuery({ queryKey: ["fin-esg", "scenarios", orgId], queryFn: () => listFinScenarios(orgId) });
  const { data: correlations, isLoading: l3 } = useQuery({ queryKey: ["fin-esg", "correlations", orgId], queryFn: () => listCorrelations(orgId) });

  if (l1 || l2 || l3) return <div className="flex h-64 items-center justify-center"><Spinner /></div>;

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">Reports, scenario analyses, and ESG–financial correlations</p>
      <Card>
        <CardHeader><CardTitle>{t("reports.title")}</CardTitle></CardHeader>
        <CardContent>
          {(reports ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("finEsg.noReports")}</p>
          ) : (
            <div className="space-y-2">
              {(reports ?? []).map((r) => (
                <div key={r.id} className="flex items-center justify-between rounded border px-4 py-3">
                  <div>
                    <p className="font-medium">{r.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(r.report_period_start).toLocaleDateString()} – {new Date(r.report_period_end).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${r.is_final ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-600"}`}>{r.overall_status}</span>
                    <p className="mt-1 text-xs text-muted-foreground">{new Date(r.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Scenario Analyses</CardTitle></CardHeader>
          <CardContent>
            {(scenarios ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("strategy.noScenarios")}</p>
            ) : (
              <div className="space-y-2">
                {(scenarios ?? []).map((s) => (
                  <div key={s.id} className="rounded border px-3 py-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{s.scenario_name}</p>
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{s.scenario_type.replace(/_/g, " ")}</span>
                    </div>
                    {s.outputs && (
                      <div className="mt-1 text-xs text-muted-foreground">
                        {Object.entries(s.outputs as Record<string, unknown>).filter(([k]) => k !== "formula").map(([k, v]) => `${k}: ${v}`).join(" · ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">ESG Financial Correlations</CardTitle></CardHeader>
          <CardContent>
            {(correlations ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No correlations</p>
            ) : (
              <div className="space-y-2">
                {(correlations ?? []).map((c) => (
                  <div key={c.id} className="rounded border px-3 py-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{c.correlation_period}</p>
                      <span className={`text-sm font-bold ${(c.correlation_coefficient ?? 0) > 0 ? "text-green-600" : "text-red-600"}`}>
                        r = {c.correlation_coefficient?.toFixed(4) ?? "—"}
                      </span>
                    </div>
                    <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
                      <span>ESG: {c.esg_score}</span>
                      <span>Risk ↓: {c.risk_reduction}%</span>
                      <span>Cost ↓: {c.cost_reduction}%</span>
                    </div>
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

// ── TAB 6: Strategy Reports ───────────────────────────────────────────────────

function CreateStrategyReportModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const { data: scenarios } = useQuery({ queryKey: ["strategy", "scenarios", orgId], queryFn: () => listStratScenarios(orgId) });
  const currentYear = new Date().getFullYear();
  const [form, setForm] = useState({ report_title: "", report_period: String(currentYear), report_methodology: "", selected_scenario_ids: [] as string[] });
  const [error, setError] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: (p: CreateReportPayload) => createReport(orgId, p),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["strategy", "reports", orgId] }); onClose(); },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Fehler"),
  });

  function toggleScenario(id: string) {
    setForm((f) => ({
      ...f,
      selected_scenario_ids: f.selected_scenario_ids.includes(id)
        ? f.selected_scenario_ids.filter((x) => x !== id)
        : [...f.selected_scenario_ids, id],
    }));
  }

  function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    if (!form.report_title.trim()) { setError("Titel erforderlich"); return; }
    mut.mutate({
      report_title: form.report_title.trim(),
      report_period: form.report_period.trim(),
      included_scenario_ids: form.selected_scenario_ids.length > 0 ? form.selected_scenario_ids : undefined,
      report_methodology: form.report_methodology.trim() || undefined,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-violet-600" />
            <h2 className="text-lg font-semibold">Neuer Strategiebericht</h2>
          </div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100"><X className="h-5 w-5 text-slate-500" /></button>
        </div>
        <form onSubmit={submit} className="space-y-5 px-6 py-5">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("common.title")} <span className="text-red-500">*</span></label>
            <input value={form.report_title} onChange={(e) => setForm((f) => ({ ...f, report_title: e.target.value }))} placeholder="z. B. Strategie-Review Q4 2026" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Berichtszeitraum <span className="text-red-500">*</span></label>
            <input value={form.report_period} onChange={(e) => setForm((f) => ({ ...f, report_period: e.target.value }))} placeholder="z. B. 2026 oder Q4-2026" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          {(scenarios ?? []).length > 0 && (
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Szenarien einschließen</label>
              <div className="max-h-36 space-y-1.5 overflow-y-auto rounded-lg border p-2">
                {(scenarios ?? []).map((s) => (
                  <label key={s.id} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 hover:bg-slate-50">
                    <input type="checkbox" checked={form.selected_scenario_ids.includes(s.id)} onChange={() => toggleScenario(s.id)} className="h-4 w-4 rounded border-slate-300 text-violet-600" />
                    <span className="text-sm">{s.name}</span>
                  </label>
                ))}
              </div>
              {form.selected_scenario_ids.length > 0 && (
                <p className="mt-1 text-xs text-violet-600">{form.selected_scenario_ids.length} Szenario(s) ausgewählt</p>
              )}
            </div>
          )}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Methodik (optional)</label>
            <input value={form.report_methodology} onChange={(e) => setForm((f) => ({ ...f, report_methodology: e.target.value }))} placeholder="z. B. SBTi, TCFD, GRI" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          <div className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">
            Der Bericht wird als Draft erstellt. Zum Finalisieren muss er separat abgeschlossen werden.
          </div>
          {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        </form>
        <div className="flex justify-end gap-3 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose}>{t("common.cancel")}</Button>
          <Button onClick={submit} disabled={mut.isPending} className="bg-violet-600 hover:bg-violet-700">
            {mut.isPending ? <Spinner className="h-4 w-4" /> : "Bericht erstellen"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function StrategyReportsTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";
  const [showCreate, setShowCreate] = useState(false);

  const { data: reports, isLoading } = useQuery({ queryKey: ["strategy", "reports", orgId], queryFn: () => listStratReports(orgId) });

  if (isLoading) return <div className="flex h-64 items-center justify-center"><Spinner /></div>;

  const finalized = (reports ?? []).filter((r) => r.is_final);
  const drafts = (reports ?? []).filter((r) => !r.is_final);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <p className="text-sm text-muted-foreground">Unveränderliche Szenario-Reports für Audit und Board</p>
        <Button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700">
          <Plus className="h-4 w-4" />{t("reports.newReport")}
        </Button>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">{t("common.total")}</p><p className="mt-1 text-3xl font-bold">{(reports ?? []).length}</p></CardContent></Card>
        <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Finalisiert</p><p className="mt-1 text-3xl font-bold text-blue-600">{finalized.length}</p></CardContent></Card>
        <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Entwurf</p><p className="mt-1 text-3xl font-bold text-slate-500">{drafts.length}</p></CardContent></Card>
      </div>
      <Card>
        <CardHeader><CardTitle>{t("reports.title")}</CardTitle></CardHeader>
        <CardContent>
          {(reports ?? []).length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <FileText className="h-10 w-10 text-slate-300" />
              <p className="text-sm text-slate-600">Noch kein Strategiebericht erstellt</p>
              <Button onClick={() => setShowCreate(true)} className="mt-1 bg-violet-600 hover:bg-violet-700">
                <Plus className="mr-2 h-4 w-4" />Ersten Bericht erstellen
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {(reports ?? []).map((r) => (
                <div key={r.id} className="flex items-start justify-between rounded-lg border px-4 py-3 transition-colors hover:bg-slate-50">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{r.report_title}</p>
                      {r.is_final ? (
                        <span className="flex items-center gap-1 rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700"><Lock className="h-2.5 w-2.5" />FINAL</span>
                      ) : (
                        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">Entwurf</span>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">Zeitraum: {r.report_period}</p>
                    {r.report_methodology && <p className="mt-0.5 text-xs text-muted-foreground">Methodik: {r.report_methodology}</p>}
                  </div>
                  <div className="ml-4 flex-shrink-0 text-right text-xs text-muted-foreground">
                    <p>{new Date(r.created_at).toLocaleDateString("de-DE")}</p>
                    {r.finalized_at && <p className="text-blue-600">Finalisiert {new Date(r.finalized_at).toLocaleDateString("de-DE")}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      {showCreate && <CreateStrategyReportModal orgId={orgId} onClose={() => setShowCreate(false)} />}
    </div>
  );
}

// ── TAB 7: AI Governance / Assurance Reports ──────────────────────────────────

const AI_GOV_ORG_ID = "default";

function AiGovernanceReportsTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", period_start: "", period_end: "" });

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ["ai-assurance-reports", AI_GOV_ORG_ID],
    queryFn: () => listAssuranceReports(AI_GOV_ORG_ID),
    retry: false,
  });

  const generate = useMutation({
    mutationFn: () =>
      generateAssuranceReport(AI_GOV_ORG_ID, {
        title: form.title,
        period_start: new Date(form.period_start).toISOString(),
        period_end: new Date(form.period_end).toISOString(),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-assurance-reports", AI_GOV_ORG_ID] });
      setShowForm(false);
      setForm({ title: "", period_start: "", period_end: "" });
    },
  });

  if (isLoading) return <div className="flex justify-center py-10"><Spinner /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <p className="text-sm text-muted-foreground">{t("aiGov.reportsSubtitle")}</p>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="mr-1 h-4 w-4" /> {t("reports.generate")}
        </Button>
      </div>
      {showForm && (
        <Card>
          <CardHeader><CardTitle className="text-base">{t("reports.newReport")}</CardTitle></CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">{t("common.title")}</label>
                <input className="w-full rounded border border-input px-3 py-2 text-sm" placeholder="Q2 2026 AI Assurance" value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Period Start</label>
                <input type="date" className="w-full rounded border border-input px-3 py-2 text-sm" value={form.period_start} onChange={(e) => setForm((f) => ({ ...f, period_start: e.target.value }))} />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Period End</label>
                <input type="date" className="w-full rounded border border-input px-3 py-2 text-sm" value={form.period_end} onChange={(e) => setForm((f) => ({ ...f, period_end: e.target.value }))} />
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <Button size="sm" onClick={() => generate.mutate()} disabled={!form.title || !form.period_start || !form.period_end || generate.isPending}>
                {generate.isPending ? "Generating…" : t("reports.generate")}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>{t("common.cancel")}</Button>
            </div>
          </CardContent>
        </Card>
      )}
      {reports.length === 0 ? (
        <div className="py-16 text-center text-muted-foreground">
          <FileText className="mx-auto mb-3 h-10 w-10 opacity-30" />
          <p className="text-sm">{t("reports.noReports")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((r) => (
            <Card key={r.id}>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold">{r.title}</p>
                      <Badge className={aiStatusColor(r.overall_status)}>{r.overall_status.replace("_", " ")}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {new Date(r.report_period_start).toLocaleDateString()} – {new Date(r.report_period_end).toLocaleDateString()}
                    </p>
                    <div className="flex gap-4 text-xs text-muted-foreground pt-1">
                      <span>{r.model_count} models</span>
                      <span>{r.use_case_count} use cases</span>
                      <span>{r.control_count} controls</span>
                      <span>{r.incident_count} incidents</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Tab nav ───────────────────────────────────────────────────────────────────

const tab_defs = [
  { key: "disclosure",    label: "Disclosure & Packages" },
  { key: "executive",     label: "Executive / Board" },
  { key: "compliance",    label: "Compliance (CSRD/ESRS)" },
  { key: "sustainability",label: "Sustainability" },
  { key: "financial",     label: "Financial ESG" },
  { key: "strategy",      label: "Strategy" },
  { key: "ai",            label: "AI Governance" },
] as const;

type TabKey = (typeof tab_defs)[number]["key"];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ReportsCenterPage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<TabKey>("disclosure");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("reports.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("reports.subtitle")}</p>
        </div>
        <CopilotDrawer contextType="disclosure" contextSummary="Reports Hub — ESG & regulatory disclosure drafting" />
      </div>

      {/* Tab bar */}
      <div className="border-b border-border">
        <nav className="-mb-px flex gap-0 overflow-x-auto">
          {tab_defs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "disclosure"     && <DisclosureTab />}
        {activeTab === "executive"      && <ExecutiveReportsTab />}
        {activeTab === "compliance"     && <ComplianceReportsTab />}
        {activeTab === "sustainability" && <SustainabilityReportsTab />}
        {activeTab === "financial"      && <FinancialEsgReportsTab />}
        {activeTab === "strategy"       && <StrategyReportsTab />}
        {activeTab === "ai"             && <AiGovernanceReportsTab />}
      </div>
    </div>
  );
}
