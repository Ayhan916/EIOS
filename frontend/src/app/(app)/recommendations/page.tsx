"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Download,
  ExternalLink,
  Filter,
  Layers,
  Loader2,
  Pencil,
  UserCheck,
} from "lucide-react";
import Link from "next/link";
import type { ActionStatus } from "@/types/api";
import apiClient from "@/lib/api/client";
import { updateRecommendation } from "@/lib/api/recommendations";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { ReadinessBanner } from "@/components/layout/readiness-banner";

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

function exportToCsv(rows: OrgRecommendation[], filename: string) {
  const headers = ["id", "title", "action_status", "priority", "due_date", "is_overdue", "supplier_name", "assessment_id"];
  const lines = [headers.join(",")];
  for (const r of rows) {
    lines.push(
      [r.id, `"${r.title.replace(/"/g, '""')}"`, r.action_status, r.priority, r.due_date ?? "", r.is_overdue, `"${r.supplier_name}"`, r.assessment_id].join(",")
    );
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ── Types ─────────────────────────────────────────────────────────────────────

interface OrgRecommendation {
  id: string;
  title: string;
  action_status: string;
  priority: string;
  due_date: string | null;
  assessment_id: string;
  created_at: string | null;
  supplier_name: string;
  supplier_id: string;
  is_overdue: boolean;
  assigned_to_id: string | null;
  expected_benefit: string | null;
  expected_risk: string | null;
  expected_roi: string | null;
  implementation_complexity: string | null;
}

const COMPLEXITY_STYLES: Record<string, string> = {
  "Low":       "bg-emerald-100 text-emerald-700",
  "Medium":    "bg-amber-100 text-amber-700",
  "High":      "bg-orange-100 text-orange-700",
  "Very High": "bg-red-100 text-red-700",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const PRIORITY_STYLES: Record<string, string> = {
  Critical:  "bg-red-100 text-red-800",
  High:      "bg-orange-100 text-orange-800",
  Medium:    "bg-amber-100 text-amber-800",
  Low:       "bg-slate-100 text-slate-700",
};

const STATUS_STYLES: Record<string, string> = {
  open:        "bg-slate-100 text-slate-700",
  in_progress: "bg-blue-100 text-blue-700",
  resolved:    "bg-amber-100 text-amber-700",
  verified:    "bg-emerald-100 text-emerald-700",
};

// ── Evidence Fields Panel (FR-015) ────────────────────────────────────────────

function EvidenceFieldsPanel({ rec, onDone }: { rec: OrgRecommendation; onDone: () => void }) {
  const [editing, setEditing] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [benefit, setBenefit] = useState(rec.expected_benefit ?? "");
  const [risk, setRisk] = useState(rec.expected_risk ?? "");
  const [roi, setRoi] = useState(rec.expected_roi ?? "");
  const [complexity, setComplexity] = useState(rec.implementation_complexity ?? "");

  const hasAny = rec.expected_benefit || rec.expected_risk || rec.expected_roi || rec.implementation_complexity;

  async function save() {
    setBusy(true);
    try {
      await updateRecommendation(rec.id, {
        expected_benefit: benefit || null,
        expected_risk: risk || null,
        expected_roi: roi || null,
        implementation_complexity: complexity || null,
      });
      setEditing(false);
      onDone();
    } finally {
      setBusy(false);
    }
  }

  if (editing) {
    return (
      <div className="mt-2 rounded-lg border border-blue-200 bg-blue-50/40 p-3 space-y-2">
        <p className="text-xs font-semibold text-blue-800">Evidenz-Felder (FR-015)</p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div>
            <label className="text-[10px] font-medium text-muted-foreground">Expected Benefit</label>
            <input
              className="mt-0.5 w-full rounded border border-border bg-background px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="Was verbessert sich?"
              value={benefit}
              onChange={(e) => setBenefit(e.target.value)}
            />
          </div>
          <div>
            <label className="text-[10px] font-medium text-muted-foreground">Expected Risk</label>
            <input
              className="mt-0.5 w-full rounded border border-border bg-background px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="Was passiert wenn nicht umgesetzt?"
              value={risk}
              onChange={(e) => setRisk(e.target.value)}
            />
          </div>
          <div>
            <label className="text-[10px] font-medium text-muted-foreground">Expected ROI</label>
            <input
              className="mt-0.5 w-full rounded border border-border bg-background px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="z.B. Audit €3k / Risiko €50k"
              value={roi}
              onChange={(e) => setRoi(e.target.value)}
            />
          </div>
          <div>
            <label className="text-[10px] font-medium text-muted-foreground">Implementation Complexity</label>
            <select
              className="mt-0.5 w-full rounded border border-border bg-background px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
              value={complexity}
              onChange={(e) => setComplexity(e.target.value)}
            >
              <option value="">— wählen —</option>
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
              <option value="Very High">Very High</option>
            </select>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={save}
            disabled={busy}
            className="inline-flex items-center gap-1 rounded bg-blue-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle2 className="h-3 w-3" />}
            Speichern
          </button>
          <button onClick={() => setEditing(false)} className="text-xs text-muted-foreground hover:text-foreground">
            Abbrechen
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-1.5">
      {hasAny ? (
        <div>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="inline-flex items-center gap-1 text-[10px] text-blue-600 hover:underline font-medium"
          >
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            Evidenz-Felder anzeigen
          </button>
          {expanded && (
            <div className="mt-1.5 rounded-md border border-border bg-muted/30 p-2 space-y-1.5 text-xs">
              {rec.expected_benefit && (
                <div><span className="font-semibold text-emerald-700">Benefit: </span>{rec.expected_benefit}</div>
              )}
              {rec.expected_risk && (
                <div><span className="font-semibold text-red-600">Risk: </span>{rec.expected_risk}</div>
              )}
              {rec.expected_roi && (
                <div><span className="font-semibold text-violet-700">ROI: </span>{rec.expected_roi}</div>
              )}
              {rec.implementation_complexity && (
                <div>
                  <span className="font-semibold text-muted-foreground">Complexity: </span>
                  <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${COMPLEXITY_STYLES[rec.implementation_complexity] ?? "bg-slate-100 text-slate-600"}`}>
                    {rec.implementation_complexity}
                  </span>
                </div>
              )}
              <button onClick={() => setEditing(true)} className="inline-flex items-center gap-1 text-[10px] text-blue-600 hover:underline mt-1">
                <Pencil className="h-2.5 w-2.5" /> Bearbeiten
              </button>
            </div>
          )}
        </div>
      ) : (
        <button
          onClick={() => setEditing(true)}
          className="inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-blue-600 transition-colors"
        >
          <Pencil className="h-2.5 w-2.5" /> Evidenz-Felder ergänzen
        </button>
      )}
    </div>
  );
}

// ── Quick status update button ────────────────────────────────────────────────

function StatusChanger({
  rec,
  onDone,
}: {
  rec: OrgRecommendation;
  onDone: () => void;
}) {
  const { t } = useLanguage();
  const [busy, setBusy] = useState<string | null>(null);

  async function changeStatus(newStatus: ActionStatus) {
    setBusy(newStatus);
    try {
      await updateRecommendation(rec.id, { action_status: newStatus });
      onDone();
    } finally {
      setBusy(null);
    }
  }

  const status = rec.action_status;

  if (status === "verified") {
    return (
      <span className="text-xs text-emerald-600 font-medium flex items-center gap-1">
        <CheckCircle2 className="h-3.5 w-3.5" /> {t("recommendations.verified")}
      </span>
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      {status === "open" && (
        <Button
          size="sm"
          variant="outline"
          className="h-7 gap-1 px-2 text-xs"
          disabled={!!busy}
          onClick={() => changeStatus("in_progress")}
        >
          {busy === "in_progress" ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
          {t("recommendations.startWork")}
        </Button>
      )}
      {(status === "open" || status === "in_progress") && (
        <Button
          size="sm"
          variant="outline"
          className="h-7 gap-1 px-2 text-xs"
          disabled={!!busy}
          onClick={() => changeStatus("resolved")}
        >
          {busy === "resolved" ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
          {t("recommendations.markResolved")}
        </Button>
      )}
      {status === "resolved" && (
        <Button
          size="sm"
          className="h-7 gap-1 px-2 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
          disabled={!!busy}
          onClick={() => changeStatus("verified")}
        >
          {busy === "verified" ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <CheckCircle2 className="h-3 w-3" />
          )}
          {t("recommendations.approve")}
        </Button>
      )}
    </div>
  );
}

// ── Assign to me ─────────────────────────────────────────────────────────────

function AssignToMeButton({ rec, onDone }: { rec: OrgRecommendation; onDone: () => void }) {
  const { user } = useAuth();
  const { t } = useLanguage();
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!user || rec.assigned_to_id === user.id || done) {
    return done ? (
      <span className="text-[10px] text-emerald-600 flex items-center gap-0.5">
        <UserCheck className="h-3 w-3" /> {t("recommendations.assigned")}
      </span>
    ) : null;
  }

  async function handleAssign() {
    setBusy(true);
    try {
      await updateRecommendation(rec.id, { assigned_to_id: user!.id });
      setDone(true);
      onDone();
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      onClick={handleAssign}
      disabled={busy}
      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-violet-700 hover:bg-violet-50 disabled:opacity-50 transition-colors"
      title="Assign to me"
    >
      {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <UserCheck className="h-3 w-3" />}
      {t("recommendations.assignToMe")}
    </button>
  );
}

// ── Summary cards ─────────────────────────────────────────────────────────────

function StatusSummary({ recs }: { recs: OrgRecommendation[] }) {
  const { t } = useLanguage();
  const open = recs.filter((r) => r.action_status === "open").length;
  const inProgress = recs.filter((r) => r.action_status === "in_progress").length;
  const overdue = recs.filter((r) => r.is_overdue).length;
  const resolved = recs.filter((r) => r.action_status === "resolved").length;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {[
        { label: t("recommendations.open"), value: open, cls: "bg-slate-50 border-slate-200" },
        { label: t("recommendations.inProgress"), value: inProgress, cls: "bg-blue-50 border-blue-200" },
        { label: t("recommendations.overdue"), value: overdue, cls: overdue > 0 ? "bg-red-50 border-red-200" : "bg-slate-50 border-slate-200" },
        { label: t("recommendations.awaitingApproval"), value: resolved, cls: resolved > 0 ? "bg-amber-50 border-amber-200" : "bg-slate-50 border-slate-200" },
      ].map(({ label, value, cls }) => (
        <Card key={label} className={`border ${cls}`}>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold tabular-nums">{value}</p>
            <p className="text-xs font-medium mt-0.5 text-muted-foreground">{label}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function RecommendationsPage() {
  const { user } = useAuth();
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const { data: recs, isLoading } = useQuery<OrgRecommendation[]>({
    queryKey: ["org-recommendations", statusFilter],
    queryFn: async () => {
      const params = statusFilter !== "all" ? `?action_status=${statusFilter}` : "";
      const res = await apiClient.get(`/executive/recommendations${params}`);
      return res.data;
    },
    staleTime: 20_000,
  });

  const allRecs = recs ?? [];
  const overdueCount = allRecs.filter((r) => r.is_overdue).length;

  function invalidate() {
    qc.invalidateQueries({ queryKey: ["org-recommendations"] });
  }

  function toggleAll() {
    if (selected.size === allRecs.length) setSelected(new Set());
    else setSelected(new Set(allRecs.map((r) => r.id)));
  }

  function toggleOne(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  const selectedRecs = allRecs.filter((r) => selected.has(r.id));
  const allSelected = allRecs.length > 0 && selected.size === allRecs.length;

  return (
    <div className="space-y-6">
      <ReadinessBanner stepKey="recommendations" />
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("recommendations.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("recommendations.subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {overdueCount > 0 && (
            <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">
              <AlertTriangle className="h-3 w-3" />
              {overdueCount} {t("recommendations.overdue")}
            </span>
          )}
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            className="h-8 rounded-md border border-input bg-background px-3 text-sm"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setSelected(new Set()); }}
          >
            <option value="all">{t("assessments.allStatus")}</option>
            <option value="open">{t("recommendations.open")}</option>
            <option value="in_progress">{t("recommendations.inProgress")}</option>
            <option value="resolved">{t("recommendations.awaitingApproval")}</option>
            <option value="verified">{t("findings.verified")}</option>
          </select>
          {selected.size > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 border-blue-300 text-blue-700"
              onClick={() => exportToCsv(selectedRecs, `recommendations-selected-${new Date().toISOString().split("T")[0]}.csv`)}
            >
              <Layers className="h-3.5 w-3.5" />
              {t("recommendations.exportSelected").replace("{n}", String(selected.size))}
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => {
              const params = statusFilter !== "all" ? `?action_status=${statusFilter}` : "";
              authenticatedDownload(
                `/executive/recommendations/export${params}`,
                `recommendations-${new Date().toISOString().split("T")[0]}.csv`
              );
            }}
          >
            <Download className="h-3.5 w-3.5" />
            CSV
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : (
        <>
          {statusFilter === "all" && <StatusSummary recs={allRecs} />}

          {allRecs.length === 0 ? (
            <div className="rounded-lg border border-dashed p-10 text-center">
              <CheckCircle2 className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">
                {statusFilter !== "all"
                  ? `${t("recommendations.noRecsWithStatus")} "${statusFilter}".`
                  : t("recommendations.noRecommendationsYetDesc")}
              </p>
            </div>
          ) : (
            <Card>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/30 text-xs text-muted-foreground">
                      <th className="px-4 py-3 text-left w-8">
                        <input type="checkbox" checked={allSelected} onChange={toggleAll} className="rounded" aria-label="Select all" />
                      </th>
                      <th className="px-4 py-3 text-left">{t("nav.recommendations")}</th>
                      <th className="px-4 py-3 text-left hidden sm:table-cell">{t("recommendations.priority")}</th>
                      <th className="px-4 py-3 text-left">{t("assessments.supplier")}</th>
                      <th className="px-4 py-3 text-left hidden md:table-cell">{t("findings.dueDate")}</th>
                      <th className="px-4 py-3 text-left">{t("common.status")}</th>
                      <th className="px-4 py-3 text-right">{t("common.actions")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {allRecs.map((r) => (
                      <tr
                        key={r.id}
                        className={`hover:bg-muted/20 transition-colors ${r.is_overdue ? "bg-red-50/30" : ""} ${selected.has(r.id) ? "bg-blue-50/40 dark:bg-blue-950/20" : ""}`}
                      >
                        <td className="px-4 py-3">
                          <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleOne(r.id)} className="rounded" />
                        </td>
                        <td className="px-4 py-3">
                          <p className="font-medium line-clamp-1 max-w-xs">{r.title}</p>
                          {r.is_overdue && (
                            <span className="inline-flex items-center gap-0.5 text-[10px] text-red-600 font-medium">
                              <Clock className="h-3 w-3" /> {t("recommendations.overdue")}
                            </span>
                          )}
                          {r.implementation_complexity && (
                            <span className={`mt-1 inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${COMPLEXITY_STYLES[r.implementation_complexity] ?? "bg-slate-100 text-slate-600"}`}>
                              {r.implementation_complexity}
                            </span>
                          )}
                          <EvidenceFieldsPanel rec={r} onDone={invalidate} />
                        </td>
                        <td className="px-4 py-3 hidden sm:table-cell">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_STYLES[r.priority] ?? "bg-slate-100 text-slate-700"}`}>
                            {r.priority || "—"}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <Link
                            href={`/suppliers/${r.supplier_id}`}
                            className="text-xs text-blue-600 hover:underline"
                          >
                            {r.supplier_name}
                          </Link>
                        </td>
                        <td className="px-4 py-3 hidden md:table-cell text-xs text-muted-foreground">
                          {r.due_date
                            ? new Date(r.due_date).toLocaleDateString()
                            : "—"}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[r.action_status] ?? "bg-slate-100 text-slate-600"}`}>
                            {r.action_status.replace("_", " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-col items-end gap-1">
                            <div className="flex items-center gap-2">
                              <StatusChanger rec={r} onDone={invalidate} />
                              <Link
                                href={`/assessments/${r.assessment_id}`}
                                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-blue-600"
                              >
                                <ExternalLink className="h-3 w-3" />
                              </Link>
                            </div>
                            {user && <AssignToMeButton rec={r} onDone={invalidate} />}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
