"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Users, Plus, Calendar, AlertTriangle, CheckCircle2, Clock,
  ChevronRight, X, Building2, Globe, Tag, MessageSquare,
} from "lucide-react";
import { useLanguage } from "@/lib/i18n/context";
import {
  listStakeholders, createStakeholder, deleteStakeholder,
  listConsultations, createConsultation,
  type Stakeholder, type Consultation, type StakeholderCreate, type ConsultationCreate,
} from "@/lib/api/stakeholders";
import { extractErrorMessage } from "@/lib/utils";

const STAKEHOLDER_TYPES = [
  { value: "worker", label: "Arbeitnehmer" },
  { value: "trade_union", label: "Gewerkschaft" },
  { value: "ngo", label: "NGO / Zivilgesellschaft" },
  { value: "supplier_community", label: "Lieferantengemeinschaft" },
  { value: "authority", label: "Behörde" },
  { value: "other", label: "Sonstige" },
];

const CONSULTATION_FORMATS = [
  { value: "meeting", label: "Meeting" },
  { value: "workshop", label: "Workshop" },
  { value: "questionnaire", label: "Fragebogen" },
  { value: "audit", label: "Audit / Vor-Ort-Prüfung" },
  { value: "other", label: "Sonstiges" },
];

const BARRIERS = [
  { value: "none", label: "Keine Barrieren" },
  { value: "language", label: "Sprachbarriere" },
  { value: "access", label: "Zugangsbarriere" },
  { value: "resources", label: "Ressourcenmangel" },
  { value: "fear_of_reprisals", label: "Angst vor Repressalien" },
  { value: "other", label: "Sonstige" },
];

const TYPE_COLORS: Record<string, string> = {
  worker: "bg-blue-100 text-blue-800",
  trade_union: "bg-purple-100 text-purple-800",
  ngo: "bg-emerald-100 text-emerald-800",
  supplier_community: "bg-amber-100 text-amber-800",
  authority: "bg-slate-100 text-slate-800",
  other: "bg-gray-100 text-gray-800",
};

const typeLabel = (v: string) => STAKEHOLDER_TYPES.find((t) => t.value === v)?.label ?? v;
const formatLabel = (v: string) => CONSULTATION_FORMATS.find((f) => f.value === v)?.label ?? v;
const barrierLabel = (v: string) => BARRIERS.find((b) => b.value === v)?.label ?? v;

function daysSince(iso: string | null): number | null {
  if (!iso) return null;
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
}

// ── Stakeholder Modal ─────────────────────────────────────────────────────────

function StakeholderModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState<StakeholderCreate>({
    name: "",
    stakeholder_type: "other",
    contact_email: "",
    language: "de",
    activity_chain_ids: [],
    regions: [],
    risk_topics: [],
    justification: "",
  });
  const [error, setError] = useState("");
  const mutation = useMutation({
    mutationFn: createStakeholder,
    onSuccess: () => { onSaved(); onClose(); },
    onError: (err) => setError(extractErrorMessage(err)),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-lg rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-base font-semibold">Stakeholder erfassen</h2>
          <button onClick={onClose}><X className="h-4 w-4 text-muted-foreground" /></button>
        </div>
        <div className="space-y-4 p-6">
          {error && (
            <div className="rounded-md bg-red-50 px-4 py-2 text-sm text-red-700 border border-red-200">{error}</div>
          )}
          <div className="space-y-1">
            <label className="block text-sm font-medium">Name *</label>
            <input className="w-full rounded-md border border-input px-3 py-2 text-sm" value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="Organisation oder Person" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="block text-sm font-medium">Typ *</label>
              <select className="w-full rounded-md border border-input px-3 py-2 text-sm bg-background"
                value={form.stakeholder_type}
                onChange={(e) => setForm((f) => ({ ...f, stakeholder_type: e.target.value }))}>
                {STAKEHOLDER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium">Sprache</label>
              <select className="w-full rounded-md border border-input px-3 py-2 text-sm bg-background"
                value={form.language}
                onChange={(e) => setForm((f) => ({ ...f, language: e.target.value }))}>
                <option value="de">Deutsch</option>
                <option value="en">English</option>
                <option value="fr">Français</option>
                <option value="es">Español</option>
                <option value="other">Andere</option>
              </select>
            </div>
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium">E-Mail (optional)</label>
            <input type="email" className="w-full rounded-md border border-input px-3 py-2 text-sm"
              value={form.contact_email ?? ""} onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))}
              placeholder="kontakt@organisation.de" />
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium">
              Begründung der Betroffenheit *
              <span className="ml-1 text-xs font-normal text-muted-foreground">(Art. 13 Abs. 1 CSDDD)</span>
            </label>
            <textarea rows={3} className="w-full rounded-md border border-input px-3 py-2 text-sm"
              value={form.justification}
              onChange={(e) => setForm((f) => ({ ...f, justification: e.target.value }))}
              placeholder="Warum ist diese Partei als 'betroffen' einzustufen?" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="rounded-md border border-border px-4 py-2 text-sm">Abbrechen</button>
            <button
              disabled={!form.name || !form.justification || mutation.isPending}
              onClick={() => mutation.mutate(form)}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50">
              {mutation.isPending ? "Speichern…" : "Speichern"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Consultation Modal ────────────────────────────────────────────────────────

function ConsultationModal({
  stakeholders, onClose, onSaved,
}: { stakeholders: Stakeholder[]; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState<ConsultationCreate>({
    stakeholder_ids: [],
    consultation_date: new Date().toISOString().split("T")[0],
    format: "meeting",
    topics: [],
    description: "",
    outcomes: "",
    barrier: "none",
    barrier_notes: "",
  });
  const [error, setError] = useState("");
  const mutation = useMutation({
    mutationFn: createConsultation,
    onSuccess: () => { onSaved(); onClose(); },
    onError: (err) => setError(extractErrorMessage(err)),
  });

  const toggleStakeholder = (id: string) =>
    setForm((f) => ({
      ...f,
      stakeholder_ids: f.stakeholder_ids.includes(id)
        ? f.stakeholder_ids.filter((x) => x !== id)
        : [...f.stakeholder_ids, id],
    }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-2xl rounded-xl bg-white shadow-xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-base font-semibold">Konsultation dokumentieren</h2>
          <button onClick={onClose}><X className="h-4 w-4 text-muted-foreground" /></button>
        </div>
        <div className="overflow-y-auto space-y-4 p-6">
          {error && (
            <div className="rounded-md bg-red-50 px-4 py-2 text-sm text-red-700 border border-red-200">{error}</div>
          )}
          <div className="space-y-1">
            <label className="block text-sm font-medium">Beteiligte Stakeholder *</label>
            <div className="max-h-36 overflow-y-auto rounded-md border border-input p-2 space-y-1">
              {stakeholders.map((s) => (
                <label key={s.id} className="flex items-center gap-2 cursor-pointer rounded px-2 py-1 hover:bg-muted/50">
                  <input type="checkbox" checked={form.stakeholder_ids.includes(s.id)}
                    onChange={() => toggleStakeholder(s.id)} className="h-3.5 w-3.5" />
                  <span className="text-sm">{s.name}</span>
                  <span className={`ml-auto rounded-full px-2 py-0.5 text-xs ${TYPE_COLORS[s.stakeholder_type] ?? "bg-gray-100"}`}>
                    {typeLabel(s.stakeholder_type)}
                  </span>
                </label>
              ))}
              {stakeholders.length === 0 && (
                <p className="text-xs text-muted-foreground p-2">Noch keine Stakeholder angelegt.</p>
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="block text-sm font-medium">Datum</label>
              <input type="date" className="w-full rounded-md border border-input px-3 py-2 text-sm"
                value={form.consultation_date ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, consultation_date: e.target.value }))} />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium">Format</label>
              <select className="w-full rounded-md border border-input px-3 py-2 text-sm bg-background"
                value={form.format}
                onChange={(e) => setForm((f) => ({ ...f, format: e.target.value }))}>
                {CONSULTATION_FORMATS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
              </select>
            </div>
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium">Beschreibung *</label>
            <textarea rows={3} className="w-full rounded-md border border-input px-3 py-2 text-sm"
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="Was wurde besprochen? Welche Themen?" />
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium">Ergebnis / Erkenntnisse</label>
            <textarea rows={2} className="w-full rounded-md border border-input px-3 py-2 text-sm"
              value={form.outcomes}
              onChange={(e) => setForm((f) => ({ ...f, outcomes: e.target.value }))}
              placeholder="Was wurde als Ergebnis festgehalten?" />
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 space-y-2">
            <label className="block text-sm font-medium text-amber-900">
              Barrieren zur Teilnahme *
              <span className="ml-1 text-xs font-normal">(Art. 13 Abs. 1 CSDDD — Pflichtfeld)</span>
            </label>
            <select className="w-full rounded-md border border-border px-3 py-2 text-sm bg-white"
              value={form.barrier}
              onChange={(e) => setForm((f) => ({ ...f, barrier: e.target.value }))}>
              {BARRIERS.map((b) => <option key={b.value} value={b.value}>{b.label}</option>)}
            </select>
            {form.barrier !== "none" && (
              <textarea rows={2} className="w-full rounded-md border border-border px-3 py-2 text-sm bg-white"
                value={form.barrier_notes}
                onChange={(e) => setForm((f) => ({ ...f, barrier_notes: e.target.value }))}
                placeholder="Wie wurde die Barriere adressiert?" />
            )}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="rounded-md border border-border px-4 py-2 text-sm">Abbrechen</button>
            <button
              disabled={form.stakeholder_ids.length === 0 || !form.description || mutation.isPending}
              onClick={() => mutation.mutate(form)}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50">
              {mutation.isPending ? "Speichern…" : "Konsultation speichern"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function StakeholdersPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"stakeholders" | "consultations">("stakeholders");
  const [showStakeholderModal, setShowStakeholderModal] = useState(false);
  const [showConsultationModal, setShowConsultationModal] = useState(false);

  const { data: stakeholders = [], isLoading: loadingS } = useQuery({
    queryKey: ["stakeholders"],
    queryFn: () => listStakeholders({ limit: 200 }),
  });

  const { data: consultations = [], isLoading: loadingC } = useQuery({
    queryKey: ["stakeholder-consultations"],
    queryFn: () => listConsultations({ limit: 200 }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteStakeholder,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["stakeholders"] }),
  });

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["stakeholders"] });
    qc.invalidateQueries({ queryKey: ["stakeholder-consultations"] });
  };

  // Stats
  const overdue = stakeholders.filter((s) => {
    const consults = consultations.filter((c) => c.stakeholder_ids.includes(s.id));
    if (consults.length === 0) return true;
    const last = consults.reduce((best, c) =>
      c.consultation_date && (!best.consultation_date || c.consultation_date > best.consultation_date) ? c : best
    );
    const days = daysSince(last.consultation_date);
    return days === null || days > 365;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t("stakeholders.title")}</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {t("stakeholders.subtitle")}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowConsultationModal(true)}
            className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:bg-muted">
            <Calendar className="h-4 w-4" />
            Konsultation
          </button>
          <button
            onClick={() => setShowStakeholderModal(true)}
            className="flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground">
            <Plus className="h-4 w-4" />
            Stakeholder
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-blue-100 p-2"><Users className="h-5 w-5 text-blue-600" /></div>
            <div>
              <p className="text-2xl font-bold">{stakeholders.length}</p>
              <p className="text-xs text-muted-foreground">{t("stakeholders.kpiTotal")}</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-emerald-100 p-2"><MessageSquare className="h-5 w-5 text-emerald-600" /></div>
            <div>
              <p className="text-2xl font-bold">{consultations.length}</p>
              <p className="text-xs text-muted-foreground">{t("stakeholders.kpiConsultations")}</p>
            </div>
          </div>
        </div>
        <div className={`rounded-xl border p-4 ${overdue.length > 0 ? "border-amber-200 bg-amber-50" : "border-border bg-card"}`}>
          <div className="flex items-center gap-3">
            <div className={`rounded-lg p-2 ${overdue.length > 0 ? "bg-amber-100" : "bg-slate-100"}`}>
              <Clock className={`h-5 w-5 ${overdue.length > 0 ? "text-amber-600" : "text-slate-500"}`} />
            </div>
            <div>
              <p className="text-2xl font-bold">{overdue.length}</p>
              <p className="text-xs text-muted-foreground">{t("stakeholders.kpiOverdue")}</p>
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-violet-100 p-2"><CheckCircle2 className="h-5 w-5 text-violet-600" /></div>
            <div>
              <p className="text-2xl font-bold">
                {stakeholders.length > 0
                  ? Math.round(((stakeholders.length - overdue.length) / stakeholders.length) * 100)
                  : 0}%
              </p>
              <p className="text-xs text-muted-foreground">{t("stakeholders.coverage")}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {(["stakeholders", "consultations"] as const).map((tabId) => (
          <button
            key={tabId}
            onClick={() => setTab(tabId)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === tabId
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}>
            {tabId === "stakeholders" ? `${t("stakeholders.tabStakeholders")} (${stakeholders.length})` : `${t("stakeholders.tabConsultations")} (${consultations.length})`}
          </button>
        ))}
      </div>

      {/* Stakeholders Tab */}
      {tab === "stakeholders" && (
        <div>
          {loadingS ? (
            <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">Laden…</div>
          ) : stakeholders.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border">
              <Users className="h-10 w-10 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">Noch keine Stakeholder erfasst.</p>
              <button onClick={() => setShowStakeholderModal(true)}
                className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground">
                <Plus className="h-3.5 w-3.5" /> Stakeholder hinzufügen
              </button>
            </div>
          ) : (
            <div className="divide-y divide-border rounded-xl border border-border bg-card">
              {stakeholders.map((s) => {
                const myConsults = consultations.filter((c) => c.stakeholder_ids.includes(s.id));
                const lastConsult = myConsults.reduce<Consultation | null>((best, c) =>
                  !best || (c.consultation_date && (!best.consultation_date || c.consultation_date > best.consultation_date)) ? c : best
                , null);
                const days = daysSince(lastConsult?.consultation_date ?? null);
                const isOverdue = days === null || days > 365;
                return (
                  <div key={s.id} className="flex items-center gap-4 px-4 py-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-semibold text-muted-foreground">
                      {s.name[0]?.toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{s.name}</span>
                        <span className={`rounded-full px-2 py-0.5 text-xs ${TYPE_COLORS[s.stakeholder_type] ?? "bg-gray-100"}`}>
                          {typeLabel(s.stakeholder_type)}
                        </span>
                        {isOverdue && (
                          <span className="flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">
                            <Clock className="h-3 w-3" /> Konsultation überfällig
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">{s.justification}</p>
                    </div>
                    <div className="text-right text-xs text-muted-foreground shrink-0">
                      {myConsults.length > 0 ? (
                        <>
                          <p className="font-medium">{myConsults.length} Konsultation{myConsults.length !== 1 ? "en" : ""}</p>
                          <p>{days !== null ? `vor ${days} Tagen` : "—"}</p>
                        </>
                      ) : (
                        <span className="text-muted-foreground/60">Keine Konsultation</span>
                      )}
                    </div>
                    <button
                      onClick={() => deleteMutation.mutate(s.id)}
                      className="ml-2 rounded p-1 hover:bg-red-50 text-muted-foreground hover:text-red-600">
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Consultations Tab */}
      {tab === "consultations" && (
        <div>
          {loadingC ? (
            <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">Laden…</div>
          ) : consultations.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border">
              <Calendar className="h-10 w-10 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">Noch keine Konsultation dokumentiert.</p>
              <button onClick={() => setShowConsultationModal(true)}
                className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground">
                <Plus className="h-3.5 w-3.5" /> Konsultation erfassen
              </button>
            </div>
          ) : (
            <div className="divide-y divide-border rounded-xl border border-border bg-card">
              {consultations.map((c) => {
                const names = c.stakeholder_ids
                  .map((id) => stakeholders.find((s) => s.id === id)?.name ?? id)
                  .join(", ");
                return (
                  <div key={c.id} className="flex items-start gap-4 px-4 py-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-100">
                      <Calendar className="h-4 w-4 text-blue-600" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-sm">{formatLabel(c.format)}</span>
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                          {c.consultation_date ?? "Datum ausstehend"}
                        </span>
                        {c.barrier !== "none" && (
                          <span className="flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">
                            <AlertTriangle className="h-3 w-3" /> {barrierLabel(c.barrier)}
                          </span>
                        )}
                        {c.feedback_count > 0 && (
                          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">
                            {c.feedback_count} Feedback
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">{names || "Keine Stakeholder"}</p>
                      <p className="text-xs text-foreground/80 mt-1 line-clamp-2">{c.description}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      {showStakeholderModal && (
        <StakeholderModal onClose={() => setShowStakeholderModal(false)} onSaved={invalidateAll} />
      )}
      {showConsultationModal && (
        <ConsultationModal
          stakeholders={stakeholders}
          onClose={() => setShowConsultationModal(false)}
          onSaved={invalidateAll}
        />
      )}
    </div>
  );
}
