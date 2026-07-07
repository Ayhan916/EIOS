"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import {
  Shield, RefreshCw, AlertTriangle, CheckCircle, Clock,
  TrendingUp, ChevronDown, ChevronUp, BarChart2,
} from "lucide-react";
import {
  computeScore, getLatestScore, getScoreHistory,
  type ReadinessSnapshot, type ArticleScore,
} from "@/lib/api/readiness";

// ── Level config ──────────────────────────────────────────────────────────────

const LEVEL_CONFIG = {
  not_ready:   { label: "Nicht bereit",     color: "text-red-600",    bg: "bg-red-500",    ring: "ring-red-200"    },
  partial:     { label: "Teilweise bereit", color: "text-amber-600",  bg: "bg-amber-500",  ring: "ring-amber-200"  },
  ready:       { label: "Bereit",           color: "text-emerald-600",bg: "bg-emerald-500",ring: "ring-emerald-200" },
  fully_ready: { label: "Vollständig",      color: "text-blue-600",   bg: "bg-blue-500",   ring: "ring-blue-200"   },
};

// ── Score ring ─────────────────────────────────────────────────────────────────

function ScoreRing({ pct, level }: { pct: number; level: string }) {
  const cfg = LEVEL_CONFIG[level as keyof typeof LEVEL_CONFIG] ?? LEVEL_CONFIG.not_ready;
  const R = 54;
  const circ = 2 * Math.PI * R;
  const dash = (pct / 100) * circ;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={140} height={140}>
        <circle cx={70} cy={70} r={R} fill="none" stroke="#e2e8f0" strokeWidth={10} />
        <circle
          cx={70} cy={70} r={R} fill="none"
          stroke={cfg.bg.replace("bg-", "").includes("500") ? undefined : "#3b82f6"}
          className={cfg.bg.replace("bg-", "stroke-")}
          strokeWidth={10}
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeDashoffset={circ / 4}
          strokeLinecap="round"
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
      </svg>
      <div className="absolute text-center">
        <p className={`text-3xl font-bold ${cfg.color}`}>{pct}%</p>
        <p className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</p>
      </div>
    </div>
  );
}

// ── Article score card ────────────────────────────────────────────────────────

function ArticleCard({ score }: { score: ArticleScore }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = LEVEL_CONFIG[score.level as keyof typeof LEVEL_CONFIG] ?? LEVEL_CONFIG.not_ready;

  return (
    <div className="bg-white border rounded-xl overflow-hidden">
      <div className="px-4 py-3 flex items-center justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-slate-400 shrink-0">{score.article}</span>
            <p className="text-sm font-medium text-slate-800 truncate">{score.title}</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-2 rounded-full transition-all ${cfg.bg}`}
                style={{ width: `${score.score_pct}%` }}
              />
            </div>
            <span className={`text-xs font-semibold ${cfg.color} w-12 text-right`}>
              {score.earned_points}/{score.max_points}
            </span>
          </div>
        </div>
        {score.gaps.length > 0 && (
          <button onClick={() => setExpanded(!expanded)}
            className="shrink-0 text-slate-400 hover:text-slate-600">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        )}
        {score.gaps.length === 0 && (
          <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />
        )}
      </div>
      {expanded && score.gaps.length > 0 && (
        <div className="px-4 pb-3 space-y-1.5 border-t pt-2.5 bg-slate-50">
          {score.gaps.map((gap, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-slate-600">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
              <span>{gap}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── History mini-chart ────────────────────────────────────────────────────────

function HistoryChart({ history }: { history: { overall_score_pct: number; computed_at: string }[] }) {
  if (history.length < 2) return null;
  const sorted = [...history].reverse();
  const max = 100;
  const W = 360;
  const H = 80;
  const step = W / (sorted.length - 1);
  const pts = sorted.map((h, i) => `${i * step},${H - (h.overall_score_pct / max) * H}`).join(" ");

  return (
    <div className="bg-white border rounded-xl p-4">
      <p className="text-sm font-medium text-slate-700 mb-3">Score-Verlauf</p>
      <svg width={W} height={H} className="overflow-visible">
        <polyline points={pts} fill="none" stroke="#3b82f6" strokeWidth={2} strokeLinecap="round" />
        {sorted.map((h, i) => (
          <g key={i}>
            <circle cx={i * step} cy={H - (h.overall_score_pct / max) * H} r={3}
              fill="#3b82f6" />
          </g>
        ))}
      </svg>
      <div className="flex justify-between mt-1 text-xs text-slate-400">
        <span>{new Date(sorted[0].computed_at).toLocaleDateString("de-DE")}</span>
        <span>{new Date(sorted[sorted.length - 1].computed_at).toLocaleDateString("de-DE")}</span>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ReadinessPage() {
  const { t } = useLanguage();
  const [tab, setTab] = useState<"score" | "history">("score");
  const qc = useQueryClient();

  const { data: latest, isLoading, isError } = useQuery({
    queryKey: ["readiness-latest"],
    queryFn: getLatestScore,
    retry: false,
  });

  const { data: history = [] } = useQuery({
    queryKey: ["readiness-history"],
    queryFn: () => getScoreHistory(12),
    enabled: tab === "history",
  });

  const computeMutation = useMutation({
    mutationFn: computeScore,
    onSuccess: (data) => {
      qc.setQueryData(["readiness-latest"], data);
      qc.invalidateQueries({ queryKey: ["readiness-history"] });
    },
  });

  const snapshot: ReadinessSnapshot | null = computeMutation.data ?? latest ?? null;

  const totalGaps = snapshot
    ? snapshot.article_scores.reduce((sum, a) => sum + a.gaps.length, 0)
    : 0;

  const TABS = [
    { id: "score" as const, label: t("readiness.tabScore") },
    { id: "history" as const, label: t("readiness.tabHistory") },
  ];

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-7 h-7 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-slate-800">{t("readiness.title")}</h1>
            <p className="text-sm text-slate-500">{t("readiness.subtitle")}</p>
          </div>
        </div>
        <button
          onClick={() => computeMutation.mutate()}
          disabled={computeMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm rounded-xl hover:bg-blue-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${computeMutation.isPending ? "animate-spin" : ""}`} />
          {computeMutation.isPending ? t("readiness.computing") : t("readiness.compute")}
        </button>
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

      {/* ── Score tab ────────────────────────────────────────────────────── */}
      {tab === "score" && (
        <>
          {isLoading && !computeMutation.data && (
            <p className="text-sm text-slate-500 py-8 text-center">Wird geladen…</p>
          )}

          {(isError && !computeMutation.data) && (
            <div className="py-16 text-center space-y-4">
              <BarChart2 className="w-14 h-14 mx-auto text-slate-300" />
              <p className="text-slate-500 text-sm">Noch kein Score berechnet.</p>
              <button
                onClick={() => computeMutation.mutate()}
                disabled={computeMutation.isPending}
                className="px-5 py-2 bg-blue-600 text-white text-sm rounded-xl hover:bg-blue-700 disabled:opacity-50"
              >
                Ersten Score berechnen
              </button>
            </div>
          )}

          {snapshot && (
            <div className="space-y-6">
              {/* Score overview */}
              <div className="bg-white border rounded-2xl p-6 flex flex-col md:flex-row items-center gap-8">
                <ScoreRing pct={snapshot.overall_score_pct} level={snapshot.overall_level} />
                <div className="flex-1 space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-slate-50 rounded-xl p-3">
                      <p className="text-xl font-bold text-slate-800">
                        {snapshot.article_scores.filter(a => a.score_pct >= 80).length}
                        <span className="text-sm font-normal text-slate-400">/{snapshot.article_scores.length}</span>
                      </p>
                      <p className="text-xs text-slate-500">{t("readiness.articleReady")}</p>
                    </div>
                    <div className="bg-slate-50 rounded-xl p-3">
                      <p className={`text-xl font-bold ${totalGaps > 0 ? "text-amber-600" : "text-emerald-600"}`}>
                        {totalGaps}
                      </p>
                      <p className="text-xs text-slate-500">{t("readiness.openGaps")}</p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400">
                    Berechnet {new Date(snapshot.computed_at).toLocaleString("de-DE")}
                    {snapshot.computed_by ? ` · ${snapshot.computed_by}` : ""}
                  </p>
                  {snapshot.overall_score_pct < 80 && (
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                      <p className="text-xs text-amber-800">
                        Score unter 80% — CSDDD-Compliance nicht vollständig nachweisbar.
                        Bitte offene Lücken schließen.
                      </p>
                    </div>
                  )}
                  {snapshot.overall_score_pct >= 100 && (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-emerald-600" />
                      <p className="text-xs text-emerald-800 font-medium">
                        Vollständige CSDDD-Compliance nachgewiesen.
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Per-article cards */}
              <div className="space-y-3">
                <h2 className="text-sm font-semibold text-slate-700">Score nach Artikel</h2>
                {snapshot.article_scores.map((a) => (
                  <ArticleCard key={a.article} score={a} />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* ── History tab ──────────────────────────────────────────────────── */}
      {tab === "history" && (
        <div className="space-y-4">
          {history.length === 0 ? (
            <p className="text-sm text-slate-500 py-8 text-center">Kein Verlauf vorhanden</p>
          ) : (
            <>
              <HistoryChart history={history} />
              <div className="bg-white border rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
                    <tr>
                      <th className="px-4 py-3 text-left">Datum</th>
                      <th className="px-4 py-3 text-left">Score</th>
                      <th className="px-4 py-3 text-left">Status</th>
                      <th className="px-4 py-3 text-left">Berechnet von</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {history.map((h) => {
                      const cfg = LEVEL_CONFIG[h.overall_level as keyof typeof LEVEL_CONFIG] ?? LEVEL_CONFIG.not_ready;
                      return (
                        <tr key={h.id} className="hover:bg-slate-50">
                          <td className="px-4 py-3 text-slate-600">
                            {new Date(h.computed_at).toLocaleString("de-DE")}
                          </td>
                          <td className="px-4 py-3 font-bold">
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                <div className={`h-1.5 ${cfg.bg} rounded-full`}
                                  style={{ width: `${h.overall_score_pct}%` }} />
                              </div>
                              <span className={cfg.color}>{h.overall_score_pct}%</span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
                          </td>
                          <td className="px-4 py-3 text-slate-400 text-xs">{h.computed_by ?? "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
