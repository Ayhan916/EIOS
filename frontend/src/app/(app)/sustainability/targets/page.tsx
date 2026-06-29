"use client";

import { useQuery } from "@tanstack/react-query";
import { Target } from "lucide-react";
import { listAllTargets, type ESGTarget } from "@/lib/api/sustainability";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

const ORG_ID = "default";

function progressColor(pct: number) {
  if (pct >= 80) return "bg-emerald-500";
  if (pct >= 40) return "bg-amber-500";
  return "bg-red-500";
}

function TargetRow({ t }: { t: ESGTarget }) {
  const pct = Math.min(100, Math.max(0, t.progress_percent));
  return (
    <div className="rounded-lg border p-4 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium truncate">{t.metric_name}</p>
          <p className="text-xs text-muted-foreground">{t.measurement_frequency}</p>
        </div>
        <span className="shrink-0 text-sm font-bold tabular-nums">
          {pct.toFixed(1)}%
        </span>
      </div>

      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full ${progressColor(pct)}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs text-center">
        <div className="rounded bg-muted p-1.5">
          <p className="text-muted-foreground">Baseline</p>
          <p className="font-semibold">{t.baseline_value.toLocaleString()}{t.target_unit ? ` ${t.target_unit}` : ""}</p>
        </div>
        <div className="rounded bg-muted p-1.5">
          <p className="text-muted-foreground">Current</p>
          <p className="font-semibold">
            {t.current_value != null ? `${t.current_value.toLocaleString()}${t.target_unit ? ` ${t.target_unit}` : ""}` : "—"}
          </p>
        </div>
        <div className="rounded bg-blue-50 p-1.5">
          <p className="text-muted-foreground">Target</p>
          <p className="font-semibold text-blue-700">{t.target_value.toLocaleString()}{t.target_unit ? ` ${t.target_unit}` : ""}</p>
        </div>
      </div>

      {t.target_date && (
        <p className="text-xs text-muted-foreground">
          Due {new Date(t.target_date).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}

export default function TargetsPage() {
  const { data: targets, isLoading } = useQuery({
    queryKey: ["all-targets", ORG_ID],
    queryFn: () => listAllTargets(ORG_ID),
  });

  const onTrack = targets?.filter((t) => t.progress_percent >= 80).length ?? 0;
  const atRisk = targets?.filter((t) => t.progress_percent < 40).length ?? 0;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Sustainability Targets</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Quantitative ESG targets with baseline, current, and goal values.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Total Targets</p>
            <p className="text-2xl font-bold">{targets?.length ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">On Track (&ge;80%)</p>
            <p className="text-2xl font-bold text-emerald-600">{onTrack}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">At Risk (&lt;40%)</p>
            <p className="text-2xl font-bold text-red-600">{atRisk}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Target className="h-4 w-4" />
            Targets{targets ? ` (${targets.length})` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <Spinner />}
          {targets?.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No targets yet. Create targets via objectives.
            </p>
          )}
          <div className="space-y-3">
            {targets?.map((t) => <TargetRow key={t.id} t={t} />)}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
