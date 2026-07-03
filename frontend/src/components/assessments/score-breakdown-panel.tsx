"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Leaf,
  Shield,
  TrendingDown,
  TrendingUp,
  Users,
  Info,
  Lightbulb,
  CheckCircle2,
} from "lucide-react";
import { getScoreBreakdown } from "@/lib/api/assessments";
import type { ScoreDriver, PillarScore, ImprovementHint } from "@/lib/api/assessments";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";

const IMPACT_COLOR: Record<string, string> = {
  high:   "text-red-600 bg-red-50 border-red-200",
  medium: "text-amber-600 bg-amber-50 border-amber-200",
  low:    "text-slate-600 bg-slate-50 border-slate-200",
};

const UNCERTAINTY_META: Record<string, { label: string; color: string; dot: string }> = {
  Low:    { label: "Niedrig",  color: "text-emerald-700 bg-emerald-50 border-emerald-200", dot: "bg-emerald-500" },
  Medium: { label: "Mittel",   color: "text-amber-700 bg-amber-50 border-amber-200",       dot: "bg-amber-500" },
  High:   { label: "Hoch",     color: "text-red-700 bg-red-50 border-red-200",             dot: "bg-red-500" },
};

const EFFORT_META: Record<string, string> = {
  Low:    "text-emerald-700 bg-emerald-50",
  Medium: "text-amber-700 bg-amber-50",
  High:   "text-red-700 bg-red-50",
};

const PILLAR_META: Record<string, { icon: React.ElementType; color: string; bar: string }> = {
  Environmental: { icon: Leaf,   color: "text-emerald-600", bar: "bg-emerald-500" },
  Social:        { icon: Users,  color: "text-blue-600",    bar: "bg-blue-500" },
  Governance:    { icon: Shield, color: "text-violet-600",  bar: "bg-violet-500" },
};

function DriverRow({ driver }: { driver: ScoreDriver }) {
  const cls = IMPACT_COLOR[driver.impact] ?? IMPACT_COLOR.low;
  return (
    <div className={`flex items-start justify-between gap-3 rounded-lg border px-3 py-2.5 ${cls}`}>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">{driver.factor}</p>
        <p className="mt-0.5 text-xs opacity-80">{driver.description}</p>
      </div>
      <div className="flex-shrink-0 text-right">
        <p className="text-sm font-bold">+{driver.score_contribution.toFixed(1)}</p>
        <p className="text-[10px] opacity-70">Risiko-Punkte</p>
      </div>
    </div>
  );
}

function PillarCard({ pillar }: { pillar: PillarScore }) {
  const meta = PILLAR_META[pillar.pillar];
  const Icon = meta?.icon ?? Shield;
  const total = pillar.critical + pillar.high + pillar.medium + pillar.low;
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`h-4 w-4 ${meta?.color}`} />
        <span className="text-sm font-semibold">{pillar.pillar}</span>
        <span className={`ml-auto text-sm font-bold ${
          pillar.score >= 70 ? "text-emerald-600" : pillar.score >= 40 ? "text-amber-600" : "text-red-600"
        }`}>
          {pillar.score.toFixed(0)}/100
        </span>
      </div>
      <Progress value={pillar.score} className="h-1.5 mb-2" />
      {total > 0 ? (
        <div className="flex gap-2 flex-wrap">
          {pillar.critical > 0 && <span className="text-[10px] rounded-full bg-red-100 text-red-700 px-2 py-0.5 font-semibold">{pillar.critical} Critical</span>}
          {pillar.high > 0    && <span className="text-[10px] rounded-full bg-orange-100 text-orange-700 px-2 py-0.5 font-semibold">{pillar.high} High</span>}
          {pillar.medium > 0  && <span className="text-[10px] rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 font-semibold">{pillar.medium} Medium</span>}
          {pillar.low > 0     && <span className="text-[10px] rounded-full bg-slate-100 text-slate-600 px-2 py-0.5 font-semibold">{pillar.low} Low</span>}
        </div>
      ) : (
        <p className="text-[10px] text-muted-foreground">Keine kategorisierten Findings</p>
      )}
    </div>
  );
}

function HintRow({ hint }: { hint: ImprovementHint }) {
  const effortCls = EFFORT_META[hint.effort] ?? EFFORT_META.Medium;
  return (
    <div className="flex items-start gap-3 rounded-lg border border-border bg-card px-3 py-2.5">
      <TrendingDown className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-sm">{hint.action}</p>
        <div className="mt-1.5 flex items-center gap-2">
          <span className="text-[10px] font-semibold text-emerald-700">
            -{hint.expected_risk_reduction.toFixed(1)} Risiko-Punkte
          </span>
          <span className={`text-[10px] rounded-full px-2 py-0.5 font-semibold ${effortCls}`}>
            Aufwand: {hint.effort}
          </span>
        </div>
      </div>
    </div>
  );
}

export function ScoreBreakdownPanel({ assessmentId }: { assessmentId: string }) {
  const [open, setOpen] = useState(false);
  const [showAssumptions, setShowAssumptions] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["score-breakdown", assessmentId],
    queryFn: () => getScoreBreakdown(assessmentId),
    enabled: open,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const uncertaintyMeta = data ? (UNCERTAINTY_META[data.uncertainty] ?? UNCERTAINTY_META.Medium) : null;

  return (
    <div className="rounded-xl border border-border bg-muted/20 overflow-hidden">
      {/* Toggle header */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted/40 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <Info className="h-4 w-4 text-blue-500" />
          <span className="text-sm font-semibold">Score-Erklärung — Warum dieser Score?</span>
          {data && (
            <span className={`ml-2 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${uncertaintyMeta?.color}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${uncertaintyMeta?.dot}`} />
              Unsicherheit: {uncertaintyMeta?.label}
            </span>
          )}
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>

      {open && (
        <div className="border-t border-border px-4 pb-4 pt-3 space-y-5">
          {isLoading && (
            <div className="flex justify-center py-6">
              <Spinner size="md" />
            </div>
          )}

          {isError && (
            <p className="text-sm text-muted-foreground text-center py-4">
              Score-Breakdown nicht verfügbar.
            </p>
          )}

          {data && (
            <>
              {/* Score Summary Row */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-lg border border-border bg-card p-3 text-center">
                  <p className="text-xs text-muted-foreground mb-1">Risk Score</p>
                  <p className={`text-xl font-bold ${
                    data.risk_score <= 25 ? "text-emerald-600" :
                    data.risk_score <= 50 ? "text-amber-600" :
                    data.risk_score <= 75 ? "text-orange-600" : "text-red-600"
                  }`}>{data.risk_score.toFixed(1)}</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">{data.risk_band}</p>
                </div>
                <div className="rounded-lg border border-border bg-card p-3 text-center">
                  <p className="text-xs text-muted-foreground mb-1">ESG Gesamt</p>
                  <p className={`text-xl font-bold ${
                    data.esg_total >= 70 ? "text-emerald-600" : data.esg_total >= 40 ? "text-amber-600" : "text-red-600"
                  }`}>{data.esg_total.toFixed(1)}</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">von 100</p>
                </div>
                <div className="rounded-lg border border-border bg-card p-3 text-center">
                  <p className="text-xs text-muted-foreground mb-1">Datenbasis</p>
                  <p className={`text-xl font-bold ${
                    data.data_completeness >= 75 ? "text-emerald-600" :
                    data.data_completeness >= 40 ? "text-amber-600" : "text-red-600"
                  }`}>{data.data_completeness}%</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">Vollständigkeit</p>
                </div>
                <div className="rounded-lg border border-border bg-card p-3 text-center">
                  <p className="text-xs text-muted-foreground mb-1">Methodik</p>
                  <p className="text-xs font-semibold mt-1">v{data.score_version}</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">deterministisch</p>
                </div>
              </div>

              {/* Uncertainty explanation */}
              <div className={`flex items-start gap-2 rounded-lg border px-3 py-2.5 ${uncertaintyMeta?.color}`}>
                <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs font-semibold">Unsicherheit: {uncertaintyMeta?.label}</p>
                  <p className="text-xs mt-0.5 opacity-80">{data.uncertainty_reason}</p>
                </div>
              </div>

              {/* Score Drivers */}
              {data.drivers.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                    Score-Treiber (Risk Score: {data.risk_score.toFixed(1)})
                  </p>
                  <div className="space-y-2">
                    {data.drivers.map((d) => <DriverRow key={d.factor} driver={d} />)}
                  </div>
                </div>
              )}

              {data.drivers.length === 0 && (
                <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-emerald-700">
                  <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
                  <p className="text-sm font-medium">Keine negativen Score-Treiber — Ausgezeichnete Datenlage!</p>
                </div>
              )}

              {/* ESG Pillars */}
              <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                  ESG-Pillar-Scores
                </p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  {data.pillars.map((p) => <PillarCard key={p.pillar} pillar={p} />)}
                </div>
              </div>

              {/* Improvement Hints */}
              {data.improvement_hints.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Lightbulb className="h-4 w-4 text-amber-500" />
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      Score verbessern — Quick Wins
                    </p>
                  </div>
                  <div className="space-y-2">
                    {data.improvement_hints.map((h, i) => <HintRow key={i} hint={h} />)}
                  </div>
                </div>
              )}

              {/* Assumptions */}
              <div>
                <button
                  onClick={() => setShowAssumptions((v) => !v)}
                  className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showAssumptions ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  Annahmen & Methodik anzeigen
                </button>
                {showAssumptions && (
                  <ul className="mt-2 space-y-1.5 pl-4">
                    {data.assumptions.map((a, i) => (
                      <li key={i} className="text-xs text-muted-foreground list-disc">{a}</li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
