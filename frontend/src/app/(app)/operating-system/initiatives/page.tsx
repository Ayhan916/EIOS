"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Loader2,
  PlayCircle,
  Plus,
  Shield,
  X,
  Zap,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

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
  escalation_rules: Record<string, unknown>[];
  evidence_required: string[];
  playbook_status: string;
  created_at: string;
}

interface WorkflowExecution {
  id: string;
  playbook_id: string | null;
  workflow_type: string;
  current_step: number;
  total_steps: number;
  execution_status: string;
  steps_completed: Record<string, unknown>[];
  pending_approvals: Record<string, unknown>[];
  initiated_by: string | null;
  linked_entity_type: string | null;
  linked_entity_id: string | null;
  created_at: string;
  updated_at: string;
}

// ── Colour maps ───────────────────────────────────────────────────────────────

const INIT_STATUS_COL: Record<string, string> = {
  DRAFT:       "bg-slate-100 text-slate-600",
  PLANNED:     "bg-blue-100 text-blue-700",
  ACTIVE:      "bg-emerald-100 text-emerald-800",
  ON_HOLD:     "bg-amber-100 text-amber-700",
  COMPLETED:   "bg-emerald-100 text-emerald-800",
  CANCELLED:   "bg-slate-100 text-slate-500",
};

const WF_STATUS_COL: Record<string, string> = {
  PENDING:    "bg-blue-100 text-blue-700",
  IN_PROGRESS:"bg-indigo-100 text-indigo-700",
  WAITING_APPROVAL: "bg-amber-100 text-amber-700",
  COMPLETED:  "bg-emerald-100 text-emerald-800",
  REJECTED:   "bg-red-100 text-red-700",
  CANCELLED:  "bg-slate-100 text-slate-500",
};

const INIT_STATUSES = ["DRAFT", "PLANNED", "ACTIVE", "ON_HOLD", "COMPLETED", "CANCELLED"];

type TabKey = "initiatives" | "playbooks" | "workflows";

const tab_defs: { key: TabKey; labelKey: string }[] = [
  { key: "initiatives", labelKey: "init.initiativesTab" },
  { key: "playbooks",   labelKey: "init.playbooksTab" },
  { key: "workflows",   labelKey: "init.workflowsTab" },
];

// ── Initiative card ───────────────────────────────────────────────────────────

function InitiativeCard({ init, onUpdated }: { init: ESGInitiative; onUpdated: () => void }) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const [newStatus, setNewStatus] = useState(init.initiative_status);
  const [showStatusForm, setShowStatusForm] = useState(false);

  const patch = useMutation({
    mutationFn: () =>
      apiClient.patch(`/operating-system/initiatives/${init.id}`, {
        initiative_status: newStatus,
      }).then((r) => r.data),
    onSuccess: () => { onUpdated(); setShowStatusForm(false); },
  });

  return (
    <Card className={init.initiative_status === "ACTIVE" ? "border-emerald-200" : init.initiative_status === "ON_HOLD" ? "border-amber-200" : ""}>
      <CardContent className="py-4 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-muted-foreground shrink-0" />
              <p className="font-semibold">{init.title}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge className={INIT_STATUS_COL[init.initiative_status] ?? "bg-slate-100 text-slate-600"}>
                {init.initiative_status}
              </Badge>
              {init.due_date && (
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  {formatDate(init.due_date)}
                </span>
              )}
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs shrink-0"
            onClick={() => setShowStatusForm((v) => !v)}
          >
            {t("init.updateStatus")}
          </Button>
        </div>

        {/* Status update inline form */}
        {showStatusForm && (
          <div className="flex items-center gap-2 border-t pt-2">
            <select
              className="h-8 rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring flex-1"
              value={newStatus}
              onChange={(e) => setNewStatus(e.target.value)}
            >
              {INIT_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <Button
              size="sm"
              className="h-8 text-xs"
              disabled={patch.isPending || newStatus === init.initiative_status}
              onClick={() => patch.mutate()}
            >
              {patch.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
            </Button>
            <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={() => setShowStatusForm(false)}>
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}

        {/* Expand */}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
        >
          {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          {expanded ? "Hide details" : "Show details"}
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

// ── Workflow card ─────────────────────────────────────────────────────────────

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
              {hasPending && (
                <Badge className="bg-amber-100 text-amber-800">{t("init.pendingApproval")}</Badge>
              )}
            </div>
          </div>
          <p className="text-xs text-muted-foreground shrink-0">{formatDate(wf.created_at)}</p>
        </div>

        {/* Progress bar */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{t("init.progress")}</span>
            <span>{wf.current_step}/{wf.total_steps} ({pct}%)</span>
          </div>
          <div className="h-1.5 rounded-full bg-muted">
            <div
              className="h-1.5 rounded-full bg-primary transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {wf.linked_entity_type && (
          <p className="text-xs text-muted-foreground">
            Linked: {wf.linked_entity_type} <span className="font-mono">{wf.linked_entity_id?.slice(0, 8)}…</span>
          </p>
        )}

        {/* Approve / Reject — only when waiting */}
        {hasPending && (
          <div className="border-t pt-2 space-y-2">
            {!showApprove && !showReject && (
              <div className="flex gap-2">
                <Button
                  size="sm"
                  className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700"
                  onClick={() => setShowApprove(true)}
                >
                  <CheckCircle2 className="h-3.5 w-3.5 mr-1" />{t("init.approve")}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 text-xs text-red-700 border-red-300 hover:bg-red-50"
                  onClick={() => setShowReject(true)}
                >
                  <X className="h-3.5 w-3.5 mr-1" />{t("init.reject")}
                </Button>
              </div>
            )}

            {showApprove && (
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground">{t("init.stepNote")}</label>
                <textarea
                  rows={2}
                  className="w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700"
                    disabled={approve.isPending}
                    onClick={() => approve.mutate()}
                  >
                    {approve.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : t("init.approve")}
                  </Button>
                  <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={() => setShowApprove(false)}>
                    {t("common.cancel")}
                  </Button>
                </div>
              </div>
            )}

            {showReject && (
              <div className="space-y-2">
                <label className="text-xs text-muted-foreground">{t("init.rejectReason")}</label>
                <textarea
                  rows={2}
                  className="w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="destructive"
                    className="h-8 text-xs"
                    disabled={reject.isPending}
                    onClick={() => reject.mutate()}
                  >
                    {reject.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : t("init.reject")}
                  </Button>
                  <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={() => setShowReject(false)}>
                    {t("common.cancel")}
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function InitiativesPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabKey>("initiatives");
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", due_date: "" });
  const [formError, setFormError] = useState("");

  // ── Queries ──────────────────────────────────────────────────────────────

  const { data: initiatives = [], isLoading: initLoading } = useQuery<ESGInitiative[]>({
    queryKey: ["os-initiatives", statusFilter],
    queryFn: () =>
      apiClient.get("/operating-system/initiatives", {
        params: { ...(statusFilter ? { initiative_status: statusFilter } : {}), limit: 200 },
      }).then((r) => r.data),
    enabled: activeTab === "initiatives",
  });

  const { data: playbooks = [], isLoading: pbLoading } = useQuery<ESGPlaybook[]>({
    queryKey: ["os-playbooks"],
    queryFn: () => apiClient.get("/operating-system/playbooks").then((r) => r.data),
    enabled: activeTab === "playbooks",
  });

  const { data: workflows = [], isLoading: wfLoading } = useQuery<WorkflowExecution[]>({
    queryKey: ["os-workflows"],
    queryFn: () => apiClient.get("/operating-system/workflows?limit=100").then((r) => r.data),
    enabled: activeTab === "workflows",
  });

  // ── Mutations ────────────────────────────────────────────────────────────

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
    onError: (e: Error) => setFormError(e.message === "validation" ? "Title is required." : "Failed to create."),
  });

  function invalidateInitiatives() {
    qc.invalidateQueries({ queryKey: ["os-initiatives"] });
  }

  function invalidateWorkflows() {
    qc.invalidateQueries({ queryKey: ["os-workflows"] });
  }

  const pendingCount = workflows.filter(
    (w) => w.execution_status === "WAITING_APPROVAL" || w.pending_approvals.length > 0
  ).length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Zap className="h-7 w-7 text-primary mt-0.5 shrink-0" />
          <div>
            <h1 className="text-2xl font-semibold">{t("init.title")}</h1>
            <p className="text-sm text-muted-foreground">{t("init.subtitle")}</p>
          </div>
        </div>
        {activeTab === "initiatives" && (
          <Button size="sm" onClick={() => { setShowForm((v) => !v); setFormError(""); }}>
            {showForm ? <X className="h-4 w-4 mr-1.5" /> : <Plus className="h-4 w-4 mr-1.5" />}
            {t("init.newInitiative")}
          </Button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {tab_defs.map(({ key, labelKey }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors ${
              activeTab === key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t(labelKey as Parameters<typeof t>[0])}
            {key === "workflows" && pendingCount > 0 && (
              <span className="rounded-full bg-amber-500 text-white text-[10px] font-bold px-1.5 py-0.5 leading-none">
                {pendingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── INITIATIVES TAB ────────────────────────────────────────────────── */}
      {activeTab === "initiatives" && (
        <div className="space-y-4">
          {/* Create form */}
          {showForm && (
            <Card className="border-primary/30 bg-muted/20">
              <CardContent className="py-5 space-y-4">
                <h2 className="text-sm font-semibold">{t("init.createTitle")}</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1.5">
                      {t("init.titleField")} <span className="text-red-500">*</span>
                    </label>
                    <input
                      className="h-9 w-full rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      value={form.title}
                      onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                      placeholder="e.g. Reduce Scope 3 emissions by 30%"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1.5">{t("init.dueDate")}</label>
                    <input
                      type="date"
                      className="h-9 w-full rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      value={form.due_date}
                      onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))}
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="text-xs text-muted-foreground block mb-1.5">{t("init.description")}</label>
                    <textarea
                      rows={2}
                      className="w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                      value={form.description}
                      onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                      placeholder="Describe the initiative scope and goals…"
                    />
                  </div>
                </div>
                {formError && <p className="text-sm text-red-600">{formError}</p>}
                <div className="flex gap-2">
                  <Button size="sm" disabled={create.isPending} onClick={() => create.mutate()}>
                    {create.isPending
                      ? <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />{t("init.creating")}</>
                      : <><Plus className="h-3.5 w-3.5 mr-1.5" />{t("init.newInitiative")}</>}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => { setShowForm(false); setFormError(""); }}>
                    {t("common.cancel")}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Filter */}
          <div className="flex gap-2">
            <select
              className="h-8 rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">{t("init.allStatuses")}</option>
              {INIT_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          {initLoading ? (
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
                <InitiativeCard key={init.id} init={init} onUpdated={invalidateInitiatives} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── PLAYBOOKS TAB ──────────────────────────────────────────────────── */}
      {activeTab === "playbooks" && (
        <div className="space-y-3">
          {pbLoading ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : playbooks.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <BookOpen className="mx-auto mb-3 h-10 w-10 opacity-25" />
              <p className="text-sm font-medium">{t("init.noPlaybooks")}</p>
              <p className="text-xs mt-1">{t("init.noPlaybooksDesc")}</p>
            </div>
          ) : (
            playbooks.map((pb) => (
              <PlaybookCard key={pb.id} pb={pb} />
            ))
          )}
        </div>
      )}

      {/* ── WORKFLOWS TAB ──────────────────────────────────────────────────── */}
      {activeTab === "workflows" && (
        <div className="space-y-3">
          {wfLoading ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : workflows.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <PlayCircle className="mx-auto mb-3 h-10 w-10 opacity-25" />
              <p className="text-sm">{t("init.noWorkflows")}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Pending first */}
              {workflows
                .slice()
                .sort((a, b) => {
                  const aPending = a.execution_status === "WAITING_APPROVAL" ? 0 : 1;
                  const bPending = b.execution_status === "WAITING_APPROVAL" ? 0 : 1;
                  return aPending - bPending;
                })
                .map((wf) => (
                  <WorkflowCard key={wf.id} wf={wf} onUpdated={invalidateWorkflows} />
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Playbook card (separate to avoid closure size) ────────────────────────────

function PlaybookCard({ pb }: { pb: ESGPlaybook }) {
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
                <Shield className="h-3 w-3 mr-1 inline" />
                {pb.playbook_status}
              </Badge>
              {pb.steps.length > 0 && (
                <span className="text-xs text-muted-foreground">{pb.steps.length} steps</span>
              )}
            </div>
          </div>
          <p className="text-xs text-muted-foreground shrink-0">{formatDate(pb.created_at)}</p>
        </div>

        {pb.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">{pb.description}</p>
        )}

        {pb.steps.length > 0 && (
          <>
            <button
              onClick={() => setExpanded((v) => !v)}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {expanded ? "Hide steps" : `Show ${pb.steps.length} steps`}
            </button>
            {expanded && (
              <ol className="border-t pt-2 space-y-1.5 pl-1">
                {pb.steps.map((step, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                    <span className="rounded-full bg-muted text-foreground h-4 w-4 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <span>{typeof step === "object" && step !== null ? String((step as Record<string, unknown>).title ?? JSON.stringify(step)) : String(step)}</span>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}

        {pb.evidence_required.length > 0 && (
          <div className="text-xs text-muted-foreground border-t pt-2">
            Evidence required: {pb.evidence_required.join(", ")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
