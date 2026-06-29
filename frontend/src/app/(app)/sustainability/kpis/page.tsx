"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, BarChart3, CheckCircle2, Loader2, Plus, TrendingUp } from "lucide-react";
import {
  listKPIs,
  createKPI,
  listAlerts,
  listMeasurements,
  recordMeasurement,
  type ESGKPI,
  type KPIAlert,
  type KPIMeasurement,
} from "@/lib/api/sustainability";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { KpiLineChart } from "@/components/charts/kpi-line-chart";
import type { KpiDataPoint } from "@/components/charts/kpi-line-chart";

const ORG_ID = "default";
const KPI_CATEGORIES = [
  "EMISSIONS", "SUPPLIER_COMPLIANCE", "AUDIT_COMPLETION",
  "TRAINING_COMPLETION", "DIVERSITY", "INCIDENT_RATE", "CUSTOM",
];

function alertTypeColor(t: string) {
  switch (t) {
    case "THRESHOLD_BREACH": return "bg-red-100 text-red-800";
    case "MISSED_TARGET":    return "bg-amber-100 text-amber-800";
    default:                 return "bg-slate-100 text-slate-600";
  }
}

function todayISO() {
  return new Date().toISOString().split("T")[0];
}

function firstOfMonthISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

// ── Sparkline ─────────────────────────────────────────────────────────────────

function Sparkline({ data, target }: { data: KPIMeasurement[]; target: number | null }) {
  if (data.length < 2) return null;
  const values = data.map((d) => d.measured_value);
  const min = Math.min(...values, target ?? Infinity);
  const max = Math.max(...values, target ?? -Infinity);
  const range = max - min || 1;
  const W = 120, H = 32;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * W;
    const y = H - ((v - min) / range) * H;
    return `${x},${y}`;
  });
  const targetY = target != null ? H - ((target - min) / range) * H : null;

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="overflow-visible">
      {targetY != null && (
        <line x1="0" y1={targetY} x2={W} y2={targetY} stroke="#3b82f6" strokeWidth="1" strokeDasharray="3 2" opacity="0.6" />
      )}
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke="#10b981"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <circle cx={pts[pts.length - 1].split(",")[0]} cy={pts[pts.length - 1].split(",")[1]} r="2.5" fill="#10b981" />
    </svg>
  );
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KPICard({ kpi, onMeasured }: { kpi: ESGKPI; onMeasured: () => void }) {
  const [showForm, setShowForm] = useState(false);

  const { data: measurements } = useQuery({
    queryKey: ["kpi-measurements", ORG_ID, kpi.id],
    queryFn: () => listMeasurements(ORG_ID, kpi.id, 12),
    staleTime: 60_000,
  });
  const [value, setValue] = useState("");
  const [periodStart, setPeriodStart] = useState(firstOfMonthISO());
  const [periodEnd, setPeriodEnd] = useState(todayISO());
  const [notes, setNotes] = useState("");
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    if (!value) return;
    setBusy(true);
    setErr(null);
    setSuccess(false);
    try {
      const numVal = parseFloat(value);
      await recordMeasurement(ORG_ID, kpi.id, {
        measured_value: numVal,
        period_start: new Date(periodStart).toISOString(),
        period_end: new Date(periodEnd).toISOString(),
        notes: notes || undefined,
      });
      setSuccess(true);
      setValue(""); setNotes("");
      onMeasured();

      // #162 Auto-compute KPI alert when measurement added below threshold
      if (kpi.alert_threshold != null && numVal < kpi.alert_threshold) {
        try {
          const stored = JSON.parse(localStorage.getItem("eios_automation_rules") ?? "{}");
          if (stored?.kpi_alert?.enabled !== false) {
            await import("@/lib/api/client").then(({ default: api }) =>
              api.post(`/api/v1/sustainability/${ORG_ID}/kpis/${kpi.id}/alert`, {
                measured_value: numVal,
                threshold: kpi.alert_threshold,
                trigger: "below_threshold",
              })
            );
          }
        } catch { /* silent — alert failure should not block measurement */ }
      }

      setTimeout(() => { setShowForm(false); setSuccess(false); }, 1500);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErr(msg ?? "Failed to record measurement");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border p-4 space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-medium text-sm">{kpi.name}</span>
        <div className="flex items-center gap-2">
          <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${
            kpi.is_active ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"
          }`}>
            {kpi.is_active ? "Active" : "Inactive"}
          </span>
          {kpi.is_active && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-xs"
              onClick={() => { setShowForm((v) => !v); setSuccess(false); setErr(null); }}
            >
              <TrendingUp className="h-3.5 w-3.5 mr-1" />
              Add Measurement
            </Button>
          )}
        </div>
      </div>
      <div className="flex gap-3 text-xs text-muted-foreground">
        <span>{kpi.category}</span>
        {kpi.unit && <span>Unit: {kpi.unit}</span>}
        {kpi.frequency && <span>{kpi.frequency}</span>}
      </div>
      {(kpi.target_value != null || kpi.alert_threshold != null) && (
        <div className="flex gap-4 text-xs mt-1">
          {kpi.target_value != null && (
            <span className="text-blue-600">Target: {kpi.target_value}</span>
          )}
          {kpi.alert_threshold != null && (
            <span className="text-amber-600">Alert threshold: {kpi.alert_threshold}</span>
          )}
        </div>
      )}

      {measurements && measurements.length >= 2 && (
        <div className="flex items-center gap-3 mt-2">
          <Sparkline data={[...measurements].reverse()} target={kpi.target_value ?? null} />
          <div className="text-xs text-muted-foreground">
            <span className="font-semibold text-foreground">{measurements[0].measured_value}</span>
            {kpi.unit ? ` ${kpi.unit}` : ""}
            <span className="ml-1">latest</span>
          </div>
        </div>
      )}

      {showForm && (
        <div className="rounded-lg border bg-muted/30 p-3 space-y-2 mt-2">
          <p className="text-xs font-medium">Log Measurement{kpi.unit ? ` (${kpi.unit})` : ""}</p>
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Value</label>
              <input
                type="number" step="any"
                className="w-full rounded border px-2 py-1 text-sm bg-background"
                placeholder="0.00"
                value={value}
                onChange={(e) => setValue(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Period Start</label>
              <input
                type="date"
                className="w-full rounded border px-2 py-1 text-sm bg-background"
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs text-muted-foreground mb-1">Period End</label>
              <input
                type="date"
                className="w-full rounded border px-2 py-1 text-sm bg-background"
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-muted-foreground mb-1">Notes (optional)</label>
            <input
              className="w-full rounded border px-2 py-1 text-sm bg-background"
              placeholder="Source, methodology…"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" className="h-7 text-xs" disabled={!value || busy} onClick={submit}>
              {busy ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
              Save
            </Button>
            <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setShowForm(false)}>
              Cancel
            </Button>
            {success && (
              <span className="flex items-center gap-1 text-xs text-emerald-600">
                <CheckCircle2 className="h-3.5 w-3.5" /> Saved
              </span>
            )}
            {err && <span className="text-xs text-red-600">{err}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

export default function KPIsPage() {
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("EMISSIONS");
  const [unit, setUnit] = useState("");
  const [targetValue, setTargetValue] = useState("");
  const [alertThreshold, setAlertThreshold] = useState("");

  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ["kpis", ORG_ID],
    queryFn: () => listKPIs(ORG_ID),
  });

  const { data: alerts } = useQuery({
    queryKey: ["alerts", ORG_ID],
    queryFn: () => listAlerts(ORG_ID),
  });

  const create = useMutation({
    mutationFn: () =>
      createKPI(ORG_ID, {
        name,
        category,
        unit: unit || undefined,
        target_value: targetValue ? Number(targetValue) : undefined,
        alert_threshold: alertThreshold ? Number(alertThreshold) : undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kpis", ORG_ID] });
      setName(""); setUnit(""); setTargetValue(""); setAlertThreshold("");
      setCreating(false);
    },
  });

  const openAlerts = alerts?.filter((a) => !a.is_resolved) ?? [];

  const activeKpis = (kpis ?? []).filter((k) => k.is_active && k.target_value != null).slice(0, 1);
  const kpiChartData: KpiDataPoint[] = activeKpis.length > 0
    ? ["Q1", "Q2", "Q3", "Q4"].map((q) => ({
        period: q,
        actual: null,
        target: activeKpis[0].target_value ?? null,
      }))
    : [];

  function invalidateKpis() {
    qc.invalidateQueries({ queryKey: ["kpis", ORG_ID] });
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">KPI Management</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Track ESG performance indicators with thresholds and alerts
          </p>
        </div>
        <Button onClick={() => setCreating(true)} size="sm">
          <Plus className="mr-2 h-4 w-4" /> New KPI
        </Button>
      </div>

      {openAlerts.length > 0 && (
        <Card className="border-amber-200 bg-amber-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              {openAlerts.length} Open Alert{openAlerts.length > 1 ? "s" : ""}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {openAlerts.slice(0, 5).map((a) => (
                <div key={a.id} className="flex items-center gap-2 text-sm">
                  <span className={`rounded px-2 py-0.5 text-xs font-medium ${alertTypeColor(a.alert_type)}`}>
                    {a.alert_type}
                  </span>
                  <span className="text-muted-foreground">
                    Value: {a.triggered_value}
                    {a.threshold_value != null ? ` (threshold: ${a.threshold_value})` : ""}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {creating && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">New KPI</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <label className="block text-xs font-medium mb-1">Name</label>
              <input
                className="w-full rounded border px-3 py-1.5 text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Supplier ESG Compliance Rate"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium mb-1">Category</label>
                <select
                  className="w-full rounded border px-3 py-1.5 text-sm"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  {KPI_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Unit</label>
                <input
                  className="w-full rounded border px-3 py-1.5 text-sm"
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  placeholder="%, tCO2e, count…"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Target Value</label>
                <input
                  type="number"
                  className="w-full rounded border px-3 py-1.5 text-sm"
                  value={targetValue}
                  onChange={(e) => setTargetValue(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Alert Threshold</label>
                <input
                  type="number"
                  className="w-full rounded border px-3 py-1.5 text-sm"
                  value={alertThreshold}
                  onChange={(e) => setAlertThreshold(e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => create.mutate()} disabled={!name || create.isPending}>
                {create.isPending ? "Creating…" : "Create"}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setCreating(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {kpiChartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{activeKpis[0].name} — Ziel: {activeKpis[0].target_value} {activeKpis[0].unit ?? ""}</CardTitle>
          </CardHeader>
          <CardContent>
            <KpiLineChart
              data={kpiChartData}
              unit={activeKpis[0].unit ? ` ${activeKpis[0].unit}` : ""}
              targetLabel="Ziel"
              height={240}
            />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            KPIs{kpis ? ` (${kpis.length})` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {kpisLoading && <Spinner />}
          {kpis?.length === 0 && (
            <p className="text-sm text-muted-foreground">No KPIs yet.</p>
          )}
          <div className="space-y-2">
            {kpis?.map((k) => <KPICard key={k.id} kpi={k} onMeasured={invalidateKpis} />)}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
