"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  ArrowRight,
  ChevronDown,
  ChevronUp,
  Sparkles,
  TrendingDown,
  Zap,
} from "lucide-react";
import { getScoreSimulation } from "@/lib/api/assessments";
import type { ScoreSimulation } from "@/lib/api/assessments";
import { Spinner } from "@/components/ui/spinner";

const EFFORT_STYLES: Record<string, string> = {
  Low:    "bg-emerald-50 text-emerald-700 border-emerald-200",
  Medium: "bg-amber-50 text-amber-700 border-amber-200",
  High:   "bg-red-50 text-red-700 border-red-200",
};

const EFFORT_LABELS: Record<string, string> = {
  Low: "Aufwand: Niedrig",
  Medium: "Aufwand: Mittel",
  High: "Aufwand: Hoch",
};

function SimRow({ sim, assessmentId }: { sim: ScoreSimulation; assessmentId: string }) {
  const riskImprovement = Math.abs(sim.risk_score_delta);
  const esgImprovement = sim.esg_delta;
  const effortCls = EFFORT_STYLES[sim.effort] ?? EFFORT_STYLES.Medium;

  // Quick-win highlight: high impact, low effort
  const isQuickWin = sim.effort === "Low" || (sim.effort === "Medium" && riskImprovement >= 10);

  return (
    <div className={`rounded-lg border p-3 space-y-2 ${
      isQuickWin ? "border-emerald-200 bg-emerald-50/40" : "border-border bg-card"
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            {isQuickWin && (
              <span className="inline-flex items-center gap-0.5 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">
                <Zap className="h-2.5 w-2.5" /> Quick Win
              </span>
            )}
            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${effortCls}`}>
              {EFFORT_LABELS[sim.effort]}
            </span>
            <span className="text-[10px] text-muted-foreground">{sim.items_affected} Element(e)</span>
          </div>
          <p className="text-sm text-muted-foreground">{sim.scenario}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-xs text-muted-foreground">Risiko-Score</p>
          <p className="text-lg font-bold text-emerald-600">−{riskImprovement.toFixed(1)}</p>
          {esgImprovement > 0 && (
            <p className="text-[10px] text-blue-600">ESG +{esgImprovement.toFixed(1)}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 pt-1 border-t border-border/60">
        <TrendingDown className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
        <div className="flex-1 text-xs text-muted-foreground">
          Score: {sim.simulated_risk_score.toFixed(1)} <span className="text-emerald-600 font-medium">(aktuell − {riskImprovement.toFixed(1)})</span>
        </div>
        {sim.action_href && (
          <Link
            href={sim.action_href}
            className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-blue-700 transition-colors"
          >
            {sim.action_label} <ArrowRight className="h-3 w-3" />
          </Link>
        )}
      </div>
    </div>
  );
}

export function ScoreSimulationPanel({ assessmentId }: { assessmentId: string }) {
  const [open, setOpen] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["score-simulation", assessmentId],
    queryFn: () => getScoreSimulation(assessmentId),
    enabled: open,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const hasSimulations = data && data.simulations.length > 0;

  return (
    <div className="rounded-xl border border-border bg-muted/20 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted/40 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-violet-500" />
          <span className="text-sm font-semibold">Score verbessern — Was-wäre-wenn Simulation</span>
          {data && hasSimulations && (
            <span className="ml-2 rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold text-violet-700">
              {data.simulations.length} Szenarien
            </span>
          )}
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>

      {open && (
        <div className="border-t border-border px-4 pb-4 pt-3">
          {isLoading && (
            <div className="flex justify-center py-6">
              <Spinner />
            </div>
          )}
          {isError && (
            <p className="text-sm text-muted-foreground text-center py-4">Simulation konnte nicht geladen werden.</p>
          )}
          {data && !hasSimulations && (
            <div className="py-6 text-center">
              <p className="text-sm font-semibold text-emerald-600">Optimaler Status erreicht!</p>
              <p className="text-xs text-muted-foreground mt-1">Keine weiteren Verbesserungsszenarien identifiziert.</p>
            </div>
          )}
          {data && hasSimulations && (
            <div className="space-y-3">
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs text-muted-foreground">
                  Aktueller Risiko-Score: <span className="font-semibold text-foreground">{data.current_risk_score.toFixed(1)}</span>
                  {" "}({data.current_risk_band})
                  {" · "}ESG: <span className="font-semibold text-foreground">{data.current_esg_total.toFixed(1)}</span>
                </div>
              </div>
              {data.simulations.map((sim, idx) => (
                <SimRow key={idx} sim={sim} assessmentId={assessmentId} />
              ))}
              <p className="text-[10px] text-muted-foreground mt-2 italic">
                Alle Simulationen sind deterministisch berechnet. Werte zeigen isolierten Effekt pro Szenario.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
