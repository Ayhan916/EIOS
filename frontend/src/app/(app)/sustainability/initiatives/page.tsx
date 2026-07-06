"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Clock,
  Link2,
  Loader2,
  PlayCircle,
  Plus,
  Shield,
  TrendingDown,
  X,
  Zap,
} from "lucide-react";
import {
  listInitiatives,
  listKPIs,
  updateInitiativeProgress,
  type DecarbonizationInitiative,
  type ESGKPI,
} from "@/lib/api/sustainability";
import apiClient from "@/lib/api/client";
import { useAuth } from "@/lib/auth/context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useLanguage } from "@/lib/i18n/context";
import { formatDate } from "@/lib/utils";

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES (OS)
// ═══════════════════════════════════════════════════════════════════════════════

interface ESGInitiative {
  id: string;
  title: string;
  description: string;
  owner_user_id: string | null;
  initiative_status: string;
  due_date: string | null;
  linked_objectives: string[];
  linked_suppliers: string[];
  linked_findings: string[];
  linked_risks: string[];
  created_at: string;
  updated_at: string;
}

interface ESGPlaybook {
  id: string;
  title: string;
  description: string;
  playbook_type: string;
  steps: Record<string, unknown>[];
  evidence_required: string[];
  playbook_status: string;
  created_at: string;
}

interface WorkflowExecution {
  id: string;
  workflow_type: string;
  current_step: number;
  total_steps: number;
  execution_status: string;
  pending_approvals: Record<string, unknown>[];
  linked_entity_type: string | null;
  linked_entity_id: string | null;
  created_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// COLOUR HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

const SUSTAIN_STATUS_COLORS: Record<string, string> = {
  IN_PROGRESS: "bg-blue-100 text-blue-800",
  COMPLETED:   "bg-emerald-100 text-emerald-800",
  CANCELLED:   "bg-red-100 text-red-800",
  PLANNED:     "bg-slate-100 text-slate-600",
};

const OS_INIT_STATUS_COL: Record<string, string> = {
  DRAFT:     "bg-slate-100 text-slate-600",
  PLANNED:   "bg-blue-100 text-blue-700",
  ACTIVE:    "bg-emerald-100 text-emerald-800",
  ON_HOLD:   "bg-amber-100 text-amber-700",
  COMPLETED: "bg-emerald-100 text-emerald-800",
  CANCELLED: "bg-slate-100 text-slate-500",
};

const WF_STATUS_COL: Record<string, string> = {
  PENDING:           "bg-blue-100 text-blue-700",
  IN_PROGRESS:       "bg-indigo-100 text-indigo-700",
  WAITING_APPROVAL:  "bg-amber-100 text-amber-700",
  COMPLETED:         "bg-emerald-100 text-emerald-800",
  REJECTED:          "bg-red-100 text-red-700",
  CANCELLED:         "bg-slate-100 text-slate-500",
};

const SUSTAIN_STATUSES = ["PLANNED", "IN_PROGRESS", "COMPLETED", "CANCELLED"] as const;
const OS_INIT_STATUSES = ["DRAFT", "PLANNED", "ACTIVE", "ON_HOLD", "COMPLETED", "CANCELLED"];

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 1 — KLIMASCHUTZ-INITIATIVEN (Sustainability / Decarbonization)
// ═══════════════════════════════════════════════════════════════════════════════

function SustainInitiativeCard({ init, orgId, kpis }: {
  init: DecarbonizationInitiative; orgId: string; kpis: ESGKPI[];
}) {
  const qc = useQueryClient();
  const { t } = useLanguage();
  const [open, setOpen] = useState(false);
  const [showKpiLink, setShowKpiLink] = useState(false);
  const [linkedKpiId, setLinkedKpiId] = useState("");
  const [actualReduction, setActualReduction] = useState(
    init.actual_reduction != null ? String(init.actual_reduction) : ""
  );
  const [newStatus, setNewStatus] = useState(init.initiative_status);

  const pct = init.actual_reduction != null && init.expected_reduction > 0
    ? Math.min(100, (init.actual_reduction / init.expected_reduction) * 100)
    : 0;

  const mutation = useMutation({
    mutationFn: () => updateInitiativeProgress(orgId, init.id, {
      actual_reduction: parseFloat(actualReduction) || 0,
      status: newStatus,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sustain-initiatives", orgId] }); setOpen(false); },
  });

  return (
    <div className="rounded-lg border p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-medium text-sm">{init.name}</p>
          <p className="text-xs text-muted-foreground">{init.initiative_type.replace(/_/g, " ")}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`rounded px-2 py-0.5 text-xs font-medium ${SUSTAIN_STATUS_COLORS[init.initiative_status] ?? "bg-slate-100 text-slate-600"}`}>
            {init.initiative_status.replace(/_/g, " ")}
          </span>
          <button onClick={() => { setShowKpiLink((v) => !v); setOpen(false); }}
            className="text-xs text-violet-600 hover:underline flex items-center gap-0.5" title="Link to KPI">
            <Link2 className="h-3.5 w-3.5" />
          </button>
          <button onClick={() => setOpen((v) => !v)}
            className="text-xs text-blue-600 hover:underline flex items-center gap-0.5">
            {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            {t("init.logProgress")}
          </button>
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{t("init.expectedReduction").replace("{n}", String(init.expected_reduction.toLocaleString()))}</span>
          {init.actual_reduction != null && <span>{t("init.actualReductionValue").replace("{n}", String(init.actual_reduction.toLocaleString()))}</span>}
        </div>
        <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
          <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${pct}%` }} />
        </div>
        <p className="text-xs text-right text-muted-foreground">{t("init.achieved").replace("{pct}", pct.toFixed(0))}</p>
      </div>

      {showKpiLink && (
        <div className="mt-3 rounded-md border border-violet-100 bg-violet-50 p-3 space-y-2">
          <p className="text-xs font-semibold text-violet-800">{t("init.linkToKpi")}</p>
          <div className="flex gap-2">
            <select className="flex-1 h-8 rounded border border-input bg-background px-2 text-xs"
              value={linkedKpiId} onChange={(e) => setLinkedKpiId(e.target.value)}>
              <option value="">{t("init.selectKpi")}</option>
              {kpis.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
            </select>
            <Button size="sm" className="h-8 text-xs bg-violet-600 hover:bg-violet-700" disabled={!linkedKpiId}
              onClick={async () => {
                await apiClient.patch(`/sustainability/${orgId}/initiatives/${init.id}`, { linked_kpi_id: linkedKpiId });
                qc.invalidateQueries({ queryKey: ["sustain-initiatives", orgId] });
                setShowKpiLink(false);
              }}>
              {t("init.link")}
            </Button>
            <button onClick={() => setShowKpiLink(false)} className="text-xs text-muted-foreground hover:underline">{t("common.cancel")}</button>
          </div>
        </div>
      )}

      {open && (
        <div className="mt-3 rounded-md border border-blue-100 bg-blue-50 p-3 space-y-3">
          <p className="text-xs font-semibold text-blue-800">{t("init.logProgressUpdate")}</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">{t("init.actualReductionLabel")}</label>
              <input type="number" min="0" step="0.01" value={actualReduction}
                onChange={(e) => setActualReduction(e.target.value)}
                placeholder={`Max ${init.expected_reduction}`}
                className="h-8 w-full rounded border border-input bg-white px-2 text-sm" />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">{t("common.status")}</label>
              <select value={newStatus} onChange={(e) => setNewStatus(e.target.value)}
                className="h-8 w-full rounded border border-input bg-white px-2 text-sm">
                {SUSTAIN_STATUSES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
              </select>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white h-7 px-3 text-xs"
              onClick={() => mutation.mutate()} disabled={mutation.isPending || !actualReduction}>
              {mutation.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
              {t("init.saveProgress")}
            </Button>
            <button onClick={() => setOpen(false)} className="text-xs text-muted-foreground hover:underline">{t("common.cancel")}</button>
            {mutation.isError && <span className="text-xs text-red-600">{(mutation.error as Error).message}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

function GanttTimeline({ initiatives }: { initiatives: DecarbonizationInitiative[] }) {
  const { t } = useLanguage();
  const withDates = initiatives.filter((i) => i.start_date && i.end_date);
  if (withDates.length === 0) return null;

  const allDates = withDates.flatMap((i) => [new Date(i.start_date!).getTime(), new Date(i.end_date!).getTime()]);
  const minTs = Math.min(...allDates);
  const maxTs = Math.max(...allDates);
  const span = maxTs - minTs || 1;

  const barColors: Record<string, string> = {
    PLANNED: "bg-slate-300", IN_PROGRESS: "bg-blue-500", COMPLETED: "bg-emerald-500", CANCELLED: "bg-red-300",
  };

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">{t("sustain.initiativeTimeline")}</CardTitle></CardHeader>
      <CardContent>
        <div className="space-y-2">
          {withDates.map((init) => {
            const start = new Date(init.start_date!).getTime();
            const end = new Date(init.end_date!).getTime();
            const left = ((start - minTs) / span) * 100;
            const width = Math.max(((end - start) / span) * 100, 2);
            return (
              <div key={init.id} className="flex items-center gap-3">
                <p className="w-36 truncate text-xs text-muted-foreground">{init.name}</p>
                <div className="flex-1 relative h-5 rounded bg-muted">
                  <div
                    className={`absolute top-0.5 h-4 rounded ${barColors[init.initiative_status] ?? "bg-slate-400"}`}
                    style={{ left: `${left}%`, width: `${width}%` }}
                    title={`${init.start_date} → ${init.end_date}`}
                  />
                </div>
              </div>
            );
          })}
        </div>
        <div className="mt-2 flex justify-between text-[10px] text-muted-foreground">
          <span>{new Date(minTs).getFullYear()}</span>
          <span>{new Date(maxTs).getFullYear()}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function KlimaschutzTab({ orgId }: { orgId: string }) {
  const { t } = useLanguage();

  const { data: initiatives, isLoading } = useQuery({
    queryKey: ["sustain-initiatives", orgId],
    queryFn: () => listInitiatives(orgId),
  });

  const { data: kpis } = useQuery({
    queryKey: ["kpis", orgId],
    queryFn: () => listKPIs(orgId),
    staleTime: 300_000,
  });

  const byStatus = {
    PLANNED:     initiatives?.filter((i) => i.initiative_status === "PLANNED") ?? [],
    IN_PROGRESS: initiatives?.filter((i) => i.initiative_status === "IN_PROGRESS") ?? [],
    COMPLETED:   initiatives?.filter((i) => i.initiative_status === "COMPLETED") ?? [],
  };
  const totalExpected = initiatives?.reduce((s, i) => s + i.expected_reduction, 0) ?? 0;
  const totalActual   = initiatives?.reduce((s, i) => s + (i.actual_reduction ?? 0), 0) ?? 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        {[
          { labelKey: "init.planned" as const,    count: byStatus.PLANNED.length,     color: "text-slate-600" },
          { labelKey: "init.inProgress" as const, count: byStatus.IN_PROGRESS.length,  color: "text-blue-600" },
          { labelKey: "init.completed" as const,  count: byStatus.COMPLETED.length,    color: "text-emerald-600" },
        ].map(({ labelKey, count, color }) => (
          <Card key={labelKey}>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">{t(labelKey)}</p>
              <p className={`text-2xl font-bold ${color}`}>{count}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {totalExpected > 0 && (
        <Card>
          <CardContent className="pt-4">
            <div className="flex justify-between text-sm mb-1">
              <span className="text-muted-foreground">{t("sustain.totalEmissionReductions")}</span>
              <span className="font-medium">{totalActual.toLocaleString()} / {totalExpected.toLocaleString()} tCO₂e</span>
            </div>
            <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
              <div className="h-full rounded-full bg-emerald-500"
                style={{ width: `${Math.min(100, (totalActual / totalExpected) * 100)}%` }} />
            </div>
          </CardContent>
        </Card>
      )}

      {initiatives && initiatives.length > 0 && <GanttTimeline initiatives={initiatives} />}

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingDown className="h-4 w-4 text-emerald-600" />
            {t("sustain.allInitiatives")}{initiatives ? ` (${initiatives.length})` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <Spinner />}
          {initiatives?.length === 0 && <p className="text-sm text-muted-foreground">{t("sustain.noInitiatives")}</p>}
          <div className="space-y-3">
            {initiatives?.map((init) => (
              <SustainInitiativeCard key={init.id} init={init} orgId={orgId} kpis={kpis ?? []} />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 2 — ESG-INITIATIVEN (Operating System)
// ═══════════════════════════════════════════════════════════════════════════════

function OsInitiativeCard({ init, onUpdated }: { init: ESGInitiative; onUpdated: () => void }) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const [newStatus, setNewStatus] = useState(init.initiative_status);
  const [showStatusForm, setShowStatusForm] = useState(false);

  const patch = useMutation({
    mutationFn: () =>
      apiClient.patch(`/operating-system/initiatives/${init.id}`, { initiative_status: newStatus }).then((r) => r.data),
    onSuccess: () => { onUpdated(); setShowStatusForm(false); },
  });

  return (
    <Card className={
      init.initiative_status === "ACTIVE"   ? "border-emerald-200" :
      init.initiative_status === "ON_HOLD"  ? "border-amber-200" : ""
    }>
      <CardContent className="py-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-muted-foreground shrink-0" />
              <p className="font-semibold">{init.title}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge className={OS_INIT_STATUS_COL[init.initiative_status] ?? "bg-slate-100 text-slate-600"}>
                {init.initiative_status}
              </Badge>
              {init.due_date && (
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />{formatDate(init.due_date)}
                </span>
              )}
            </div>
          </div>
          <Button size="sm" variant="outline" className="h-7 text-xs shrink-0"
            onClick={() => setShowStatusForm((v) => !v)}>
            {t("init.updateStatus")}
          </Button>
        </div>

        {showStatusForm && (
          <div className="flex items-center gap-2 border-t pt-2">
            <select className="h-8 rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring flex-1"
              value={newStatus} onChange={(e) => setNewStatus(e.target.value)}>
              {OS_INIT_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <Button size="sm" className="h-8 text-xs" disabled={patch.isPending || newStatus === init.initiative_status}
              onClick={() => patch.mutate()}>
              {patch.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
            </Button>
            <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={() => setShowStatusForm(false)}>
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}

        <button onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
          {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          {expanded ? t("init.hideDetails") : t("init.showDetails")}
        </button>

        {expanded && (
          <div className="border-t pt-2 space-y-2">
            {init.description && <p className="text-sm text-muted-foreground">{init.description}</p>}
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span>{t("init.linkedObjectives")}: <strong>{init.linked_objectives.length}</strong></span>
              <span>{t("init.linkedSuppliers")}: <strong>{init.linked_suppliers.length}</strong></span>
              <span>{t("init.linkedFindings")}: <strong>{init.linked_findings.length}</strong></span>
              <span>{t("init.linkedRisks")}: <strong>{init.linked_risks.length}</strong></span>
            </div>
            {init.owner_user_id && (
              <p className="text-xs text-muted-foreground font-mono">{t("init.owner")}: {init.owner_user_id.slice(0, 12)}…</p>
            )}
            <p className="text-xs text-muted-foreground">{formatDate(init.created_at)}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EsgInitiativesTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", due_date: "" });
  const [formError, setFormError] = useState("");

  const { data: initiatives = [], isLoading } = useQuery<ESGInitiative[]>({
    queryKey: ["os-initiatives", statusFilter],
    queryFn: () => apiClient.get("/operating-system/initiatives", {
      params: { ...(statusFilter ? { initiative_status: statusFilter } : {}), limit: 200 },
    }).then((r) => r.data),
  });

  const create = useMutation({
    mutationFn: () => {
      if (!form.title.trim()) throw new Error("validation");
      return apiClient.post("/operating-system/initiatives", {
        title: form.title.trim(),
        description: form.description.trim(),
        due_date: form.due_date ? new Date(form.due_date).toISOString() : undefined,
      }).then((r) => r.data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["os-initiatives"] });
      setShowForm(false);
      setForm({ title: "", description: "", due_date: "" });
      setFormError("");
    },
    onError: (e: Error) => setFormError(e.message === "validation" ? t("init.titleRequired") : t("init.createError")),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <select className="h-8 rounded border border-input bg-background px-3 text-sm"
          value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">{t("init.allStatuses")}</option>
          {OS_INIT_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <Button size="sm" onClick={() => { setShowForm((v) => !v); setFormError(""); }}>
          {showForm ? <X className="h-4 w-4 mr-1.5" /> : <Plus className="h-4 w-4 mr-1.5" />}
          {t("init.newInitiative")}
        </Button>
      </div>

      {showForm && (
        <Card className="border-primary/30 bg-muted/20">
          <CardContent className="py-5 space-y-4">
            <h2 className="text-sm font-semibold">{t("init.createTitle")}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-muted-foreground block mb-1.5">{t("init.titleField")} <span className="text-red-500">*</span></label>
                <input className="h-9 w-full rounded border border-input bg-background px-3 text-sm"
                  value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  placeholder="e.g. Reduce Scope 3 emissions by 30%" />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1.5">{t("init.dueDate")}</label>
                <input type="date" className="h-9 w-full rounded border border-input bg-background px-3 text-sm"
                  value={form.due_date} onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))} />
              </div>
              <div className="md:col-span-2">
                <label className="text-xs text-muted-foreground block mb-1.5">{t("init.description")}</label>
                <textarea rows={2} className="w-full rounded border border-input bg-background px-3 py-1.5 text-sm resize-none"
                  value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="Describe the initiative scope and goals…" />
              </div>
            </div>
            {formError && <p className="text-sm text-red-600">{formError}</p>}
            <div className="flex gap-2">
              <Button size="sm" disabled={create.isPending} onClick={() => create.mutate()}>
                {create.isPending
                  ? <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />{t("init.creating")}</>
                  : <><Plus className="h-3.5 w-3.5 mr-1.5" />{t("init.newInitiative")}</>}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setShowForm(false); setFormError(""); }}>{t("common.cancel")}</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : initiatives.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Zap className="mx-auto mb-3 h-10 w-10 opacity-25" />
          <p className="text-sm font-medium">{t("init.noInitiatives")}</p>
          <p className="text-xs mt-1">{t("init.noInitiativesDesc")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {initiatives.map((init) => (
            <OsInitiativeCard key={init.id} init={init} onUpdated={() => qc.invalidateQueries({ queryKey: ["os-initiatives"] })} />
          ))}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 3 — PLAYBOOKS
// ═══════════════════════════════════════════════════════════════════════════════

function PlaybookCard({ pb }: { pb: ESGPlaybook }) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  return (
    <Card>
      <CardContent className="py-4 space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1 flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-muted-foreground shrink-0" />
              <p className="font-semibold">{pb.title}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge className="bg-purple-100 text-purple-700">{pb.playbook_type}</Badge>
              <Badge className="bg-slate-100 text-slate-600">
                <Shield className="h-3 w-3 mr-1 inline" />{pb.playbook_status}
              </Badge>
              {pb.steps.length > 0 && <span className="text-xs text-muted-foreground">{pb.steps.length} {t("init.steps")}</span>}
            </div>
          </div>
          <p className="text-xs text-muted-foreground shrink-0">{formatDate(pb.created_at)}</p>
        </div>

        {pb.description && <p className="text-sm text-muted-foreground line-clamp-2">{pb.description}</p>}

        {pb.steps.length > 0 && (
          <>
            <button onClick={() => setExpanded((v) => !v)}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {expanded ? t("init.hideSteps") : t("init.showSteps").replace("{n}", String(pb.steps.length))}
            </button>
            {expanded && (
              <ol className="border-t pt-2 space-y-1.5 pl-1">
                {pb.steps.map((step, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                    <span className="rounded-full bg-muted text-foreground h-4 w-4 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">{i + 1}</span>
                    <span>{typeof step === "object" && step !== null ? String((step as Record<string, unknown>).title ?? JSON.stringify(step)) : String(step)}</span>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}

        {pb.evidence_required.length > 0 && (
          <div className="text-xs text-muted-foreground border-t pt-2">
            {t("init.evidenceRequired")}: {pb.evidence_required.join(", ")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PlaybooksTab() {
  const { t } = useLanguage();
  const { data: playbooks = [], isLoading } = useQuery<ESGPlaybook[]>({
    queryKey: ["os-playbooks"],
    queryFn: () => apiClient.get("/operating-system/playbooks").then((r) => r.data),
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (playbooks.length === 0) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <BookOpen className="mx-auto mb-3 h-10 w-10 opacity-25" />
        <p className="text-sm font-medium">{t("init.noPlaybooks")}</p>
        <p className="text-xs mt-1">{t("init.noPlaybooksDesc")}</p>
      </div>
    );
  }
  return <div className="space-y-3">{playbooks.map((pb) => <PlaybookCard key={pb.id} pb={pb} />)}</div>;
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 4 — WORKFLOWS
// ═══════════════════════════════════════════════════════════════════════════════

function WorkflowCard({ wf, onUpdated }: { wf: WorkflowExecution; onUpdated: () => void }) {
  const { t } = useLanguage();
  const [showApprove, setShowApprove] = useState(false);
  const [showReject, setShowReject] = useState(false);
  const [note, setNote] = useState("");
  const [reason, setReason] = useState("");

  const approve = useMutation({
    mutationFn: () =>
      apiClient.post(`/operating-system/workflows/${wf.id}/approve`, { step_note: note }).then((r) => r.data),
    onSuccess: () => { onUpdated(); setShowApprove(false); setNote(""); },
  });

  const reject = useMutation({
    mutationFn: () =>
      apiClient.post(`/operating-system/workflows/${wf.id}/reject`, { reason }).then((r) => r.data),
    onSuccess: () => { onUpdated(); setShowReject(false); setReason(""); },
  });

  const pct = wf.total_steps > 0 ? Math.round((wf.current_step / wf.total_steps) * 100) : 0;
  const hasPending = wf.pending_approvals.length > 0 || wf.execution_status === "WAITING_APPROVAL";

  return (
    <Card className={hasPending ? "border-amber-200" : ""}>
      <CardContent className="py-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-center gap-2">
              <PlayCircle className="h-4 w-4 text-muted-foreground shrink-0" />
              <p className="font-semibold">{wf.workflow_type}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge className={WF_STATUS_COL[wf.execution_status] ?? "bg-slate-100 text-slate-600"}>
                {wf.execution_status}
              </Badge>
              {hasPending && <Badge className="bg-amber-100 text-amber-800">{t("init.pendingApproval")}</Badge>}
            </div>
          </div>
          <p className="text-xs text-muted-foreground shrink-0">{formatDate(wf.created_at)}</p>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{t("init.progress")}</span>
            <span>{wf.current_step}/{wf.total_steps} ({pct}%)</span>
          </div>
          <div className="h-1.5 rounded-full bg-muted">
            <div className="h-1.5 rounded-full bg-primary transition-all" style={{ width: `${pct}%` }} />
          </div>
        </div>

        {wf.linked_entity_type && (
          <p className="text-xs text-muted-foreground">
            {t("init.linkedEntity").replace("{type}", wf.linked_entity_type!)} <span className="font-mono">{wf.linked_entity_id?.slice(0, 8)}…</span>
          </p>
        )}

        {hasPending && (
          <div className="border-t pt-2 space-y-2">
            {!showApprove && !showReject && (
              <div className="flex gap-2">
                <Button size="sm" className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700" onClick={() => setShowApprove(true)}>
                  <CheckCircle2 className="h-3.5 w-3.5 mr-1" />{t("init.approve")}
                </Button>
                <Button size="sm" variant="outline" className="h-8 text-xs text-red-700 border-red-300 hover:bg-red-50" onClick={() => setShowReject(true)}>
                  <X className="h-3.5 w-3.5 mr-1" />{t("init.reject")}
                </Button>
              </div>
            )}
            {showApprove && (
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground">{t("init.stepNote")}</label>
                <textarea rows={2} className="w-full rounded border border-input bg-background px-3 py-1.5 text-sm resize-none"
                  value={note} onChange={(e) => setNote(e.target.value)} />
                <div className="flex gap-2">
                  <Button size="sm" className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700"
                    disabled={approve.isPending} onClick={() => approve.mutate()}>
                    {approve.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : t("init.approve")}
                  </Button>
                  <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={() => setShowApprove(false)}>{t("common.cancel")}</Button>
                </div>
              </div>
            )}
            {showReject && (
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground">{t("init.rejectReason")}</label>
                <textarea rows={2} className="w-full rounded border border-input bg-background px-3 py-1.5 text-sm resize-none"
                  value={reason} onChange={(e) => setReason(e.target.value)} />
                <div className="flex gap-2">
                  <Button size="sm" variant="destructive" className="h-8 text-xs"
                    disabled={reject.isPending} onClick={() => reject.mutate()}>
                    {reject.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : t("init.reject")}
                  </Button>
                  <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={() => setShowReject(false)}>{t("common.cancel")}</Button>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function WorkflowsTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const { data: workflows = [], isLoading } = useQuery<WorkflowExecution[]>({
    queryKey: ["os-workflows"],
    queryFn: () => apiClient.get("/operating-system/workflows?limit=100").then((r) => r.data),
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (workflows.length === 0) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <PlayCircle className="mx-auto mb-3 h-10 w-10 opacity-25" />
        <p className="text-sm">{t("init.noWorkflows")}</p>
      </div>
    );
  }

  const sorted = [...workflows].sort((a, b) => {
    const aPending = a.execution_status === "WAITING_APPROVAL" ? 0 : 1;
    const bPending = b.execution_status === "WAITING_APPROVAL" ? 0 : 1;
    return aPending - bPending;
  });

  return (
    <div className="space-y-3">
      {sorted.map((wf) => (
        <WorkflowCard key={wf.id} wf={wf} onUpdated={() => qc.invalidateQueries({ queryKey: ["os-workflows"] })} />
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN HUB
// ═══════════════════════════════════════════════════════════════════════════════

const tab_defs = [
  { key: "klimaschutz", labelKey: "init.klimaschutzTab" as const },
  { key: "esg",         labelKey: "init.esgTab" as const },
  { key: "playbooks",   labelKey: "init.playbooksTab" as const },
  { key: "workflows",   labelKey: "init.workflowsTab" as const },
] as const;
type TabKey = (typeof tab_defs)[number]["key"];

export default function InitiativesHubPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";
  const [activeTab, setActiveTab] = useState<TabKey>("klimaschutz");

  // Preload workflow count for badge
  const { data: workflows = [] } = useQuery<WorkflowExecution[]>({
    queryKey: ["os-workflows"],
    queryFn: () => apiClient.get("/operating-system/workflows?limit=100").then((r) => r.data),
    staleTime: 60_000,
  });

  const pendingCount = workflows.filter(
    (w) => w.execution_status === "WAITING_APPROVAL" || w.pending_approvals.length > 0
  ).length;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("sustain.initiativesTitle")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("sustain.initiativesSubtitle")}</p>
      </div>

      {/* Tab bar */}
      <div className="border-b border-border">
        <nav className="-mb-px flex gap-0">
          {tab_defs.map((tab) => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`relative whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
              }`}>
              {t(tab.labelKey)}
              {tab.key === "workflows" && pendingCount > 0 && (
                <span className="ml-1.5 inline-flex items-center justify-center rounded-full bg-amber-500 text-white text-[10px] font-bold px-1.5 py-0.5 leading-none">
                  {pendingCount}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      {activeTab === "klimaschutz" && <KlimaschutzTab orgId={orgId} />}
      {activeTab === "esg"         && <EsgInitiativesTab />}
      {activeTab === "playbooks"   && <PlaybooksTab />}
      {activeTab === "workflows"   && <WorkflowsTab />}
    </div>
  );
}
