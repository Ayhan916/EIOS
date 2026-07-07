"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Target, Plus, AlertTriangle, CheckCircle2, ChevronRight,
  X, Settings, Play, FileText, Clock, Shield,
} from "lucide-react";
import { useLanguage } from "@/lib/i18n/context";
import {
  getLatestConfig, createDefaultConfig, runAnalysis, listStudies,
  createStudy, submitStudy, approveStudy, cloneStudy, getScopingReviewStatus,
  type ScopingConfig, type ScopingResult, type ScopingStudy,
} from "@/lib/api/scoping";
import { extractErrorMessage } from "@/lib/utils";

const PRIORITY_COLORS: Record<string, string> = {
  priority_1: "bg-red-100 text-red-700",
  priority_2: "bg-amber-100 text-amber-700",
  priority_3: "bg-emerald-100 text-emerald-700",
};

const PRIORITY_LABELS: Record<string, string> = {
  priority_1: "Priorität 1 — Sofortige DD",
  priority_2: "Priorität 2 — Planmäßige DD",
  priority_3: "Priorität 3 — Vereinfachte DD",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600",
  submitted: "bg-amber-100 text-amber-700",
  approved: "bg-emerald-100 text-emerald-700",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Entwurf",
  submitted: "Eingereicht",
  approved: "Genehmigt",
};

function Badge({ label, colorClass }: { label: string; colorClass: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {label}
    </span>
  );
}

// ── Review Status Banner ───────────────────────────────────────────────────────

function ReviewStatusBanner() {
  const { data } = useQuery({
    queryKey: ["scoping-review-status"],
    queryFn: getScopingReviewStatus,
  });

  if (!data || data.status === "current") return null;

  const configs: Record<string, { color: string; text: string }> = {
    no_study: { color: "bg-slate-50 border-slate-200 text-slate-700", text: "Noch keine genehmigte Scoping Study vorhanden. Art. 8 Abs. 3 CSDDD empfiehlt eine jährliche Dokumentation." },
    due_soon: { color: "bg-amber-50 border-amber-200 text-amber-800", text: `Scoping Study Review fällig in ${data.days_until_review} Tagen (${data.latest_approved_year ? `letzte Genehmigung: ${data.latest_approved_year}` : ""}).` },
    overdue: { color: "bg-red-50 border-red-200 text-red-800", text: `Scoping Study Review überfällig seit ${data.latest_approved_year || "—"}. Bitte neue Studie erstellen.` },
  };

  const cfg = configs[data.status];
  if (!cfg) return null;

  return (
    <div className={`border rounded-xl px-4 py-3 flex items-center gap-3 ${cfg.color}`}>
      <AlertTriangle className="w-5 h-5 shrink-0" />
      <p className="text-sm">{cfg.text}</p>
    </div>
  );
}

// ── Analysis Results Table ─────────────────────────────────────────────────────

function AnalysisResults({
  results,
  summary,
  configId,
  onSaved,
}: {
  results: ScopingResult[];
  summary: { total: number; priority_1: number; priority_2: number; priority_3: number };
  configId: string;
  onSaved: () => void;
}) {
  const qc = useQueryClient();
  const [title, setTitle] = useState(`Scoping Study ${new Date().getFullYear()}`);
  const [notes, setNotes] = useState("");

  const saveMut = useMutation({
    mutationFn: () =>
      createStudy({
        title,
        report_year: new Date().getFullYear(),
        config_id: configId,
        methodology_notes: notes,
        results,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scoping-studies"] });
      onSaved();
    },
  });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Gesamt", value: summary.total, color: "text-slate-700" },
          { label: "Priorität 1", value: summary.priority_1, color: "text-red-600" },
          { label: "Priorität 2", value: summary.priority_2, color: "text-amber-600" },
          { label: "Priorität 3", value: summary.priority_3, color: "text-emerald-600" },
        ].map((s) => (
          <div key={s.label} className="bg-white border rounded-xl p-3 text-center">
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-xs text-slate-500">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="bg-white border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 text-slate-600 font-medium">Lieferant</th>
              <th className="text-left px-4 py-3 text-slate-600 font-medium">Land</th>
              <th className="text-left px-4 py-3 text-slate-600 font-medium">Score</th>
              <th className="text-left px-4 py-3 text-slate-600 font-medium">Priorität</th>
              <th className="text-left px-4 py-3 text-slate-600 font-medium">Begründung</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.supplier_id} className="border-b last:border-0 hover:bg-slate-50">
                <td className="px-4 py-3 font-medium text-slate-800">{r.supplier_name}</td>
                <td className="px-4 py-3 text-slate-600">{r.country || "—"}</td>
                <td className="px-4 py-3">
                  <span className={`font-semibold ${r.risk_score >= 7 ? "text-red-600" : r.risk_score >= 4 ? "text-amber-600" : "text-emerald-600"}`}>
                    {r.risk_score.toFixed(1)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <Badge label={PRIORITY_LABELS[r.priority]?.split("—")[0].trim() || r.priority} colorClass={PRIORITY_COLORS[r.priority] || "bg-slate-100 text-slate-600"} />
                </td>
                <td className="px-4 py-3 text-xs text-slate-500">{r.reasons.join(" · ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-white border rounded-xl p-4 space-y-3">
        <h3 className="text-sm font-semibold text-slate-700">Als Scoping Study speichern</h3>
        <input
          className="w-full border rounded-lg px-3 py-2 text-sm"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Titel der Studie"
        />
        <textarea
          rows={3}
          className="w-full border rounded-lg px-3 py-2 text-sm"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Methodischer Begründungstext (für Behörden-Nachweis)..."
        />
        <button
          onClick={() => saveMut.mutate()}
          disabled={saveMut.isPending || !title}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {saveMut.isPending ? "Wird gespeichert..." : "Studie erstellen"}
        </button>
      </div>
    </div>
  );
}

// ── Study Detail Panel ─────────────────────────────────────────────────────────

function StudyDetail({ study, onClose }: { study: ScopingStudy; onClose: () => void }) {
  const qc = useQueryClient();

  const submitMut = useMutation({
    mutationFn: () => submitStudy(study.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["scoping-studies"] }); onClose(); },
  });

  const approveMut = useMutation({
    mutationFn: () => approveStudy(study.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["scoping-studies", "scoping-review-status"] }); onClose(); },
  });

  const cloneMut = useMutation({
    mutationFn: () => cloneStudy(study.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["scoping-studies"] }); onClose(); },
  });

  const p1 = study.results_snapshot.filter((r) => r.priority === "priority_1").length;
  const p2 = study.results_snapshot.filter((r) => r.priority === "priority_2").length;
  const p3 = study.results_snapshot.filter((r) => r.priority === "priority_3").length;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end bg-black/30">
      <div className="w-full max-w-lg h-full bg-white shadow-2xl flex flex-col overflow-y-auto">
        <div className="flex items-center justify-between p-5 border-b">
          <div>
            <h2 className="text-base font-semibold text-slate-800">{study.title}</h2>
            <div className="flex items-center gap-2 mt-1">
              <Badge label={STATUS_LABELS[study.status] || study.status} colorClass={STATUS_COLORS[study.status] || "bg-slate-100 text-slate-600"} />
              <span className="text-xs text-slate-400">{study.report_year}</span>
            </div>
          </div>
          <button onClick={onClose}><X className="w-5 h-5 text-slate-400 hover:text-slate-700" /></button>
        </div>

        <div className="p-5 space-y-5">
          {/* Results summary */}
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center p-3 bg-red-50 rounded-xl">
              <p className="text-xl font-bold text-red-600">{p1}</p>
              <p className="text-xs text-red-500">Priorität 1</p>
            </div>
            <div className="text-center p-3 bg-amber-50 rounded-xl">
              <p className="text-xl font-bold text-amber-600">{p2}</p>
              <p className="text-xs text-amber-500">Priorität 2</p>
            </div>
            <div className="text-center p-3 bg-emerald-50 rounded-xl">
              <p className="text-xl font-bold text-emerald-600">{p3}</p>
              <p className="text-xs text-emerald-500">Priorität 3</p>
            </div>
          </div>

          {study.methodology_notes && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Methodische Begründung</p>
              <p className="text-sm text-slate-700 whitespace-pre-line">{study.methodology_notes}</p>
            </div>
          )}

          {study.next_review_due && (
            <p className="text-xs text-slate-500">
              Nächster Review fällig: {new Date(study.next_review_due).toLocaleDateString("de-DE")}
            </p>
          )}

          {/* Top P1 suppliers */}
          {p1 > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Priorität-1-Lieferanten ({p1})</p>
              <div className="space-y-1">
                {study.results_snapshot
                  .filter((r) => r.priority === "priority_1")
                  .slice(0, 5)
                  .map((r) => (
                    <div key={r.supplier_id} className="flex items-center gap-2 p-2 bg-red-50 rounded text-sm">
                      <span className="flex-1 font-medium text-slate-800">{r.supplier_name}</span>
                      <span className="text-xs text-red-600 font-semibold">{r.risk_score.toFixed(1)}</span>
                    </div>
                  ))}
                {p1 > 5 && <p className="text-xs text-slate-400">+ {p1 - 5} weitere</p>}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="border-t pt-4 space-y-2">
            {study.status === "draft" && (
              <button onClick={() => submitMut.mutate()} disabled={submitMut.isPending}
                className="w-full py-2 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50">
                {submitMut.isPending ? "..." : "Zur Genehmigung einreichen"}
              </button>
            )}
            {study.status === "submitted" && (
              <button onClick={() => approveMut.mutate()} disabled={approveMut.isPending}
                className="w-full py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50">
                {approveMut.isPending ? "..." : "Genehmigen & sperren (Analyst / Admin)"}
              </button>
            )}
            <button onClick={() => cloneMut.mutate()} disabled={cloneMut.isPending}
              className="w-full py-2 text-sm border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50 disabled:opacity-50">
              {cloneMut.isPending ? "..." : "Als Basis für neuen Review klonen"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function ScopingPage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<"studies" | "analyze" | "config">("studies");
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [selected, setSelected] = useState<ScopingStudy | null>(null);
  const [configError, setConfigError] = useState("");

  const { data: config, isLoading: configLoading, refetch: refetchConfig } = useQuery({
    queryKey: ["scoping-config"],
    queryFn: getLatestConfig,
    retry: false,
  });

  const { data: studies = [], isLoading: studiesLoading } = useQuery({
    queryKey: ["scoping-studies"],
    queryFn: listStudies,
  });

  const qc = useQueryClient();

  const defaultConfigMut = useMutation({
    mutationFn: createDefaultConfig,
    onSuccess: () => { refetchConfig(); setConfigError(""); },
    onError: (e: unknown) => setConfigError(extractErrorMessage(e)),
  });

  const analyzeMut = useMutation({
    mutationFn: () => runAnalysis(config!.id),
    onSuccess: (data) => setAnalysisResult(data),
  });

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Target className="w-7 h-7 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-slate-800">{t("scoping.title")}</h1>
            <p className="text-sm text-slate-500">{t("scoping.subtitle")}</p>
          </div>
        </div>
      </div>

      <ReviewStatusBanner />

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border rounded-xl p-4 flex items-center gap-3">
          <FileText className="w-7 h-7 text-slate-500" />
          <div>
            <p className="text-2xl font-bold text-slate-800">{studies.length}</p>
            <p className="text-xs text-slate-500">{t("scoping.kpiTotal")}</p>
          </div>
        </div>
        <div className="bg-white border rounded-xl p-4 flex items-center gap-3">
          <CheckCircle2 className="w-7 h-7 text-emerald-500" />
          <div>
            <p className="text-2xl font-bold text-slate-800">{studies.filter((s) => s.status === "approved").length}</p>
            <p className="text-xs text-slate-500">{t("scoping.approved")}</p>
          </div>
        </div>
        <div className="bg-white border rounded-xl p-4 flex items-center gap-3">
          <Settings className="w-7 h-7 text-blue-500" />
          <div>
            <p className="text-2xl font-bold text-slate-800">{config ? `v${config.version}` : "—"}</p>
            <p className="text-xs text-slate-500">{t("scoping.activeConfig")}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b">
        {[
          { id: "studies", label: t("scoping.tabStudies") },
          { id: "analyze", label: t("scoping.tabAnalyze") },
          { id: "config", label: t("scoping.tabConfig") },
        ].map((tabItem) => (
          <button key={tabItem.id} onClick={() => setActiveTab(tabItem.id as typeof activeTab)}
            className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${activeTab === tabItem.id ? "border-blue-600 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700"}`}>
            {tabItem.label}
          </button>
        ))}
      </div>

      {/* Studies tab */}
      {activeTab === "studies" && (
        <div className="space-y-2">
          {studiesLoading ? (
            <p className="text-sm text-slate-500">Wird geladen...</p>
          ) : studies.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Target className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Noch keine Scoping Studies vorhanden</p>
              <button onClick={() => setActiveTab("analyze")} className="mt-3 text-sm text-blue-600 hover:underline">
                Jetzt erste Analyse starten
              </button>
            </div>
          ) : (
            studies.map((s) => (
              <div key={s.id} onClick={() => setSelected(s)}
                className="bg-white border rounded-xl p-4 flex items-center gap-4 cursor-pointer hover:border-blue-300 transition-colors">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-medium text-slate-800 truncate">{s.title}</p>
                    <Badge label={STATUS_LABELS[s.status] || s.status} colorClass={STATUS_COLORS[s.status] || "bg-slate-100 text-slate-600"} />
                  </div>
                  <p className="text-xs text-slate-500">
                    {s.report_year} · {s.results_snapshot.length} Lieferanten analysiert
                    {s.results_snapshot.filter((r) => r.priority === "priority_1").length > 0 &&
                      ` · ${s.results_snapshot.filter((r) => r.priority === "priority_1").length}× P1`}
                  </p>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
              </div>
            ))
          )}
        </div>
      )}

      {/* Analyze tab */}
      {activeTab === "analyze" && (
        <div className="space-y-4">
          {!config ? (
            <div className="bg-white border rounded-xl p-6 text-center">
              <Settings className="w-12 h-12 mx-auto mb-3 text-slate-300" />
              <p className="text-sm text-slate-600 mb-3">Noch keine Scoping-Konfiguration vorhanden.</p>
              <button onClick={() => defaultConfigMut.mutate()} disabled={defaultConfigMut.isPending}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {defaultConfigMut.isPending ? "Wird erstellt..." : "Best-Practice Konfiguration erstellen"}
              </button>
              {configError && <p className="mt-2 text-xs text-red-600">{configError}</p>}
            </div>
          ) : (
            <div className="bg-white border rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-sm font-semibold text-slate-700">Aktive Konfiguration v{config.version}</p>
                  <p className="text-xs text-slate-500">
                    P1-Schwelle: {config.risk_score_threshold_p1} · P2-Schwelle: {config.risk_score_threshold_p2} ·{" "}
                    {config.high_risk_countries.length} Hochrisikoländer · {config.high_risk_sectors.length} Branchen
                  </p>
                </div>
                <button onClick={() => analyzeMut.mutate()} disabled={analyzeMut.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
                  <Play className="w-4 h-4" />
                  {analyzeMut.isPending ? "Analysiere..." : "Analyse starten"}
                </button>
              </div>
              <p className="text-xs text-slate-400">
                Der Algorithmus ist deterministisch und auditierbar — kein KI-basiertes Scoring (CSDDD Art. 8 Abs. 3).
              </p>
            </div>
          )}

          {analysisResult && (
            <AnalysisResults
              results={analysisResult.results}
              summary={analysisResult.summary}
              configId={config!.id}
              onSaved={() => { setActiveTab("studies"); setAnalysisResult(null); }}
            />
          )}
        </div>
      )}

      {/* Config tab */}
      {activeTab === "config" && (
        <div className="bg-white border rounded-xl p-6">
          {configLoading ? (
            <p className="text-sm text-slate-500">Wird geladen...</p>
          ) : !config ? (
            <div className="text-center">
              <p className="text-sm text-slate-600 mb-3">Keine Konfiguration vorhanden.</p>
              <button onClick={() => defaultConfigMut.mutate()} disabled={defaultConfigMut.isPending}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                Best-Practice Konfiguration erstellen
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-slate-800">Scoping-Konfiguration v{config.version}</h2>
                <span className="text-xs text-slate-400">Erstellt von {config.created_by}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-slate-500 text-xs mb-1">P1-Risikoschwelle</p>
                  <p className="font-semibold text-red-600">≥ {config.risk_score_threshold_p1}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-slate-500 text-xs mb-1">P2-Risikoschwelle</p>
                  <p className="font-semibold text-amber-600">≥ {config.risk_score_threshold_p2}</p>
                </div>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Hochrisikoländer ({config.high_risk_countries.length})</p>
                <div className="flex flex-wrap gap-1">
                  {config.high_risk_countries.map((c) => (
                    <span key={c} className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs">{c}</span>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Hochrisikobranchen ({config.high_risk_sectors.length})</p>
                <div className="flex flex-wrap gap-1">
                  {config.high_risk_sectors.map((s) => (
                    <span key={s} className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs">{s}</span>
                  ))}
                </div>
              </div>
              {config.notes && <p className="text-sm text-slate-600">{config.notes}</p>}
            </div>
          )}
        </div>
      )}

      {selected && <StudyDetail study={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
