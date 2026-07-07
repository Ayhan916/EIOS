"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Zap, AlertTriangle, TrendingUp, Plus, X, Trash2, Edit2, BarChart2,
} from "lucide-react";
import { useLanguage } from "@/lib/i18n/context";
import {
  previewScore, getImpactDashboard, listAssessments,
  createAssessment, updateAssessment, deleteAssessment,
  type ImpactAssessment, type PreviewResult,
} from "@/lib/api/impact-assessment";

// ── Config ────────────────────────────────────────────────────────────────────

const SEVERITY_CONFIG = {
  critical: { label: "Kritisch",  color: "text-red-600",    bg: "bg-red-500",     badge: "bg-red-50 border-red-200 text-red-700" },
  high:     { label: "Hoch",      color: "text-orange-600", bg: "bg-orange-500",  badge: "bg-orange-50 border-orange-200 text-orange-700" },
  medium:   { label: "Mittel",    color: "text-amber-600",  bg: "bg-amber-500",   badge: "bg-amber-50 border-amber-200 text-amber-700" },
  low:      { label: "Gering",    color: "text-emerald-600",bg: "bg-emerald-500", badge: "bg-emerald-50 border-emerald-200 text-emerald-700" },
};

const IMPACT_TYPES: Record<string, string> = {
  human_rights: "Menschenrechte",
  labor_rights: "Arbeitsrechte",
  environment: "Umwelt",
  health_safety: "Gesundheit & Sicherheit",
  anti_corruption: "Antikorruption",
  other: "Sonstige",
};

const DIMENSION_LABELS: Record<string, { label: string; desc: string[] }> = {
  gravity: {
    label: "Schwere (Gravity)",
    desc: ["1 = Geringfügig", "2 = Leicht", "3 = Moderat", "4 = Schwerwiegend", "5 = Katastrophal"],
  },
  scope: {
    label: "Ausmaß (Scope)",
    desc: ["1 = Einzelperson", "2 = Wenige", "3 = Gemeinschaft", "4 = Regional", "5 = Weit verbreitet"],
  },
  remediability: {
    label: "Irreversibilität",
    desc: ["1 = Vollständig reversibel", "2 = Größtenteils", "3 = Teilweise", "4 = Schwer", "5 = Irreversibel"],
  },
  likelihood: {
    label: "Wahrscheinlichkeit",
    desc: ["1 = Sehr unwahrscheinlich", "2 = Unwahrscheinlich", "3 = Möglich", "4 = Wahrscheinlich", "5 = Sicher/Bereits eingetreten"],
  },
};

// ── Score meter ───────────────────────────────────────────────────────────────

function ScoreMeter({ score, level }: { score: number; level: string }) {
  const cfg = SEVERITY_CONFIG[level as keyof typeof SEVERITY_CONFIG] ?? SEVERITY_CONFIG.low;
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <span className={`text-2xl font-bold ${cfg.color}`}>{score.toFixed(1)}</span>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${cfg.badge}`}>{cfg.label}</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-2 ${cfg.bg} rounded-full transition-all duration-500`}
          style={{ width: `${score * 10}%` }} />
      </div>
      <p className="text-xs text-slate-400">Schwere-Score 0–10 (OECD RBC)</p>
    </div>
  );
}

// ── Dimension slider ──────────────────────────────────────────────────────────

function DimensionSlider({
  name, value, onChange,
}: { name: string; value: number; onChange: (v: number) => void }) {
  const info = DIMENSION_LABELS[name];
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <label className="text-xs font-medium text-slate-700">{info.label}</label>
        <span className="text-sm font-bold text-blue-600 w-5 text-right">{value}</span>
      </div>
      <input
        type="range" min={1} max={5} step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-blue-600"
      />
      <p className="text-xs text-slate-400">{info.desc[value - 1]}</p>
    </div>
  );
}

// ── Live calculator panel ─────────────────────────────────────────────────────

function LiveCalculator({ onSave }: { onSave: (dims: { gravity: number; scope: number; remediability: number; likelihood: number }, title: string, type: string, justification: string) => void }) {
  const [gravity, setGravity] = useState(3);
  const [scope, setScope] = useState(3);
  const [remediability, setRemediability] = useState(3);
  const [likelihood, setLikelihood] = useState(3);
  const [title, setTitle] = useState("");
  const [impactType, setImpactType] = useState("other");
  const [justification, setJustification] = useState("");
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [computing, setComputing] = useState(false);

  useEffect(() => {
    setComputing(true);
    previewScore({ gravity, scope, remediability, likelihood })
      .then(setPreview)
      .finally(() => setComputing(false));
  }, [gravity, scope, remediability, likelihood]);

  return (
    <div className="bg-white border rounded-2xl p-6 space-y-5">
      <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
        <Zap className="w-4 h-4 text-blue-600" /> Live-Kalkulator
      </h3>

      {/* Live score */}
      <div className="bg-slate-50 rounded-xl p-4">
        {computing ? (
          <p className="text-xs text-slate-400 text-center">Berechnung…</p>
        ) : preview ? (
          <div className="space-y-3">
            <ScoreMeter score={preview.severity_score} level={preview.severity_level} />
            <div className="flex justify-between text-xs text-slate-500">
              <span>Priorität (mit Wahrscheinlichkeit)</span>
              <span className="font-semibold text-slate-700">{preview.priority_score.toFixed(1)}</span>
            </div>
          </div>
        ) : null}
      </div>

      {/* Sliders */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <DimensionSlider name="gravity" value={gravity} onChange={setGravity} />
        <DimensionSlider name="scope" value={scope} onChange={setScope} />
        <DimensionSlider name="remediability" value={remediability} onChange={setRemediability} />
        <DimensionSlider name="likelihood" value={likelihood} onChange={setLikelihood} />
      </div>

      {/* Save form */}
      <div className="border-t pt-4 space-y-3">
        <div>
          <label className="text-xs font-medium text-slate-600 block mb-1">Titel *</label>
          <input
            className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="z.B. Kinderarbeit bei Tier-2 Lieferant"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs font-medium text-slate-600 block mb-1">Kategorie</label>
          <select value={impactType} onChange={(e) => setImpactType(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500">
            {Object.entries(IMPACT_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-slate-600 block mb-1">Begründung</label>
          <textarea rows={2} className="w-full border rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            value={justification} onChange={(e) => setJustification(e.target.value)} />
        </div>
        <button
          onClick={() => {
            if (title.trim()) {
              onSave({ gravity, scope, remediability, likelihood }, title.trim(), impactType, justification);
              setTitle(""); setJustification("");
            }
          }}
          disabled={!title.trim()}
          className="w-full py-2 bg-blue-600 text-white text-sm rounded-xl hover:bg-blue-700 disabled:opacity-40"
        >
          Bewertung speichern
        </button>
      </div>
    </div>
  );
}

// ── Assessment row ────────────────────────────────────────────────────────────

function AssessmentRow({
  assessment, onDelete,
}: { assessment: ImpactAssessment; onDelete: () => void }) {
  const cfg = SEVERITY_CONFIG[assessment.severity_level] ?? SEVERITY_CONFIG.low;
  return (
    <tr className="hover:bg-slate-50 text-sm">
      <td className="px-4 py-3">
        <p className="font-medium text-slate-800 truncate max-w-xs">{assessment.title}</p>
        <p className="text-xs text-slate-400">{IMPACT_TYPES[assessment.impact_type] || assessment.impact_type}</p>
      </td>
      <td className="px-4 py-3">
        <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${cfg.badge}`}>{cfg.label}</span>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div className={`h-1.5 ${cfg.bg} rounded-full`}
              style={{ width: `${assessment.severity_score * 10}%` }} />
          </div>
          <span className={`text-xs font-bold ${cfg.color}`}>{assessment.severity_score.toFixed(1)}</span>
        </div>
      </td>
      <td className="px-4 py-3 text-xs text-slate-600">
        G:{assessment.gravity} S:{assessment.scope} I:{assessment.remediability} W:{assessment.likelihood}
      </td>
      <td className="px-4 py-3 text-xs font-medium text-slate-700">{assessment.priority_score.toFixed(1)}</td>
      <td className="px-4 py-3">
        <button onClick={onDelete} className="text-slate-300 hover:text-red-500">
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </td>
    </tr>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

type Tab = "calculator" | "list" | "dashboard";

export default function ImpactAssessmentPage() {
  const { t } = useLanguage();
  const [tab, setTab] = useState<Tab>("calculator");
  const [levelFilter, setLevelFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const qc = useQueryClient();

  const { data: dashboard } = useQuery({
    queryKey: ["impact-dashboard"],
    queryFn: getImpactDashboard,
  });

  const { data: assessments = [], isLoading } = useQuery({
    queryKey: ["impact-list", levelFilter, typeFilter],
    queryFn: () => listAssessments({
      severity_level: levelFilter || undefined,
      impact_type: typeFilter || undefined,
    }),
    enabled: tab === "list",
  });

  const createMutation = useMutation({
    mutationFn: createAssessment,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["impact-list"] });
      qc.invalidateQueries({ queryKey: ["impact-dashboard"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAssessment,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["impact-list"] });
      qc.invalidateQueries({ queryKey: ["impact-dashboard"] });
    },
  });

  function handleSave(
    dims: { gravity: number; scope: number; remediability: number; likelihood: number },
    title: string, impact_type: string, justification: string
  ) {
    createMutation.mutate({
      title,
      impact_type,
      entity_type: "standalone",
      ...dims,
      justification: justification || null,
    });
    setTab("list");
  }

  const TABS: { id: Tab; label: string }[] = [
    { id: "calculator", label: t("impactAssess.tabCalc") },
    { id: "list", label: t("impactAssess.tabList") },
    { id: "dashboard", label: t("impactAssess.tabDashboard") },
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Zap className="w-7 h-7 text-orange-500" />
        <div>
          <h1 className="text-2xl font-bold text-slate-800">{t("impactAssess.title")}</h1>
          <p className="text-sm text-slate-500">{t("impactAssess.subtitle")}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b">
        {TABS.map((tabItem) => (
          <button key={tabItem.id} onClick={() => setTab(tabItem.id)}
            className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${tab === tabItem.id ? "border-blue-600 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700"}`}>
            {tabItem.label}
          </button>
        ))}
      </div>

      {/* ── Calculator ─────────────────────────────────────────────────────── */}
      {tab === "calculator" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <LiveCalculator onSave={handleSave} />
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 space-y-2">
              <p className="text-sm font-semibold text-blue-800">OECD RBC Formel</p>
              <p className="text-xs text-blue-700 font-mono">
                Schwere = (Gravity×0.4 + Scope×0.3 + Irremediability×0.3 − 1) / 4 × 10
              </p>
              <p className="text-xs text-blue-700 font-mono">
                Priorität = Schwere × (Likelihood / 5)
              </p>
            </div>
            <div className="bg-white border rounded-xl p-4 space-y-3">
              <p className="text-sm font-semibold text-slate-700">Schwere-Level</p>
              {Object.entries(SEVERITY_CONFIG).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${v.badge}`}>{v.label}</span>
                  <span className="text-xs text-slate-500">
                    {k === "critical" ? "≥ 8.0" : k === "high" ? "≥ 6.0" : k === "medium" ? "≥ 3.0" : "< 3.0"}
                  </span>
                </div>
              ))}
            </div>
            {createMutation.isSuccess && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-sm text-emerald-700">
                Bewertung gespeichert ✓
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── List ───────────────────────────────────────────────────────────── */}
      {tab === "list" && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <select value={levelFilter} onChange={(e) => setLevelFilter(e.target.value)}
              className="border rounded-lg px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Alle Level</option>
              {Object.entries(SEVERITY_CONFIG).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}
              className="border rounded-lg px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Alle Kategorien</option>
              {Object.entries(IMPACT_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>

          {isLoading ? (
            <p className="text-sm text-slate-500">Wird geladen…</p>
          ) : assessments.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <BarChart2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Keine Bewertungen vorhanden</p>
            </div>
          ) : (
            <div className="bg-white border rounded-xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-3 text-left">Impact</th>
                    <th className="px-4 py-3 text-left">Level</th>
                    <th className="px-4 py-3 text-left">Schwere</th>
                    <th className="px-4 py-3 text-left">Dimensionen</th>
                    <th className="px-4 py-3 text-left">Priorität</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {assessments.map((a) => (
                    <AssessmentRow key={a.id} assessment={a}
                      onDelete={() => {
                        if (confirm("Bewertung löschen?")) deleteMutation.mutate(a.id);
                      }}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Dashboard ──────────────────────────────────────────────────────── */}
      {tab === "dashboard" && dashboard && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="col-span-1 bg-white border rounded-xl p-4">
              <p className="text-2xl font-bold text-slate-800">{dashboard.total}</p>
              <p className="text-xs text-slate-500">Gesamt</p>
            </div>
            {Object.entries(SEVERITY_CONFIG).map(([level, cfg]) => (
              <div key={level} className="bg-white border rounded-xl p-4">
                <p className={`text-2xl font-bold ${cfg.color}`}>
                  {dashboard[level as keyof typeof dashboard] as number}
                </p>
                <p className="text-xs text-slate-500">{cfg.label}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white border rounded-xl p-5">
              <p className="text-sm font-semibold text-slate-700 mb-3">Ø Schwere-Score</p>
              <ScoreMeter
                score={dashboard.avg_severity_score}
                level={
                  dashboard.avg_severity_score >= 8 ? "critical"
                  : dashboard.avg_severity_score >= 6 ? "high"
                  : dashboard.avg_severity_score >= 3 ? "medium"
                  : "low"
                }
              />
            </div>

            <div className="bg-white border rounded-xl p-5">
              <p className="text-sm font-semibold text-slate-700 mb-3">Nach Kategorie</p>
              <div className="space-y-2">
                {Object.entries(dashboard.by_type)
                  .filter(([, v]) => v > 0)
                  .sort(([, a], [, b]) => b - a)
                  .map(([type, count]) => (
                    <div key={type} className="flex items-center gap-2">
                      <span className="text-xs text-slate-500 w-40 truncate">
                        {IMPACT_TYPES[type] || type}
                      </span>
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full">
                        <div className="h-1.5 bg-blue-500 rounded-full"
                          style={{ width: `${(count / dashboard.total) * 100}%` }} />
                      </div>
                      <span className="text-xs font-medium text-slate-600 w-4">{count}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>

          {dashboard.top5_priority.length > 0 && (
            <div className="bg-white border rounded-xl overflow-hidden">
              <div className="px-5 py-3 border-b bg-slate-50">
                <p className="text-sm font-semibold text-slate-700">Top 5 nach Priorität</p>
              </div>
              <div className="divide-y">
                {dashboard.top5_priority.map((a, i) => {
                  const cfg = SEVERITY_CONFIG[a.severity_level as keyof typeof SEVERITY_CONFIG] ?? SEVERITY_CONFIG.low;
                  return (
                    <div key={a.id} className="px-5 py-3 flex items-center gap-4">
                      <span className="text-slate-300 text-sm font-bold w-4">{i + 1}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800 truncate">{a.title}</p>
                        <p className="text-xs text-slate-400">{IMPACT_TYPES[a.impact_type] || a.impact_type}</p>
                      </div>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${cfg.badge}`}>{cfg.label}</span>
                      <span className={`text-sm font-bold ${cfg.color} w-12 text-right`}>
                        {a.priority_score.toFixed(1)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
