"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Building2, CheckCircle, Clock, Play, XCircle, AlertTriangle,
  Plus, ChevronDown, ChevronUp, X, Euro, Users,
} from "lucide-react";
import {
  listProfiles, getProfileSummary, upsertProfile, confirmProfile,
  listPrograms, createProgram, activateProgram, completeProgram,
  listMeasures, addMeasure, completeMeasure, updateMeasureStatus,
  getAnnualReport,
  type SMEProfile, type SupportProgram, type SupportMeasure,
} from "@/lib/api/sme-support";

const CLASSIFICATION_CONFIG: Record<string, { label: string; color: string; desc: string }> = {
  micro: { label: "Micro", color: "text-purple-600 bg-purple-50 border-purple-200", desc: "<10 MA / ≤€2M" },
  small: { label: "Klein", color: "text-blue-600 bg-blue-50 border-blue-200", desc: "<50 MA / ≤€10M" },
  medium: { label: "Mittel", color: "text-emerald-600 bg-emerald-50 border-emerald-200", desc: "<250 MA / ≤€50M" },
  large: { label: "Groß", color: "text-slate-600 bg-slate-50 border-slate-200", desc: "≥250 MA / >€50M" },
};

const PROGRAM_STATUS: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  draft: { label: "Entwurf", color: "text-slate-600 bg-slate-50 border-slate-200", icon: <Clock className="w-3 h-3" /> },
  active: { label: "Aktiv", color: "text-blue-600 bg-blue-50 border-blue-200", icon: <Play className="w-3 h-3" /> },
  completed: { label: "Abgeschlossen", color: "text-emerald-600 bg-emerald-50 border-emerald-200", icon: <CheckCircle className="w-3 h-3" /> },
  cancelled: { label: "Abgebrochen", color: "text-red-600 bg-red-50 border-red-200", icon: <XCircle className="w-3 h-3" /> },
};

const MEASURE_STATUS: Record<string, { label: string; color: string }> = {
  planned: { label: "Geplant", color: "text-slate-600" },
  in_progress: { label: "In Arbeit", color: "text-blue-600" },
  completed: { label: "Erledigt", color: "text-emerald-600" },
  cancelled: { label: "Abgebrochen", color: "text-red-600" },
};

const SUPPORT_TYPES: Record<string, string> = {
  training: "Training",
  financial_aid: "Finanzhilfe",
  tools_resources: "Tools & Ressourcen",
  capacity_building: "Kapazitätsaufbau",
  co_investment: "Co-Investition",
  mentoring: "Mentoring",
  audit_support: "Audit-Unterstützung",
  other: "Sonstige",
};

// ── Small components ──────────────────────────────────────────────────────────

function ClassificationBadge({ cls }: { cls: string }) {
  const cfg = CLASSIFICATION_CONFIG[cls] ?? CLASSIFICATION_CONFIG.small;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium ${cfg.color}`}>
      {cfg.label}
      <span className="text-xs opacity-60">{cfg.desc}</span>
    </span>
  );
}

function ProgramBadge({ status }: { status: string }) {
  const cfg = PROGRAM_STATUS[status] ?? PROGRAM_STATUS.draft;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium ${cfg.color}`}>
      {cfg.icon} {cfg.label}
    </span>
  );
}

function KpiCard({ label, value, color = "text-slate-800", sub }: { label: string; value: number | string; color?: string; sub?: string }) {
  return (
    <div className="bg-white border rounded-xl p-4">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-xs text-slate-500 mt-0.5">{label}</p>
      {sub && <p className="text-xs text-slate-400">{sub}</p>}
    </div>
  );
}

// ── Register SME dialog ───────────────────────────────────────────────────────

function RegisterDialog({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [supplierId, setSupplierId] = useState("");
  const [employees, setEmployees] = useState("");
  const [revenue, setRevenue] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    if (!supplierId.trim()) { setError("Lieferanten-ID ist erforderlich"); return; }
    setSaving(true);
    setError("");
    try {
      await upsertProfile({
        supplier_id: supplierId.trim(),
        employee_count: employees ? Number(employees) : null,
        annual_revenue_eur: revenue ? Number(revenue) : null,
        notes: notes || null,
      });
      onCreated();
      onClose();
    } catch {
      setError("Fehler beim Speichern");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose}>
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold">KMU registrieren</h3>
          <button onClick={onClose}><X className="w-4 h-4 text-slate-400" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Lieferanten-ID *</label>
            <input className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="UUID des Lieferanten" value={supplierId} onChange={(e) => setSupplierId(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Mitarbeiterzahl</label>
              <input type="number" className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="z.B. 45" value={employees} onChange={(e) => setEmployees(e.target.value)} />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Jahresumsatz (€)</label>
              <input type="number" className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="z.B. 8000000" value={revenue} onChange={(e) => setRevenue(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Notizen</label>
            <textarea rows={2} className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </div>
        {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-3 py-1.5 text-sm border rounded-lg text-slate-600">Abbrechen</button>
          <button onClick={submit} disabled={saving}
            className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {saving ? "Speichern…" : "Registrieren"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Program panel ─────────────────────────────────────────────────────────────

function ProgramPanel({ program, onAction }: { program: SupportProgram; onAction: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [showAddMeasure, setShowAddMeasure] = useState(false);

  const { data: measures = [], refetch: refetchMeasures } = useQuery({
    queryKey: ["sme-measures", program.id],
    queryFn: () => listMeasures(program.id),
    enabled: expanded,
  });

  async function handleActivate() {
    setBusy(true);
    try { await activateProgram(program.id); onAction(); } finally { setBusy(false); }
  }

  async function handleComplete() {
    if (!confirm("Programm als abgeschlossen markieren?")) return;
    setBusy(true);
    try { await completeProgram(program.id); onAction(); } finally { setBusy(false); }
  }

  async function handleCompleteMeasure(id: string) {
    await completeMeasure(id, undefined);
    refetchMeasures();
    onAction();
  }

  async function handleMeasureStatus(id: string, status: string) {
    await updateMeasureStatus(id, status);
    refetchMeasures();
  }

  const completedMeasures = measures.filter((m) => m.status === "completed").length;
  const progressPct = measures.length > 0 ? Math.round((completedMeasures / measures.length) * 100) : 0;

  return (
    <div className="bg-white border rounded-xl overflow-hidden">
      <div className="p-4 flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <p className="text-sm font-semibold text-slate-800 truncate">{program.title}</p>
            <ProgramBadge status={program.status} />
          </div>
          <p className="text-xs text-slate-400 font-mono">{program.supplier_id.slice(0, 8)}…</p>
          {program.total_budget_eur && (
            <p className="text-xs text-slate-500 mt-1">
              Budget: <span className="font-medium">€{program.total_budget_eur.toLocaleString()}</span>
              {program.spent_budget_eur > 0 && (
                <span className="text-slate-400"> / verbraucht: €{program.spent_budget_eur.toLocaleString()}</span>
              )}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {program.status === "draft" && (
            <button onClick={handleActivate} disabled={busy}
              className="text-xs px-2.5 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
              Aktivieren
            </button>
          )}
          {program.status === "active" && (
            <button onClick={handleComplete} disabled={busy}
              className="text-xs px-2.5 py-1 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50">
              Abschließen
            </button>
          )}
          <button onClick={() => setExpanded(!expanded)}
            className="text-slate-400 hover:text-slate-600">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t px-4 py-3 space-y-3">
          {program.description && (
            <p className="text-xs text-slate-600 bg-slate-50 rounded p-2 border">{program.description}</p>
          )}

          {measures.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <p className="text-xs font-medium text-slate-600">Fortschritt</p>
                <p className="text-xs text-slate-400">{completedMeasures}/{measures.length} erledigt</p>
              </div>
              <div className="h-1.5 bg-slate-100 rounded-full">
                <div className="h-1.5 bg-blue-500 rounded-full transition-all"
                  style={{ width: `${progressPct}%` }} />
              </div>
            </div>
          )}

          <div className="space-y-2">
            {measures.map((m) => (
              <MeasureRow key={m.id} measure={m}
                onComplete={() => handleCompleteMeasure(m.id)}
                onStatusChange={(s) => handleMeasureStatus(m.id, s)} />
            ))}
          </div>

          <button onClick={() => setShowAddMeasure(true)}
            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700">
            <Plus className="w-3.5 h-3.5" /> Maßnahme hinzufügen
          </button>

          {showAddMeasure && (
            <AddMeasureForm programId={program.id} onCreated={() => { refetchMeasures(); setShowAddMeasure(false); }} onCancel={() => setShowAddMeasure(false)} />
          )}
        </div>
      )}
    </div>
  );
}

// ── Measure row ───────────────────────────────────────────────────────────────

function MeasureRow({
  measure,
  onComplete,
  onStatusChange,
}: {
  measure: SupportMeasure;
  onComplete: () => void;
  onStatusChange: (s: string) => void;
}) {
  const cfg = MEASURE_STATUS[measure.status] ?? MEASURE_STATUS.planned;
  return (
    <div className="flex items-center justify-between gap-3 text-xs border rounded-lg px-3 py-2">
      <div className="flex-1 min-w-0">
        <p className="font-medium text-slate-700 truncate">{measure.title}</p>
        <p className="text-slate-400">{SUPPORT_TYPES[measure.support_type] || measure.support_type}
          {measure.cost_eur ? ` · €${measure.cost_eur.toLocaleString()}` : ""}
        </p>
      </div>
      <span className={`font-medium ${cfg.color}`}>{cfg.label}</span>
      {measure.status !== "completed" && measure.status !== "cancelled" && (
        <div className="flex items-center gap-1">
          {measure.status === "planned" && (
            <button onClick={() => onStatusChange("in_progress")}
              className="px-2 py-0.5 bg-blue-50 text-blue-600 border border-blue-200 rounded hover:bg-blue-100">
              Starten
            </button>
          )}
          {measure.status === "in_progress" && (
            <button onClick={onComplete}
              className="px-2 py-0.5 bg-emerald-50 text-emerald-600 border border-emerald-200 rounded hover:bg-emerald-100">
              Erledigt
            </button>
          )}
        </div>
      )}
      {measure.status === "completed" && measure.impact_notes && (
        <span title={measure.impact_notes} className="text-emerald-500">✓</span>
      )}
    </div>
  );
}

// ── Add measure form ──────────────────────────────────────────────────────────

function AddMeasureForm({
  programId, onCreated, onCancel,
}: { programId: string; onCreated: () => void; onCancel: () => void }) {
  const [title, setTitle] = useState("");
  const [type, setType] = useState("training");
  const [cost, setCost] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (!title.trim()) return;
    setSaving(true);
    try {
      await addMeasure(programId, { title: title.trim(), support_type: type, cost_eur: cost ? Number(cost) : null });
      onCreated();
    } finally { setSaving(false); }
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 space-y-2">
      <div className="flex gap-2">
        <input value={title} onChange={(e) => setTitle(e.target.value)}
          className="flex-1 border rounded px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="Maßnahme Titel" />
        <select value={type} onChange={(e) => setType(e.target.value)}
          className="border rounded px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-blue-500">
          {Object.entries(SUPPORT_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input type="number" value={cost} onChange={(e) => setCost(e.target.value)}
          className="w-24 border rounded px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-blue-500"
          placeholder="Kosten €" />
      </div>
      <div className="flex justify-end gap-2">
        <button onClick={onCancel} className="text-xs px-2 py-1 border rounded text-slate-600">Abbrechen</button>
        <button onClick={submit} disabled={saving || !title.trim()}
          className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
          {saving ? "…" : "Hinzufügen"}
        </button>
      </div>
    </div>
  );
}

// ── Create program dialog ─────────────────────────────────────────────────────

function CreateProgramDialog({
  onClose, onCreated,
}: { onClose: () => void; onCreated: () => void }) {
  const [supplierId, setSupplierId] = useState("");
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [budget, setBudget] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    if (!supplierId.trim() || !title.trim()) { setError("Lieferanten-ID und Titel erforderlich"); return; }
    setSaving(true); setError("");
    try {
      await createProgram({
        supplier_id: supplierId.trim(),
        title: title.trim(),
        description: desc,
        total_budget_eur: budget ? Number(budget) : null,
      });
      onCreated(); onClose();
    } catch { setError("Fehler beim Erstellen"); } finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose}>
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold">Förderprogramm erstellen</h3>
          <button onClick={onClose}><X className="w-4 h-4 text-slate-400" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Lieferanten-ID *</label>
            <input className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
              value={supplierId} onChange={(e) => setSupplierId(e.target.value)} placeholder="UUID" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Titel *</label>
            <input className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
              value={title} onChange={(e) => setTitle(e.target.value)} placeholder="z.B. Schulungsprogramm 2026" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Beschreibung</label>
            <textarea rows={2} className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              value={desc} onChange={(e) => setDesc(e.target.value)} />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Gesamtbudget (€)</label>
            <input type="number" className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
              value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="z.B. 20000" />
          </div>
        </div>
        {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-3 py-1.5 text-sm border rounded-lg text-slate-600">Abbrechen</button>
          <button onClick={submit} disabled={saving}
            className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
            {saving ? "Erstellen…" : "Erstellen"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

type Tab = "overview" | "programs" | "report";

export default function SMESupportPage() {
  const [tab, setTab] = useState<Tab>("overview");
  const [showRegister, setShowRegister] = useState(false);
  const [showCreateProgram, setShowCreateProgram] = useState(false);
  const [reportYear, setReportYear] = useState(new Date().getFullYear());
  const [statusFilter, setStatusFilter] = useState("");
  const qc = useQueryClient();

  const { data: summary } = useQuery({
    queryKey: ["sme-summary"],
    queryFn: getProfileSummary,
  });

  const { data: profiles = [], isLoading: profilesLoading } = useQuery({
    queryKey: ["sme-profiles"],
    queryFn: () => listProfiles(false),
    enabled: tab === "overview",
  });

  const { data: programs = [], isLoading: programsLoading } = useQuery({
    queryKey: ["sme-programs", statusFilter],
    queryFn: () => listPrograms({ status: statusFilter || undefined }),
    enabled: tab === "programs",
  });

  const { data: report } = useQuery({
    queryKey: ["sme-annual-report", reportYear],
    queryFn: () => getAnnualReport(reportYear),
    enabled: tab === "report",
  });

  function refetchAll() {
    qc.invalidateQueries({ queryKey: ["sme-summary"] });
    qc.invalidateQueries({ queryKey: ["sme-profiles"] });
    qc.invalidateQueries({ queryKey: ["sme-programs"] });
  }

  const TABS: { id: Tab; label: string }[] = [
    { id: "overview", label: "KMU-Übersicht" },
    { id: "programs", label: "Förderprogramme" },
    { id: "report", label: "Jahresbericht" },
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Building2 className="w-7 h-7 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-slate-800">KMU-Unterstützung</h1>
            <p className="text-sm text-slate-500">CSDDD Art. 10 Abs. 2 lit. b — Gezielte Unterstützung für KMU-Lieferanten</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${tab === t.id ? "border-blue-600 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── KMU Overview ───────────────────────────────────────────────────── */}
      {tab === "overview" && (
        <div className="space-y-6">
          {summary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard label="Lieferanten gesamt" value={summary.total} />
              <KpiCard label="KMU-Lieferanten" value={summary.sme_count}
                color="text-blue-600" sub="Micro + Klein + Mittel" />
              <KpiCard label="Verifiziert" value={summary.confirmed}
                color={summary.confirmed === summary.sme_count ? "text-emerald-600" : "text-amber-600"} />
              <KpiCard label="Nicht verifiziert"
                value={summary.sme_count - summary.confirmed}
                color={summary.sme_count - summary.confirmed > 0 ? "text-amber-600" : "text-emerald-600"} />
            </div>
          )}

          {summary && Object.keys(summary.by_classification).length > 0 && (
            <div className="bg-white border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Klassifizierung nach EU-Definition</h3>
              <div className="flex flex-wrap gap-3">
                {Object.entries(CLASSIFICATION_CONFIG).map(([key, cfg]) => {
                  const count = summary.by_classification[key] ?? 0;
                  return (
                    <div key={key} className={`border rounded-xl px-4 py-3 ${cfg.color}`}>
                      <p className="text-xl font-bold">{count}</p>
                      <p className="text-xs font-medium">{cfg.label}</p>
                      <p className="text-xs opacity-70">{cfg.desc}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="flex justify-between items-center">
            <h3 className="text-sm font-semibold text-slate-700">Registrierte KMU ({profiles.length})</h3>
            <button onClick={() => setShowRegister(true)}
              className="flex items-center gap-2 text-sm px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              <Plus className="w-4 h-4" /> KMU registrieren
            </button>
          </div>

          {profilesLoading ? (
            <p className="text-sm text-slate-500">Wird geladen…</p>
          ) : profiles.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Keine KMU-Lieferanten erfasst</p>
            </div>
          ) : (
            <div className="bg-white border rounded-xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-3 text-left">Lieferant</th>
                    <th className="px-4 py-3 text-left">Klassifizierung</th>
                    <th className="px-4 py-3 text-left">MA</th>
                    <th className="px-4 py-3 text-left">Umsatz</th>
                    <th className="px-4 py-3 text-left">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm">
                  {profiles.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">{p.supplier_id.slice(0, 8)}…</td>
                      <td className="px-4 py-3"><ClassificationBadge cls={p.classification} /></td>
                      <td className="px-4 py-3 text-slate-700">{p.employee_count ?? "—"}</td>
                      <td className="px-4 py-3 text-slate-700">
                        {p.annual_revenue_eur ? `€${(p.annual_revenue_eur / 1_000_000).toFixed(1)}M` : "—"}
                      </td>
                      <td className="px-4 py-3">
                        {p.is_confirmed ? (
                          <span className="text-xs text-emerald-600 font-medium">✓ Verifiziert</span>
                        ) : (
                          <span className="text-xs text-amber-600">Ausstehend</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Programs ────────────────────────────────────────────────────────── */}
      {tab === "programs" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <label className="text-sm text-slate-600">Status:</label>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
                className="border rounded-lg px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">Alle</option>
                {Object.entries(PROGRAM_STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
              </select>
            </div>
            <button onClick={() => setShowCreateProgram(true)}
              className="flex items-center gap-2 text-sm px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              <Plus className="w-4 h-4" /> Programm erstellen
            </button>
          </div>

          {programsLoading ? (
            <p className="text-sm text-slate-500">Wird geladen…</p>
          ) : programs.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <Building2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Keine Förderprogramme vorhanden</p>
            </div>
          ) : (
            <div className="space-y-3">
              {programs.map((p) => (
                <ProgramPanel key={p.id} program={p} onAction={refetchAll} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Annual report ───────────────────────────────────────────────────── */}
      {tab === "report" && (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-600">Berichtsjahr:</label>
            <input type="number" value={reportYear}
              onChange={(e) => setReportYear(Number(e.target.value))}
              className="w-24 border rounded-lg px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
              min={2020} max={2100} />
          </div>

          {report ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <KpiCard label="Förderprogramme" value={report.programs_total} />
                <KpiCard label="Abgeschlossen" value={report.programs_completed} color="text-emerald-600" />
                <KpiCard label="KMU-Lieferanten unterstützt" value={report.sme_suppliers_supported} color="text-blue-600" />
              </div>
              <div className="bg-white border rounded-xl p-5">
                <div className="flex items-center gap-3">
                  <Euro className="w-8 h-8 text-emerald-600" />
                  <div>
                    <p className="text-3xl font-bold text-slate-800">
                      €{report.total_invested_eur.toLocaleString("de-DE")}
                    </p>
                    <p className="text-sm text-slate-500">Gesamtinvestition in KMU-Unterstützung {report.year}</p>
                  </div>
                </div>
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                <p className="text-sm text-blue-800">
                  <strong>CSDDD Art. 16 Berichtspflicht:</strong> Diese Daten sind Bestandteil des jährlichen Nachhaltigkeitsberichts.
                  Das Unternehmen hat {report.year} insgesamt {report.sme_suppliers_supported} KMU-Lieferanten mit
                  €{report.total_invested_eur.toLocaleString("de-DE")} unterstützt (Art. 10 Abs. 2 lit. b).
                </p>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-500">Wird geladen…</p>
          )}
        </div>
      )}

      {showRegister && (
        <RegisterDialog onClose={() => setShowRegister(false)} onCreated={refetchAll} />
      )}
      {showCreateProgram && (
        <CreateProgramDialog onClose={() => setShowCreateProgram(false)} onCreated={refetchAll} />
      )}
    </div>
  );
}
