"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  ClipboardList,
  Download,
  FileText,
  Loader2,
  Lock,
  Package,
  PenLine,
  Printer,
  Shield,
  ShieldCheck,
  Shuffle,
  UserCheck,
  XCircle,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { listAssessments } from "@/lib/api/assessments";
import { formatDate, formatDateTime } from "@/lib/utils";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import type { AssessmentResponse } from "@/types/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface SecuritySummary {
  ga_ready: boolean;
  generated_at: string;
  soc2: { readiness_pct: number; implemented: number; total: number };
  owasp: { coverage_pct: number; categories_covered: number; total: number };
  pentest: { open_findings: number; critical_open: number; high_open: number };
  production_checklist: { completion_pct: number; complete: number; total: number };
}

interface Soc2Control {
  id: string;
  control_id: string;
  category: string;
  control_name: string;
  description: string;
  status: string;
  evidence_notes: string | null;
  owner: string | null;
}

interface PentestFinding {
  id: string;
  owasp_category: string;
  title: string;
  severity: string;
  status: string;
  cvss_score: number | null;
  discovered_at: string | null;
  remediated_at: string | null;
}

interface ChecklistItem {
  id: string;
  category: string;
  item_name: string;
  description: string;
  status: string;
  priority: string;
  owner: string | null;
  notes: string | null;
  completed_at: string | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const SOC2_STATUS_STYLES: Record<string, string> = {
  "Not Started":  "bg-slate-100 text-slate-600",
  "In Progress":  "bg-blue-100 text-blue-700",
  "Implemented":  "bg-emerald-100 text-emerald-700",
  "Tested":       "bg-violet-100 text-violet-700",
};

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800",
  HIGH:     "bg-orange-100 text-orange-800",
  MEDIUM:   "bg-amber-100 text-amber-800",
  LOW:      "bg-slate-100 text-slate-700",
  INFO:     "bg-sky-100 text-sky-700",
};

const CHECKLIST_STATUS_STYLES: Record<string, string> = {
  Pending:  "bg-slate-100 text-slate-600",
  Complete: "bg-emerald-100 text-emerald-700",
  "N/A":    "bg-slate-50 text-slate-400",
};

function pctColor(pct: number) {
  if (pct >= 80) return "text-emerald-600";
  if (pct >= 60) return "text-amber-600";
  return "text-red-500";
}

function ProgressBar({ pct }: { pct: number }) {
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 60 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="mt-1 h-1.5 w-full rounded-full bg-slate-100">
      <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
    </div>
  );
}

function authenticatedDownload(url: string, filename: string) {
  const token = typeof window !== "undefined" ? localStorage.getItem("eios_access_token") : null;
  fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    .then((r) => r.blob())
    .then((blob) => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
    });
}

// ── SOC2 Controls Tab ─────────────────────────────────────────────────────────

function Soc2Tab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [editing, setEditing] = useState<{ id: string; field: "status" | "notes"; value: string } | null>(null);

  const { data, isLoading } = useQuery<{ items: Soc2Control[]; total: number }>({
    queryKey: ["soc2-controls", categoryFilter],
    queryFn: async () => {
      const params = categoryFilter !== "all" ? `?category=${encodeURIComponent(categoryFilter)}` : "";
      const res = await apiClient.get(`/security/soc2/controls${params}`);
      return res.data;
    },
    staleTime: 30_000,
  });

  const updateMutation = useMutation({
    mutationFn: async ({ controlId, payload }: { controlId: string; payload: Record<string, string> }) => {
      await apiClient.put(`/security/soc2/controls/${controlId}`, payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["soc2-controls"] });
      qc.invalidateQueries({ queryKey: ["security-summary"] });
      setEditing(null);
    },
  });

  const controls = data?.items ?? [];
  const categories = Array.from(new Set(controls.map((c) => c.category))).sort();

  const byCategory: Record<string, Soc2Control[]> = {};
  for (const ctrl of controls) {
    if (!byCategory[ctrl.category]) byCategory[ctrl.category] = [];
    byCategory[ctrl.category].push(ctrl);
  }

  if (isLoading) return <div className="flex justify-center py-16"><Spinner /></div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{t("auditor.controlsLoaded").replace("{n}", String(controls.length))}</p>
        <select
          className="h-8 rounded-md border border-input bg-background px-3 text-sm"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        >
          <option value="all">{t("auditor.category")} — {t("common.all")}</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {Object.entries(byCategory).map(([cat, items]) => (
        <Card key={cat}>
          <CardHeader className="pb-2 pt-4">
            <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              {cat}
              <span className="ml-2 font-normal">
                {t("auditor.implementedOf").replace("{n}", String(items.filter((i) => i.status === "Implemented" || i.status === "Tested").length)).replace("{m}", String(items.length))}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-y bg-muted/20 text-xs text-muted-foreground">
                  <th className="px-4 py-2 text-left w-20">{t("auditor.controlId")}</th>
                  <th className="px-4 py-2 text-left">{t("common.description")}</th>
                  <th className="px-4 py-2 text-left w-32">{t("common.status")}</th>
                  <th className="px-4 py-2 text-left hidden lg:table-cell">{t("auditor.evidenceStatus")}</th>
                  <th className="px-4 py-2 text-left w-24">{t("common.actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {items.map((ctrl) => (
                  <tr key={ctrl.id} className="hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-2.5">
                      <span className="font-mono text-xs font-semibold text-slate-500">{ctrl.control_id}</span>
                    </td>
                    <td className="px-4 py-2.5">
                      <p className="font-medium text-xs">{ctrl.control_name}</p>
                    </td>
                    <td className="px-4 py-2.5">
                      {editing?.id === ctrl.control_id && editing.field === "status" ? (
                        <div className="flex items-center gap-1">
                          <select
                            autoFocus
                            className="h-7 rounded border border-input bg-background px-2 text-xs"
                            defaultValue={ctrl.status}
                            onBlur={(e) => {
                              if (e.target.value !== ctrl.status) {
                                updateMutation.mutate({
                                  controlId: ctrl.control_id,
                                  payload: { status: e.target.value, evidence_notes: ctrl.evidence_notes ?? "" },
                                });
                              } else {
                                setEditing(null);
                              }
                            }}
                          >
                            <option>Not Started</option>
                            <option>In Progress</option>
                            <option>Implemented</option>
                            <option>Tested</option>
                          </select>
                          {updateMutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                        </div>
                      ) : (
                        <button
                          onClick={() => setEditing({ id: ctrl.control_id, field: "status", value: ctrl.status })}
                          className={`rounded-full px-2.5 py-0.5 text-xs font-medium cursor-pointer hover:opacity-80 ${SOC2_STATUS_STYLES[ctrl.status] ?? "bg-slate-100 text-slate-600"}`}
                        >
                          {ctrl.status}
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-2.5 hidden lg:table-cell">
                      {ctrl.evidence_notes ? (
                        <p className="text-xs text-muted-foreground line-clamp-1 max-w-xs">{ctrl.evidence_notes}</p>
                      ) : (
                        <span className="text-xs text-muted-foreground/40 italic">{t("auditor.noControls")}</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <button
                        onClick={() => setEditing({ id: ctrl.control_id, field: "status", value: ctrl.status })}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        {t("common.edit")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Pentest Tab ───────────────────────────────────────────────────────────────

function PentestTab() {
  const { t } = useLanguage();
  const { data, isLoading } = useQuery<{ items: PentestFinding[]; total: number; open: number }>({
    queryKey: ["pentest-findings"],
    queryFn: async () => {
      const res = await apiClient.get("/security/pentest/findings");
      return res.data;
    },
    staleTime: 30_000,
  });

  const { data: owasp, isLoading: owaspLoading } = useQuery<Record<string, unknown>>({
    queryKey: ["owasp-assessment"],
    queryFn: async () => {
      const res = await apiClient.get("/security/pentest/owasp");
      return res.data;
    },
    staleTime: 60_000,
  });

  if (isLoading || owaspLoading) return <div className="flex justify-center py-16"><Spinner /></div>;

  const findings = data?.items ?? [];

  return (
    <div className="space-y-4">
      {owasp && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3 mb-2">
              <ShieldCheck className="h-5 w-5 text-blue-500" />
              <p className="font-semibold">{t("auditor.owasp")} {t("auditor.top10Coverage")}</p>
              <span className={`ml-auto font-bold tabular-nums ${pctColor((owasp as { overall_pct?: number }).overall_pct ?? 0)}`}>
                {Math.round((owasp as { overall_pct?: number }).overall_pct ?? 0)}%
              </span>
            </div>
            <ProgressBar pct={(owasp as { overall_pct?: number }).overall_pct ?? 0} />
          </CardContent>
        </Card>
      )}

      {findings.length === 0 ? (
        <div className="rounded-lg border border-dashed p-10 text-center">
          <CheckCircle2 className="mx-auto mb-3 h-8 w-8 text-emerald-400" />
          <p className="text-sm text-muted-foreground">{t("auditor.finding")} — {t("common.noData")}</p>
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/20 text-xs text-muted-foreground">
                  <th className="px-4 py-2 text-left">{t("auditor.category")}</th>
                  <th className="px-4 py-2 text-left">{t("common.title")}</th>
                  <th className="px-4 py-2 text-left">{t("auditor.severity")}</th>
                  <th className="px-4 py-2 text-left">CVSS</th>
                  <th className="px-4 py-2 text-left">{t("common.status")}</th>
                  <th className="px-4 py-2 text-left hidden md:table-cell">{t("common.date")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {findings.map((f) => (
                  <tr key={f.id} className="hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-2.5">
                      <span className="font-mono text-xs text-slate-500">{f.owasp_category}</span>
                    </td>
                    <td className="px-4 py-2.5">
                      <p className="font-medium text-xs max-w-xs line-clamp-1">{f.title}</p>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${SEVERITY_STYLES[f.severity] ?? "bg-slate-100 text-slate-600"}`}>
                        {f.severity}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground tabular-nums">
                      {f.cvss_score != null ? f.cvss_score.toFixed(1) : "—"}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${f.status === "Remediated" ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>
                        {f.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 hidden md:table-cell text-xs text-muted-foreground">
                      {f.discovered_at ? formatDate(f.discovered_at) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Production Checklist Tab ──────────────────────────────────────────────────

function ChecklistTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<{ items: ChecklistItem[]; summary: Record<string, unknown> }>({
    queryKey: ["production-checklist"],
    queryFn: async () => {
      const res = await apiClient.get("/security/production-checklist");
      return res.data;
    },
    staleTime: 20_000,
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      await apiClient.put(`/security/production-checklist/${id}`, { status });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["production-checklist"] });
      qc.invalidateQueries({ queryKey: ["security-summary"] });
    },
  });

  if (isLoading) return <div className="flex justify-center py-16"><Spinner /></div>;

  const items = data?.items ?? [];
  const byCategory: Record<string, ChecklistItem[]> = {};
  for (const item of items) {
    if (!byCategory[item.category]) byCategory[item.category] = [];
    byCategory[item.category].push(item);
  }

  return (
    <div className="space-y-4">
      {Object.entries(byCategory).map(([cat, catItems]) => {
        const complete = catItems.filter((i) => i.status === "Complete" || i.status === "N/A").length;
        return (
          <Card key={cat}>
            <CardHeader className="pb-2 pt-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                  {cat}
                </CardTitle>
                <span className="text-xs text-muted-foreground">{t("auditor.doneOf").replace("{n}", String(complete)).replace("{m}", String(catItems.length))}</span>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-border">
                {catItems.map((item) => (
                  <div key={item.id} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/20 transition-colors">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{item.item_name}</p>
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{item.description}</p>
                    </div>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${CHECKLIST_STATUS_STYLES[item.status] ?? "bg-slate-100"}`}>
                      {item.priority}
                    </span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {item.status === "Complete" ? (
                        <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
                          <CheckCircle2 className="h-3.5 w-3.5" /> {t("auditor.done")}
                        </span>
                      ) : item.status === "N/A" ? (
                        <span className="text-xs text-slate-400">N/A</span>
                      ) : (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 px-2 text-xs"
                            disabled={updateMutation.isPending}
                            onClick={() => updateMutation.mutate({ id: item.id, status: "Complete" })}
                          >
                            {updateMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
                            {t("auditor.complete")}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 px-2 text-xs text-muted-foreground"
                            disabled={updateMutation.isPending}
                            onClick={() => updateMutation.mutate({ id: item.id, status: "N/A" })}
                          >
                            {t("auditor.na")}
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        );
      })}

      {items.length === 0 && (
        <div className="rounded-lg border border-dashed p-10 text-center">
          <ClipboardList className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground mb-3">{t("auditor.noControls")}</p>
          <Button
            size="sm"
            onClick={async () => {
              await apiClient.post("/security/production-checklist/seed");
              qc.invalidateQueries({ queryKey: ["production-checklist"] });
              qc.invalidateQueries({ queryKey: ["security-summary"] });
            }}
          >
            {t("auditor.checklistTab")}
          </Button>
        </div>
      )}
    </div>
  );
}

// ── #142 Evidence Map ─────────────────────────────────────────────────────────

function EvidenceMapTab() {
  const { t } = useLanguage();
  const [category, setCategory] = useState("all");

  const { data, isLoading } = useQuery<{ items: Soc2Control[] }>({
    queryKey: ["soc2-controls-evidence-map"],
    queryFn: async () => {
      const res = await apiClient.get("/security/soc2/controls?limit=500");
      return res.data;
    },
    staleTime: 60_000,
  });

  const controls = data?.items ?? [];
  const categories = Array.from(new Set(controls.map((c) => c.category))).sort();
  const filtered = category === "all" ? controls : controls.filter((c) => c.category === category);

  const withEvidence = filtered.filter((c) => c.evidence_notes).length;
  const pct = filtered.length > 0 ? Math.round((withEvidence / filtered.length) * 100) : 0;

  if (isLoading) return <div className="flex justify-center py-16"><Spinner /></div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <select
          className="h-8 rounded-md border border-input bg-background px-3 text-sm"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option value="all">{t("auditor.category")} — {t("common.all")}</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <span className="text-xs text-muted-foreground">
          {t("auditor.withEvidence").replace("{n}", String(withEvidence)).replace("{m}", String(filtered.length)).replace("{pct}", String(pct))}
        </span>
        <div className="ml-auto h-2 w-32 rounded-full bg-muted overflow-hidden">
          <div className={`h-full rounded-full transition-all ${pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-400" : "bg-red-400"}`} style={{ width: `${pct}%` }} />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b bg-muted/20 text-muted-foreground">
                <th className="px-4 py-2.5 text-left font-semibold w-20">{t("auditor.controlId")}</th>
                <th className="px-4 py-2.5 text-left font-semibold">{t("common.name")}</th>
                <th className="px-4 py-2.5 text-left font-semibold w-24">{t("common.status")}</th>
                <th className="px-4 py-2.5 text-left font-semibold">{t("auditor.evidenceStatus")}</th>
                <th className="px-4 py-2.5 text-left font-semibold w-28 hidden lg:table-cell">{t("common.createdBy")}</th>
                <th className="px-4 py-2.5 text-center font-semibold w-28">{t("auditor.signOff")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.map((ctrl) => (
                <tr key={ctrl.id} className="hover:bg-muted/20 transition-colors">
                  <td className="px-4 py-2.5">
                    <span className="font-mono font-semibold text-slate-500">{ctrl.control_id}</span>
                  </td>
                  <td className="px-4 py-2.5 font-medium max-w-xs">
                    <p className="line-clamp-1">{ctrl.control_name}</p>
                    <p className="text-muted-foreground text-[10px]">{ctrl.category}</p>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`rounded-full px-2 py-0.5 font-medium ${SOC2_STATUS_STYLES[ctrl.status] ?? "bg-slate-100 text-slate-600"}`}>
                      {ctrl.status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    {ctrl.evidence_notes ? (
                      <div className="flex items-center gap-1.5">
                        <CheckCircle2 className="h-3 w-3 text-emerald-500 flex-shrink-0" />
                        <span className="text-muted-foreground line-clamp-1 max-w-xs">{ctrl.evidence_notes}</span>
                      </div>
                    ) : (
                      <span className="flex items-center gap-1 text-amber-600">
                        <AlertTriangle className="h-3 w-3" /> {t("auditor.evidenceStatus")}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 hidden lg:table-cell text-muted-foreground">
                    {ctrl.owner ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    {/* #147 Per-control evidence package download */}
                    <button
                      onClick={() => authenticatedDownload(
                        `/security/soc2/controls/${ctrl.control_id}/evidence-package`,
                        `evidence-${ctrl.control_id}.zip`
                      )}
                      title={t("auditor.downloadEvidencePkg")}
                      className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-[10px] font-medium hover:bg-muted transition-colors"
                    >
                      <Package className="h-3 w-3" /> ZIP
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <p className="py-10 text-center text-sm text-muted-foreground">{t("auditor.noControls")}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ── #146 Approval Log ─────────────────────────────────────────────────────────

interface ApprovalRecord {
  id: string;
  title: string;
  decision: string;
  decided_by?: string;
  decided_at?: string;
  comment?: string;
  priority?: string;
  entity_type?: string;
}

const APPROVAL_BADGE: Record<string, string> = {
  Approved:         "bg-emerald-100 text-emerald-700",
  Rejected:         "bg-red-100 text-red-700",
  ChangesRequested: "bg-amber-100 text-amber-700",
};

function ApprovalsTab() {
  const { t } = useLanguage();

  function approvalLabel(decision: string): string {
    if (decision === "Approved") return t("exec.approved");
    if (decision === "Rejected") return t("exec.rejected");
    if (decision === "ChangesRequested") return t("auditor.changesRequested");
    return decision;
  }

  const { data, isLoading } = useQuery<ApprovalRecord[]>({
    queryKey: ["auditor-approvals"],
    queryFn: async () => {
      const res = await apiClient.get("/recommendations/decisions?limit=200");
      return res.data?.items ?? res.data ?? [];
    },
    staleTime: 60_000,
  });

  const records = data ?? [];

  function exportCsv() {
    const rows = [["Title","Decision","Decided By","Decided At","Entity Type","Comment"]];
    for (const r of records) {
      rows.push([r.title, r.decision, r.decided_by ?? "", r.decided_at ?? "", r.entity_type ?? "", r.comment ?? ""]);
    }
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `approval-log-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  if (isLoading) return <div className="flex justify-center py-16"><Spinner /></div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">{(records.length === 1 ? t("auditor.decisionsOnRecord") : t("auditor.decisionsOnRecordPlural")).replace("{n}", String(records.length))}</p>
        <Button variant="outline" size="sm" className="gap-2" onClick={exportCsv}>
          <Download className="h-3.5 w-3.5" /> {t("findings.exportCsv")}
        </Button>
      </div>

      {records.length === 0 ? (
        <div className="rounded-lg border border-dashed py-12 text-center">
          <UserCheck className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">{t("common.noData")}</p>
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b bg-muted/20 text-muted-foreground">
                  <th className="px-4 py-2.5 text-left font-semibold">{t("exec.decisionsTitle")}</th>
                  <th className="px-4 py-2.5 text-left font-semibold">{t("common.title")}</th>
                  <th className="px-4 py-2.5 text-left font-semibold hidden md:table-cell">{t("common.createdBy")}</th>
                  <th className="px-4 py-2.5 text-left font-semibold hidden lg:table-cell">{t("common.date")}</th>
                  <th className="px-4 py-2.5 text-left font-semibold hidden lg:table-cell">{t("common.notes")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {records.map((r) => {
                  const badgeClass = APPROVAL_BADGE[r.decision] ?? "bg-slate-100 text-slate-600";
                  return (
                    <tr key={r.id} className="hover:bg-muted/20">
                      <td className="px-4 py-2.5">
                        <span className={`rounded-full px-2 py-0.5 font-semibold ${badgeClass}`}>{approvalLabel(r.decision)}</span>
                      </td>
                      <td className="px-4 py-2.5 max-w-xs">
                        <p className="font-medium line-clamp-1">{r.title}</p>
                        {r.entity_type && <p className="text-muted-foreground text-[10px]">{r.entity_type.replace(/_/g, " ")}</p>}
                      </td>
                      <td className="px-4 py-2.5 hidden md:table-cell text-muted-foreground">{r.decided_by ?? "—"}</td>
                      <td className="px-4 py-2.5 hidden lg:table-cell text-muted-foreground whitespace-nowrap">
                        {r.decided_at ? formatDate(r.decided_at) : "—"}
                      </td>
                      <td className="px-4 py-2.5 hidden lg:table-cell text-muted-foreground max-w-xs">
                        <p className="line-clamp-1 italic">{r.comment ?? "—"}</p>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── #148 Audit Sampling ───────────────────────────────────────────────────────

function SamplingTab() {
  const { t } = useLanguage();
  const [n, setN] = useState(5);
  const [sample, setSample] = useState<AssessmentResponse[]>([]);
  const [sampledAt, setSampledAt] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["assessments-for-sampling"],
    queryFn: () => listAssessments({ page: 1, page_size: 500 }),
    staleTime: 120_000,
  });

  const total = data?.total ?? 0;

  function drawSample() {
    if (!data?.items?.length) return;
    const pool = [...data.items];
    const drawn: AssessmentResponse[] = [];
    for (let i = 0; i < Math.min(n, pool.length); i++) {
      const idx = Math.floor(Math.random() * (pool.length - i));
      drawn.push(...pool.splice(idx, 1));
    }
    setSample(drawn);
    setSampledAt(new Date().toISOString());
  }

  function exportSample() {
    if (!sample.length) return;
    const rows = [["#","ID","Title","Type","Status","Supplier ID","Sampled At"]];
    sample.forEach((a, i) => rows.push([
      String(i + 1), a.id, a.title, a.assessment_type, a.status, a.supplier_id ?? "",
      sampledAt ?? "",
    ]));
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `audit-sample-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="pt-5 space-y-4">
          <div>
            <p className="text-sm font-semibold mb-1">{t("auditor.randomSampleTitle")}</p>
            <p className="text-xs text-muted-foreground">
              {t("auditor.randomSampleDesc").replace("{n}", isLoading ? "…" : String(total))}
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">{t("auditor.sampleSize")}</label>
              <Input
                type="number"
                min={1}
                max={Math.min(50, total)}
                value={n}
                onChange={(e) => setN(Math.max(1, Math.min(50, parseInt(e.target.value) || 1)))}
                className="w-20 h-8 text-sm"
              />
            </div>
            <Button size="sm" onClick={drawSample} disabled={isLoading || total === 0} className="gap-2">
              <Shuffle className="h-3.5 w-3.5" /> {t("common.refresh")}
            </Button>
            {sample.length > 0 && (
              <Button size="sm" variant="outline" onClick={exportSample} className="gap-2">
                <Download className="h-3.5 w-3.5" /> {t("findings.exportCsv")}
              </Button>
            )}
          </div>
          {sampledAt && (
            <p className="text-xs text-muted-foreground">
              {t("auditor.sampleDrawnAt").replace("{time}", formatDateTime(sampledAt)).replace("{n}", String(sample.length)).replace("{total}", String(total))}
            </p>
          )}
        </CardContent>
      </Card>

      {sample.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">{t("auditor.selectedSample").replace("{n}", String(sample.length))}</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b bg-muted/20 text-muted-foreground">
                  <th className="px-4 py-2.5 text-left w-8">#</th>
                  <th className="px-4 py-2.5 text-left">{t("assessments.title")}</th>
                  <th className="px-4 py-2.5 text-left">{t("common.type")}</th>
                  <th className="px-4 py-2.5 text-left">{t("common.status")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {sample.map((a, i) => (
                  <tr key={a.id} className="hover:bg-muted/20">
                    <td className="px-4 py-2.5 font-mono text-muted-foreground">{i + 1}</td>
                    <td className="px-4 py-2.5">
                      <p className="font-medium line-clamp-1">{a.title}</p>
                      <p className="text-muted-foreground text-[10px] font-mono">{a.id.slice(0, 8)}…</p>
                    </td>
                    <td className="px-4 py-2.5 capitalize text-muted-foreground">{a.assessment_type}</td>
                    <td className="px-4 py-2.5">
                      <span className="rounded-full bg-secondary px-2 py-0.5 capitalize">{a.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── #149 Sign-off Workflow ────────────────────────────────────────────────────

const SIGNOFF_KEY = "eios_signoff_state";

interface SignoffRecord {
  id: string;
  controlId: string;
  controlName: string;
  reviewedBy: string;
  reviewedAt: string;
  notes: string;
}

function SignoffTab() {
  const { t } = useLanguage();
  const [records, setRecords] = useState<SignoffRecord[]>([]);
  const [reviewer, setReviewer] = useState("");
  const [noteFor, setNoteFor] = useState<Record<string, string>>({});

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(SIGNOFF_KEY) ?? "[]");
      setRecords(stored);
    } catch { /* ignore */ }
  }, []);

  const { data, isLoading } = useQuery<{ items: Soc2Control[] }>({
    queryKey: ["soc2-controls-signoff"],
    queryFn: async () => {
      const res = await apiClient.get("/security/soc2/controls?limit=200");
      return res.data;
    },
    staleTime: 120_000,
  });

  const controls = data?.items ?? [];
  const signedIds = new Set(records.map((r) => r.controlId));

  function signOff(ctrl: Soc2Control) {
    const record: SignoffRecord = {
      id: `${ctrl.control_id}-${Date.now()}`,
      controlId: ctrl.control_id,
      controlName: ctrl.control_name,
      reviewedBy: reviewer.trim() || "Auditor",
      reviewedAt: new Date().toISOString(),
      notes: noteFor[ctrl.control_id] ?? "",
    };
    const next = [record, ...records.filter((r) => r.controlId !== ctrl.control_id)];
    setRecords(next);
    localStorage.setItem(SIGNOFF_KEY, JSON.stringify(next));
  }

  function clearSignoffs() {
    setRecords([]);
    localStorage.removeItem(SIGNOFF_KEY);
  }

  function exportSignoffs() {
    const rows = [["Control ID","Control Name","Reviewed By","Reviewed At","Notes"]];
    for (const r of records) {
      rows.push([r.controlId, r.controlName, r.reviewedBy, r.reviewedAt, r.notes]);
    }
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `sign-off-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  if (isLoading) return <div className="flex justify-center py-16"><Spinner /></div>;

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-4 space-y-3">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2 flex-1 min-w-48">
              <label className="text-sm font-medium whitespace-nowrap">{t("auditor.reviewerName")}</label>
              <Input
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                placeholder={t("auditor.yourName")}
                className="h-8 text-sm"
              />
            </div>
            <div className="flex gap-2">
              {records.length > 0 && (
                <>
                  <Button size="sm" variant="outline" onClick={exportSignoffs} className="gap-2">
                    <Download className="h-3.5 w-3.5" /> {t("common.export")}
                  </Button>
                  {/* #150 Audit report print */}
                  <Button size="sm" variant="outline" onClick={() => window.print()} className="gap-2 print:hidden">
                    <Printer className="h-3.5 w-3.5" /> {t("auditor.downloadAudit")}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={clearSignoffs} className="text-muted-foreground text-xs">
                    {t("common.delete")}
                  </Button>
                </>
              )}
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            {t("auditor.signedOff").replace("{n}", String(records.length)).replace("{m}", String(controls.length))}
          </p>
          {records.length > 0 && controls.length > 0 && (
            <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-emerald-500 transition-all"
                style={{ width: `${Math.round((records.length / controls.length) * 100)}%` }}
              />
            </div>
          )}
        </CardContent>
      </Card>

      <div className="space-y-2">
        {controls.map((ctrl) => {
          const signed = records.find((r) => r.controlId === ctrl.control_id);
          return (
            <div key={ctrl.id} className={`rounded-lg border p-3 transition-colors ${signed ? "border-emerald-200 bg-emerald-50/30" : "border-border hover:bg-muted/20"}`}>
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-semibold text-slate-500">{ctrl.control_id}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${SOC2_STATUS_STYLES[ctrl.status] ?? "bg-slate-100"}`}>{ctrl.status}</span>
                  </div>
                  <p className="text-sm font-medium mt-0.5">{ctrl.control_name}</p>
                  {signed ? (
                    <p className="text-xs text-emerald-700 mt-0.5 flex items-center gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      {t("auditor.reviewedBy").replace("{name}", signed.reviewedBy)} · {formatDateTime(signed.reviewedAt)}
                      {signed.notes && <> · <em>{signed.notes}</em></>}
                    </p>
                  ) : (
                    <div className="mt-1.5 flex items-center gap-2">
                      <Input
                        placeholder={t("auditor.notesOptional")}
                        value={noteFor[ctrl.control_id] ?? ""}
                        onChange={(e) => setNoteFor((prev) => ({ ...prev, [ctrl.control_id]: e.target.value }))}
                        className="h-7 text-xs flex-1"
                      />
                      <Button size="sm" onClick={() => signOff(ctrl)} className="h-7 px-3 text-xs gap-1.5 shrink-0">
                        <PenLine className="h-3 w-3" /> {t("auditor.signOff")}
                      </Button>
                    </div>
                  )}
                </div>
                {signed && (
                  <button
                    onClick={() => {
                      const next = records.filter((r) => r.controlId !== ctrl.control_id);
                      setRecords(next);
                      localStorage.setItem(SIGNOFF_KEY, JSON.stringify(next));
                    }}
                    className="text-[10px] text-muted-foreground hover:text-foreground shrink-0"
                  >
                    {t("auditor.undo")}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Role gating ───────────────────────────────────────────────────────────────

const AUDITOR_ROLES = new Set(["auditor", "admin", "enterprise_admin", "bu_admin", "compliance_officer"]);

// ── Page ──────────────────────────────────────────────────────────────────────

const TABS = ["SOC 2 Controls", "Evidence Map", "Pentest", "Checklist", "Approvals", "Sampling", "Sign-off"] as const;
type Tab = (typeof TABS)[number];

export default function AuditorWorkspacePage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>("SOC 2 Controls");

  const TAB_LABELS: Record<Tab, string> = {
    "SOC 2 Controls": t("auditor.soc2Tab"),
    "Evidence Map": t("auditor.evidenceMapTab"),
    "Pentest": t("auditor.pentestTab"),
    "Checklist": t("auditor.checklistTab"),
    "Approvals": t("auditor.approvalsTab"),
    "Sampling": t("auditor.samplingTab"),
    "Sign-off": t("auditor.signOff"),
  };
  const [csvFrom, setCsvFrom] = useState("");
  const [csvTo, setCsvTo] = useState("");

  // #141 Role-based gating
  if (user && !AUDITOR_ROLES.has(user.role)) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3 text-center">
        <Lock className="h-10 w-10 text-muted-foreground/40" />
        <p className="text-sm font-medium">{t("auditor.title")}</p>
        <p className="text-xs text-muted-foreground max-w-xs">
          {t("auditor.subtitle")}
        </p>
      </div>
    );
  }

  const { data: summary, isLoading: summaryLoading } = useQuery<SecuritySummary>({
    queryKey: ["security-summary"],
    queryFn: async () => {
      const res = await apiClient.get("/security/audit-summary");
      return res.data;
    },
    staleTime: 60_000,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">{t("auditor.title")}</h1>
            {user?.role && (
              <span className="rounded-full bg-violet-100 px-2.5 py-0.5 text-xs font-semibold text-violet-700 capitalize">
                {user.role.replace(/_/g, " ")}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("auditor.subtitle")}
          </p>
        </div>
        {/* #143 Enhanced audit trail export with date range */}
        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          <Input
            type="date"
            value={csvFrom}
            onChange={(e) => setCsvFrom(e.target.value)}
            className="h-8 w-36 text-xs"
            placeholder="From"
          />
          <Input
            type="date"
            value={csvTo}
            onChange={(e) => setCsvTo(e.target.value)}
            className="h-8 w-36 text-xs"
            placeholder="To"
          />
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => {
              const params = new URLSearchParams({ format: "csv" });
              if (csvFrom) params.set("from", csvFrom);
              if (csvTo) params.set("to", csvTo);
              authenticatedDownload(
                `/audit/events/export?${params}`,
                `audit-trail-${new Date().toISOString().split("T")[0]}.csv`
              );
            }}
          >
            <Download className="h-4 w-4" />
            {t("auditor.downloadAudit")}
          </Button>
          {/* #150 Audit report PDF */}
          <Button
            size="sm"
            variant="outline"
            className="gap-2 print:hidden"
            onClick={() => window.print()}
          >
            <Printer className="h-4 w-4" />
            {t("common.download")}
          </Button>
          <Button
            size="sm"
            className="gap-2 bg-slate-700 hover:bg-slate-800 text-white"
            onClick={() =>
              authenticatedDownload(
                "/security/auditor/sign-off",
                `eios-sign-off-${new Date().toISOString().split("T")[0]}.json`
              )
            }
          >
            <BookOpen className="h-4 w-4" />
            {t("auditor.signOff")}
          </Button>
        </div>
      </div>

      {/* Security posture summary */}
      {summaryLoading ? (
        <div className="flex justify-center py-6"><Spinner /></div>
      ) : summary ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {/* GA Ready */}
          <Card className={`col-span-2 sm:col-span-1 border-2 ${summary.ga_ready ? "border-emerald-400 bg-emerald-50/40" : "border-amber-300 bg-amber-50/30"}`}>
            <CardContent className="pt-4 pb-3 text-center">
              {summary.ga_ready ? (
                <CheckCircle2 className="mx-auto mb-1 h-7 w-7 text-emerald-500" />
              ) : (
                <XCircle className="mx-auto mb-1 h-7 w-7 text-amber-500" />
              )}
              <p className="text-sm font-bold">{summary.ga_ready ? t("esgOs.passed") : t("sec.checklistFailed")}</p>
              <p className="text-[10px] text-muted-foreground mt-0.5">{t("auditor.checklistTab")}</p>
            </CardContent>
          </Card>

          {/* SOC2 */}
          <Card>
            <CardContent className="pt-4 pb-3">
              <div className="flex items-center gap-2 mb-1">
                <Shield className="h-4 w-4 text-blue-500" />
                <p className="text-xs font-medium text-muted-foreground">SOC 2</p>
              </div>
              <p className={`text-2xl font-bold tabular-nums ${pctColor(summary.soc2.readiness_pct)}`}>
                {Math.round(summary.soc2.readiness_pct)}%
              </p>
              <ProgressBar pct={summary.soc2.readiness_pct} />
              <p className="text-[10px] text-muted-foreground mt-1">
                {t("auditor.implementedCount").replace("{n}", String(summary.soc2.implemented)).replace("{m}", String(summary.soc2.total))}
              </p>
            </CardContent>
          </Card>

          {/* OWASP */}
          <Card>
            <CardContent className="pt-4 pb-3">
              <div className="flex items-center gap-2 mb-1">
                <ShieldCheck className="h-4 w-4 text-violet-500" />
                <p className="text-xs font-medium text-muted-foreground">OWASP</p>
              </div>
              <p className={`text-2xl font-bold tabular-nums ${pctColor(summary.owasp.coverage_pct)}`}>
                {Math.round(summary.owasp.coverage_pct)}%
              </p>
              <ProgressBar pct={summary.owasp.coverage_pct} />
              <p className="text-[10px] text-muted-foreground mt-1">
                {t("auditor.categoriesCovered").replace("{n}", String(summary.owasp.categories_covered)).replace("{m}", String(summary.owasp.total))}
              </p>
            </CardContent>
          </Card>

          {/* Checklist */}
          <Card>
            <CardContent className="pt-4 pb-3">
              <div className="flex items-center gap-2 mb-1">
                <FileText className="h-4 w-4 text-emerald-500" />
                <p className="text-xs font-medium text-muted-foreground">{t("auditor.checklistTab")}</p>
              </div>
              <p className={`text-2xl font-bold tabular-nums ${pctColor(summary.production_checklist.completion_pct)}`}>
                {Math.round(summary.production_checklist.completion_pct)}%
              </p>
              <ProgressBar pct={summary.production_checklist.completion_pct} />
              <p className="text-[10px] text-muted-foreground mt-1">
                {t("auditor.completedCount").replace("{n}", String(summary.production_checklist.complete)).replace("{m}", String(summary.production_checklist.total))}
              </p>
            </CardContent>
          </Card>

          {/* Open Pentest Findings */}
          {summary.pentest.open_findings > 0 && (
            <Card className="col-span-2 sm:col-span-4 border-red-200 bg-red-50/30">
              <CardContent className="py-3 px-4 flex items-center gap-3">
                <AlertTriangle className="h-4 w-4 text-red-500 shrink-0" />
                <p className="text-sm">
                  <span className="font-semibold text-red-700">{t("auditor.openPentestFindings").replace("{n}", String(summary.pentest.open_findings))}</span>
                  {summary.pentest.critical_open > 0 && (
                    <span className="ml-1 text-red-600">{t("auditor.criticalCount").replace("{n}", String(summary.pentest.critical_open))}</span>
                  )}
                  {summary.pentest.high_open > 0 && (
                    <span className="ml-1 text-orange-600">{t("auditor.highCount").replace("{n}", String(summary.pentest.high_open))}</span>
                  )}
                  <span className="ml-2 text-muted-foreground text-xs">{t("auditor.pentestTab")}</span>
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      ) : null}

      {/* Tabs */}
      <div>
        <div className="flex border-b border-border gap-0">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {TAB_LABELS[tab]}
            </button>
          ))}
        </div>

        <div className="mt-6">
          {activeTab === "SOC 2 Controls" && <Soc2Tab />}
          {activeTab === "Evidence Map" && <EvidenceMapTab />}
          {activeTab === "Pentest" && <PentestTab />}
          {activeTab === "Checklist" && <ChecklistTab />}
          {activeTab === "Approvals" && <ApprovalsTab />}
          {activeTab === "Sampling" && <SamplingTab />}
          {activeTab === "Sign-off" && <SignoffTab />}
        </div>
      </div>
    </div>
  );
}
