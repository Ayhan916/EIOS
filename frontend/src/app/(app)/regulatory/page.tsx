"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  Download,
  FileText,
  Loader2,
  Radio,
  RefreshCw,
  Scale,
  Send,
  ShieldAlert,
  ScanSearch,
  X,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { regulatoryChangesApi, RegulatoryChange } from "@/lib/api/regulatory-changes";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface FrameworkStatusTyped {
  regulation_code: string;
  regulation_name: string;
  status: string;
  total_requirements: number;
  covered_requirements: number;
  coverage_ratio: number;
  open_gap_count: number;
  critical_gap_count: number;
  high_gap_count: number;
  medium_gap_count: number;
  low_gap_count: number;
  top_gap_requirement_codes: string[];
}

interface ComplianceDashboard {
  organization_id: string;
  overall_coverage_ratio: number;
  total_open_gaps: number;
  total_critical_gaps: number;
  frameworks: FrameworkStatusTyped[];
}

interface Regulation {
  id: string;
  code: string;
  name: string;
  jurisdiction: string;
  reg_version: string;
  reg_status: string;
  description: string;
  requirement_count: number;
}

interface ComplianceGap {
  id: string;
  requirement_code: string;
  requirement_title: string;
  gap_type: string;
  severity: string;
  description: string;
  supplier_id: string | null;
  is_resolved: boolean;
  calculated_at: string;
}

interface GapSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  by_gap_type: Record<string, number>;
  by_framework: Record<string, number>;
}

interface ReportSummary {
  id: string;
  report_type: string;
  framework_code: string;
  framework_version: string;
  generated_at: string;
  generated_by: string;
  report_hash: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const SEV_COL: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800",
  HIGH:     "bg-orange-100 text-orange-800",
  MEDIUM:   "bg-amber-100 text-amber-800",
  LOW:      "bg-green-100 text-green-800",
};

const REG_STATUS_COL: Record<string, string> = {
  ACTIVE:     "bg-green-100 text-green-800",
  DRAFT:      "bg-slate-100 text-slate-600",
  SUPERSEDED: "bg-amber-100 text-amber-700",
  REPEALED:   "bg-red-100 text-red-700",
};

function coverageColor(ratio: number) {
  if (ratio >= 0.8) return "bg-emerald-500";
  if (ratio >= 0.5) return "bg-amber-500";
  return "bg-red-500";
}

function authenticatedDownload(path: string, filename: string) {
  apiClient.get(path, { responseType: "blob" })
    .then(({ data }) => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(data as Blob);
      a.download = filename;
      a.click();
    })
    .catch(() => {/* silent */});
}

// ── Dashboard Tab ─────────────────────────────────────────────────────────────

function DashboardTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const { data: dash, isLoading } = useQuery<ComplianceDashboard>({
    queryKey: ["regulatory-dashboard"],
    queryFn: () => apiClient.get("/regulatory/dashboard").then((r) => r.data),
  });

  const recalc = useMutation({
    mutationFn: () => apiClient.post("/regulatory/gaps/recalculate").then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["regulatory-dashboard"] });
      qc.invalidateQueries({ queryKey: ["regulatory-gaps"] });
    },
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (!dash) return null;

  const coveragePct = Math.round(dash.overall_coverage_ratio * 100);

  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-5 pb-5">
            <p className="text-xs text-muted-foreground">{t("reg.overallCoverage")}</p>
            <p className={`text-3xl font-bold mt-1 ${coveragePct >= 80 ? "text-emerald-600" : coveragePct >= 50 ? "text-amber-600" : "text-red-600"}`}>
              {coveragePct}%
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-5">
            <p className="text-xs text-muted-foreground">{t("reg.openGaps")}</p>
            <p className={`text-3xl font-bold mt-1 ${dash.total_open_gaps > 0 ? "text-orange-600" : ""}`}>
              {dash.total_open_gaps}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-5">
            <p className="text-xs text-muted-foreground">{t("reg.criticalGaps")}</p>
            <p className={`text-3xl font-bold mt-1 ${dash.total_critical_gaps > 0 ? "text-red-600" : ""}`}>
              {dash.total_critical_gaps}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-5">
            <p className="text-xs text-muted-foreground">{t("reg.frameworks")}</p>
            <p className="text-3xl font-bold mt-1">{dash.frameworks.length}</p>
          </CardContent>
        </Card>
      </div>

      {/* Recalculate */}
      <div className="flex justify-end">
        <Button size="sm" variant="outline" disabled={recalc.isPending} onClick={() => recalc.mutate()}>
          {recalc.isPending
            ? <><Loader2 className="h-4 w-4 animate-spin mr-1.5" />{t("reg.recalculating")}</>
            : <><RefreshCw className="h-4 w-4 mr-1.5" />{t("reg.recalculate")}</>}
        </Button>
      </div>

      {/* Framework coverage table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">{t("reg.frameworkStatus")}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-xs text-muted-foreground">
                  <th className="px-4 py-2.5 text-left">Framework</th>
                  <th className="px-4 py-2.5 text-right">{t("reg.requirement")}</th>
                  <th className="px-4 py-2.5 text-right">{t("reg.covered")}</th>
                  <th className="px-4 py-2.5 text-right min-w-[120px]">{t("reg.coverageRatio")}</th>
                  <th className="px-4 py-2.5 text-right">{t("reg.openGaps")}</th>
                  <th className="px-4 py-2.5 text-right text-red-600">Critical</th>
                </tr>
              </thead>
              <tbody>
                {dash.frameworks.map((fw) => {
                  const pct = Math.round(fw.coverage_ratio * 100);
                  return (
                    <tr key={fw.regulation_code} className="border-b last:border-0 hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <p className="font-medium">{fw.regulation_name}</p>
                        <p className="text-xs text-muted-foreground">{fw.regulation_code}</p>
                      </td>
                      <td className="px-4 py-3 text-right">{fw.total_requirements}</td>
                      <td className="px-4 py-3 text-right">{fw.covered_requirements}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2 justify-end">
                          <div className="w-16 bg-muted rounded-full h-1.5">
                            <div className={`h-1.5 rounded-full ${coverageColor(fw.coverage_ratio)}`} style={{ width: `${pct}%` }} />
                          </div>
                          <span className="text-xs tabular-nums w-10 text-right">{pct}%</span>
                        </div>
                      </td>
                      <td className={`px-4 py-3 text-right ${fw.open_gap_count > 0 ? "text-orange-600 font-semibold" : ""}`}>
                        {fw.open_gap_count}
                      </td>
                      <td className={`px-4 py-3 text-right ${fw.critical_gap_count > 0 ? "text-red-600 font-bold" : ""}`}>
                        {fw.critical_gap_count}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Regulations Tab ───────────────────────────────────────────────────────────

function RegulationsTab() {
  const { t } = useLanguage();
  const [search, setSearch] = useState("");

  const { data: regs = [], isLoading } = useQuery<Regulation[]>({
    queryKey: ["regulations"],
    queryFn: () => apiClient.get("/regulatory/regulations?limit=100").then((r) => r.data),
    staleTime: 10 * 60_000,
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  const filtered = search
    ? regs.filter((r) =>
        r.name.toLowerCase().includes(search.toLowerCase()) ||
        r.code.toLowerCase().includes(search.toLowerCase()) ||
        r.jurisdiction.toLowerCase().includes(search.toLowerCase())
      )
    : regs;

  return (
    <div className="space-y-4">
      <input
        className="h-9 w-full max-w-sm rounded-md border border-input bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        placeholder="Search regulations…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      <div className="space-y-3">
        {filtered.map((reg) => (
          <Card key={reg.id}>
            <CardContent className="py-4 flex items-start justify-between gap-4">
              <div className="space-y-1 flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-semibold">{reg.name}</p>
                  <Badge className={REG_STATUS_COL[reg.reg_status] ?? "bg-slate-100 text-slate-600"}>
                    {reg.reg_status}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground line-clamp-2">{reg.description}</p>
                <div className="flex gap-3 text-xs text-muted-foreground">
                  <span>{t("reg.jurisdiction")}: {reg.jurisdiction}</span>
                  <span>{t("reg.version")}: {reg.reg_version}</span>
                  <span>{reg.requirement_count} requirements</span>
                </div>
              </div>
              <Badge className="shrink-0 font-mono bg-slate-100 text-slate-700">{reg.code}</Badge>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            <Scale className="mx-auto mb-2 h-8 w-8 opacity-30" />
            {t("reg.noRegulations")}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Gaps Tab ──────────────────────────────────────────────────────────────────

function GapsTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [sevFilter, setSevFilter] = useState("");

  const { data: gaps = [], isLoading } = useQuery<ComplianceGap[]>({
    queryKey: ["regulatory-gaps", sevFilter],
    queryFn: () =>
      apiClient.get("/regulatory/gaps", {
        params: { severity: sevFilter || undefined, is_resolved: false, limit: 200 },
      }).then((r) => r.data),
  });

  const { data: summary } = useQuery<GapSummary>({
    queryKey: ["regulatory-gaps-summary"],
    queryFn: () => apiClient.get("/regulatory/gaps/summary").then((r) => r.data),
  });

  const resolve = useMutation({
    mutationFn: (id: string) => apiClient.patch(`/regulatory/gaps/${id}/resolve`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["regulatory-gaps"] });
      qc.invalidateQueries({ queryKey: ["regulatory-gaps-summary"] });
      qc.invalidateQueries({ queryKey: ["regulatory-dashboard"] });
    },
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-4">
      {/* Summary chips */}
      {summary && (
        <div className="flex flex-wrap gap-2">
          {[
            { label: "All", value: "", count: summary.total },
            { label: "Critical", value: "CRITICAL", count: summary.critical },
            { label: "High", value: "HIGH", count: summary.high },
            { label: "Medium", value: "MEDIUM", count: summary.medium },
            { label: "Low", value: "LOW", count: summary.low },
          ].map(({ label, value, count }) => (
            <button
              key={label}
              onClick={() => setSevFilter(value)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                sevFilter === value
                  ? "bg-slate-800 text-white border-slate-800"
                  : "bg-slate-100 text-slate-700 hover:border-slate-400"
              }`}
            >
              {label} · {count}
            </button>
          ))}
        </div>
      )}

      {/* By framework breakdown */}
      {summary && Object.keys(summary.by_framework).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(summary.by_framework).map(([fw, cnt]) => (
            <span key={fw} className="rounded bg-blue-50 border border-blue-200 px-2 py-0.5 text-xs text-blue-700">
              {fw}: {cnt}
            </span>
          ))}
        </div>
      )}

      <div className="space-y-3">
        {gaps.map((gap) => (
          <Card key={gap.id}>
            <CardContent className="py-4 flex items-start justify-between gap-4">
              <div className="space-y-1 flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge className={SEV_COL[gap.severity] ?? "bg-slate-100 text-slate-600"}>
                    {gap.severity}
                  </Badge>
                  <span className="text-xs text-muted-foreground font-mono">{gap.requirement_code}</span>
                </div>
                <p className="font-medium">{gap.requirement_title || gap.requirement_code}</p>
                <p className="text-sm text-muted-foreground line-clamp-2">{gap.description}</p>
                <p className="text-xs text-muted-foreground">
                  {t("reg.gapType")}: {gap.gap_type} · Calculated {formatDate(gap.calculated_at)}
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                className="h-8 text-xs shrink-0 text-green-700 border-green-300 hover:bg-green-50"
                disabled={resolve.isPending}
                onClick={() => resolve.mutate(gap.id)}
              >
                <CheckCircle2 className="h-3 w-3 mr-1" /> {t("reg.resolveGap")}
              </Button>
            </CardContent>
          </Card>
        ))}
        {gaps.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            <CheckCircle2 className="mx-auto mb-2 h-8 w-8 text-green-500 opacity-50" />
            {t("reg.noGaps")}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Reports Tab ───────────────────────────────────────────────────────────────

function ReportsTab() {
  const { t } = useLanguage();

  const { data: reports = [], isLoading } = useQuery<ReportSummary[]>({
    queryKey: ["regulatory-reports"],
    queryFn: () => apiClient.get("/regulatory/reports?limit=50").then((r) => r.data),
  });

  const specialReports = [
    { label: t("reg.downloadCsrd"), url: "/regulatory/reports/csrd-gap",         file: "csrd-gap.json" },
    { label: t("reg.downloadEsrs"), url: "/regulatory/reports/esrs-readiness",   file: "esrs-readiness.json" },
    { label: t("reg.downloadCsddd"), url: "/regulatory/reports/csddd-due-diligence", file: "csddd.json" },
  ];

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-6">
      {/* Special report downloads */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Framework Reports</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {specialReports.map(({ label, url, file }) => (
              <Button
                key={url}
                size="sm"
                variant="outline"
                onClick={() => authenticatedDownload(url, file)}
              >
                <Download className="h-4 w-4 mr-1.5" /> {label}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Historical reports list */}
      <div className="space-y-3">
        {reports.map((r) => (
          <Card key={r.id}>
            <CardContent className="py-4 flex items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <p className="font-medium">{r.report_type}</p>
                  <Badge className="font-mono bg-slate-100 text-slate-700 text-[10px]">{r.framework_code}</Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Generated {formatDate(r.generated_at)} · v{r.framework_version}
                </p>
                <p className="text-[10px] font-mono text-muted-foreground">Hash: {r.report_hash.slice(0, 16)}…</p>
              </div>
              <Button
                size="sm"
                variant="ghost"
                className="h-8 text-xs shrink-0"
                onClick={() => authenticatedDownload(`/regulatory/reports/${r.id}/download`, `report-${r.id}.json`)}
              >
                <Download className="h-3.5 w-3.5 mr-1" /> Download
              </Button>
            </CardContent>
          </Card>
        ))}
        {reports.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            <ShieldAlert className="mx-auto mb-2 h-8 w-8 opacity-30" />
            {t("reg.noReports")}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Calendar Tab ──────────────────────────────────────────────────────────────

interface RegulatoryDeadline {
  id: string;
  framework_code: string;
  deadline_name: string;
  deadline_date: string;
  description: string;
  jurisdiction: string;
  entity_size: string;
  is_mandatory: boolean;
  reporting_year: string | null;
}

function CalendarTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [jurisdiction, setJurisdiction] = useState("");
  const [framework, setFramework] = useState("");
  const [year, setYear] = useState<string>("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    framework_code: "", deadline_name: "", deadline_date: "",
    description: "", jurisdiction: "", entity_size: "All",
    is_mandatory: true, reporting_year: "", organization_id: "",
  });

  const { data: deadlines = [], isLoading } = useQuery<RegulatoryDeadline[]>({
    queryKey: ["regulatory-calendar", jurisdiction, framework, year],
    queryFn: () =>
      apiClient.get("/regulatory/calendar", {
        params: {
          jurisdiction: jurisdiction || undefined,
          framework_code: framework || undefined,
          year: year ? Number(year) : undefined,
        },
      }).then((r) => r.data),
  });

  const create = useMutation({
    mutationFn: () => apiClient.post("/regulatory/calendar", { ...form, is_mandatory: form.is_mandatory }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["regulatory-calendar"] });
      setShowForm(false);
      setForm({ framework_code: "", deadline_name: "", deadline_date: "", description: "", jurisdiction: "", entity_size: "All", is_mandatory: true, reporting_year: "", organization_id: "" });
    },
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  const today = new Date().toISOString().split("T")[0];

  function daysUntil(dateStr: string) {
    const diff = Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86_400_000);
    return diff;
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="text-xs text-muted-foreground block mb-1">{t("reg.filterJurisdiction")}</label>
          <input
            className="h-9 w-32 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="EU, DE…"
            value={jurisdiction}
            onChange={(e) => setJurisdiction(e.target.value.toUpperCase())}
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground block mb-1">{t("reg.filterFramework")}</label>
          <input
            className="h-9 w-32 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="CSRD…"
            value={framework}
            onChange={(e) => setFramework(e.target.value.toUpperCase())}
          />
        </div>
        <div>
          <label className="text-xs text-muted-foreground block mb-1">{t("reg.filterYear")}</label>
          <input
            type="number"
            className="h-9 w-24 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="2025"
            value={year}
            onChange={(e) => setYear(e.target.value)}
          />
        </div>
        <Button size="sm" className="ml-auto" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : `+ ${t("reg.addDeadline")}`}
        </Button>
      </div>

      {/* Create form */}
      {showForm && (
        <Card>
          <CardContent className="py-4 grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              { key: "framework_code", label: "Framework Code", placeholder: "CSRD" },
              { key: "deadline_name",  label: "Deadline Name",  placeholder: "Annual Report Filing" },
              { key: "jurisdiction",   label: "Jurisdiction",   placeholder: "EU" },
              { key: "entity_size",    label: "Entity Size",    placeholder: "Large" },
              { key: "reporting_year", label: "Reporting Year", placeholder: "2025" },
            ].map(({ key, label, placeholder }) => (
              <div key={key}>
                <label className="text-xs text-muted-foreground">{label}</label>
                <input
                  className="mt-1 h-9 w-full rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder={placeholder}
                  value={(form as Record<string, unknown>)[key] as string}
                  onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                />
              </div>
            ))}
            <div>
              <label className="text-xs text-muted-foreground">{t("reg.deadlineDate")}</label>
              <input
                type="date"
                className="mt-1 h-9 w-full rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={form.deadline_date}
                onChange={(e) => setForm((f) => ({ ...f, deadline_date: e.target.value }))}
              />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-muted-foreground">Description</label>
              <input
                className="mt-1 h-9 w-full rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              />
            </div>
            <div className="flex items-center gap-2 md:col-span-2">
              <input
                type="checkbox"
                id="mandatory"
                checked={form.is_mandatory}
                onChange={(e) => setForm((f) => ({ ...f, is_mandatory: e.target.checked }))}
                className="h-4 w-4"
              />
              <label htmlFor="mandatory" className="text-sm">{t("reg.mandatory")}</label>
            </div>
            <div className="md:col-span-2">
              <Button
                size="sm"
                disabled={create.isPending || !form.framework_code || !form.deadline_name || !form.deadline_date}
                onClick={() => create.mutate()}
              >
                {create.isPending ? <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />Saving…</> : <><Send className="h-3.5 w-3.5 mr-1" />Add Deadline</>}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Deadline list */}
      <div className="space-y-3">
        {deadlines.map((dl) => {
          const days = daysUntil(dl.deadline_date);
          const isOverdue = days < 0;
          const isClose = days >= 0 && days <= 30;
          return (
            <Card key={dl.id} className={isOverdue ? "border-red-300" : isClose ? "border-amber-300" : ""}>
              <CardContent className="py-4 flex items-start justify-between gap-4">
                <div className="space-y-1 flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-semibold">{dl.deadline_name}</p>
                    {dl.is_mandatory && (
                      <Badge className="bg-red-100 text-red-700 text-[10px]">{t("reg.mandatory")}</Badge>
                    )}
                    <Badge className="bg-slate-100 text-slate-700 font-mono text-[10px]">{dl.framework_code}</Badge>
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-2">{dl.description}</p>
                  <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                    <span>{dl.jurisdiction}</span>
                    <span>{t("reg.entitySize")}: {dl.entity_size}</span>
                    {dl.reporting_year && <span>Year: {dl.reporting_year}</span>}
                  </div>
                </div>
                <div className="shrink-0 text-right space-y-1">
                  <p className={`text-sm font-semibold tabular-nums ${isOverdue ? "text-red-600" : isClose ? "text-amber-600" : "text-foreground"}`}>
                    {formatDate(dl.deadline_date)}
                  </p>
                  <p className={`text-xs ${isOverdue ? "text-red-500" : isClose ? "text-amber-500" : "text-muted-foreground"}`}>
                    {isOverdue
                      ? `${t("reg.overdue")} ${Math.abs(days)}d`
                      : days === 0 ? "Today"
                      : `${days} ${t("reg.daysLeft")}`}
                  </p>
                </div>
              </CardContent>
            </Card>
          );
        })}
        {deadlines.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            <CalendarDays className="mx-auto mb-2 h-8 w-8 opacity-30" />
            {t("reg.noDeadlines")}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Exports Tab ───────────────────────────────────────────────────────────────

interface PkgOption { id: string; framework_code: string; package_type: string; publication_date: string; }

function ExportsTab() {
  const { t } = useLanguage();
  const [tcfdYear, setTcfdYear] = useState("2024");
  const [sfdrYear, setSfdrYear] = useState("2024");
  const [auditStart, setAuditStart] = useState("");
  const [auditEnd, setAuditEnd] = useState("");
  const [selectedPkg, setSelectedPkg] = useState("");
  const [exportFormat, setExportFormat] = useState<"xbrl" | "gri" | "json">("xbrl");
  const [loading, setLoading] = useState<string | null>(null);

  const { data: packages = [] } = useQuery<PkgOption[]>({
    queryKey: ["disclosure-packages-export"],
    queryFn: () => apiClient.get("/reporting/packages").then((r) => r.data),
  });

  function download(path: string, filename: string, params?: Record<string, string>) {
    setLoading(filename);
    const url = params
      ? `${path}?${new URLSearchParams(params).toString()}`
      : path;
    apiClient.get(url, { responseType: "blob" })
      .then(({ data, headers }) => {
        const ct = headers["content-type"] as string ?? "application/octet-stream";
        const blob = new Blob([data as BlobPart], { type: ct });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
      })
      .finally(() => setLoading(null));
  }

  return (
    <div className="space-y-6">
      {/* TCFD */}
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">TCFD Report (G-038)</CardTitle></CardHeader>
        <CardContent className="flex items-end gap-3">
          <div>
            <label className="text-xs text-muted-foreground">{t("reg.reportingYear")}</label>
            <input type="number" min={2020} max={2035}
              className="mt-1 h-9 w-24 rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              value={tcfdYear} onChange={(e) => setTcfdYear(e.target.value)} />
          </div>
          <Button size="sm" variant="outline"
            disabled={loading === "tcfd.json"}
            onClick={() => download("/executive/tcfd", "tcfd.json", { reporting_year: tcfdYear })}>
            {loading === "tcfd.json" ? <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />{t("reg.downloading")}</> : <><Download className="h-3.5 w-3.5 mr-1" />{t("reg.exportTcfd")}</>}
          </Button>
        </CardContent>
      </Card>

      {/* SFDR PAI */}
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">SFDR PAI — Principal Adverse Impacts (G-039)</CardTitle></CardHeader>
        <CardContent className="flex items-end gap-3">
          <div>
            <label className="text-xs text-muted-foreground">{t("reg.reportingYear")}</label>
            <input type="number" min={2020} max={2035}
              className="mt-1 h-9 w-24 rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              value={sfdrYear} onChange={(e) => setSfdrYear(e.target.value)} />
          </div>
          <Button size="sm" variant="outline"
            disabled={loading === "sfdr_pai.json"}
            onClick={() => download("/financial-esg/sfdr/pai", "sfdr_pai.json", { reference_year: sfdrYear })}>
            {loading === "sfdr_pai.json" ? <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />{t("reg.downloading")}</> : <><Download className="h-3.5 w-3.5 mr-1" />{t("reg.exportSfdr")}</>}
          </Button>
        </CardContent>
      </Card>

      {/* Audit Trail CSV */}
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Audit Trail Export — CSV (G-013)</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div>
            <label className="text-xs text-muted-foreground">From</label>
            <input type="date"
              className="mt-1 h-9 rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              value={auditStart} onChange={(e) => setAuditStart(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">To</label>
            <input type="date"
              className="mt-1 h-9 rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              value={auditEnd} onChange={(e) => setAuditEnd(e.target.value)} />
          </div>
          <Button size="sm" variant="outline"
            disabled={loading === "audit.csv"}
            onClick={() => {
              const params: Record<string, string> = { format: "csv" };
              if (auditStart) params.start = auditStart;
              if (auditEnd) params.end = auditEnd;
              download("/audit/events/export", "audit.csv", params);
            }}>
            {loading === "audit.csv" ? <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />{t("reg.downloading")}</> : <><Download className="h-3.5 w-3.5 mr-1" />{t("reg.exportAudit")}</>}
          </Button>
        </CardContent>
      </Card>

      {/* Package Exports (iXBRL / GRI / JSON) */}
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Reporting Package Exports — iXBRL · GRI · JSON (G-012 / G-037)</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div>
            <label className="text-xs text-muted-foreground">{t("reg.selectPackage")}</label>
            <select
              className="mt-1 h-9 rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              value={selectedPkg}
              onChange={(e) => setSelectedPkg(e.target.value)}
            >
              <option value="">Select…</option>
              {packages.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.framework_code} · {p.package_type} · {formatDate(p.publication_date)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Format</label>
            <select
              className="mt-1 h-9 rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value as "xbrl" | "gri" | "json")}
            >
              <option value="xbrl">{t("reg.exportXbrl")}</option>
              <option value="gri">{t("reg.exportGri")}</option>
              <option value="json">{t("reg.exportJson")}</option>
            </select>
          </div>
          <Button size="sm" variant="outline" disabled={!selectedPkg || loading === "pkg-export"}
            onClick={() => {
              const ext = exportFormat === "xbrl" ? "html" : "json";
              download(`/disclosure/packages/${selectedPkg}/export`, `package-${selectedPkg.slice(0,8)}.${ext}`, { format: exportFormat });
            }}>
            {loading === "pkg-export" ? <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />{t("reg.downloading")}</> : <><Download className="h-3.5 w-3.5 mr-1" />Export</>}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Regulatory Change Monitoring (GAP-19) ─────────────────────────────────────

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-300",
  major: "bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-900/30 dark:text-orange-300",
  moderate: "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-900/30 dark:text-amber-300",
  minor: "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-900/30 dark:text-blue-300",
};

const STATUS_STYLES: Record<string, string> = {
  new: "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
  scanning: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
  impacts_identified: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  notified: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  acknowledged: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
};

function ChangesTab() {
  const qc = useQueryClient();
  const [showAddForm, setShowAddForm] = useState(false);
  const [framework, setFramework] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [article, setArticle] = useState("");
  const [severity, setSeverity] = useState("moderate");
  const [sourceName, setSourceName] = useState("Manual");

  const { data: changes = [], isLoading } = useQuery({
    queryKey: ["regulatory-changes"],
    queryFn: () => regulatoryChangesApi.list(),
  });

  const seedMutation = useMutation({
    mutationFn: () => regulatoryChangesApi.seed(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["regulatory-changes"] }),
  });

  const scanMutation = useMutation({
    mutationFn: (changeId: string) => regulatoryChangesApi.scanImpact(changeId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["regulatory-changes"] });
      qc.invalidateQueries({ queryKey: ["regulatory-changes-summary"] });
    },
  });

  const createMutation = useMutation({
    mutationFn: () =>
      regulatoryChangesApi.create({
        framework_code: framework,
        change_title: title,
        change_description: description,
        affected_article: article,
        severity,
        source_name: sourceName,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["regulatory-changes"] });
      setShowAddForm(false);
      setFramework(""); setTitle(""); setDescription(""); setArticle("");
    },
  });

  return (
    <div className="space-y-4">
      {/* Actions bar */}
      <div className="flex items-center gap-3 justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => seedMutation.mutate()}
            disabled={seedMutation.isPending}
            className="flex items-center gap-1.5 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            <RefreshCw className={`h-4 w-4 ${seedMutation.isPending ? "animate-spin" : ""}`} />
            Load Curated Feed
          </button>
          <button
            onClick={() => setShowAddForm((v) => !v)}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            + Log Manual Change
          </button>
        </div>
        <span className="text-xs text-gray-400">{changes.length} change(s) tracked</span>
      </div>

      {/* Add form */}
      {showAddForm && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4 space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">Log Regulatory Change</span>
            <button onClick={() => setShowAddForm(false)}><X className="h-4 w-4 text-gray-400" /></button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Framework</label>
              <input value={framework} onChange={(e) => setFramework(e.target.value)}
                placeholder="LkSG / CSDDD / CSRD"
                className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Affected Article</label>
              <input value={article} onChange={(e) => setArticle(e.target.value)}
                placeholder="e.g. Art. 10 Abs. 2"
                className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1.5 text-sm" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-gray-500 mb-1">Title</label>
              <input value={title} onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1.5 text-sm" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-gray-500 mb-1">Description</label>
              <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1.5 text-sm resize-none" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Severity</label>
              <select value={severity} onChange={(e) => setSeverity(e.target.value)}
                className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1.5 text-sm">
                <option value="minor">Minor</option>
                <option value="moderate">Moderate</option>
                <option value="major">Major</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Source</label>
              <input value={sourceName} onChange={(e) => setSourceName(e.target.value)}
                className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-1.5 text-sm" />
            </div>
          </div>
          <div className="flex justify-end">
            <button onClick={() => createMutation.mutate()}
              disabled={!framework || !title || createMutation.isPending}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
              {createMutation.isPending ? "Saving…" : "Save Change"}
            </button>
          </div>
        </div>
      )}

      {/* Change list */}
      {isLoading ? (
        <div className="py-10 text-center text-sm text-gray-400">Loading…</div>
      ) : changes.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 py-16 text-center text-gray-400">
          No regulatory changes tracked. Click "Load Curated Feed" to seed known EU/German changes.
        </div>
      ) : (
        <div className="space-y-3">
          {changes.map((c: RegulatoryChange) => (
            <div key={c.id}
              className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded">
                      {c.framework_code}
                    </span>
                    {c.affected_article && (
                      <span className="text-xs text-gray-400">{c.affected_article}</span>
                    )}
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${SEVERITY_STYLES[c.severity] ?? ""}`}>
                      {c.severity}
                    </span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[c.change_status] ?? ""}`}>
                      {c.change_status.replace("_", " ")}
                    </span>
                  </div>
                  <p className="mt-1 text-sm font-semibold text-gray-900 dark:text-white">
                    {c.change_title}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                    {c.change_description}
                  </p>
                  {c.impact_summary && (
                    <p className="mt-1 text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 rounded px-2 py-1">
                      {c.impact_summary}
                    </p>
                  )}
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                    <span>Source: {c.source_name}</span>
                    {c.effective_date && <span>Effective: {c.effective_date}</span>}
                    {c.impacted_assessment_count > 0 && (
                      <span className="text-orange-500">
                        {c.impacted_assessment_count} assessment(s) flagged
                      </span>
                    )}
                    {c.impacted_gap_count > 0 && (
                      <span className="text-orange-500">
                        {c.impacted_gap_count} gap(s) flagged
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => scanMutation.mutate(c.id)}
                  disabled={scanMutation.isPending}
                  title="Run impact scan"
                  className="flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 shrink-0"
                >
                  <ScanSearch className="h-3.5 w-3.5" />
                  Scan Impact
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Regulatory Change Banner (shown when new unscanned changes exist) ──────────

function RegulatoryChangeBanner() {
  const [dismissed, setDismissed] = useState(false);
  const { data: summary } = useQuery({
    queryKey: ["regulatory-changes-summary"],
    queryFn: () => regulatoryChangesApi.getSummary(),
    staleTime: 60_000,
  });

  if (dismissed || !summary || summary.new_changes === 0) return null;

  return (
    <div className="flex items-start gap-3 rounded-lg border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 px-4 py-3 text-sm text-amber-800 dark:text-amber-200">
      <Radio className="h-4 w-4 mt-0.5 shrink-0 text-amber-600" />
      <div className="flex-1">
        <span className="font-semibold">{summary.new_changes} new regulatory change(s)</span>{" "}
        require impact assessment.
        {summary.pending_re_reviews > 0 && (
          <span className="ml-1">
            {summary.pending_re_reviews} assessment(s) pending re-review.
          </span>
        )}{" "}
        Go to the <strong>Changes</strong> tab to run impact scans.
      </div>
      <button onClick={() => setDismissed(true)} className="text-amber-500 hover:text-amber-700">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = "dashboard" | "regulations" | "gaps" | "reports" | "calendar" | "exports" | "changes";

const tab_defs: { key: Tab; labelKey: string; icon: React.ElementType }[] = [
  { key: "dashboard",   labelKey: "reg.dashboardTab",    icon: ClipboardList },
  { key: "regulations", labelKey: "reg.regulationsTab",  icon: Scale },
  { key: "gaps",        labelKey: "reg.gapsTab",         icon: ShieldAlert },
  { key: "reports",     labelKey: "reg.reportsTab",      icon: FileText },
  { key: "calendar",   labelKey: "reg.calendarTab",     icon: CalendarDays },
  { key: "exports",     labelKey: "reg.exportsTab",      icon: Download },
  { key: "changes",     labelKey: "reg.changesTab",      icon: Radio },
];

export default function RegulatoryPage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");

  return (
    <div className="p-6 space-y-6">
      <RegulatoryChangeBanner />

      <div className="flex items-center gap-3">
        <Scale className="h-7 w-7 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold">{t("reg.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("reg.subtitle")}</p>
        </div>
      </div>

      <div className="flex gap-1 border-b overflow-x-auto">
        {tab_defs.map(({ key, labelKey, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors ${
              activeTab === key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="h-4 w-4" />
            {t(labelKey as Parameters<typeof t>[0])}
          </button>
        ))}
      </div>

      <div>
        {activeTab === "dashboard"   && <DashboardTab />}
        {activeTab === "regulations" && <RegulationsTab />}
        {activeTab === "gaps"        && <GapsTab />}
        {activeTab === "reports"     && <ReportsTab />}
        {activeTab === "calendar"    && <CalendarTab />}
        {activeTab === "exports"     && <ExportsTab />}
        {activeTab === "changes"     && <ChangesTab />}
      </div>
    </div>
  );
}
