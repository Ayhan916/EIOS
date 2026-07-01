"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import { CheckCircle2, Loader2, Lock, Plus, RefreshCw } from "lucide-react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import {
  listInventories,
  listEmissionSources,
  recalculateInventory,
  finalizeInventory,
  addEmissionSource,
  type CarbonInventory,
  type EmissionSource,
} from "@/lib/api/sustainability";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { CarbonStackedBarChart } from "@/components/charts/carbon-stacked-bar";
import type { CarbonDataPoint } from "@/components/charts/carbon-stacked-bar";

const ORG_ID = "default";
const CURRENT_YEAR = new Date().getFullYear();

function scopeColor(scope: string) {
  switch (scope) {
    case "SCOPE1": return "bg-red-100 text-red-800";
    case "SCOPE2": return "bg-orange-100 text-orange-800";
    case "SCOPE3": return "bg-amber-100 text-amber-800";
    default:       return "bg-slate-100 text-slate-600";
  }
}

function InventoryCard({ inv }: { inv: CarbonInventory }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const recalc = useMutation({
    mutationFn: () => recalculateInventory(ORG_ID, inv.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["inventories", ORG_ID] }),
  });
  const finalize = useMutation({
    mutationFn: () => finalizeInventory(ORG_ID, inv.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["inventories", ORG_ID] }),
  });

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-semibold">Year {inv.reporting_year}</p>
          <p className="text-xs text-muted-foreground">{inv.unit}</p>
        </div>
        <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${
          inv.inventory_status === "FINALIZED"
            ? "bg-emerald-100 text-emerald-800"
            : "bg-slate-100 text-slate-600"
        }`}>
          {inv.inventory_status}
        </span>
      </div>

      <div className="grid grid-cols-4 gap-2 text-center">
        {[
          { label: "Scope 1", value: inv.scope1_emissions },
          { label: "Scope 2", value: inv.scope2_emissions },
          { label: "Scope 3", value: inv.scope3_emissions },
          { label: t("common.total"), value: inv.total_emissions },
        ].map(({ label, value }) => (
          <div key={label} className="rounded bg-muted p-2">
            <p className="text-[10px] text-muted-foreground">{label}</p>
            <p className="text-sm font-bold">{value.toLocaleString()}</p>
          </div>
        ))}
      </div>

      {inv.inventory_status !== "FINALIZED" && (
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => recalc.mutate()} disabled={recalc.isPending}>
            <RefreshCw className="mr-1 h-3 w-3" />
            {recalc.isPending ? "Recalculating…" : "Recalculate"}
          </Button>
          <Button size="sm" variant="outline" onClick={() => finalize.mutate()} disabled={finalize.isPending}>
            <Lock className="mr-1 h-3 w-3" />
            {finalize.isPending ? "Finalizing…" : "Finalize"}
          </Button>
        </div>
      )}
      {inv.inventory_status === "FINALIZED" && inv.finalized_at && (
        <p className="text-xs text-emerald-600">
          Finalized {new Date(inv.finalized_at).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}

function AddEmissionSourceForm({ onDone }: { onDone: () => void }) {
  const { t } = useLanguage();
  const [name, setName] = useState("");
  const [scope, setScope] = useState<"SCOPE1" | "SCOPE2" | "SCOPE3">("SCOPE1");
  const [activityData, setActivityData] = useState("");
  const [emissionFactor, setEmissionFactor] = useState("");
  const [activityUnit, setActivityUnit] = useState("MWh");
  const [category, setCategory] = useState("");
  const [reportingYear, setReportingYear] = useState(String(CURRENT_YEAR));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  async function submit() {
    if (!name || !activityData || !emissionFactor) return;
    setBusy(true);
    setErr(null);
    try {
      const yr = parseInt(reportingYear);
      const src = await addEmissionSource(ORG_ID, {
        name,
        scope,
        activity_data: parseFloat(activityData),
        emission_factor: parseFloat(emissionFactor),
        period_start: `${yr}-01-01T00:00:00Z`,
        period_end: `${yr}-12-31T23:59:59Z`,
        reporting_year: yr,
        category: category || undefined,
        activity_unit: activityUnit || undefined,
        emission_factor_unit: "tCO2e",
      });
      setOk(true);
      onDone();
      setTimeout(() => setOk(false), 2000);
      setName(""); setActivityData(""); setEmissionFactor(""); setCategory("");
      // #165 Auto-link GHG calculation to carbon inventory entry
      try {
        const stored = JSON.parse(localStorage.getItem("eios_automation_rules") ?? "{}");
        if (stored?.ghg_carbon_link?.enabled !== false && src?.id) {
          const scopeConfig = stored?.ghg_carbon_link?.config?.scope_mapping ?? "all";
          if (scopeConfig === "all" || scopeConfig === scope) {
            await import("@/lib/api/client").then(({ default: api }) =>
              api.post(`/automations/trigger`, {
                rule_id: "ghg_carbon_link",
                entity_type: "emission_source",
                entity_id: src.id,
                payload: { scope, reporting_year: yr, match_period: stored?.ghg_carbon_link?.config?.match_period ?? true },
              })
            );
          }
        }
      } catch { /* silent */ }
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErr(msg ?? "Failed to add emission source");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border bg-muted/30 p-3 space-y-3">
      <p className="text-xs font-medium">{t("sustain.addSource")}</p>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="col-span-2">
          <label className="block text-muted-foreground mb-1">Source Name</label>
          <input
            className="w-full rounded border px-2 py-1 text-sm bg-background"
            placeholder="e.g. Natural Gas Boiler, Grid Electricity"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-muted-foreground mb-1">{t("sustain.scope")}</label>
          <select
            className="w-full rounded border px-2 py-1 text-sm bg-background"
            value={scope}
            onChange={(e) => setScope(e.target.value as "SCOPE1" | "SCOPE2" | "SCOPE3")}
          >
            <option value="SCOPE1">Scope 1 (Direct)</option>
            <option value="SCOPE2">Scope 2 (Electricity)</option>
            <option value="SCOPE3">Scope 3 (Value chain)</option>
          </select>
        </div>
        <div>
          <label className="block text-muted-foreground mb-1">Category (optional)</label>
          <input
            className="w-full rounded border px-2 py-1 text-sm bg-background"
            placeholder="e.g. Stationary combustion"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-muted-foreground mb-1">{t("sustain.activityData")}</label>
          <input
            type="number" step="any" min="0"
            className="w-full rounded border px-2 py-1 text-sm bg-background"
            placeholder="e.g. 10000"
            value={activityData}
            onChange={(e) => setActivityData(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-muted-foreground mb-1">Activity Unit</label>
          <select
            className="w-full rounded border px-2 py-1 text-sm bg-background"
            value={activityUnit}
            onChange={(e) => setActivityUnit(e.target.value)}
          >
            {["MWh", "kWh", "GJ", "litres", "kg", "tonnes", "m3", "km"].map((u) => (
              <option key={u}>{u}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-muted-foreground mb-1">{t("sustain.emissionFactor")} (tCO₂e per unit)</label>
          <input
            type="number" step="any" min="0"
            className="w-full rounded border px-2 py-1 text-sm bg-background"
            placeholder="e.g. 0.00053"
            value={emissionFactor}
            onChange={(e) => setEmissionFactor(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-muted-foreground mb-1">{t("scope3.reportingYear")}</label>
          <input
            type="number" min="2000" max="2100"
            className="w-full rounded border px-2 py-1 text-sm bg-background"
            value={reportingYear}
            onChange={(e) => setReportingYear(e.target.value)}
          />
        </div>
      </div>
      {err && <p className="text-xs text-red-600">{err}</p>}
      <div className="flex items-center gap-2">
        <Button size="sm" className="h-7 text-xs" disabled={!name || !activityData || !emissionFactor || busy} onClick={submit}>
          {busy ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
          Add Source
        </Button>
        {ok && (
          <span className="flex items-center gap-1 text-xs text-emerald-600">
            <CheckCircle2 className="h-3.5 w-3.5" /> Added
          </span>
        )}
      </div>
    </div>
  );
}

export default function CarbonInventoryPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showAddSource, setShowAddSource] = useState(false);

  const { data: inventories, isLoading } = useQuery({
    queryKey: ["inventories", ORG_ID],
    queryFn: () => listInventories(ORG_ID),
  });

  const { data: sources } = useQuery({
    queryKey: ["emission-sources", ORG_ID],
    queryFn: () => listEmissionSources(ORG_ID),
  });

  const sortedInventories = [...(inventories ?? [])].sort((a, b) => b.reporting_year - a.reporting_year);
  const currentInv = sortedInventories[0] ?? null;
  const priorInv = sortedInventories[1] ?? null;

  const carbonChartData: CarbonDataPoint[] = (inventories ?? [])
    .slice()
    .sort((a, b) => a.reporting_year - b.reporting_year)
    .map((inv) => ({
      period: String(inv.reporting_year),
      scope1: inv.scope1_emissions,
      scope2: inv.scope2_emissions,
      scope3: inv.scope3_emissions,
    }));

  function onSourceAdded() {
    qc.invalidateQueries({ queryKey: ["emission-sources", ORG_ID] });
    qc.invalidateQueries({ queryKey: ["inventories", ORG_ID] });
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("sustain.carbonTitle")}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {t("sustain.carbonSubtitle")}
        </p>
      </div>

      {currentInv && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Scope Breakdown — {currentInv.reporting_year}
              {priorInv && (
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  vs. {priorInv.reporting_year}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { label: "Scope 1 — Direct", cur: currentInv.scope1_emissions, prior: priorInv?.scope1_emissions ?? null, color: "bg-red-500" },
              { label: "Scope 2 — Electricity", cur: currentInv.scope2_emissions, prior: priorInv?.scope2_emissions ?? null, color: "bg-orange-500" },
              { label: "Scope 3 — Value Chain", cur: currentInv.scope3_emissions, prior: priorInv?.scope3_emissions ?? null, color: "bg-amber-500" },
            ].map(({ label, cur, prior, color }) => {
              const pct = currentInv.total_emissions > 0 ? (cur / currentInv.total_emissions) * 100 : 0;
              const delta = prior != null && prior > 0 ? ((cur - prior) / prior) * 100 : null;
              return (
                <div key={label} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium">{label}</span>
                    <div className="flex items-center gap-3">
                      <span className="tabular-nums">{cur.toLocaleString()} tCO₂e</span>
                      {delta != null && (
                        <span className={`font-medium ${delta > 0 ? "text-red-600" : "text-emerald-600"}`}>
                          {delta > 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}% vs prior year
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                    <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
                  </div>
                  {prior != null && (
                    <div className="h-1 w-full rounded-full bg-muted overflow-hidden opacity-40">
                      <div
                        className={`h-full rounded-full ${color}`}
                        style={{ width: `${currentInv.total_emissions > 0 ? (prior / currentInv.total_emissions) * 100 : 0}%` }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      {currentInv && currentInv.total_emissions > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Scope Contributions</CardTitle></CardHeader>
            <CardContent className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { name: "Scope 1", value: currentInv.scope1_emissions },
                      { name: "Scope 2", value: currentInv.scope2_emissions },
                      { name: "Scope 3", value: currentInv.scope3_emissions },
                    ]}
                    cx="50%" cy="50%" innerRadius={48} outerRadius={76}
                    dataKey="value"
                  >
                    <Cell fill="#ef4444" />
                    <Cell fill="#f97316" />
                    <Cell fill="#f59e0b" />
                  </Pie>
                  <Tooltip formatter={(v: number) => `${v.toLocaleString()} tCO₂e`} />
                  <Legend iconSize={10} iconType="circle" />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Emissionen nach Scope (tCO₂e)</CardTitle></CardHeader>
            <CardContent>
              <CarbonStackedBarChart data={carbonChartData} unit="tCO₂e" height={176} />
            </CardContent>
          </Card>
        </div>
      )}

      {!currentInv && carbonChartData.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Emissionen nach Scope (tCO₂e)</CardTitle></CardHeader>
          <CardContent>
            <CarbonStackedBarChart data={carbonChartData} unit="tCO₂e" height={280} />
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("scope3.inventories")}</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading && <Spinner />}
            {inventories?.length === 0 && (
              <p className="text-sm text-muted-foreground">{t("scope3.noInventories")}</p>
            )}
            <div className="space-y-3">
              {inventories?.map((inv) => (
                <InventoryCard key={inv.id} inv={inv} />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">
                Emission Sources{sources ? ` (${sources.length})` : ""}
              </CardTitle>
              <Button
                size="sm"
                variant="outline"
                className="h-7 px-2 text-xs gap-1"
                onClick={() => setShowAddSource((v) => !v)}
              >
                <Plus className="h-3.5 w-3.5" />
                {t("sustain.addSource")}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {showAddSource && (
              <AddEmissionSourceForm onDone={() => { onSourceAdded(); setShowAddSource(false); }} />
            )}
            {sources?.length === 0 && !showAddSource && (
              <p className="text-sm text-muted-foreground">{t("sustain.noCarbon")}</p>
            )}
            <div className="space-y-2">
              {sources?.slice(0, 20).map((src) => (
                <div key={src.id} className="flex items-center justify-between rounded border p-2 text-sm">
                  <div>
                    <p className="font-medium">{src.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {src.activity_data} × {src.emission_factor} = {src.calculated_emissions.toFixed(3)} tCO₂e
                    </p>
                  </div>
                  <span className={`rounded px-2 py-0.5 text-xs font-medium ${scopeColor(src.scope)}`}>
                    {src.scope}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
