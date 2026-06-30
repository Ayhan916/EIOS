"use client";

import { useQuery } from "@tanstack/react-query";
import { Globe } from "lucide-react";
import { listRoadmaps, type NetZeroRoadmap } from "@/lib/api/sustainability";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useLanguage } from "@/lib/i18n/context";

const ORG_ID = "default";

function statusColor(s: string) {
  switch (s) {
    case "ACTIVE":    return "bg-blue-100 text-blue-800";
    case "COMPLETED": return "bg-emerald-100 text-emerald-800";
    default:          return "bg-slate-100 text-slate-600";
  }
}

function statusBarColor(s: string) {
  switch (s) {
    case "ACTIVE":    return "bg-blue-400";
    case "COMPLETED": return "bg-emerald-500";
    default:          return "bg-slate-300";
  }
}

// ── #60 Gantt Timeline ────────────────────────────────────────────────────────

function GanttTimeline({ roadmaps }: { roadmaps: NetZeroRoadmap[] }) {
  const { t } = useLanguage();
  if (roadmaps.length === 0) return null;

  const currentYear = new Date().getFullYear();
  const minYear = Math.min(...roadmaps.map((r) => r.baseline_year));
  const maxYear = Math.max(...roadmaps.map((r) => r.target_year));
  const span = maxYear - minYear || 1;

  function pct(year: number) {
    return Math.max(0, Math.min(100, ((year - minYear) / span) * 100));
  }

  const currentPct = pct(currentYear);

  // Year tick marks (every 5 or 10 years depending on span)
  const tickStep = span <= 20 ? 5 : 10;
  const firstTick = Math.ceil(minYear / tickStep) * tickStep;
  const ticks: number[] = [];
  for (let y = firstTick; y <= maxYear; y += tickStep) ticks.push(y);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Globe className="h-4 w-4 text-emerald-600" />
          Roadmap Timeline — {minYear} to {maxYear}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Year axis */}
          <div className="relative h-5 ml-40">
            {ticks.map((y) => (
              <div
                key={y}
                className="absolute flex flex-col items-center"
                style={{ left: `${pct(y)}%` }}
              >
                <div className="h-2 w-px bg-border" />
                <span className="text-[10px] text-muted-foreground">{y}</span>
              </div>
            ))}
          </div>

          {/* Gantt rows */}
          <div className="space-y-2">
            {roadmaps.map((rm) => {
              const leftPct = pct(rm.baseline_year);
              const widthPct = pct(rm.target_year) - leftPct;
              const reduction = rm.target_reduction_percent;
              return (
                <div key={rm.id} className="flex items-center gap-3">
                  {/* Label */}
                  <div className="w-40 flex-shrink-0 text-right pr-2">
                    <p className="text-xs font-medium truncate" title={rm.name}>{rm.name}</p>
                    <p className="text-[10px] text-muted-foreground">{rm.baseline_year}–{rm.target_year}</p>
                  </div>
                  {/* Bar track */}
                  <div className="relative flex-1 h-7 rounded bg-muted overflow-hidden">
                    {/* Roadmap bar */}
                    <div
                      className={`absolute top-1 bottom-1 rounded ${statusBarColor(rm.roadmap_status)} flex items-center px-2 overflow-hidden`}
                      style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                    >
                      <span className="text-[10px] font-semibold text-white whitespace-nowrap truncate">
                        −{reduction}%
                      </span>
                    </div>
                    {/* Current year marker */}
                    {currentPct >= 0 && currentPct <= 100 && (
                      <div
                        className="absolute top-0 bottom-0 w-px bg-red-500/80 z-10"
                        style={{ left: `${currentPct}%` }}
                        title={`Now (${currentYear})`}
                      />
                    )}
                  </div>
                  {/* Status badge */}
                  <span className={`flex-shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${statusColor(rm.roadmap_status)}`}>
                    {rm.roadmap_status}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 pt-1 text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1"><span className="inline-block h-2 w-4 rounded bg-blue-400" /> {t("common.active")}</span>
            <span className="flex items-center gap-1"><span className="inline-block h-2 w-4 rounded bg-emerald-500" /> Completed</span>
            <span className="flex items-center gap-1"><span className="inline-block h-3 w-px bg-red-500" /> Today</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Roadmap detail card ───────────────────────────────────────────────────────

function RoadmapCard({ rm }: { rm: NetZeroRoadmap }) {
  const yearsTotal = rm.target_year - rm.baseline_year;
  const yearsPassed = Math.max(0, new Date().getFullYear() - rm.baseline_year);
  const timePct = yearsTotal > 0 ? Math.min(100, (yearsPassed / yearsTotal) * 100) : 0;

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold">{rm.name}</p>
          <p className="text-xs text-muted-foreground">
            {rm.baseline_year} → {rm.target_year}
          </p>
        </div>
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${statusColor(rm.roadmap_status)}`}>
          {rm.roadmap_status}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <div className="rounded bg-muted p-2">
          <p className="text-muted-foreground">Baseline</p>
          <p className="font-bold">{rm.baseline_emissions.toLocaleString()} tCO₂e</p>
        </div>
        <div className="rounded bg-muted p-2">
          <p className="text-muted-foreground">Target</p>
          <p className="font-bold">{rm.target_emissions.toLocaleString()} tCO₂e</p>
        </div>
        <div className="rounded bg-emerald-50 p-2">
          <p className="text-muted-foreground">Reduction</p>
          <p className="font-bold text-emerald-700">{rm.target_reduction_percent}%</p>
        </div>
      </div>

      <div>
        <div className="flex justify-between text-xs text-muted-foreground mb-1">
          <span>Timeline progress</span>
          <span>{timePct.toFixed(0)}% of years elapsed</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-blue-500"
            style={{ width: `${timePct}%` }}
          />
        </div>
      </div>
    </div>
  );
}

export default function RoadmapsPage() {
  const { t } = useLanguage();
  const { data: roadmaps, isLoading } = useQuery({
    queryKey: ["roadmaps", ORG_ID],
    queryFn: () => listRoadmaps(ORG_ID),
  });

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Net Zero Roadmaps</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Long-term decarbonization trajectories with yearly milestones and science-based targets
        </p>
      </div>

      {isLoading && (
        <div className="flex justify-center py-12"><Spinner /></div>
      )}

      {/* #60 Gantt-style timeline */}
      {(roadmaps ?? []).length > 0 && (
        <GanttTimeline roadmaps={roadmaps!} />
      )}

      {/* Roadmap detail cards */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Globe className="h-4 w-4 text-emerald-600" />
            {t("sustain.roadmapsTitle")}{roadmaps ? ` (${roadmaps.length})` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!isLoading && (roadmaps ?? []).length === 0 && (
            <p className="text-sm text-muted-foreground">
              {t("sustain.noRoadmaps")} {t("sustain.noRoadmapsDesc")}
            </p>
          )}
          <div className="space-y-4">
            {roadmaps?.map((rm) => <RoadmapCard key={rm.id} rm={rm} />)}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
