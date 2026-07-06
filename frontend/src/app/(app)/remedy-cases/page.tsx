"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Scale, Plus, AlertTriangle, CheckCircle2, Clock, X,
  ChevronRight, ListChecks, Users, BarChart2,
} from "lucide-react";
import {
  listRemedyCases, createRemedyCase, updateRemedyCase, closeRemedyCase,
  listActions, addAction, updateAction, getRemedySummaryReport,
  type RemedyCase, type RemedyCaseCreate, type RemedyAction,
} from "@/lib/api/remedy-cases";
import { extractErrorMessage } from "@/lib/utils";

const STATUS_COLORS: Record<string, string> = {
  open: "bg-red-100 text-red-700",
  in_progress: "bg-amber-100 text-amber-700",
  completed: "bg-emerald-100 text-emerald-700",
  verified: "bg-blue-100 text-blue-700",
};

const STATUS_LABELS: Record<string, string> = {
  open: "Offen",
  in_progress: "In Bearbeitung",
  completed: "Abgeschlossen",
  verified: "Verifiziert",
};

const ACTION_STATUS_COLORS: Record<string, string> = {
  todo: "bg-slate-100 text-slate-600",
  in_progress: "bg-amber-100 text-amber-700",
  done: "bg-emerald-100 text-emerald-700",
};

const SEVERITY_COLOR = (score: number) => {
  if (score >= 7) return "text-red-600 font-semibold";
  if (score >= 4) return "text-amber-600";
  return "text-emerald-600";
};

const CURRENT_YEAR = new Date().getFullYear();

// ── Helpers ───────────────────────────────────────────────────────────────────

function Badge({ label, colorClass }: { label: string; colorClass: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {label}
    </span>
  );
}

// ── New Case Modal ─────────────────────────────────────────────────────────────

function NewCaseModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<RemedyCaseCreate>({
    title: "",
    description: "",
    incident_date: new Date().toISOString().slice(0, 16),
    affected_count: 0,
    affected_type: "worker",
    impact_causation: "own",
    severity_score: 5,
    rights: [],
    remedy_types: [],
    co_responsible_parties: [],
  });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: createRemedyCase,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["remedy-cases"] });
      onClose();
    },
    onError: (e: unknown) => setError(extractErrorMessage(e)),
  });

  const set = (k: keyof RemedyCaseCreate, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-800">Neuer Remedy Case</h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400 hover:text-slate-700" /></button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium text-slate-700">Titel *</label>
            <input
              className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              value={form.title}
              onChange={(e) => set("title", e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Beschreibung</label>
            <textarea
              className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              rows={3}
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium text-slate-700">Vorfalldatum *</label>
              <input
                type="datetime-local"
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={form.incident_date}
                onChange={(e) => set("incident_date", e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Betroffene Personen</label>
              <input
                type="number"
                min={0}
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={form.affected_count}
                onChange={(e) => set("affected_count", parseInt(e.target.value) || 0)}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium text-slate-700">Betroffene Art *</label>
              <select
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={form.affected_type}
                onChange={(e) => set("affected_type", e.target.value)}
              >
                <option value="worker">Arbeitnehmer</option>
                <option value="community">Gemeinschaft</option>
                <option value="environment">Umwelt</option>
                <option value="other">Sonstige</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Verursachung *</label>
              <select
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={form.impact_causation}
                onChange={(e) => set("impact_causation", e.target.value)}
              >
                <option value="own">Eigene Verursachung</option>
                <option value="joint_with_third_party">Gemeinsam mit Dritten</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Schweregrad (0–10)</label>
            <input
              type="range"
              min={0}
              max={10}
              step={0.5}
              className="mt-1 w-full"
              value={form.severity_score}
              onChange={(e) => set("severity_score", parseFloat(e.target.value))}
            />
            <div className="text-right text-xs text-slate-500">{form.severity_score}</div>
          </div>
        </div>

        {error && <p className="mt-3 text-xs text-red-600">{error}</p>}

        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800">
            Abbrechen
          </button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.title}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {mutation.isPending ? "Wird erstellt..." : "Erstellen"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Case Detail Panel ─────────────────────────────────────────────────────────

function CaseDetail({
  remedyCase,
  onClose,
}: {
  remedyCase: RemedyCase;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [newAction, setNewAction] = useState("");
  const [closeNotes, setCloseNotes] = useState("");
  const [showClose, setShowClose] = useState(false);

  const { data: actions = [] } = useQuery({
    queryKey: ["remedy-actions", remedyCase.id],
    queryFn: () => listActions(remedyCase.id),
  });

  const addActionMut = useMutation({
    mutationFn: (title: string) => addAction(remedyCase.id, { title }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["remedy-actions", remedyCase.id] });
      setNewAction("");
    },
  });

  const updateActionMut = useMutation({
    mutationFn: ({ actionId, status }: { actionId: string; status: string }) =>
      updateAction(remedyCase.id, actionId, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["remedy-actions", remedyCase.id] }),
  });

  const closeMut = useMutation({
    mutationFn: () => closeRemedyCase(remedyCase.id, closeNotes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["remedy-cases"] });
      setShowClose(false);
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end bg-black/30">
      <div className="w-full max-w-lg h-full bg-white shadow-2xl flex flex-col overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b">
          <div>
            <h2 className="text-base font-semibold text-slate-800">{remedyCase.title}</h2>
            <Badge
              label={STATUS_LABELS[remedyCase.status] || remedyCase.status}
              colorClass={STATUS_COLORS[remedyCase.status] || "bg-slate-100 text-slate-600"}
            />
          </div>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400 hover:text-slate-700" /></button>
        </div>

        <div className="p-5 space-y-4">
          {/* Meta */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-slate-500">Vorfall</p>
              <p className="font-medium">{new Date(remedyCase.incident_date).toLocaleDateString("de-DE")}</p>
            </div>
            <div>
              <p className="text-slate-500">Betroffene</p>
              <p className="font-medium">{remedyCase.affected_count} ({remedyCase.affected_type})</p>
            </div>
            <div>
              <p className="text-slate-500">Schweregrad</p>
              <p className={`font-medium ${SEVERITY_COLOR(remedyCase.severity_score)}`}>{remedyCase.severity_score}/10</p>
            </div>
            <div>
              <p className="text-slate-500">Verursachung</p>
              <p className="font-medium">{remedyCase.impact_causation === "own" ? "Eigene" : "Mit Dritten"}</p>
            </div>
          </div>

          {remedyCase.description && (
            <p className="text-sm text-slate-600">{remedyCase.description}</p>
          )}

          {/* Actions */}
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1.5">
              <ListChecks className="w-4 h-4" /> Maßnahmen
            </h3>
            <div className="space-y-2">
              {actions.map((a) => (
                <div key={a.id} className="flex items-center gap-2 p-2 bg-slate-50 rounded-lg text-sm">
                  <span className="flex-1">{a.title}</span>
                  <select
                    className={`text-xs rounded px-1.5 py-0.5 border-0 ${ACTION_STATUS_COLORS[a.status]}`}
                    value={a.status}
                    onChange={(e) => updateActionMut.mutate({ actionId: a.id, status: e.target.value })}
                  >
                    <option value="todo">Offen</option>
                    <option value="in_progress">In Bearbeitung</option>
                    <option value="done">Erledigt</option>
                  </select>
                </div>
              ))}
            </div>
            <div className="mt-2 flex gap-2">
              <input
                className="flex-1 border rounded-lg px-3 py-1.5 text-sm"
                placeholder="Neue Maßnahme..."
                value={newAction}
                onChange={(e) => setNewAction(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && newAction && addActionMut.mutate(newAction)}
              />
              <button
                onClick={() => newAction && addActionMut.mutate(newAction)}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Close Case — Analyst/Admin only */}
          {remedyCase.status !== "completed" && remedyCase.status !== "verified" && (
            <div className="border-t pt-4">
              {!showClose ? (
                <button
                  onClick={() => setShowClose(true)}
                  className="w-full py-2 text-sm text-slate-600 border border-dashed rounded-lg hover:border-emerald-500 hover:text-emerald-600"
                >
                  Fall abschließen (Analyst / Admin)
                </button>
              ) : (
                <div className="space-y-2">
                  <textarea
                    rows={3}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    placeholder="Abschlussnotiz (optional)..."
                    value={closeNotes}
                    onChange={(e) => setCloseNotes(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowClose(false)}
                      className="flex-1 py-2 text-sm border rounded-lg text-slate-600 hover:bg-slate-50"
                    >
                      Abbrechen
                    </button>
                    <button
                      onClick={() => closeMut.mutate()}
                      disabled={closeMut.isPending}
                      className="flex-1 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50"
                    >
                      {closeMut.isPending ? "..." : "Abschließen bestätigen"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function RemedyCasesPage() {
  const [activeTab, setActiveTab] = useState<"all" | "report">("all");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [showNew, setShowNew] = useState(false);
  const [selected, setSelected] = useState<RemedyCase | null>(null);

  const { data: cases = [], isLoading } = useQuery({
    queryKey: ["remedy-cases", statusFilter],
    queryFn: () => listRemedyCases(statusFilter || undefined),
  });

  const { data: report } = useQuery({
    queryKey: ["remedy-summary", CURRENT_YEAR],
    queryFn: () => getRemedySummaryReport(CURRENT_YEAR),
    enabled: activeTab === "report",
  });

  const open = cases.filter((c) => c.status === "open").length;
  const inProgress = cases.filter((c) => c.status === "in_progress").length;
  const completed = cases.filter((c) => c.status === "completed" || c.status === "verified").length;
  const highSeverity = cases.filter((c) => c.severity_score >= 7).length;

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Scale className="w-7 h-7 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Remedy Case Manager</h1>
            <p className="text-sm text-slate-500">CSDDD Art. 12 — Wiedergutmachungsmaßnahmen</p>
          </div>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" /> Neuer Fall
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Offen", value: open, icon: Clock, color: "text-red-600" },
          { label: "In Bearbeitung", value: inProgress, icon: ChevronRight, color: "text-amber-600" },
          { label: "Abgeschlossen", value: completed, icon: CheckCircle2, color: "text-emerald-600" },
          { label: "Hohes Risiko (≥7)", value: highSeverity, icon: AlertTriangle, color: "text-red-500" },
        ].map((kpi) => (
          <div key={kpi.label} className="bg-white border rounded-xl p-4 flex items-center gap-3">
            <kpi.icon className={`w-8 h-8 ${kpi.color}`} />
            <div>
              <p className="text-2xl font-bold text-slate-800">{kpi.value}</p>
              <p className="text-xs text-slate-500">{kpi.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b">
        {[
          { id: "all", label: "Alle Fälle" },
          { id: "report", label: `Jahresbericht ${CURRENT_YEAR}` },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id as typeof activeTab)}
            className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              activeTab === t.id
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab: Alle Fälle */}
      {activeTab === "all" && (
        <div className="space-y-3">
          <div className="flex gap-2">
            {["", "open", "in_progress", "completed", "verified"].map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  statusFilter === s
                    ? "bg-blue-600 text-white border-blue-600"
                    : "border-slate-200 text-slate-600 hover:border-blue-300"
                }`}
              >
                {s === "" ? "Alle" : STATUS_LABELS[s] || s}
              </button>
            ))}
          </div>

          {isLoading ? (
            <p className="text-sm text-slate-500">Wird geladen...</p>
          ) : cases.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Scale className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Keine Remedy Cases vorhanden</p>
            </div>
          ) : (
            <div className="space-y-2">
              {cases.map((c) => (
                <div
                  key={c.id}
                  onClick={() => setSelected(c)}
                  className="bg-white border rounded-xl p-4 flex items-center gap-4 cursor-pointer hover:border-blue-300 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-medium text-slate-800 truncate">{c.title}</p>
                      <Badge
                        label={STATUS_LABELS[c.status] || c.status}
                        colorClass={STATUS_COLORS[c.status] || "bg-slate-100 text-slate-600"}
                      />
                    </div>
                    <p className="text-xs text-slate-500">
                      {new Date(c.incident_date).toLocaleDateString("de-DE")} ·{" "}
                      {c.affected_count} Betroffene · {c.affected_type}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className={`text-sm font-semibold ${SEVERITY_COLOR(c.severity_score)}`}>
                      {c.severity_score}/10
                    </p>
                    <p className="text-xs text-slate-400">Schweregrad</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab: Jahresbericht */}
      {activeTab === "report" && (
        <div className="bg-white border rounded-xl p-6">
          {!report ? (
            <p className="text-sm text-slate-500">Wird geladen...</p>
          ) : (
            <div className="space-y-6">
              <div className="flex items-center gap-2">
                <BarChart2 className="w-5 h-5 text-blue-600" />
                <h2 className="text-base font-semibold text-slate-800">
                  CSDDD Art. 12 Jahresbericht {report.year}
                </h2>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Stat label="Fälle gesamt" value={report.total} />
                <Stat label="Betroffene Personen" value={report.total_affected_persons} />
                <Stat label="Ø Schweregrad" value={report.avg_severity} />
                <Stat label="Abgeschlossen" value={(report.by_status?.completed || 0) + (report.by_status?.verified || 0)} />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <StatusBreakdown title="Nach Status" data={report.by_status} labels={STATUS_LABELS} />
                <StatusBreakdown
                  title="Nach Betroffener Art"
                  data={report.by_affected_type}
                  labels={{ worker: "Arbeitnehmer", community: "Gemeinschaft", environment: "Umwelt", other: "Sonstige" }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {showNew && <NewCaseModal onClose={() => setShowNew(false)} />}
      {selected && <CaseDetail remedyCase={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-slate-50 rounded-xl p-4">
      <p className="text-2xl font-bold text-slate-800">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  );
}

function StatusBreakdown({
  title,
  data,
  labels,
}: {
  title: string;
  data: Record<string, number>;
  labels: Record<string, string>;
}) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-700 mb-2">{title}</h3>
      <div className="space-y-1">
        {Object.entries(data).map(([k, v]) => (
          <div key={k} className="flex justify-between text-sm">
            <span className="text-slate-600">{labels[k] || k}</span>
            <span className="font-medium text-slate-800">{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
