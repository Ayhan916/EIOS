"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity, Plus, AlertTriangle, CheckCircle2, ChevronRight,
  TrendingDown, TrendingUp, X, BookOpen, ClipboardList, BarChart2,
  ArrowUp, ArrowDown, Minus,
} from "lucide-react";
import {
  listIndicators, listReviews, createReview, submitReview, closeReview,
  getEffectivenessDashboard, createIndicator,
  type EffectivenessReview, type ReviewCreate, type EffectivenessIndicator,
} from "@/lib/api/effectiveness";
import { extractErrorMessage } from "@/lib/utils";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600",
  submitted: "bg-amber-100 text-amber-700",
  approved: "bg-blue-100 text-blue-700",
  closed: "bg-emerald-100 text-emerald-700",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Entwurf",
  submitted: "Eingereicht",
  approved: "Genehmigt",
  closed: "Abgeschlossen",
};

function Badge({ label, colorClass }: { label: string; colorClass: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {label}
    </span>
  );
}

// ── Dashboard Tab ─────────────────────────────────────────────────────────────

function DashboardTab() {
  const { data: dash, isLoading } = useQuery({
    queryKey: ["effectiveness-dashboard"],
    queryFn: getEffectivenessDashboard,
    refetchInterval: 60_000,
  });

  if (isLoading || !dash) return <p className="text-sm text-slate-500">Wird geladen...</p>;

  const metrics = [
    {
      label: "Offene CAPs",
      value: dash.open_caps,
      icon: ClipboardList,
      color: dash.open_caps > 10 ? "text-red-600" : "text-slate-700",
    },
    {
      label: "Überfällige CAPs",
      value: dash.overdue_caps,
      icon: AlertTriangle,
      color: dash.overdue_caps > 0 ? "text-red-600" : "text-emerald-600",
    },
    {
      label: "Abg. CAPs (12M)",
      value: dash.closed_caps_12m,
      icon: CheckCircle2,
      color: "text-emerald-600",
    },
    {
      label: "Ø Risikoänderung",
      value: dash.avg_risk_delta !== null ? `${dash.avg_risk_delta > 0 ? "+" : ""}${dash.avg_risk_delta}` : "—",
      icon: dash.avg_risk_delta !== null && dash.avg_risk_delta < 0 ? TrendingDown : TrendingUp,
      color: dash.avg_risk_delta !== null && dash.avg_risk_delta < 0 ? "text-emerald-600" : "text-amber-600",
    },
    {
      label: "Stakeh. Konsult. (12M)",
      value: dash.stakeholder_consultations_12m,
      icon: Activity,
      color: "text-blue-600",
    },
    {
      label: "Remedy abg. (12M)",
      value: dash.remedy_cases_closed_12m,
      icon: CheckCircle2,
      color: "text-emerald-600",
    },
  ];

  return (
    <div className="space-y-4">
      {dash.escalation_needed && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 shrink-0" />
          <p className="text-sm text-red-700">
            <strong>Eskalation empfohlen:</strong> Überfällige CAPs oder steigende Risikotrends erkannt. Art. 15 Abs. 2 CSDDD — bitte neuen Wirksamkeits-Review starten.
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {metrics.map((m) => (
          <div key={m.label} className="bg-white border rounded-xl p-4 flex items-center gap-3">
            <m.icon className={`w-8 h-8 ${m.color}`} />
            <div>
              <p className={`text-2xl font-bold ${m.color}`}>{m.value}</p>
              <p className="text-xs text-slate-500">{m.label}</p>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-slate-400">
        Stand: {new Date(dash.generated_at).toLocaleString("de-DE")} · Aktualisierung alle 60s
      </p>
    </div>
  );
}

// ── New Review Modal ──────────────────────────────────────────────────────────

function NewReviewModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<ReviewCreate>({
    title: "",
    period_start: new Date(new Date().getFullYear(), 0, 1).toISOString().slice(0, 10) + "T00:00",
    period_end: new Date().toISOString().slice(0, 16),
  });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: createReview,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["effectiveness-reviews"] });
      onClose();
    },
    onError: (e: unknown) => setError(extractErrorMessage(e)),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-800">Neuer Wirksamkeits-Review</h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400 hover:text-slate-700" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium text-slate-700">Titel *</label>
            <input
              className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              placeholder="z.B. Jahres-Review 2025"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium text-slate-700">Zeitraum von *</label>
              <input
                type="datetime-local"
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={form.period_start}
                onChange={(e) => setForm((f) => ({ ...f, period_start: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Zeitraum bis *</label>
              <input
                type="datetime-local"
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={form.period_end}
                onChange={(e) => setForm((f) => ({ ...f, period_end: e.target.value }))}
              />
            </div>
          </div>
        </div>
        {error && <p className="mt-3 text-xs text-red-600">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800">Abbrechen</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.title}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {mutation.isPending ? "..." : "Erstellen"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Review Detail Panel ───────────────────────────────────────────────────────

function ReviewDetail({ review, onClose }: { review: EffectivenessReview; onClose: () => void }) {
  const qc = useQueryClient();

  const submitMut = useMutation({
    mutationFn: () => submitReview(review.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["effectiveness-reviews"] });
      onClose();
    },
  });

  const closeMut = useMutation({
    mutationFn: () => closeReview(review.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["effectiveness-reviews"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end bg-black/30">
      <div className="w-full max-w-lg h-full bg-white shadow-2xl flex flex-col overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b">
          <div>
            <h2 className="text-base font-semibold text-slate-800">{review.title}</h2>
            <Badge
              label={STATUS_LABELS[review.status] || review.status}
              colorClass={STATUS_COLORS[review.status] || "bg-slate-100 text-slate-600"}
            />
          </div>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400 hover:text-slate-700" /></button>
        </div>

        <div className="p-5 space-y-5">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-slate-500">Zeitraum</p>
              <p className="font-medium">
                {new Date(review.period_start).toLocaleDateString("de-DE")} –{" "}
                {new Date(review.period_end).toLocaleDateString("de-DE")}
              </p>
            </div>
            {review.overall_rating && (
              <div>
                <p className="text-slate-500">Gesamtbewertung</p>
                <p className="font-medium">{"★".repeat(review.overall_rating)}{"☆".repeat(5 - review.overall_rating)}</p>
              </div>
            )}
          </div>

          {review.key_findings && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Kernbefunde</p>
              <p className="text-sm text-slate-700 whitespace-pre-line">{review.key_findings}</p>
            </div>
          )}

          {review.improvement_actions && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Verbesserungsmaßnahmen</p>
              <p className="text-sm text-slate-700 whitespace-pre-line">{review.improvement_actions}</p>
            </div>
          )}

          {review.lines.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Messpunkte ({review.lines.length})</p>
              <div className="space-y-2">
                {review.lines.map((l) => (
                  <div key={l.id} className="p-2 bg-slate-50 rounded text-sm">
                    <p className="font-medium text-slate-700">{l.indicator_name}</p>
                    {l.measured_value !== null && (
                      <p className="text-slate-600">Wert: <span className="font-medium">{l.measured_value}</span></p>
                    )}
                    {l.measured_text && <p className="text-slate-600">{l.measured_text}</p>}
                    {l.comment && <p className="text-xs text-slate-400 mt-0.5">{l.comment}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="border-t pt-4 space-y-2">
            {review.status === "draft" && (
              <button
                onClick={() => submitMut.mutate()}
                disabled={submitMut.isPending}
                className="w-full py-2 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50"
              >
                {submitMut.isPending ? "..." : "Zur Genehmigung einreichen"}
              </button>
            )}
            {review.status === "submitted" && (
              <button
                onClick={() => closeMut.mutate()}
                disabled={closeMut.isPending}
                className="w-full py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50"
              >
                {closeMut.isPending ? "..." : "Review abschließen (Analyst / Admin)"}
              </button>
            )}
          </div>

          {review.submitted_by && (
            <p className="text-xs text-slate-400">
              Eingereicht von {review.submitted_by} am{" "}
              {review.submitted_at ? new Date(review.submitted_at).toLocaleDateString("de-DE") : "—"}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── New Indicator Modal ───────────────────────────────────────────────────────

function NewIndicatorModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ name: "", description: "", indicator_type: "qualitative", unit: "", csddd_article: "" });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: createIndicator,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["effectiveness-indicators"] });
      onClose();
    },
    onError: (e: unknown) => setError(extractErrorMessage(e)),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-800">Eigenen KPI hinzufügen</h2>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400 hover:text-slate-700" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium text-slate-700">Name *</label>
            <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Beschreibung</label>
            <textarea rows={2} className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium text-slate-700">Typ</label>
              <select className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" value={form.indicator_type} onChange={(e) => setForm((f) => ({ ...f, indicator_type: e.target.value }))}>
                <option value="qualitative">Qualitativ</option>
                <option value="quantitative">Quantitativ</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Einheit</label>
              <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" value={form.unit} onChange={(e) => setForm((f) => ({ ...f, unit: e.target.value }))} placeholder="z.B. %" />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">CSDDD-Artikel</label>
            <input className="mt-1 w-full border rounded-lg px-3 py-2 text-sm" value={form.csddd_article} onChange={(e) => setForm((f) => ({ ...f, csddd_article: e.target.value }))} placeholder="z.B. Art. 15" />
          </div>
        </div>
        {error && <p className="mt-3 text-xs text-red-600">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800">Abbrechen</button>
          <button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.name}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {mutation.isPending ? "..." : "Hinzufügen"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function EffectivenessPage() {
  const [activeTab, setActiveTab] = useState<"dashboard" | "reviews" | "indicators">("dashboard");
  const [showNewReview, setShowNewReview] = useState(false);
  const [showNewIndicator, setShowNewIndicator] = useState(false);
  const [selected, setSelected] = useState<EffectivenessReview | null>(null);

  const { data: reviews = [], isLoading: reviewsLoading } = useQuery({
    queryKey: ["effectiveness-reviews"],
    queryFn: listReviews,
  });

  const { data: indicators = [], isLoading: indLoading } = useQuery({
    queryKey: ["effectiveness-indicators"],
    queryFn: () => listIndicators(),
    enabled: activeTab === "indicators",
  });

  const reviewsByStatus = {
    draft: reviews.filter((r) => r.status === "draft").length,
    submitted: reviews.filter((r) => r.status === "submitted").length,
    closed: reviews.filter((r) => r.status === "closed").length,
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="w-7 h-7 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Effectiveness Monitoring</h1>
            <p className="text-sm text-slate-500">CSDDD Art. 15 — Überwachung der Wirksamkeit</p>
          </div>
        </div>
        {activeTab === "reviews" && (
          <button
            onClick={() => setShowNewReview(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" /> Neuer Review
          </button>
        )}
        {activeTab === "indicators" && (
          <button
            onClick={() => setShowNewIndicator(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" /> Eigener KPI
          </button>
        )}
      </div>

      {/* KPI Summary (always visible) */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border rounded-xl p-4 flex items-center gap-3">
          <ClipboardList className="w-7 h-7 text-slate-500" />
          <div>
            <p className="text-2xl font-bold text-slate-800">{reviews.length}</p>
            <p className="text-xs text-slate-500">Reviews gesamt</p>
          </div>
        </div>
        <div className="bg-white border rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle className="w-7 h-7 text-amber-500" />
          <div>
            <p className="text-2xl font-bold text-slate-800">{reviewsByStatus.submitted}</p>
            <p className="text-xs text-slate-500">Ausstehend</p>
          </div>
        </div>
        <div className="bg-white border rounded-xl p-4 flex items-center gap-3">
          <CheckCircle2 className="w-7 h-7 text-emerald-500" />
          <div>
            <p className="text-2xl font-bold text-slate-800">{reviewsByStatus.closed}</p>
            <p className="text-xs text-slate-500">Abgeschlossen</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b">
        {[
          { id: "dashboard", label: "Live-Dashboard" },
          { id: "reviews", label: "Wirksamkeits-Reviews" },
          { id: "indicators", label: `KPI-Bibliothek (${indicators.length || "…"})` },
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

      {/* Dashboard */}
      {activeTab === "dashboard" && <DashboardTab />}

      {/* Reviews */}
      {activeTab === "reviews" && (
        <div className="space-y-2">
          {reviewsLoading ? (
            <p className="text-sm text-slate-500">Wird geladen...</p>
          ) : reviews.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Activity className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Noch keine Reviews vorhanden</p>
              <p className="text-xs mt-1">Art. 15 CSDDD — mindestens einmal jährlich</p>
            </div>
          ) : (
            reviews.map((r) => (
              <div
                key={r.id}
                onClick={() => setSelected(r)}
                className="bg-white border rounded-xl p-4 flex items-center gap-4 cursor-pointer hover:border-blue-300 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-medium text-slate-800 truncate">{r.title}</p>
                    <Badge label={STATUS_LABELS[r.status] || r.status} colorClass={STATUS_COLORS[r.status] || "bg-slate-100 text-slate-600"} />
                  </div>
                  <p className="text-xs text-slate-500">
                    {new Date(r.period_start).toLocaleDateString("de-DE")} –{" "}
                    {new Date(r.period_end).toLocaleDateString("de-DE")}
                    {r.overall_rating && ` · ★${r.overall_rating}/5`}
                    {r.lines.length > 0 && ` · ${r.lines.length} Messpunkte`}
                  </p>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
              </div>
            ))
          )}
        </div>
      )}

      {/* Indicator Library */}
      {activeTab === "indicators" && (
        <div className="space-y-3">
          {indLoading ? (
            <p className="text-sm text-slate-500">Wird geladen...</p>
          ) : (
            <div className="bg-white border rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 border-b">
                  <tr>
                    <th className="text-left px-4 py-3 text-slate-600 font-medium">KPI</th>
                    <th className="text-left px-4 py-3 text-slate-600 font-medium">Typ</th>
                    <th className="text-left px-4 py-3 text-slate-600 font-medium">Einheit</th>
                    <th className="text-left px-4 py-3 text-slate-600 font-medium">Quelle</th>
                    <th className="text-left px-4 py-3 text-slate-600 font-medium">Artikel</th>
                    <th className="text-left px-4 py-3 text-slate-600 font-medium">Bereich</th>
                  </tr>
                </thead>
                <tbody>
                  {indicators.map((ind) => (
                    <tr key={ind.id} className="border-b last:border-0 hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-800">{ind.name}</p>
                        {ind.description && <p className="text-xs text-slate-400 truncate max-w-xs">{ind.description}</p>}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${ind.indicator_type === "quantitative" ? "bg-blue-100 text-blue-700" : "bg-purple-100 text-purple-700"}`}>
                          {ind.indicator_type === "quantitative" ? "Quantitativ" : "Qualitativ"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{ind.unit || "—"}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${ind.data_source === "automatic" ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                          {ind.data_source === "automatic" ? "Automatisch" : "Manuell"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600 text-xs">{ind.csddd_article || "—"}</td>
                      <td className="px-4 py-3 text-slate-500 text-xs">{ind.risk_category || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {showNewReview && <NewReviewModal onClose={() => setShowNewReview(false)} />}
      {showNewIndicator && <NewIndicatorModal onClose={() => setShowNewIndicator(false)} />}
      {selected && <ReviewDetail review={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
