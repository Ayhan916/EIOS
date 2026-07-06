"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FileText, CheckCircle, Clock, XCircle, AlertTriangle,
  Plus, ChevronDown, ChevronUp, X, BookOpen, BarChart2, ArrowRight,
} from "lucide-react";
import {
  listClauses, getClauseSummary, seedClauses, createClause,
  listAssurances, createAssurance, acceptAssurance, updateAssuranceStatus,
  confirmCascade, getAssuranceDashboard, getSupplierCoverage,
  type ContractClause, type ContractAssurance,
} from "@/lib/api/contractual-assurance";

const CATEGORY_LABELS: Record<string, string> = {
  labor_rights: "Arbeitsrechte",
  human_rights: "Menschenrechte",
  environment: "Umwelt",
  anti_corruption: "Antikorruption",
  health_safety: "Arbeitssicherheit",
  data_protection: "Datenschutz",
  other: "Sonstige",
};

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  pending: { label: "Ausstehend", color: "text-amber-600 bg-amber-50 border-amber-200", icon: <Clock className="w-3.5 h-3.5" /> },
  accepted: { label: "Akzeptiert", color: "text-emerald-600 bg-emerald-50 border-emerald-200", icon: <CheckCircle className="w-3.5 h-3.5" /> },
  rejected: { label: "Abgelehnt", color: "text-red-600 bg-red-50 border-red-200", icon: <XCircle className="w-3.5 h-3.5" /> },
  expired: { label: "Abgelaufen", color: "text-slate-500 bg-slate-50 border-slate-200", icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  waived: { label: "Ausgenommen", color: "text-purple-600 bg-purple-50 border-purple-200", icon: <ArrowRight className="w-3.5 h-3.5" /> },
};

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium ${cfg.color}`}>
      {cfg.icon}
      {cfg.label}
    </span>
  );
}

// ── KPI card ──────────────────────────────────────────────────────────────────

function KpiCard({
  label, value, sub, color = "text-slate-800",
}: { label: string; value: number | string; sub?: string; color?: string }) {
  return (
    <div className="bg-white border rounded-xl p-4">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-xs text-slate-500 mt-0.5">{label}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

// ── Clause card ───────────────────────────────────────────────────────────────

function ClauseCard({
  clause,
  onAssign,
}: {
  clause: ContractClause;
  onAssign: (c: ContractClause) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="bg-white border rounded-xl p-4 space-y-2">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-slate-800 truncate">{clause.title}</p>
          <div className="flex flex-wrap items-center gap-2 mt-1">
            <span className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded border border-blue-200">
              {CATEGORY_LABELS[clause.category] || clause.category}
            </span>
            {clause.cascade_required && (
              <span className="text-xs px-1.5 py-0.5 bg-purple-50 text-purple-700 rounded border border-purple-200">
                Cascade
              </span>
            )}
            {clause.is_mandatory && (
              <span className="text-xs px-1.5 py-0.5 bg-red-50 text-red-700 rounded border border-red-200">
                Pflicht
              </span>
            )}
            {!clause.is_active && (
              <span className="text-xs px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded">
                Inaktiv
              </span>
            )}
          </div>
        </div>
        <button
          onClick={() => onAssign(clause)}
          className="shrink-0 text-xs px-2.5 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Zuweisen
        </button>
      </div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600"
      >
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        Klauseltext
      </button>
      {expanded && (
        <p className="text-xs text-slate-600 bg-slate-50 rounded p-3 border leading-relaxed">
          {clause.clause_text}
        </p>
      )}
    </div>
  );
}

// ── Assign dialog ─────────────────────────────────────────────────────────────

function AssignDialog({
  clause,
  onClose,
  onCreated,
}: {
  clause: ContractClause;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [supplierId, setSupplierId] = useState("");
  const [docRef, setDocRef] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    if (!supplierId.trim()) { setError("Lieferanten-ID ist erforderlich"); return; }
    setSaving(true);
    setError("");
    try {
      await createAssurance({
        supplier_id: supplierId.trim(),
        clause_id: clause.id,
        document_ref: docRef || null,
        notes: notes || null,
      });
      onCreated();
      onClose();
    } catch {
      setError("Fehler beim Erstellen");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose}>
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-slate-800">Klausel zuweisen</h3>
          <button onClick={onClose}><X className="w-4 h-4 text-slate-400" /></button>
        </div>
        <p className="text-sm text-slate-600 mb-4 bg-slate-50 rounded p-3 border">{clause.title}</p>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Lieferanten-ID *</label>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="UUID des Lieferanten"
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Vertragsdokument (Referenz)</label>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="z.B. Vertrag-2026-Lieferant-XY.pdf"
              value={docRef}
              onChange={(e) => setDocRef(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Notizen</label>
            <textarea
              rows={2}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none resize-none"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
        </div>
        {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="px-3 py-1.5 text-sm border rounded-lg text-slate-600">Abbrechen</button>
          <button
            onClick={submit}
            disabled={saving}
            className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "Speichern…" : "Zuweisen"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Assurance row ─────────────────────────────────────────────────────────────

function AssuranceRow({
  assurance,
  clauses,
  onAction,
}: {
  assurance: ContractAssurance;
  clauses: ContractClause[];
  onAction: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const clause = clauses.find((c) => c.id === assurance.clause_id);

  async function handleAccept() {
    if (!confirm("Akzeptanz dieser Klausel durch den Lieferanten bestätigen?")) return;
    setBusy(true);
    try { await acceptAssurance(assurance.id); onAction(); } finally { setBusy(false); }
  }

  async function handleReject() {
    if (!confirm("Klausel als abgelehnt markieren?")) return;
    setBusy(true);
    try { await updateAssuranceStatus(assurance.id, "rejected", "Manually rejected"); onAction(); } finally { setBusy(false); }
  }

  async function handleCascade() {
    if (!confirm("Cascade-Weitergabe als bestätigt markieren?")) return;
    setBusy(true);
    try { await confirmCascade(assurance.id); onAction(); } finally { setBusy(false); }
  }

  return (
    <tr className="hover:bg-slate-50 text-sm">
      <td className="px-4 py-3 max-w-xs">
        <p className="font-medium text-slate-800 truncate">{clause?.title ?? assurance.clause_id}</p>
        <p className="text-xs text-slate-400">{clause ? CATEGORY_LABELS[clause.category] : ""}</p>
      </td>
      <td className="px-4 py-3 font-mono text-xs text-slate-500">{assurance.supplier_id.slice(0, 8)}…</td>
      <td className="px-4 py-3"><StatusBadge status={assurance.status} /></td>
      <td className="px-4 py-3">
        {clause?.cascade_required ? (
          assurance.cascade_confirmed ? (
            <span className="text-xs text-emerald-600 font-medium">✓ Bestätigt</span>
          ) : (
            <span className="text-xs text-amber-600">Ausstehend</span>
          )
        ) : (
          <span className="text-xs text-slate-300">—</span>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1">
          {assurance.status === "pending" && (
            <>
              <button
                onClick={handleAccept}
                disabled={busy}
                className="text-xs px-2 py-1 bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50"
              >
                Akzeptieren
              </button>
              <button
                onClick={handleReject}
                disabled={busy}
                className="text-xs px-2 py-1 border border-red-300 text-red-600 rounded hover:bg-red-50 disabled:opacity-50"
              >
                Ablehnen
              </button>
            </>
          )}
          {assurance.status === "accepted" && clause?.cascade_required && !assurance.cascade_confirmed && (
            <button
              onClick={handleCascade}
              disabled={busy}
              className="text-xs px-2 py-1 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
            >
              Cascade ✓
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

type Tab = "dashboard" | "assurances" | "clauses";

export default function ContractualAssurancePage() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [assignClause, setAssignClause] = useState<ContractClause | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const qc = useQueryClient();

  const { data: dashboard } = useQuery({
    queryKey: ["ca-dashboard"],
    queryFn: getAssuranceDashboard,
  });

  const { data: clauses = [], isLoading: clausesLoading } = useQuery({
    queryKey: ["ca-clauses"],
    queryFn: () => listClauses(false),
    enabled: tab === "clauses" || tab === "assurances",
  });

  const { data: assurances = [], isLoading: assurancesLoading } = useQuery({
    queryKey: ["ca-assurances", statusFilter],
    queryFn: () => listAssurances({ status: statusFilter || undefined }),
    enabled: tab === "assurances",
  });

  const seedMutation = useMutation({
    mutationFn: seedClauses,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ca-clauses"] }),
  });

  function refetchAll() {
    qc.invalidateQueries({ queryKey: ["ca-dashboard"] });
    qc.invalidateQueries({ queryKey: ["ca-assurances"] });
  }

  const TABS: { id: Tab; label: string }[] = [
    { id: "dashboard", label: "Dashboard" },
    { id: "assurances", label: "Zusicherungen" },
    { id: "clauses", label: "Klauselbibliothek" },
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="w-7 h-7 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Contractual Assurance</h1>
            <p className="text-sm text-slate-500">CSDDD Art. 10 — Vertragliche Sorgfaltspflichten</p>
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

      {/* ── Dashboard ──────────────────────────────────────────────────────── */}
      {tab === "dashboard" && (
        <div className="space-y-6">
          {dashboard ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard label="Zusicherungen gesamt" value={dashboard.total} />
                <KpiCard label="Akzeptanzrate" value={`${dashboard.acceptance_rate_pct}%`}
                  color={dashboard.acceptance_rate_pct >= 80 ? "text-emerald-600" : "text-amber-600"} />
                <KpiCard label="Ausstehend" value={dashboard.pending} color="text-amber-600" />
                <KpiCard label="Abgelehnt" value={dashboard.rejected} color="text-red-600" />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <KpiCard label="Akzeptiert" value={dashboard.accepted} color="text-emerald-600" />
                <KpiCard label="Abgelaufen" value={dashboard.expired} color="text-slate-500" />
                <KpiCard
                  label="Cascade ausstehend"
                  value={dashboard.cascade_unconfirmed}
                  color={dashboard.cascade_unconfirmed > 0 ? "text-purple-600" : "text-emerald-600"}
                  sub="Klauseln mit Cascade-Pflicht ohne Bestätigung"
                />
              </div>

              {dashboard.pending > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
                  <p className="text-sm text-amber-800">
                    <strong>{dashboard.pending} Zusicherungen</strong> warten auf Lieferantenbestätigung.
                    CSDDD Art. 10 Abs. 4 verlangt angemessene Maßnahmen bei Nichterfüllung.
                  </p>
                </div>
              )}

              {dashboard.cascade_unconfirmed > 0 && (
                <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 flex items-start gap-3">
                  <ArrowRight className="w-5 h-5 text-purple-600 mt-0.5 shrink-0" />
                  <p className="text-sm text-purple-800">
                    <strong>{dashboard.cascade_unconfirmed} Klauseln</strong> mit Cascade-Pflicht wurden noch nicht von Lieferanten an ihre eigenen Lieferanten weitergegeben (Art. 10 Abs. 3).
                  </p>
                </div>
              )}
            </>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-20 bg-slate-100 rounded-xl animate-pulse" />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Assurances ─────────────────────────────────────────────────────── */}
      {tab === "assurances" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <label className="text-sm text-slate-600">Status:</label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="border rounded-lg px-2 py-1 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="">Alle</option>
                {Object.entries(STATUS_CONFIG).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
            </div>
          </div>

          {assurancesLoading ? (
            <p className="text-sm text-slate-500">Wird geladen…</p>
          ) : assurances.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <BarChart2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Keine Zusicherungen vorhanden</p>
              <p className="text-xs mt-1">Klauseln aus der Bibliothek Lieferanten zuweisen</p>
            </div>
          ) : (
            <div className="bg-white border rounded-xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-3 text-left">Klausel</th>
                    <th className="px-4 py-3 text-left">Lieferant</th>
                    <th className="px-4 py-3 text-left">Status</th>
                    <th className="px-4 py-3 text-left">Cascade</th>
                    <th className="px-4 py-3 text-left">Aktionen</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {assurances.map((a) => (
                    <AssuranceRow
                      key={a.id}
                      assurance={a}
                      clauses={clauses}
                      onAction={refetchAll}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Clause Library ─────────────────────────────────────────────────── */}
      {tab === "clauses" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">{clauses.length} Klauseln</p>
            <button
              onClick={() => seedMutation.mutate()}
              disabled={seedMutation.isPending}
              className="flex items-center gap-2 text-sm px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              <BookOpen className="w-4 h-4" />
              {seedMutation.isPending ? "Lade…" : "Best-Practice Klauseln laden"}
            </button>
          </div>

          {seedMutation.isSuccess && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
              <p className="text-sm text-emerald-700">
                {seedMutation.data?.seeded} Klauseln erfolgreich geladen.
              </p>
            </div>
          )}

          {clausesLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-24 bg-slate-100 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : clauses.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Keine Klauseln vorhanden</p>
              <p className="text-xs mt-1">Best-Practice Klauseln laden oder neue erstellen</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {clauses.map((c) => (
                <ClauseCard key={c.id} clause={c} onAssign={setAssignClause} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Assign dialog */}
      {assignClause && (
        <AssignDialog
          clause={assignClause}
          onClose={() => setAssignClause(null)}
          onCreated={() => {
            qc.invalidateQueries({ queryKey: ["ca-assurances"] });
            qc.invalidateQueries({ queryKey: ["ca-dashboard"] });
            setTab("assurances");
          }}
        />
      )}
    </div>
  );
}
