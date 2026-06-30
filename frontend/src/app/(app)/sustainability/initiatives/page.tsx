"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Link2, Loader2, TrendingDown } from "lucide-react";
import { listInitiatives, listKPIs, updateInitiativeProgress, type DecarbonizationInitiative, type ESGKPI } from "@/lib/api/sustainability";
import { useAuth } from "@/lib/auth/context";
import apiClient from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useLanguage } from "@/lib/i18n/context";

const STATUSES = ["PLANNED", "IN_PROGRESS", "COMPLETED", "CANCELLED"] as const;

function statusColor(s: string) {
  switch (s) {
    case "IN_PROGRESS": return "bg-blue-100 text-blue-800";
    case "COMPLETED":   return "bg-emerald-100 text-emerald-800";
    case "CANCELLED":   return "bg-red-100 text-red-800";
    default:            return "bg-slate-100 text-slate-600";
  }
}

function typeLabel(t: string) {
  return t.replace(/_/g, " ");
}

function InitiativeCard({ init, orgId, kpis }: { init: DecarbonizationInitiative; orgId: string; kpis: ESGKPI[] }) {
  const qc = useQueryClient();
  const { t } = useLanguage();
  const [open, setOpen] = useState(false);
  const [showKpiLink, setShowKpiLink] = useState(false);
  const [linkedKpiId, setLinkedKpiId] = useState("");
  const [actualReduction, setActualReduction] = useState(
    init.actual_reduction != null ? String(init.actual_reduction) : ""
  );
  const [newStatus, setNewStatus] = useState(init.initiative_status);

  const pct =
    init.actual_reduction != null && init.expected_reduction > 0
      ? Math.min(100, (init.actual_reduction / init.expected_reduction) * 100)
      : 0;

  const mutation = useMutation({
    mutationFn: () =>
      updateInitiativeProgress(orgId, init.id, {
        actual_reduction: parseFloat(actualReduction) || 0,
        status: newStatus,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["initiatives", orgId] });
      setOpen(false);
    },
  });

  return (
    <div className="rounded-lg border p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-medium text-sm">{init.name}</p>
          <p className="text-xs text-muted-foreground">{typeLabel(init.initiative_type)}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`rounded px-2 py-0.5 text-xs font-medium ${statusColor(init.initiative_status)}`}>
            {init.initiative_status.replace(/_/g, " ")}
          </span>
          <button
            onClick={() => { setShowKpiLink((v) => !v); setOpen(false); }}
            className="text-xs text-violet-600 hover:underline flex items-center gap-0.5"
            title="Link to KPI"
          >
            <Link2 className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setOpen((v) => !v)}
            className="text-xs text-blue-600 hover:underline flex items-center gap-0.5"
          >
            {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            Log Progress
          </button>
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Expected reduction: {init.expected_reduction.toLocaleString()} tCO₂e</span>
          {init.actual_reduction != null && (
            <span>Actual: {init.actual_reduction.toLocaleString()} tCO₂e</span>
          )}
        </div>
        <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-emerald-500 transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="text-xs text-right text-muted-foreground">{pct.toFixed(0)}% achieved</p>
      </div>

      {showKpiLink && (
        <div className="mt-3 rounded-md border border-violet-100 bg-violet-50 p-3 space-y-2">
          <p className="text-xs font-semibold text-violet-800">Link to KPI</p>
          <div className="flex gap-2">
            <select
              className="flex-1 h-8 rounded border border-input bg-background px-2 text-xs"
              value={linkedKpiId}
              onChange={(e) => setLinkedKpiId(e.target.value)}
            >
              <option value="">Select a KPI…</option>
              {kpis.map((k) => (
                <option key={k.id} value={k.id}>{k.name}</option>
              ))}
            </select>
            <Button
              size="sm"
              className="h-8 text-xs bg-violet-600 hover:bg-violet-700"
              disabled={!linkedKpiId}
              onClick={async () => {
                await apiClient.patch(`/api/v1/sustainability/${orgId}/initiatives/${init.id}`, { linked_kpi_id: linkedKpiId });
                qc.invalidateQueries({ queryKey: ["initiatives", orgId] });
                setShowKpiLink(false);
              }}
            >
              Link
            </Button>
            <button onClick={() => setShowKpiLink(false)} className="text-xs text-muted-foreground hover:underline">{t("common.cancel")}</button>
          </div>
        </div>
      )}

      {open && (
        <div className="mt-3 rounded-md border border-blue-100 bg-blue-50 p-3 space-y-3">
          <p className="text-xs font-semibold text-blue-800">Log Progress Update</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Actual Reduction (tCO₂e)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={actualReduction}
                onChange={(e) => setActualReduction(e.target.value)}
                placeholder={`Max ${init.expected_reduction}`}
                className="h-8 w-full rounded border border-input bg-white px-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">{t("common.status")}</label>
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
                className="h-8 w-full rounded border border-input bg-white px-2 text-sm"
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              className="bg-emerald-600 hover:bg-emerald-700 text-white h-7 px-3 text-xs"
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending || !actualReduction}
            >
              {mutation.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
              Save Progress
            </Button>
            <button onClick={() => setOpen(false)} className="text-xs text-muted-foreground hover:underline">
              {t("common.cancel")}
            </button>
            {mutation.isError && (
              <span className="text-xs text-red-600">
                {(mutation.error as Error).message}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function GanttTimeline({ initiatives }: { initiatives: DecarbonizationInitiative[] }) {
  const withDates = initiatives.filter((i) => i.start_date && i.end_date);
  if (withDates.length === 0) return null;

  const allDates = withDates.flatMap((i) => [new Date(i.start_date!).getTime(), new Date(i.end_date!).getTime()]);
  const minTs = Math.min(...allDates);
  const maxTs = Math.max(...allDates);
  const span = maxTs - minTs || 1;

  const statusColors: Record<string, string> = {
    PLANNED: "bg-slate-300",
    IN_PROGRESS: "bg-blue-500",
    COMPLETED: "bg-emerald-500",
    CANCELLED: "bg-red-300",
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Initiative Timeline</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {withDates.map((init) => {
            const start = new Date(init.start_date!).getTime();
            const end = new Date(init.end_date!).getTime();
            const left = ((start - minTs) / span) * 100;
            const width = Math.max(((end - start) / span) * 100, 2);
            return (
              <div key={init.id} className="flex items-center gap-3">
                <p className="w-36 truncate text-xs text-muted-foreground">{init.name}</p>
                <div className="flex-1 relative h-5 rounded bg-muted">
                  <div
                    className={`absolute top-0.5 h-4 rounded ${statusColors[init.initiative_status] ?? "bg-slate-400"}`}
                    style={{ left: `${left}%`, width: `${width}%` }}
                    title={`${init.start_date} → ${init.end_date}`}
                  />
                </div>
              </div>
            );
          })}
        </div>
        <div className="mt-2 flex justify-between text-[10px] text-muted-foreground">
          <span>{new Date(minTs).getFullYear()}</span>
          <span>{new Date(maxTs).getFullYear()}</span>
        </div>
      </CardContent>
    </Card>
  );
}

export default function InitiativesPage() {
  const { user } = useAuth();
  const { t } = useLanguage();
  const orgId = user?.organization_id ?? "default";

  const { data: initiatives, isLoading } = useQuery({
    queryKey: ["initiatives", orgId],
    queryFn: () => listInitiatives(orgId),
  });

  const { data: kpis } = useQuery({
    queryKey: ["kpis", orgId],
    queryFn: () => listKPIs(orgId),
    staleTime: 300_000,
  });

  const byStatus = {
    PLANNED: initiatives?.filter((i) => i.initiative_status === "PLANNED") ?? [],
    IN_PROGRESS: initiatives?.filter((i) => i.initiative_status === "IN_PROGRESS") ?? [],
    COMPLETED: initiatives?.filter((i) => i.initiative_status === "COMPLETED") ?? [],
  };

  const totalExpected = initiatives?.reduce((s, i) => s + i.expected_reduction, 0) ?? 0;
  const totalActual = initiatives?.reduce((s, i) => s + (i.actual_reduction ?? 0), 0) ?? 0;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("sustain.initiativesTitle")}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {t("sustain.initiativesSubtitle")}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Planned", count: byStatus.PLANNED.length, color: "text-slate-600" },
          { label: "In Progress", count: byStatus.IN_PROGRESS.length, color: "text-blue-600" },
          { label: "Completed", count: byStatus.COMPLETED.length, color: "text-emerald-600" },
        ].map(({ label, count, color }) => (
          <Card key={label}>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">{label}</p>
              <p className={`text-2xl font-bold ${color}`}>{count}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {totalExpected > 0 && (
        <Card>
          <CardContent className="pt-4">
            <div className="flex justify-between text-sm mb-1">
              <span className="text-muted-foreground">Total Emission Reductions</span>
              <span className="font-medium">
                {totalActual.toLocaleString()} / {totalExpected.toLocaleString()} tCO₂e
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-emerald-500"
                style={{ width: `${Math.min(100, (totalActual / totalExpected) * 100)}%` }}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {initiatives && initiatives.length > 0 && (
        <GanttTimeline initiatives={initiatives} />
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingDown className="h-4 w-4 text-emerald-600" />
            All Initiatives{initiatives ? ` (${initiatives.length})` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <Spinner />}
          {initiatives?.length === 0 && (
            <p className="text-sm text-muted-foreground">{t("sustain.noInitiatives")}</p>
          )}
          <div className="space-y-3">
            {initiatives?.map((init) => (
              <InitiativeCard key={init.id} init={init} orgId={orgId} kpis={kpis ?? []} />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
