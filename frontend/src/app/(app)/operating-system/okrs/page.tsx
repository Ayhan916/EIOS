"use client";

import { useQuery } from "@tanstack/react-query";
import { Target, TrendingUp, AlertTriangle, CheckCircle2 } from "lucide-react";
import { listObjectives, listAllTargets, listKPIs, type ESGObjective, type ESGTarget, type ESGKPI } from "@/lib/api/sustainability";
import { useAuth } from "@/lib/auth/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

const STATUS_STYLES: Record<string, string> = {
  ON_TRACK:    "bg-emerald-100 text-emerald-700",
  AT_RISK:     "bg-amber-100 text-amber-700",
  BEHIND:      "bg-red-100 text-red-700",
  COMPLETED:   "bg-blue-100 text-blue-700",
  CANCELLED:   "bg-slate-100 text-slate-500",
  DRAFT:       "bg-slate-100 text-slate-600",
};

function progressColor(pct: number) {
  if (pct >= 80) return "bg-emerald-500";
  if (pct >= 50) return "bg-blue-500";
  if (pct >= 25) return "bg-amber-500";
  return "bg-red-400";
}

function ObjectiveCard({
  obj,
  targets,
  kpis,
}: {
  obj: ESGObjective;
  targets: ESGTarget[];
  kpis: ESGKPI[];
}) {
  const myTargets = targets.filter((t) => t.objective_id === obj.id);
  const avgProgress = myTargets.length > 0
    ? myTargets.reduce((s, t) => s + t.progress_percent, 0) / myTargets.length
    : null;

  const linkedKpis = kpis.filter((k) => k.category === obj.category);

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold truncate">{obj.title}</p>
          {obj.description && (
            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{obj.description}</p>
          )}
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">{obj.category}</span>
            {obj.target_date && (
              <span className="text-[10px] text-muted-foreground">
                Due {new Date(obj.target_date).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold whitespace-nowrap ${STATUS_STYLES[obj.objective_status] ?? "bg-slate-100 text-slate-600"}`}>
          {obj.objective_status}
        </span>
      </div>

      {/* Progress toward this objective */}
      {avgProgress != null ? (
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Overall Progress</span>
            <span className="font-semibold">{avgProgress.toFixed(0)}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${progressColor(avgProgress)}`}
              style={{ width: `${Math.min(avgProgress, 100)}%` }}
            />
          </div>
        </div>
      ) : (
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">No targets linked yet</p>
          <div className="h-2 w-full rounded-full bg-muted" />
        </div>
      )}

      {/* Key Results (targets) */}
      {myTargets.length > 0 && (
        <div className="space-y-2 pt-1">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Key Results</p>
          {myTargets.map((t) => (
            <div key={t.id} className="space-y-0.5">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground truncate max-w-xs">{t.metric_name}</span>
                <span className="font-medium ml-2">
                  {t.current_value != null ? t.current_value : "—"}
                  {t.target_unit ? ` ${t.target_unit}` : ""}
                  <span className="text-muted-foreground"> / {t.target_value}</span>
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className={`h-full rounded-full ${progressColor(t.progress_percent)}`}
                  style={{ width: `${Math.min(t.progress_percent, 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Linked KPIs by category */}
      {linkedKpis.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-1">
          <p className="w-full text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Related KPIs</p>
          {linkedKpis.slice(0, 3).map((k) => (
            <span key={k.id} className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[10px] text-blue-700">
              <TrendingUp className="h-3 w-3" />{k.name}
            </span>
          ))}
          {linkedKpis.length > 3 && (
            <span className="text-[10px] text-muted-foreground">+{linkedKpis.length - 3} more</span>
          )}
        </div>
      )}
    </div>
  );
}

export default function OKRsPage() {
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";

  const { data: objectives, isLoading: objLoading } = useQuery({
    queryKey: ["esg-objectives", orgId],
    queryFn: () => listObjectives(orgId),
  });

  const { data: targets } = useQuery({
    queryKey: ["esg-all-targets", orgId],
    queryFn: () => listAllTargets(orgId),
    staleTime: 120_000,
  });

  const { data: kpis } = useQuery({
    queryKey: ["esg-kpis", orgId],
    queryFn: () => listKPIs(orgId),
    staleTime: 300_000,
  });

  const objs = objectives ?? [];
  const allTargets = targets ?? [];
  const allKPIs = kpis ?? [];

  const onTrack = objs.filter((o) => o.objective_status === "ON_TRACK").length;
  const atRisk  = objs.filter((o) => o.objective_status === "AT_RISK" || o.objective_status === "BEHIND").length;
  const completed = objs.filter((o) => o.objective_status === "COMPLETED").length;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">ESG OKRs</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Objectives & Key Results — track ESG goals with measurable progress
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "On Track", value: onTrack, icon: CheckCircle2, color: "text-emerald-600" },
          { label: "At Risk", value: atRisk, icon: AlertTriangle, color: "text-amber-600" },
          { label: "Completed", value: completed, icon: Target, color: "text-blue-600" },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <CardContent className="pt-4 pb-3 flex items-center gap-3">
              <Icon className={`h-8 w-8 ${color}`} />
              <div>
                <p className="text-2xl font-bold">{value}</p>
                <p className="text-xs text-muted-foreground">{label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Objectives</CardTitle>
        </CardHeader>
        <CardContent>
          {objLoading && <Spinner />}
          {!objLoading && objs.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-10 text-center">
              <Target className="h-10 w-10 text-slate-300" />
              <p className="text-sm text-slate-600">No ESG objectives defined yet.</p>
              <p className="text-xs text-muted-foreground">Create objectives via the Sustainability module.</p>
            </div>
          )}
          <div className="space-y-4">
            {objs.map((obj) => (
              <ObjectiveCard key={obj.id} obj={obj} targets={allTargets} kpis={allKPIs} />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
