"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import {
  AlertCircle,
  ArrowRight,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Download,
  Eye,
  FileJson,
  FileText,
  Globe,
  Loader2,
  Plus,
  Shield,
  X,
  XCircle,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

// ── Download helper (authenticated) ──────────────────────────────────────────

async function authenticatedDownload(url: string, filename: string) {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("eios_access_token")
      : null;

  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `Download failed (${res.status})`);
  }

  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(blobUrl);
}

// ── #96 Complete Disclosure Wizard ───────────────────────────────────────────

function CompleteDisclosureWizard({
  framework,
  onClose,
}: {
  framework: FrameworkDisclosureSummary;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);

  const { data: requirements, isLoading } = useQuery<DisclosureRequirement[]>({
    queryKey: ["disclosure-requirements", framework.framework_id],
    queryFn: async () => {
      const r = await apiClient.get(
        `/api/v1/reporting/frameworks/${framework.framework_id}/requirements`,
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
      await apiClient.post("/api/v1/reporting/responses", {
        requirement_id: req.id,
      });
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
        `/api/v1/reporting/responses?requirement_id=${req.id}&limit=1`,
      );
      const respId = listR.data?.[0]?.id;
      if (respId) {
        await apiClient.post(`/api/v1/reporting/responses/${respId}/submit`, {});
        qc.invalidateQueries({ queryKey: ["disclosure-requirements", framework.framework_id] });
        qc.invalidateQueries({ queryKey: ["disclosure-dashboard"] });
        if (step < incomplete.length - 1) setStep((s) => s + 1);
      }
    } catch { /* ignore */ }
    finally { setBusy(null); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="w-full max-w-2xl rounded-xl bg-background border border-border shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <p className="font-semibold">{framework.framework_name}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Step-by-step disclosure completion
            </p>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Progress */}
        <div className="px-5 py-3 border-b border-border bg-muted/30">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
            <span>{done} of {total} requirements complete</span>
            <span className="font-semibold text-foreground">{pct}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-blue-500"}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="mt-2 flex gap-3 text-[10px]">
            {[
              { label: "Published", val: published, cls: "text-emerald-600" },
              { label: "Approved", val: approved, cls: "text-blue-600" },
              { label: "In Review", val: inReview, cls: "text-amber-600" },
              { label: "Remaining", val: incomplete.length, cls: "text-muted-foreground" },
            ].map(({ label, val, cls }) => (
              <span key={label} className={cls}><span className="font-semibold">{val}</span> {label}</span>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-5">
          {isLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : incomplete.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-500 mb-3" />
              <p className="font-medium">All requirements addressed!</p>
              <p className="text-xs text-muted-foreground mt-1">
                {inReview} in review · {approved} approved · {published} published
              </p>
            </div>
          ) : current ? (
            <div className="space-y-4">
              {/* Navigation */}
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <button
                  onClick={() => setStep((s) => Math.max(0, s - 1))}
                  disabled={step === 0}
                  className="flex items-center gap-1 hover:text-foreground disabled:opacity-40"
                >
                  ← Previous
                </button>
                <span>Requirement {step + 1} of {incomplete.length} remaining</span>
                <button
                  onClick={() => setStep((s) => Math.min(incomplete.length - 1, s + 1))}
                  disabled={step === incomplete.length - 1}
                  className="flex items-center gap-1 hover:text-foreground disabled:opacity-40"
                >
                  Next →
                </button>
              </div>

              {/* Requirement card */}
              <div className="rounded-lg border border-border p-4 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-mono font-medium text-slate-600">
                        {current.reference}
                      </span>
                      <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700">
                        {current.category}
                      </span>
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${current.status === "Draft" ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-600"}`}>
                        {current.status}
                      </span>
                    </div>
                    <p className="font-medium text-sm">{current.title}</p>
                    {current.description && (
                      <p className="mt-1.5 text-xs text-muted-foreground line-clamp-3">
                        {current.description}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  {current.status === "Not Started" ? (
                    <Button
                      size="sm"
                      onClick={() => handleBegin(current)}
                      disabled={busy === current.id}
                      className="gap-1.5 text-xs"
                    >
                      {busy === current.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ArrowRight className="h-3.5 w-3.5" />}
                      Begin Draft
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      onClick={() => handleSubmit(current)}
                      disabled={busy === current.id + "-submit"}
                      className="gap-1.5 text-xs"
                    >
                      {busy === current.id + "-submit" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ChevronRight className="h-3.5 w-3.5" />}
                      Submit for Review
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setStep((s) => Math.min(incomplete.length - 1, s + 1))}
                    className="text-xs text-muted-foreground"
                    disabled={step === incomplete.length - 1}
                  >
                    Skip for now
                  </Button>
                </div>
              </div>

              {/* Remaining list preview */}
              {incomplete.length > 1 && (
                <div className="space-y-1">
                  <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                    Remaining requirements
                  </p>
                  <div className="max-h-32 overflow-y-auto space-y-1">
                    {incomplete.map((r, i) => (
                      <button
                        key={r.id}
                        onClick={() => setStep(i)}
                        className={`w-full text-left rounded px-2 py-1.5 text-xs transition-colors flex items-center gap-2 ${i === step ? "bg-primary/10 text-primary" : "hover:bg-muted/50 text-muted-foreground"}`}
                      >
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

// ── #95 Disclosure gap analysis ───────────────────────────────────────────────

function DisclosureGapAnalysis() {
  const [wizard, setWizard] = useState<FrameworkDisclosureSummary | null>(null);

  const { data: dashboard, isLoading } = useQuery<DisclosureDashboardResponse>({
    queryKey: ["disclosure-dashboard"],
    queryFn: async () => {
      const r = await apiClient.get("/api/v1/reporting/dashboard");
      return r.data;
    },
    staleTime: 60_000,
    retry: false,
  });

  if (isLoading) {
    return (
      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Disclosure Gap Analysis
        </h2>
        <Card><CardContent className="flex justify-center py-8"><Spinner /></CardContent></Card>
      </section>
    );
  }

  if (!dashboard || dashboard.frameworks.length === 0) return null;

  const overall = Math.round(dashboard.overall_completion_pct);

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Disclosure Gap Analysis
        </h2>
        <span className="text-xs text-muted-foreground">
          {dashboard.total_requirements} total requirements across {dashboard.frameworks.length} frameworks
        </span>
      </div>

      {/* Overall hero */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-6">
            <div className="text-center">
              <p className={`text-3xl font-bold ${overall >= 80 ? "text-emerald-600" : overall >= 50 ? "text-amber-600" : "text-red-600"}`}>
                {overall}%
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">Overall Coverage</p>
            </div>
            <div className="flex-1">
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>Current</span>
                <span>Required: 100%</span>
              </div>
              <div className="h-3 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${overall >= 80 ? "bg-emerald-500" : overall >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                  style={{ width: `${overall}%` }}
                />
              </div>
              <div className="mt-2 flex gap-4 text-[10px]">
                {[
                  { label: "Published", val: dashboard.total_published, cls: "text-emerald-600 font-semibold" },
                  { label: "Approved", val: dashboard.total_approved, cls: "text-blue-600" },
                  { label: "Draft", val: dashboard.total_draft, cls: "text-amber-600" },
                  { label: "Not Started", val: dashboard.total_not_started, cls: "text-slate-500" },
                ].map(({ label, val, cls }) => (
                  <span key={label} className={cls}>{val} {label}</span>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Per-framework table */}
      <Card>
        <CardContent className="pt-4 pb-2">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="pb-2 text-left text-xs font-medium text-muted-foreground">Framework</th>
                  <th className="pb-2 text-right text-xs font-medium text-muted-foreground">Current</th>
                  <th className="pb-2 text-right text-xs font-medium text-muted-foreground">Gap</th>
                  <th className="pb-2 text-left text-xs font-medium text-muted-foreground px-4">Status Breakdown</th>
                  <th className="pb-2 text-center text-xs font-medium text-muted-foreground">Blockers</th>
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
                        <span className={`text-sm font-semibold ${pct >= 80 ? "text-emerald-600" : pct >= 50 ? "text-amber-600" : "text-red-600"}`}>
                          {pct}%
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-right">
                        <span className={`text-xs font-medium ${gapCls}`}>
                          {gap === 0 ? "✓ Complete" : `−${gap}%`}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {/* Stacked mini bar */}
                        <div className="flex h-2 w-36 rounded-full overflow-hidden gap-px">
                          {fw.published > 0 && <div className="bg-emerald-500" style={{ width: `${(fw.published / total) * 100}%` }} title={`Published: ${fw.published}`} />}
                          {fw.approved > 0 && <div className="bg-blue-400" style={{ width: `${(fw.approved / total) * 100}%` }} title={`Approved: ${fw.approved}`} />}
                          {fw.in_review > 0 && <div className="bg-amber-400" style={{ width: `${(fw.in_review / total) * 100}%` }} title={`In Review: ${fw.in_review}`} />}
                          {fw.draft > 0 && <div className="bg-slate-300" style={{ width: `${(fw.draft / total) * 100}%` }} title={`Draft: ${fw.draft}`} />}
                          {fw.not_started > 0 && <div className="bg-slate-100" style={{ width: `${(fw.not_started / total) * 100}%` }} title={`Not Started: ${fw.not_started}`} />}
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
                          <button
                            onClick={() => setWizard(fw)}
                            className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 transition-colors"
                          >
                            Complete <ChevronRight className="h-3.5 w-3.5" />
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

      {/* Wizard modal */}
      {wizard && (
        <CompleteDisclosureWizard
          framework={wizard}
          onClose={() => setWizard(null)}
        />
      )}
    </section>
  );
}

// ── Report type definitions ───────────────────────────────────────────────────

const DIRECT_REPORTS = [
  {
    id: "tcfd",
    name: "TCFD Climate Report",
    description:
      "Task Force on Climate-related Financial Disclosures report (JSON)",
    icon: Globe,
    color: "bg-teal-50 text-teal-700 border-teal-200",
    iconColor: "text-teal-600",
    action: async (year: number) => {
      await authenticatedDownload(
        `/api/v1/executive/tcfd?reporting_year=${year}`,
        `tcfd_report_${year}.json`,
      );
    },
  },
  {
    id: "sfdr-pai",
    name: "SFDR PAI Calculation",
    description:
      "Sustainable Finance Disclosure Regulation Principal Adverse Impacts",
    icon: Shield,
    color: "bg-purple-50 text-purple-700 border-purple-200",
    iconColor: "text-purple-600",
    action: async (year: number) => {
      const start = `${year}-01-01`;
      const end = `${year}-12-31`;
      await authenticatedDownload(
        `/api/v1/financial-esg/sfdr/pai?reference_period_start=${start}&reference_period_end=${end}`,
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
      await authenticatedDownload(
        `/api/v1/audit/events/export?format=csv`,
        `audit_trail.csv`,
      );
    },
  },
] as const;

// ── CDP Module card (#99) ─────────────────────────────────────────────────────

function CDPModuleCard() {
  const { data: settings } = useQuery({
    queryKey: ["org-settings-cdp"],
    queryFn: async () => {
      try {
        const r = await apiClient.get("/api/v1/commercial/organizations/me/settings");
        return r.data;
      } catch { return null; }
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
            <p className="font-medium text-sm">CDP Climate Report</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Carbon Disclosure Project annual submission
            </p>
          </div>
        </div>
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-amber-800">
            <span>Module Completion</span>
            <span className="font-semibold">{completedCount}/{CDP_MODULES.length}</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-amber-200 overflow-hidden">
            <div className="h-full rounded-full bg-amber-500 transition-all" style={{ width: `${pct}%` }} />
          </div>
        </div>
        <div className="space-y-1">
          {CDP_MODULES.map((m) => (
            <div key={m.name} className="flex items-center gap-2 text-xs">
              {m.complete
                ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 flex-shrink-0" />
                : <XCircle className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" />}
              <span className={m.complete ? "text-amber-900" : "text-amber-700"}>{m.name}</span>
            </div>
          ))}
        </div>
        {!cdpConnected && (
          <p className="text-xs text-amber-700">
            Connect CDP integration in Settings → Integrations to complete modules.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ── Direct report card ────────────────────────────────────────────────────────

function DirectReportCard({
  report,
}: {
  report: (typeof DIRECT_REPORTS)[number];
}) {
  const { t } = useLanguage();
  const [year, setYear] = useState(new Date().getFullYear() - 1);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState<Record<string, unknown> | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  async function handleDownload() {
    setDownloading(true);
    setError(null);
    setSuccess(false);
    try {
      await report.action(year);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  }

  async function handlePreview() {
    if (previewOpen) { setPreviewOpen(false); return; }
    setPreviewLoading(true);
    try {
      const r = await apiClient.get(`/api/v1/executive/tcfd?reporting_year=${year}`);
      setPreviewData(r.data);
      setPreviewOpen(true);
    } catch { setError("Preview unavailable"); }
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
            <p className="mt-0.5 text-xs text-muted-foreground">
              {report.description}
            </p>
            {error && (
              <p className="mt-1.5 text-xs text-red-600 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" /> {error}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {report.id !== "audit-csv" && (
              <select
                className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
              >
                {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 1 - i).map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            )}
            {/* #97 TCFD in-browser preview button */}
            {report.id === "tcfd" && (
              <Button
                size="sm"
                variant="ghost"
                onClick={handlePreview}
                disabled={previewLoading}
                className="gap-1.5 text-xs"
                title="Preview in browser"
              >
                {previewLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Eye className="h-3.5 w-3.5" />}
                {previewOpen ? "Hide" : "Preview"}
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={handleDownload}
              disabled={downloading}
              className="gap-1.5 text-xs"
            >
              {downloading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : success ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
              ) : (
                <Download className="h-3.5 w-3.5" />
              )}
              {success ? "Downloaded" : t("common.export")}
            </Button>
          </div>
        </div>

        {/* #97 TCFD in-browser preview panel */}
        {previewOpen && previewData && (
          <div className="rounded-lg border border-teal-200 bg-teal-50/40 p-4 space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <p className="font-semibold text-teal-800">TCFD Report Preview — {year}</p>
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
            <p className="text-teal-600 text-[10px]">Full data available via Export.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Disclosure packages section ───────────────────────────────────────────────

function PackageExportButtons({ pkg }: { pkg: DisclosurePackage }) {
  const [busy, setBusy] = useState<"ixbrl" | "gri" | "json" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function doExport(format: "xbrl" | "gri" | "json") {
    setBusy(format === "xbrl" ? "ixbrl" : (format as "gri" | "json"));
    setError(null);
    try {
      const ext = format === "xbrl" ? "html" : format;
      const name = `${pkg.package_name.replace(/\s+/g, "_").toLowerCase()}_${format}.${ext}`;
      await authenticatedDownload(
        `/api/v1/disclosure/packages/${pkg.id}/export?format=${format}`,
        name,
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex items-center gap-2">
      {error && (
        <span className="text-xs text-red-500">{error}</span>
      )}
      <Button
        size="sm"
        variant="outline"
        className="gap-1 text-xs"
        disabled={!!busy}
        onClick={() => doExport("xbrl")}
      >
        {busy === "ixbrl" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />}
        iXBRL
      </Button>
      <Button
        size="sm"
        variant="outline"
        className="gap-1 text-xs"
        disabled={!!busy}
        onClick={() => doExport("gri")}
      >
        {busy === "gri" ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileJson className="h-3 w-3" />}
        GRI
      </Button>
      <Button
        size="sm"
        variant="outline"
        className="gap-1 text-xs"
        disabled={!!busy}
        onClick={() => doExport("json")}
      >
        {busy === "json" ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileJson className="h-3 w-3" />}
        JSON
      </Button>
    </div>
  );
}

function GeneratePackageForm({ onSuccess }: { onSuccess: () => void }) {
  const { t } = useLanguage();
  const [name, setName] = useState("CSRD Annual Report");
  const [frameworks, setFrameworks] = useState("CSRD,GRI");
  const [pubDate, setPubDate] = useState(() => {
    const d = new Date();
    return d.toISOString().split("T")[0];
  });
  const [error, setError] = useState<string | null>(null);

  const { mutate, isPending } = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/api/v1/disclosure/packages/generate", {
        package_name: name,
        framework_codes: frameworks.split(",").map((f) => f.trim()),
        publication_date: pubDate,
      });
      return res.data;
    },
    onSuccess: () => {
      setError(null);
      onSuccess();
    },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <div className="rounded-lg border border-dashed border-border p-5 space-y-4">
      <p className="text-sm font-medium">Generate New Reporting Package</p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <Label className="text-xs">Package Name</Label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="CSRD Annual Report"
            className="mt-1 h-8 text-sm"
          />
        </div>
        <div>
          <Label className="text-xs">Frameworks (comma-separated)</Label>
          <Input
            value={frameworks}
            onChange={(e) => setFrameworks(e.target.value)}
            placeholder="CSRD,GRI"
            className="mt-1 h-8 text-sm"
          />
        </div>
        <div>
          <Label className="text-xs">Publication Date</Label>
          <Input
            type="date"
            value={pubDate}
            onChange={(e) => setPubDate(e.target.value)}
            className="mt-1 h-8 text-sm"
          />
        </div>
      </div>
      {error && (
        <p className="text-xs text-red-600 flex items-center gap-1">
          <AlertCircle className="h-3 w-3" /> {error}
        </p>
      )}
      <Button size="sm" disabled={isPending} onClick={() => mutate()} className="gap-1.5">
        {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
        {t("reports.generate")}
      </Button>
    </div>
  );
}

function statusColor(status: string) {
  const m: Record<string, string> = {
    DRAFT: "bg-slate-100 text-slate-600",
    IN_REVIEW: "bg-blue-100 text-blue-700",
    APPROVED: "bg-emerald-100 text-emerald-700",
    PUBLISHED: "bg-green-100 text-green-700",
  };
  return m[status] ?? "bg-slate-100 text-slate-600";
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ReportsCenterPage() {
  const qc = useQueryClient();
  const { t } = useLanguage();

  const { data: packages, isLoading } = useQuery<DisclosurePackage[]>({
    queryKey: ["disclosure-packages"],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/disclosure/packages?limit=50");
      return res.data;
    },
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("reports.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Generate and download all regulatory and compliance reports
          </p>
        </div>
        <div className="flex items-center gap-2">
          <CopilotDrawer
            contextType="disclosure"
            contextSummary="Reports Center — ESG & regulatory disclosure drafting"
          />
          <Button asChild variant="outline" size="sm">
            <Link href="/executive/reports">
              <FileText className="mr-1.5 h-4 w-4" />
              Board Reports
            </Link>
          </Button>
        </div>
      </div>

      {/* #95 Disclosure gap analysis */}
      <DisclosureGapAnalysis />

      {/* Direct reports */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Regulatory Reports
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {DIRECT_REPORTS.map((r) => (
            <DirectReportCard key={r.id} report={r} />
          ))}
          {/* #99 CDP module completion progress */}
          <CDPModuleCard />
        </div>
      </section>

      {/* Disclosure packages (GRI / iXBRL / CSRD) */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Disclosure Packages (GRI / iXBRL / CSRD)
          </h2>
          <Link
            href="/regulatory"
            className="text-xs text-blue-600 hover:underline"
          >
            Manage frameworks →
          </Link>
        </div>

        <GeneratePackageForm
          onSuccess={() => qc.invalidateQueries({ queryKey: ["disclosure-packages"] })}
        />

        {isLoading ? (
          <div className="flex justify-center py-8">
            <Spinner />
          </div>
        ) : !packages || packages.length === 0 ? (
          <div className="rounded-lg border border-dashed p-8 text-center">
            <Calendar className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">
              {t("reports.noReports")}
            </p>
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
                            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(pkg.report_status)}`}>
                              {pkg.report_status}
                            </span>
                            {(pkg.framework_codes ?? []).map((f) => (
                              <span key={f} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{f}</span>
                            ))}
                            {/* #100 iXBRL validation status */}
                            {hasIXBRL && (
                              <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${ixbrlValid ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                                {ixbrlValid ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                                iXBRL {ixbrlValid ? "Valid" : "Pending"}
                              </span>
                            )}
                            <span className="text-xs text-muted-foreground">
                              {new Date(pkg.publication_date).toLocaleDateString()}
                            </span>
                          </div>
                          {/* #98 GRI section completion */}
                          {hasGRI && griPct != null && (
                            <div className="mt-2 space-y-1">
                              <div className="flex justify-between text-[10px] text-muted-foreground">
                                <span>GRI Coverage</span>
                                <span className="font-semibold">{griPct}%</span>
                              </div>
                              <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                                <div
                                  className={`h-full rounded-full transition-all ${griPct >= 80 ? "bg-emerald-500" : griPct >= 50 ? "bg-amber-500" : "bg-red-400"}`}
                                  style={{ width: `${griPct}%` }}
                                />
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

      {/* Regulatory Calendar CTA */}
      <section>
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="flex items-center justify-between py-4">
            <div className="flex items-center gap-3">
              <Calendar className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm font-medium text-blue-900">
                  Regulatory Calendar
                </p>
                <p className="text-xs text-blue-700">
                  View upcoming filing deadlines — CSRD, GRI, TCFD, SFDR
                </p>
              </div>
            </div>
            <Button asChild variant="outline" size="sm" className="border-blue-300 text-blue-700 hover:bg-blue-100">
              <Link href="/regulatory">View Calendar →</Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
