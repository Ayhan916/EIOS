"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  Download,
  FileText,
  Loader2,
  RefreshCw,
  ScrollText,
  Send,
  X,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface FrameworkDisclosureSummary {
  framework_id: string;
  framework_code: string;
  framework_name: string;
  fw_version: string;
  total_requirements: number;
  not_started: number;
  draft: number;
  in_review: number;
  approved: number;
  published: number;
  completion_pct: number;
  avg_coverage: number;
  critical_blockers: number;
}

interface DisclosureDashboard {
  organization_id: string;
  frameworks: FrameworkDisclosureSummary[];
  total_requirements: number;
  total_published: number;
  total_approved: number;
  total_draft: number;
  total_not_started: number;
  overall_completion_pct: number;
  packages_published: number;
}

interface DisclosureFramework {
  id: string;
  code: string;
  name: string;
  fw_version: string;
  jurisdiction: string;
  effective_date: string | null;
  description: string;
  status: string;
}

interface DisclosureResponseSummary {
  id: string;
  organization_id: string;
  requirement_id: string;
  disclosure_status: string;
  evidence_coverage: number;
  coverage_category: string;
  readiness_status: string;
  updated_at: string;
}

interface DisclosureResponseDetail extends DisclosureResponseSummary {
  narrative_text: string;
  coverage_rationale: Record<string, unknown>;
  readiness_rationale: string;
  reviewed_by: string | null;
  approved_by: string | null;
  published_at: string | null;
  created_at: string;
}

interface ReportingPackageSummary {
  id: string;
  organization_id: string;
  framework_id: string;
  framework_code: string;
  framework_version: string;
  package_type: string;
  publication_date: string;
  published_by: string;
  report_hash: string;
  status: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_COL: Record<string, string> = {
  "Not Started": "bg-slate-100 text-slate-600",
  Draft:         "bg-amber-100 text-amber-700",
  "In Review":   "bg-blue-100 text-blue-700",
  Approved:      "bg-emerald-100 text-emerald-700",
  Published:     "bg-green-100 text-green-800",
  Blocked:       "bg-red-100 text-red-700",
  Ready:         "bg-teal-100 text-teal-700",
};

const READY_COL: Record<string, string> = {
  Ready:       "bg-teal-100 text-teal-700",
  Blocked:     "bg-red-100 text-red-700",
  "In Progress": "bg-blue-100 text-blue-700",
  "Not Started": "bg-slate-100 text-slate-600",
};

function coveragePill(cat: string) {
  const map: Record<string, string> = {
    Strong:   "bg-emerald-100 text-emerald-700",
    Moderate: "bg-amber-100 text-amber-700",
    Weak:     "bg-red-100 text-red-700",
  };
  return map[cat] ?? "bg-slate-100 text-slate-600";
}

function completionColor(pct: number) {
  if (pct >= 80) return "bg-emerald-500";
  if (pct >= 40) return "bg-amber-500";
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

  const { data: dash, isLoading } = useQuery<DisclosureDashboard>({
    queryKey: ["disclosure-dashboard"],
    queryFn: () => apiClient.get("/reporting/dashboard").then((r) => r.data),
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (!dash) return null;

  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: t("disclosure.overallCompletion"), value: `${dash.overall_completion_pct}%`, colored: dash.overall_completion_pct < 50 },
          { label: t("disclosure.totalRequirements"), value: dash.total_requirements },
          { label: t("disclosure.published"),         value: dash.total_published,  green: true },
          { label: t("disclosure.packagesPublished"), value: dash.packages_published },
        ].map(({ label, value, colored, green }) => (
          <Card key={label}>
            <CardContent className="pt-5 pb-5">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className={`text-3xl font-bold mt-1 ${colored ? "text-orange-600" : green && Number(value) > 0 ? "text-emerald-600" : ""}`}>
                {value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Status breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: t("disclosure.notStarted"), value: dash.total_not_started, col: "bg-slate-50 border-slate-200" },
          { label: t("disclosure.draft"),      value: dash.total_draft,        col: "bg-amber-50 border-amber-200" },
          { label: t("disclosure.inReview"),   value: dash.total_requirements - dash.total_published - dash.total_approved - dash.total_draft - dash.total_not_started, col: "bg-blue-50 border-blue-200" },
          { label: t("disclosure.approved"),   value: dash.total_approved,     col: "bg-emerald-50 border-emerald-200" },
          { label: t("disclosure.published"),  value: dash.total_published,    col: "bg-green-50 border-green-200" },
        ].map(({ label, value, col }) => (
          <div key={label} className={`rounded-lg border p-3 text-center ${col}`}>
            <p className="text-2xl font-bold">{Math.max(0, value)}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Framework table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">{t("disclosure.frameworkOverview")}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-xs text-muted-foreground">
                  <th className="px-4 py-2.5 text-left">{t("disclosure.frameworkName")}</th>
                  <th className="px-4 py-2.5 text-right">{t("disclosure.reqHeader")}</th>
                  <th className="px-4 py-2.5 text-right min-w-[120px]">{t("disclosure.completionPct")}</th>
                  <th className="px-4 py-2.5 text-right">{t("disclosure.approved")}</th>
                  <th className="px-4 py-2.5 text-right">{t("disclosure.published")}</th>
                  <th className="px-4 py-2.5 text-right text-red-600">{t("disclosure.criticalBlockers")}</th>
                </tr>
              </thead>
              <tbody>
                {dash.frameworks.map((fw) => (
                  <tr key={fw.framework_id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-3">
                      <p className="font-medium">{fw.framework_name}</p>
                      <p className="text-xs text-muted-foreground">{fw.framework_code} v{fw.fw_version}</p>
                    </td>
                    <td className="px-4 py-3 text-right">{fw.total_requirements}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 justify-end">
                        <div className="w-16 bg-muted rounded-full h-1.5">
                          <div className={`h-1.5 rounded-full ${completionColor(fw.completion_pct)}`} style={{ width: `${fw.completion_pct}%` }} />
                        </div>
                        <span className="text-xs tabular-nums w-10 text-right">{fw.completion_pct}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-emerald-600">{fw.approved}</td>
                    <td className="px-4 py-3 text-right text-green-700 font-semibold">{fw.published}</td>
                    <td className={`px-4 py-3 text-right ${fw.critical_blockers > 0 ? "text-red-600 font-bold" : ""}`}>
                      {fw.critical_blockers || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Frameworks Tab ────────────────────────────────────────────────────────────

function FrameworksTab() {
  const { t } = useLanguage();
  const [search, setSearch] = useState("");

  const { data: frameworks = [], isLoading } = useQuery<DisclosureFramework[]>({
    queryKey: ["disclosure-frameworks"],
    queryFn: () => apiClient.get("/reporting/frameworks").then((r) => r.data),
    staleTime: 10 * 60_000,
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  const filtered = search
    ? frameworks.filter((fw) =>
        fw.name.toLowerCase().includes(search.toLowerCase()) ||
        fw.code.toLowerCase().includes(search.toLowerCase()) ||
        fw.jurisdiction.toLowerCase().includes(search.toLowerCase())
      )
    : frameworks;

  return (
    <div className="space-y-4">
      <input
        className="h-9 w-full max-w-sm rounded-md border border-input bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        placeholder={t("disclosure.searchFrameworks")}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      <div className="space-y-3">
        {filtered.map((fw) => (
          <Card key={fw.id}>
            <CardContent className="py-4 flex items-start justify-between gap-4">
              <div className="space-y-1 flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-semibold">{fw.name}</p>
                  <Badge className={STATUS_COL[fw.status] ?? "bg-slate-100 text-slate-600"}>{fw.status}</Badge>
                </div>
                <p className="text-sm text-muted-foreground line-clamp-2">{fw.description}</p>
                <div className="flex gap-4 text-xs text-muted-foreground">
                  <span>{t("disclosure.jurisdiction")}: {fw.jurisdiction}</span>
                  <span>{t("disclosure.version")}: {fw.fw_version}</span>
                  {fw.effective_date && <span>{t("disclosure.effective")}: {formatDate(fw.effective_date)}</span>}
                </div>
              </div>
              <Badge className="shrink-0 font-mono bg-slate-100 text-slate-700">{fw.code}</Badge>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            <ScrollText className="mx-auto mb-2 h-8 w-8 opacity-30" />
            {t("disclosure.noFrameworks")}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Responses Tab ─────────────────────────────────────────────────────────────

function ResponsesTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const { data: frameworks = [] } = useQuery<DisclosureFramework[]>({
    queryKey: ["disclosure-frameworks"],
    queryFn: () => apiClient.get("/reporting/frameworks").then((r) => r.data),
    staleTime: 10 * 60_000,
  });

  const [fwFilter, setFwFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [editId, setEditId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const { data: responses = [], isLoading } = useQuery<DisclosureResponseSummary[]>({
    queryKey: ["disclosure-responses", fwFilter, statusFilter],
    queryFn: () =>
      apiClient.get("/reporting/responses", {
        params: {
          framework_id: fwFilter || undefined,
          disclosure_status: statusFilter || undefined,
        },
      }).then((r) => r.data),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["disclosure-responses"] });
    qc.invalidateQueries({ queryKey: ["disclosure-dashboard"] });
  };

  const updateNarrative = useMutation({
    mutationFn: ({ id, text }: { id: string; text: string }) =>
      apiClient.patch(`/reporting/responses/${id}`, { narrative_text: text }).then((r) => r.data),
    onSuccess: () => { invalidate(); setEditId(null); },
  });

  const submit = useMutation({
    mutationFn: (id: string) => apiClient.post(`/reporting/responses/${id}/submit`).then((r) => r.data),
    onSuccess: invalidate,
  });

  const approve = useMutation({
    mutationFn: (id: string) => apiClient.post(`/reporting/responses/${id}/approve`).then((r) => r.data),
    onSuccess: invalidate,
  });

  const reject = useMutation({
    mutationFn: ({ id, rationale }: { id: string; rationale: string }) =>
      apiClient.post(`/reporting/responses/${id}/reject`, { rationale }).then((r) => r.data),
    onSuccess: () => { invalidate(); setRejectId(null); setRejectReason(""); },
  });

  const recalc = useMutation({
    mutationFn: (id: string) => apiClient.post(`/reporting/responses/${id}/recalculate`).then((r) => r.data),
    onSuccess: invalidate,
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          value={fwFilter}
          onChange={(e) => setFwFilter(e.target.value)}
        >
          <option value="">{t("disclosure.allFrameworks")}</option>
          {frameworks.map((fw) => (
            <option key={fw.id} value={fw.id}>{fw.name}</option>
          ))}
        </select>

        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">{t("osDash.allStatuses")}</option>
          {["Not Started", "Draft", "In Review", "Approved", "Published"].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {/* Response cards */}
      <div className="space-y-3">
        {responses.map((resp) => (
          <Card key={resp.id}>
            <CardContent className="py-4 space-y-3">
              {/* Header row */}
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge className={STATUS_COL[resp.disclosure_status] ?? "bg-slate-100 text-slate-600"}>
                      {resp.disclosure_status}
                    </Badge>
                    <Badge className={READY_COL[resp.readiness_status] ?? "bg-slate-100 text-slate-600"}>
                      {resp.readiness_status}
                    </Badge>
                    <Badge className={coveragePill(resp.coverage_category)}>
                      {resp.coverage_category} · {Math.round(resp.evidence_coverage * 100)}%
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground font-mono truncate">
                    {t("disclosure.reqPrefix")}: {resp.requirement_id.slice(0, 12)}… · {t("disclosure.updated")} {formatDate(resp.updated_at)}
                  </p>
                </div>

                {/* Action buttons */}
                <div className="flex flex-wrap gap-2 shrink-0">
                  {resp.disclosure_status === "Draft" && (
                    <Button size="sm" variant="outline" className="h-7 text-xs"
                      disabled={submit.isPending}
                      onClick={() => submit.mutate(resp.id)}>
                      <Send className="h-3 w-3 mr-1" /> {t("disclosure.submit")}
                    </Button>
                  )}
                  {resp.disclosure_status === "In Review" && (
                    <>
                      <Button size="sm" variant="outline" className="h-7 text-xs text-emerald-700 border-emerald-300 hover:bg-emerald-50"
                        disabled={approve.isPending}
                        onClick={() => approve.mutate(resp.id)}>
                        <CheckCircle2 className="h-3 w-3 mr-1" /> {t("disclosure.approve")}
                      </Button>
                      <Button size="sm" variant="outline" className="h-7 text-xs text-red-700 border-red-300 hover:bg-red-50"
                        onClick={() => { setRejectId(resp.id); setRejectReason(""); }}>
                        <X className="h-3 w-3 mr-1" /> {t("disclosure.reject")}
                      </Button>
                    </>
                  )}
                  <Button size="sm" variant="ghost" className="h-7 text-xs"
                    disabled={recalc.isPending}
                    onClick={() => recalc.mutate(resp.id)}>
                    <RefreshCw className="h-3 w-3 mr-1" /> {t("disclosure.recalculate")}
                  </Button>
                  <Button size="sm" variant="ghost" className="h-7 text-xs"
                    onClick={() => {
                      setEditId(resp.id);
                      setEditText("");
                    }}>
                    {t("disclosure.editNarrative")}
                  </Button>
                </div>
              </div>

              {/* Reject form */}
              {rejectId === resp.id && (
                <div className="flex gap-2 items-end pt-1 border-t">
                  <div className="flex-1">
                    <label className="text-xs text-muted-foreground">{t("disclosure.rejectReason")}</label>
                    <input
                      className="mt-1 h-8 w-full rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                    />
                  </div>
                  <Button size="sm" variant="destructive" className="h-8 text-xs"
                    disabled={reject.isPending || !rejectReason.trim()}
                    onClick={() => reject.mutate({ id: resp.id, rationale: rejectReason })}>
                    {reject.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : t("disclosure.confirmReject")}
                  </Button>
                  <Button size="sm" variant="ghost" className="h-8 text-xs"
                    onClick={() => setRejectId(null)}>{t("common.cancel")}</Button>
                </div>
              )}

              {/* Narrative edit form */}
              {editId === resp.id && (
                <div className="space-y-2 border-t pt-2">
                  <label className="text-xs text-muted-foreground">{t("disclosure.narrativeText")}</label>
                  <textarea
                    rows={4}
                    className="w-full rounded border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-y"
                    placeholder={t("disclosure.narrativePlaceholder")}
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <Button size="sm" className="h-8 text-xs"
                      disabled={updateNarrative.isPending || !editText.trim()}
                      onClick={() => updateNarrative.mutate({ id: resp.id, text: editText })}>
                      {updateNarrative.isPending
                        ? <><Loader2 className="h-3 w-3 animate-spin mr-1" />{t("disclosure.saving")}</>
                        : t("disclosure.updateNarrative")}
                    </Button>
                    <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={() => setEditId(null)}>
                      {t("common.cancel")}
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}

        {responses.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            <FileText className="mx-auto mb-2 h-8 w-8 opacity-30" />
            {t("disclosure.noResponses")}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Packages Tab ──────────────────────────────────────────────────────────────

function PackagesTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const { data: packages = [], isLoading } = useQuery<ReportingPackageSummary[]>({
    queryKey: ["disclosure-packages"],
    queryFn: () => apiClient.get("/reporting/packages").then((r) => r.data),
  });

  const { data: frameworks = [] } = useQuery<DisclosureFramework[]>({
    queryKey: ["disclosure-frameworks"],
    queryFn: () => apiClient.get("/reporting/frameworks").then((r) => r.data),
    staleTime: 10 * 60_000,
  });

  const [showForm, setShowForm] = useState(false);
  const [fwCode, setFwCode] = useState("");
  const [pkgType, setPkgType] = useState("CSRD");

  const generate = useMutation({
    mutationFn: () =>
      apiClient.post("/reporting/packages/generate", {
        framework_code: fwCode,
        package_type: pkgType,
      }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["disclosure-packages"] });
      qc.invalidateQueries({ queryKey: ["disclosure-dashboard"] });
      setShowForm(false);
      setFwCode("");
    },
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setShowForm((v) => !v)}>
          {showForm ? t("common.cancel") : `+ ${t("disclosure.generatePackage")}`}
        </Button>
      </div>

      {/* Generate form */}
      {showForm && (
        <Card>
          <CardContent className="py-4 space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted-foreground">{t("disclosure.frameworkCode")}</label>
                <select
                  className="mt-1 h-9 w-full rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={fwCode}
                  onChange={(e) => setFwCode(e.target.value)}
                >
                  <option value="">{t("disclosure.selectFramework")}</option>
                  {frameworks.map((fw) => (
                    <option key={fw.id} value={fw.code}>{fw.name} ({fw.code})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground">{t("disclosure.packageType")}</label>
                <select
                  className="mt-1 h-9 w-full rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={pkgType}
                  onChange={(e) => setPkgType(e.target.value)}
                >
                  {["CSRD", "GRI", "ESRS", "iXBRL", "FULL"].map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
            </div>
            <Button size="sm" disabled={generate.isPending || !fwCode} onClick={() => generate.mutate()}>
              {generate.isPending
                ? <><Loader2 className="h-4 w-4 animate-spin mr-1.5" />{t("disclosure.generating")}</>
                : t("disclosure.generatePackage")}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Packages list */}
      <div className="space-y-3">
        {packages.map((pkg) => (
          <Card key={pkg.id}>
            <CardContent className="py-4 flex items-start justify-between gap-4">
              <div className="space-y-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-semibold">{t("disclosure.packageLabel").replace("{type}", pkg.package_type)}</p>
                  <Badge className="font-mono bg-slate-100 text-slate-700">{pkg.framework_code}</Badge>
                  <Badge className={STATUS_COL[pkg.status] ?? "bg-slate-100 text-slate-600"}>{pkg.status}</Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  {t("disclosure.publishedBy")}: {pkg.published_by?.slice(0, 16)}…
                  · v{pkg.framework_version}
                  · {formatDate(pkg.publication_date)}
                </p>
                <p className="text-[10px] font-mono text-muted-foreground">
                  {t("disclosure.packageHash")}: {pkg.report_hash.slice(0, 16)}…
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                className="h-8 text-xs shrink-0"
                onClick={() => authenticatedDownload(`/reporting/packages/${pkg.id}/download`, `package-${pkg.id.slice(0, 8)}.pdf`)}
              >
                <Download className="h-3.5 w-3.5 mr-1" /> {t("disclosure.downloadPdf")}
              </Button>
            </CardContent>
          </Card>
        ))}

        {packages.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            <ScrollText className="mx-auto mb-2 h-8 w-8 opacity-30" />
            {t("disclosure.noPackages")}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = "dashboard" | "frameworks" | "responses" | "packages";

const tab_defs: { key: Tab; labelKey: string; icon: React.ElementType }[] = [
  { key: "dashboard",  labelKey: "disclosure.dashboardTab",  icon: ScrollText },
  { key: "frameworks", labelKey: "disclosure.frameworksTab", icon: FileText },
  { key: "responses",  labelKey: "disclosure.responsesTab",  icon: CheckCircle2 },
  { key: "packages",   labelKey: "disclosure.packagesTab",   icon: Download },
];

export default function DisclosurePage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <ScrollText className="h-7 w-7 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold">{t("disclosure.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("disclosure.subtitle")}</p>
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
        {activeTab === "dashboard"  && <DashboardTab />}
        {activeTab === "frameworks" && <FrameworksTab />}
        {activeTab === "responses"  && <ResponsesTab />}
        {activeTab === "packages"   && <PackagesTab />}
      </div>
    </div>
  );
}
