"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Database,
  Loader2,
  Play,
  RefreshCw,
  Timer,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { formatDate, formatDateTime } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ConnectorHealth {
  connector_name: string;
  status: string;
  last_success: string | null;
  last_failure: string | null;
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  avg_runtime_seconds: number;
  consecutive_failures: number;
}

interface ConnectorHealthList {
  items: ConnectorHealth[];
  overall_status: string;
  total: number;
}

interface DatasetFreshness {
  source_name: string;
  freshness_status: string;
  last_refresh: string | null;
  expected_cadence_hours: number;
  hours_since_refresh: number | null;
  hours_overdue: number;
  next_expected_refresh: string | null;
}

interface DatasetFreshnessList {
  items: DatasetFreshness[];
  stale_count: number;
  expired_count: number;
  fresh_count: number;
}

interface OperationsDashboard {
  overall_health: string;
  fresh_datasets: number;
  stale_datasets: number;
  expired_datasets: number;
  total_connectors: number;
  healthy_connectors: number;
  degraded_connectors: number;
  failed_connectors: number;
  dataset_refresh_total: number;
  dataset_refresh_failed_total: number;
  sanctions_updates_total: number;
  benchmark_refresh_total: number;
}

interface SchedulerHealth {
  scheduler_alive: boolean;
  last_cycle_started: string | null;
  last_cycle_completed: string | null;
  seconds_since_last_cycle: number | null;
  cycles_completed: number;
}

interface TriggerResult {
  connector_name: string;
  success: boolean;
  row_count: number;
  runtime_seconds: number;
  dataset_id: string | null;
  error_message: string | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const HEALTH_COL: Record<string, string> = {
  HEALTHY:   "bg-emerald-100 text-emerald-800",
  DEGRADED:  "bg-amber-100 text-amber-700",
  FAILED:    "bg-red-100 text-red-800",
  UNKNOWN:   "bg-slate-100 text-slate-600",
};

const FRESH_COL: Record<string, string> = {
  FRESH:   "bg-emerald-100 text-emerald-800",
  STALE:   "bg-amber-100 text-amber-700",
  EXPIRED: "bg-red-100 text-red-800",
};

function HealthIcon({ status }: { status: string }) {
  if (status === "HEALTHY")  return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
  if (status === "DEGRADED") return <AlertTriangle className="h-4 w-4 text-amber-500" />;
  return <AlertTriangle className="h-4 w-4 text-red-500" />;
}

// ── Dashboard Tab ─────────────────────────────────────────────────────────────

function DashboardTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const { data: dash, isLoading } = useQuery<OperationsDashboard>({
    queryKey: ["ops-dashboard"],
    queryFn: () => apiClient.get("/external-intelligence/operations/dashboard").then((r) => r.data),
    refetchInterval: 30_000,
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (!dash) return null;

  const healthColor = dash.overall_health === "HEALTHY" ? "text-emerald-600"
    : dash.overall_health === "DEGRADED" ? "text-amber-600" : "text-red-600";

  return (
    <div className="space-y-6">
      {/* Overall health banner */}
      <Card className={`border-2 ${dash.overall_health === "HEALTHY" ? "border-emerald-300" : dash.overall_health === "DEGRADED" ? "border-amber-300" : "border-red-300"}`}>
        <CardContent className="py-4 flex items-center gap-3">
          <HealthIcon status={dash.overall_health} />
          <div>
            <p className="text-sm text-muted-foreground">{t("ops.overallHealth")}</p>
            <p className={`text-xl font-bold ${healthColor}`}>{dash.overall_health}</p>
          </div>
        </CardContent>
      </Card>

      {/* Connector KPIs */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Connectors</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: t("ops.totalConnectors"), value: dash.total_connectors },
            { label: t("ops.healthy"),  value: dash.healthy_connectors,  cls: "text-emerald-600" },
            { label: t("ops.degraded"), value: dash.degraded_connectors, cls: dash.degraded_connectors > 0 ? "text-amber-600" : "" },
            { label: t("ops.failed"),   value: dash.failed_connectors,   cls: dash.failed_connectors > 0 ? "text-red-600" : "" },
          ].map(({ label, value, cls }) => (
            <Card key={label}>
              <CardContent className="pt-4 pb-4">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className={`text-3xl font-bold mt-1 ${cls ?? ""}`}>{value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Dataset KPIs */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Datasets</p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[
            { label: t("ops.freshDatasets"),   value: dash.fresh_datasets,   cls: "text-emerald-600" },
            { label: t("ops.staleDatasets"),   value: dash.stale_datasets,   cls: dash.stale_datasets > 0 ? "text-amber-600" : "" },
            { label: t("ops.expiredDatasets"), value: dash.expired_datasets, cls: dash.expired_datasets > 0 ? "text-red-600" : "" },
          ].map(({ label, value, cls }) => (
            <Card key={label}>
              <CardContent className="pt-4 pb-4">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className={`text-3xl font-bold mt-1 ${cls ?? ""}`}>{value}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Metrics counters */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Lifetime Metrics</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: t("ops.refreshTotal"),    value: dash.dataset_refresh_total },
            { label: t("ops.refreshFailed"),   value: dash.dataset_refresh_failed_total, cls: dash.dataset_refresh_failed_total > 0 ? "text-red-600" : "" },
            { label: t("ops.sanctionsUpdates"),value: dash.sanctions_updates_total },
            { label: t("ops.benchmarkRefresh"),value: dash.benchmark_refresh_total },
          ].map(({ label, value, cls }) => (
            <Card key={label}>
              <CardContent className="pt-4 pb-4">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className={`text-2xl font-bold mt-1 tabular-nums ${cls ?? ""}`}>{value.toLocaleString()}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Connectors Tab ────────────────────────────────────────────────────────────

function ConnectorsTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [triggerResult, setTriggerResult] = useState<Record<string, TriggerResult>>({});
  const [triggering, setTriggering] = useState<string | null>(null);

  const { data, isLoading } = useQuery<ConnectorHealthList>({
    queryKey: ["ops-connectors"],
    queryFn: () => apiClient.get("/external-intelligence/operations/health").then((r) => r.data),
    refetchInterval: 15_000,
  });

  async function triggerConnector(name: string) {
    setTriggering(name);
    try {
      const res = await apiClient.post("/external-intelligence/operations/trigger", { connector_name: name });
      setTriggerResult((prev) => ({ ...prev, [name]: res.data as TriggerResult }));
      qc.invalidateQueries({ queryKey: ["ops-connectors"] });
      qc.invalidateQueries({ queryKey: ["ops-dashboard"] });
    } catch {/* silent */} finally {
      setTriggering(null);
    }
  }

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Badge className={HEALTH_COL[data.overall_status] ?? "bg-slate-100 text-slate-600"}>
          {data.overall_status}
        </Badge>
        <span className="text-sm text-muted-foreground">{data.total} connectors</span>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-xs text-muted-foreground">
                  <th className="px-4 py-2.5 text-left">{t("ops.connectorName")}</th>
                  <th className="px-4 py-2.5 text-left">{t("ops.status")}</th>
                  <th className="px-4 py-2.5 text-right">{t("ops.totalRuns")}</th>
                  <th className="px-4 py-2.5 text-right">{t("ops.successRate")}</th>
                  <th className="px-4 py-2.5 text-right">{t("ops.avgRuntime")}</th>
                  <th className="px-4 py-2.5 text-right text-red-600">{t("ops.consecutiveFailures")}</th>
                  <th className="px-4 py-2.5 text-right">{t("ops.lastSuccess")}</th>
                  <th className="px-4 py-2.5 text-right"></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((c) => {
                  const successRate = c.total_runs > 0
                    ? Math.round((c.successful_runs / c.total_runs) * 100)
                    : 0;
                  const result = triggerResult[c.connector_name];
                  return (
                    <tr key={c.connector_name} className="border-b last:border-0 hover:bg-muted/30">
                      <td className="px-4 py-3 font-mono text-xs">{c.connector_name}</td>
                      <td className="px-4 py-3">
                        <Badge className={HEALTH_COL[c.status] ?? "bg-slate-100 text-slate-600"}>
                          {c.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">{c.total_runs}</td>
                      <td className={`px-4 py-3 text-right tabular-nums ${successRate < 80 ? "text-red-600" : successRate < 95 ? "text-amber-600" : "text-emerald-600"}`}>
                        {successRate}%
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">
                        {c.avg_runtime_seconds.toFixed(1)}s
                      </td>
                      <td className={`px-4 py-3 text-right ${c.consecutive_failures > 0 ? "text-red-600 font-bold" : ""}`}>
                        {c.consecutive_failures || "—"}
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                        {c.last_success ? formatDate(c.last_success) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex flex-col items-end gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs"
                            disabled={triggering === c.connector_name}
                            onClick={() => triggerConnector(c.connector_name)}
                          >
                            {triggering === c.connector_name
                              ? <Loader2 className="h-3 w-3 animate-spin" />
                              : <><Play className="h-3 w-3 mr-1" />{t("ops.trigger")}</>}
                          </Button>
                          {result && (
                            <span className={`text-[10px] ${result.success ? "text-emerald-600" : "text-red-500"}`}>
                              {result.success
                                ? `✓ ${result.row_count} rows · ${result.runtime_seconds.toFixed(1)}s`
                                : `✗ ${result.error_message?.slice(0, 30)}`}
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {data.items.length === 0 && (
        <div className="text-center py-12 text-muted-foreground text-sm">
          <Cpu className="mx-auto mb-2 h-8 w-8 opacity-30" />
          {t("ops.noConnectors")}
        </div>
      )}
    </div>
  );
}

// ── Freshness Tab ─────────────────────────────────────────────────────────────

function FreshnessTab() {
  const { t } = useLanguage();

  const { data, isLoading } = useQuery<DatasetFreshnessList>({
    queryKey: ["ops-freshness"],
    queryFn: () => apiClient.get("/external-intelligence/operations/freshness").then((r) => r.data),
    refetchInterval: 30_000,
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        {[
          { label: t("ops.freshDatasets"),   value: data.fresh_count,   col: "bg-emerald-50 border-emerald-200 text-emerald-800" },
          { label: t("ops.staleDatasets"),   value: data.stale_count,   col: "bg-amber-50 border-amber-200 text-amber-700" },
          { label: t("ops.expiredDatasets"), value: data.expired_count, col: "bg-red-50 border-red-200 text-red-700" },
        ].map(({ label, value, col }) => (
          <div key={label} className={`rounded-lg border px-4 py-2 text-sm font-semibold ${col}`}>
            {value} {label}
          </div>
        ))}
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-xs text-muted-foreground">
                  <th className="px-4 py-2.5 text-left">{t("ops.sourceName")}</th>
                  <th className="px-4 py-2.5 text-left">{t("ops.freshnessStatus")}</th>
                  <th className="px-4 py-2.5 text-right">{t("ops.lastRefresh")}</th>
                  <th className="px-4 py-2.5 text-right">{t("ops.cadence")}</th>
                  <th className="px-4 py-2.5 text-right">{t("ops.hoursSince")}</th>
                  <th className="px-4 py-2.5 text-right text-red-600">{t("ops.hoursOverdue")}</th>
                  <th className="px-4 py-2.5 text-right">{t("ops.nextRefresh")}</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((ds) => (
                  <tr key={ds.source_name} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-3 font-mono text-xs">{ds.source_name}</td>
                    <td className="px-4 py-3">
                      <Badge className={FRESH_COL[ds.freshness_status] ?? "bg-slate-100 text-slate-600"}>
                        {ds.freshness_status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                      {ds.last_refresh ? formatDate(ds.last_refresh) : "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">{ds.expected_cadence_hours}h</td>
                    <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">
                      {ds.hours_since_refresh != null ? ds.hours_since_refresh.toFixed(1) : "—"}
                    </td>
                    <td className={`px-4 py-3 text-right tabular-nums ${ds.hours_overdue > 0 ? "text-red-600 font-semibold" : ""}`}>
                      {ds.hours_overdue > 0 ? ds.hours_overdue.toFixed(1) : "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                      {ds.next_expected_refresh ? formatDate(ds.next_expected_refresh) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {data.items.length === 0 && (
        <div className="text-center py-12 text-muted-foreground text-sm">
          <Database className="mx-auto mb-2 h-8 w-8 opacity-30" />
          {t("ops.noDatasets")}
        </div>
      )}
    </div>
  );
}

// ── Scheduler Tab ─────────────────────────────────────────────────────────────

function SchedulerTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const { data, isLoading, refetch } = useQuery<SchedulerHealth>({
    queryKey: ["ops-scheduler"],
    queryFn: () => apiClient.get("/external-intelligence/operations/scheduler-health").then((r) => r.data),
    refetchInterval: 20_000,
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" variant="outline" onClick={() => refetch()}>
          <RefreshCw className="h-3.5 w-3.5 mr-1.5" /> Refresh
        </Button>
      </div>

      <Card className={`border-2 ${data.scheduler_alive ? "border-emerald-300" : "border-red-300"}`}>
        <CardContent className="py-6 flex items-center gap-4">
          <div className={`h-12 w-12 rounded-full flex items-center justify-center ${data.scheduler_alive ? "bg-emerald-100" : "bg-red-100"}`}>
            <Activity className={`h-6 w-6 ${data.scheduler_alive ? "text-emerald-600" : "text-red-600"}`} />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("ops.schedulerAlive")}</p>
            <p className={`text-2xl font-bold ${data.scheduler_alive ? "text-emerald-600" : "text-red-600"}`}>
              {data.scheduler_alive ? "Active" : "Down"}
            </p>
          </div>
          <div className="ml-auto text-right">
            <p className="text-xs text-muted-foreground">{t("ops.cyclesCompleted")}</p>
            <p className="text-2xl font-bold tabular-nums">{data.cycles_completed.toLocaleString()}</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          { label: t("ops.lastCycleStarted"),   value: data.last_cycle_started,   icon: Timer },
          { label: t("ops.lastCycleCompleted"), value: data.last_cycle_completed, icon: CheckCircle2 },
        ].map(({ label, value, icon: Icon }) => (
          <Card key={label}>
            <CardContent className="py-4 flex items-start gap-3">
              <Icon className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="text-sm font-medium mt-0.5">
                  {value ? formatDateTime(value) : "—"}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {data.seconds_since_last_cycle != null && (
        <Card>
          <CardContent className="py-4">
            <p className="text-xs text-muted-foreground">{t("ops.secondsSince")}</p>
            <p className={`text-2xl font-bold tabular-nums mt-1 ${data.seconds_since_last_cycle > 3600 ? "text-amber-600" : ""}`}>
              {data.seconds_since_last_cycle.toFixed(0)}s
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = "dashboard" | "connectors" | "freshness" | "scheduler";

const tab_defs: { key: Tab; labelKey: string; icon: React.ElementType }[] = [
  { key: "dashboard",  labelKey: "ops.dashboardTab",  icon: Activity },
  { key: "connectors", labelKey: "ops.connectorsTab", icon: Cpu },
  { key: "freshness",  labelKey: "ops.freshnessTab",  icon: Database },
  { key: "scheduler",  labelKey: "ops.schedulerTab",  icon: Timer },
];

export default function IntelOperationsPage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Cpu className="h-7 w-7 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold">{t("ops.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("ops.subtitle")}</p>
        </div>
      </div>

      <div className="flex gap-1 border-b overflow-x-auto">
        {tab_defs.map(({ key, labelKey, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors ${
              activeTab === key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="h-4 w-4" />
            {t(labelKey as Parameters<typeof t>[0])}
          </button>
        ))}
      </div>

      <div>
        {activeTab === "dashboard"  && <DashboardTab />}
        {activeTab === "connectors" && <ConnectorsTab />}
        {activeTab === "freshness"  && <FreshnessTab />}
        {activeTab === "scheduler"  && <SchedulerTab />}
      </div>
    </div>
  );
}
