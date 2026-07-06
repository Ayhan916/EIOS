"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ScrollText, Plus, CheckCircle2, Clock, AlertTriangle,
  X, ChevronRight, FileText, Shield, Calendar, RotateCcw,
} from "lucide-react";
import {
  listPolicies, createPolicy, activatePolicy, clonePolicy, archivePolicy,
  listCoCs, createCoC, getReviewStatus, getCalendar,
  type DDPolicy, type CodeOfConduct, type DDPolicyCreate,
} from "@/lib/api/dd-governance";
import { extractErrorMessage } from "@/lib/utils";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600",
  active: "bg-emerald-100 text-emerald-700",
  archived: "bg-gray-100 text-gray-500",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Entwurf",
  active: "Aktiv",
  archived: "Archiviert",
};

const REVIEW_COLORS: Record<string, string> = {
  current: "text-emerald-600",
  due_soon_60: "text-amber-500",
  due_soon_30: "text-orange-600",
  overdue: "text-red-600",
  no_policy: "text-slate-400",
  inactive: "text-slate-400",
  unknown: "text-slate-400",
};

const REVIEW_LABELS: Record<string, string> = {
  current: "Aktuell",
  due_soon_60: "Review fällig in < 60 Tagen",
  due_soon_30: "Review fällig in < 30 Tagen",
  overdue: "Überfällig",
  no_policy: "Keine aktive Politik",
  inactive: "Inaktiv",
  unknown: "Unbekannt",
};

// ── Policy Modal ──────────────────────────────────────────────────────────────

function PolicyModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState<DDPolicyCreate>({
    title: "",
    content_text: "",
    approved_by: "",
    approved_role: "",
    is_public: false,
  });
  const [error, setError] = useState("");
  const mutation = useMutation({
    mutationFn: createPolicy,
    onSuccess: () => { onSaved(); onClose(); },
    onError: (err) => setError(extractErrorMessage(err)),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-2xl rounded-xl bg-white shadow-xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-base font-semibold">DD-Politik erstellen</h2>
          <button onClick={onClose}><X className="h-4 w-4 text-muted-foreground" /></button>
        </div>
        <div className="overflow-y-auto space-y-4 p-6">
          {error && <div className="rounded-md bg-red-50 px-4 py-2 text-sm text-red-700 border border-red-200">{error}</div>}
          <div className="space-y-1">
            <label className="block text-sm font-medium">Titel *</label>
            <input className="w-full rounded-md border border-input px-3 py-2 text-sm"
              value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              placeholder="z.B. Due-Diligence-Politik 2026" />
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium">
              Inhalt
              <span className="ml-1 text-xs font-normal text-muted-foreground">(Art. 7 Abs. 1–3 CSDDD: Werte, Ansätze, Verhaltenskodex)</span>
            </label>
            <textarea rows={8} className="w-full rounded-md border border-input px-3 py-2 text-sm font-mono"
              value={form.content_text}
              onChange={(e) => setForm((f) => ({ ...f, content_text: e.target.value }))}
              placeholder="Vollständiger Text der DD-Politik…" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="block text-sm font-medium">Genehmigt von</label>
              <input className="w-full rounded-md border border-input px-3 py-2 text-sm"
                value={form.approved_by ?? ""} onChange={(e) => setForm((f) => ({ ...f, approved_by: e.target.value }))}
                placeholder="Name" />
            </div>
            <div className="space-y-1">
              <label className="block text-sm font-medium">Rolle / Funktion</label>
              <input className="w-full rounded-md border border-input px-3 py-2 text-sm"
                value={form.approved_role ?? ""} onChange={(e) => setForm((f) => ({ ...f, approved_role: e.target.value }))}
                placeholder="z.B. Vorstand / CFO" />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="checkbox" checked={form.is_public ?? false}
              onChange={(e) => setForm((f) => ({ ...f, is_public: e.target.checked }))}
              className="h-4 w-4" />
            <span>Öffentlich zugänglich machen (Art. 7 Abs. 3 CSDDD — Veröffentlichungspflicht)</span>
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="rounded-md border border-border px-4 py-2 text-sm">Abbrechen</button>
            <button
              disabled={!form.title || mutation.isPending}
              onClick={() => mutation.mutate(form)}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50">
              {mutation.isPending ? "Speichern…" : "Als Entwurf speichern"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── CoC Modal ─────────────────────────────────────────────────────────────────

function CoCModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ title: "", content_text: "", acceptance_validity_months: 24 });
  const [error, setError] = useState("");
  const mutation = useMutation({
    mutationFn: createCoC,
    onSuccess: () => { onSaved(); onClose(); },
    onError: (err) => setError(extractErrorMessage(err)),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-xl rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="text-base font-semibold">Verhaltenskodex erstellen</h2>
          <button onClick={onClose}><X className="h-4 w-4 text-muted-foreground" /></button>
        </div>
        <div className="space-y-4 p-6">
          {error && <div className="rounded-md bg-red-50 px-4 py-2 text-sm text-red-700 border border-red-200">{error}</div>}
          <div className="space-y-1">
            <label className="block text-sm font-medium">Titel *</label>
            <input className="w-full rounded-md border border-input px-3 py-2 text-sm"
              value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              placeholder="z.B. Lieferanten-Verhaltenskodex 2026" />
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium">Inhalt</label>
            <textarea rows={6} className="w-full rounded-md border border-input px-3 py-2 text-sm"
              value={form.content_text} onChange={(e) => setForm((f) => ({ ...f, content_text: e.target.value }))}
              placeholder="Vollständiger Text des Verhaltenskodex…" />
          </div>
          <div className="space-y-1">
            <label className="block text-sm font-medium">Gültigkeitsdauer der Bestätigung</label>
            <select className="w-full rounded-md border border-input px-3 py-2 text-sm bg-background"
              value={form.acceptance_validity_months}
              onChange={(e) => setForm((f) => ({ ...f, acceptance_validity_months: parseInt(e.target.value) }))}>
              <option value={12}>12 Monate</option>
              <option value={24}>24 Monate</option>
              <option value={36}>36 Monate</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="rounded-md border border-border px-4 py-2 text-sm">Abbrechen</button>
            <button
              disabled={!form.title || mutation.isPending}
              onClick={() => mutation.mutate(form)}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50">
              {mutation.isPending ? "Speichern…" : "Speichern & aktivieren"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function GovernancePage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"policies" | "coc" | "calendar">("policies");
  const [showPolicyModal, setShowPolicyModal] = useState(false);
  const [showCoCModal, setShowCoCModal] = useState(false);

  const { data: policies = [] } = useQuery({ queryKey: ["dd-policies"], queryFn: listPolicies });
  const { data: cocs = [] } = useQuery({ queryKey: ["codes-of-conduct"], queryFn: listCoCs });
  const { data: reviewStatus } = useQuery({ queryKey: ["governance-review-status"], queryFn: getReviewStatus });
  const { data: calendar } = useQuery({ queryKey: ["governance-calendar"], queryFn: getCalendar });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["dd-policies"] });
    qc.invalidateQueries({ queryKey: ["governance-review-status"] });
    qc.invalidateQueries({ queryKey: ["governance-calendar"] });
  };
  const invalidateCoc = () => qc.invalidateQueries({ queryKey: ["codes-of-conduct"] });

  const activateMutation = useMutation({ mutationFn: activatePolicy, onSuccess: invalidate });
  const cloneMutation = useMutation({ mutationFn: clonePolicy, onSuccess: invalidate });
  const archiveMutation = useMutation({ mutationFn: archivePolicy, onSuccess: invalidate });

  const activePolicy = policies.find((p) => p.policy_status === "active");
  const draftPolicies = policies.filter((p) => p.policy_status === "draft");
  const archivedPolicies = policies.filter((p) => p.policy_status === "archived");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">DD-Governance & Policies</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Art. 7 CSDDD — Due-Diligence-Politik, Verhaltenskodex, 24-Monats-Review
          </p>
        </div>
        <div className="flex gap-2">
          {tab === "coc" && (
            <button onClick={() => setShowCoCModal(true)}
              className="flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground">
              <Plus className="h-4 w-4" /> Verhaltenskodex
            </button>
          )}
          {tab === "policies" && (
            <button onClick={() => setShowPolicyModal(true)}
              className="flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground">
              <Plus className="h-4 w-4" /> Neue Politik
            </button>
          )}
        </div>
      </div>

      {/* Review Status Banner */}
      {reviewStatus && (
        <div className={`rounded-xl border p-4 flex items-center gap-4 ${
          reviewStatus.review_status === "overdue" ? "border-red-200 bg-red-50" :
          reviewStatus.review_status.startsWith("due_soon") ? "border-amber-200 bg-amber-50" :
          "border-border bg-card"
        }`}>
          <div className={`rounded-full p-2 ${
            reviewStatus.review_status === "overdue" ? "bg-red-100" :
            reviewStatus.review_status.startsWith("due_soon") ? "bg-amber-100" : "bg-emerald-100"
          }`}>
            {reviewStatus.review_status === "overdue" ? (
              <AlertTriangle className="h-5 w-5 text-red-600" />
            ) : reviewStatus.review_status.startsWith("due_soon") ? (
              <Clock className="h-5 w-5 text-amber-600" />
            ) : (
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            )}
          </div>
          <div className="flex-1">
            <p className={`font-semibold text-sm ${REVIEW_COLORS[reviewStatus.review_status]}`}>
              {REVIEW_LABELS[reviewStatus.review_status]}
            </p>
            {reviewStatus.policy_title && (
              <p className="text-xs text-muted-foreground mt-0.5">
                {reviewStatus.policy_title} — Version {reviewStatus.policy_version}
                {reviewStatus.next_review_due && ` · Nächster Review: ${new Date(reviewStatus.next_review_due).toLocaleDateString("de-DE")}`}
              </p>
            )}
            {!reviewStatus.has_active_policy && (
              <p className="text-xs text-muted-foreground mt-0.5">
                Keine aktive DD-Politik hinterlegt — Art. 7 CSDDD nicht erfüllt
              </p>
            )}
          </div>
          {reviewStatus.has_active_policy && (
            <button onClick={() => {
              const active = policies.find((p) => p.policy_status === "active");
              if (active) cloneMutation.mutate(active.id);
            }}
              className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs hover:bg-muted">
              <RotateCcw className="h-3.5 w-3.5" /> Review starten
            </button>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {([
          ["policies", `Politiken (${policies.length})`],
          ["coc", `Verhaltenskodex (${cocs.length})`],
          ["calendar", "Governance-Kalender"],
        ] as const).map(([t, label]) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
            }`}>
            {label}
          </button>
        ))}
      </div>

      {/* Policies Tab */}
      {tab === "policies" && (
        <div className="space-y-6">
          {/* Active Policy */}
          {activePolicy ? (
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">Aktive Politik</h3>
              <PolicyCard
                policy={activePolicy}
                onClone={() => cloneMutation.mutate(activePolicy.id)}
                onArchive={() => archiveMutation.mutate(activePolicy.id)}
              />
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-amber-300 bg-amber-50 p-6 text-center">
              <AlertTriangle className="mx-auto mb-2 h-8 w-8 text-amber-500" />
              <p className="font-medium text-amber-800 text-sm">Keine aktive DD-Politik</p>
              <p className="text-xs text-amber-700 mt-1">Art. 7 CSDDD erfordert eine veröffentlichte DD-Politik.</p>
              <button onClick={() => setShowPolicyModal(true)}
                className="mt-3 flex items-center gap-1 mx-auto rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground">
                <Plus className="h-3.5 w-3.5" /> Politik erstellen
              </button>
            </div>
          )}

          {/* Draft Policies */}
          {draftPolicies.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">Entwürfe</h3>
              <div className="divide-y divide-border rounded-xl border border-border bg-card">
                {draftPolicies.map((p) => (
                  <PolicyCard key={p.id} policy={p}
                    onActivate={() => activateMutation.mutate(p.id)}
                    onArchive={() => archiveMutation.mutate(p.id)} />
                ))}
              </div>
            </div>
          )}

          {/* Archived */}
          {archivedPolicies.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                Archiv ({archivedPolicies.length})
              </h3>
              <div className="divide-y divide-border rounded-xl border border-border bg-card opacity-75">
                {archivedPolicies.map((p) => <PolicyCard key={p.id} policy={p} />)}
              </div>
            </div>
          )}

          {policies.length === 0 && (
            <div className="flex h-40 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border">
              <FileText className="h-10 w-10 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">Noch keine DD-Politik erstellt.</p>
            </div>
          )}
        </div>
      )}

      {/* CoC Tab */}
      {tab === "coc" && (
        <div className="space-y-4">
          {cocs.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border">
              <Shield className="h-10 w-10 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">Noch kein Verhaltenskodex erstellt.</p>
              <button onClick={() => setShowCoCModal(true)}
                className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground">
                <Plus className="h-3.5 w-3.5" /> Verhaltenskodex erstellen
              </button>
            </div>
          ) : (
            <div className="divide-y divide-border rounded-xl border border-border bg-card">
              {cocs.map((c) => (
                <div key={c.id} className="flex items-center gap-4 px-4 py-3">
                  <div className={`flex h-9 w-9 items-center justify-center rounded-full ${c.is_active ? "bg-emerald-100" : "bg-slate-100"}`}>
                    <Shield className={`h-4 w-4 ${c.is_active ? "text-emerald-600" : "text-slate-400"}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{c.title}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs ${c.is_active ? "bg-emerald-100 text-emerald-700" : "bg-gray-100 text-gray-500"}`}>
                        {c.is_active ? "Aktiv" : "Inaktiv"} · v{c.coc_version}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Bestätigung gültig für {c.acceptance_validity_months} Monate
                      {c.valid_from && ` · ab ${new Date(c.valid_from).toLocaleDateString("de-DE")}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Calendar Tab */}
      {tab === "calendar" && (
        <div className="space-y-3">
          {(calendar?.events ?? []).length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border">
              <Calendar className="h-10 w-10 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">Keine Governance-Fristen gefunden.</p>
            </div>
          ) : (
            <div className="divide-y divide-border rounded-xl border border-border bg-card">
              {(calendar?.events ?? []).map((evt) => (
                <div key={evt.reference_id + evt.event_type} className="flex items-center gap-4 px-4 py-3">
                  <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${
                    evt.status === "overdue" ? "bg-red-100" :
                    evt.status === "due_soon" ? "bg-amber-100" : "bg-blue-100"
                  }`}>
                    <Calendar className={`h-4 w-4 ${
                      evt.status === "overdue" ? "text-red-600" :
                      evt.status === "due_soon" ? "text-amber-600" : "text-blue-600"
                    }`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-sm">{evt.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{evt.detail}</p>
                  </div>
                  <div className="text-right text-xs shrink-0">
                    {evt.due_date && (
                      <p className={`font-medium ${
                        evt.status === "overdue" ? "text-red-600" :
                        evt.status === "due_soon" ? "text-amber-600" : "text-muted-foreground"
                      }`}>
                        {new Date(evt.due_date).toLocaleDateString("de-DE")}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {showPolicyModal && (
        <PolicyModal onClose={() => setShowPolicyModal(false)} onSaved={invalidate} />
      )}
      {showCoCModal && (
        <CoCModal onClose={() => setShowCoCModal(false)} onSaved={invalidateCoc} />
      )}
    </div>
  );
}

// ── Policy Card ───────────────────────────────────────────────────────────────

function PolicyCard({
  policy, onActivate, onClone, onArchive,
}: {
  policy: DDPolicy;
  onActivate?: () => void;
  onClone?: () => void;
  onArchive?: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="px-4 py-3">
      <div className="flex items-start gap-4">
        <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${
          policy.policy_status === "active" ? "bg-emerald-100" :
          policy.policy_status === "draft" ? "bg-blue-100" : "bg-gray-100"
        }`}>
          <ScrollText className={`h-4 w-4 ${
            policy.policy_status === "active" ? "text-emerald-600" :
            policy.policy_status === "draft" ? "text-blue-600" : "text-gray-400"
          }`} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm">{policy.title}</span>
            <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_COLORS[policy.policy_status]}`}>
              {STATUS_LABELS[policy.policy_status]}
            </span>
            <span className="text-xs text-muted-foreground">v{policy.policy_version}</span>
            {policy.is_public && (
              <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">Öffentlich</span>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {policy.approved_by && `Genehmigt von: ${policy.approved_by}${policy.approved_role ? ` (${policy.approved_role})` : ""} · `}
            {policy.valid_from && `Gültig ab: ${new Date(policy.valid_from).toLocaleDateString("de-DE")} · `}
            {policy.next_review_due && `Review: ${new Date(policy.next_review_due).toLocaleDateString("de-DE")}`}
          </p>
          {expanded && policy.content_text && (
            <pre className="mt-2 whitespace-pre-wrap text-xs text-foreground/80 bg-muted/40 rounded-md p-3 max-h-48 overflow-y-auto">
              {policy.content_text}
            </pre>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {policy.content_text && (
            <button onClick={() => setExpanded(!expanded)}
              className="rounded p-1.5 hover:bg-muted text-muted-foreground text-xs">
              {expanded ? "Schließen" : "Anzeigen"}
            </button>
          )}
          {onActivate && (
            <button onClick={onActivate}
              className="rounded-md bg-emerald-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-emerald-700">
              Aktivieren
            </button>
          )}
          {onClone && (
            <button onClick={onClone}
              className="rounded-md border border-border px-2.5 py-1 text-xs hover:bg-muted flex items-center gap-1">
              <RotateCcw className="h-3 w-3" /> Review
            </button>
          )}
          {onArchive && (
            <button onClick={onArchive}
              className="rounded p-1.5 hover:bg-red-50 text-muted-foreground hover:text-red-600">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
