"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import {
  Activity,
  AlertTriangle,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Eye,
  Loader2,
  Plus,
  Radio,
  Shield,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  Trash2,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import apiClient from "@/lib/api/client";
import { formatDateTime } from "@/lib/utils";

// ── API ───────────────────────────────────────────────────────────────────────

async function getSurveillanceDashboard() {
  const res = await apiClient.get("/surveillance/dashboard");
  return res.data;
}

async function getActiveSignals() {
  const res = await apiClient.get("/surveillance/signals?signal_status=ACTIVE&limit=20");
  return res.data;
}

async function getWatchlist() {
  const res = await apiClient.get("/surveillance/watchlists?active_only=true&limit=50");
  return res.data;
}

async function getOpenEpisodes() {
  const res = await apiClient.get("/surveillance/episodes?episode_status=OPEN&limit=20");
  return res.data;
}

async function getSignalsByConnector() {
  const res = await apiClient.get("/external-intelligence/signals/by-connector?top_n=10");
  return res.data as {
    connectors: Array<{
      source_name: string;
      label: string;
      total: number;
      signals: Array<{
        id: string;
        signal_type: string;
        severity: string;
        description: string;
        source_name: string;
        observed_at: string;
        supplier_id: string;
        country_code: string;
      }>;
    }>;
  };
}

async function getRiskTrends() {
  const res = await apiClient.get("/surveillance/trends?limit=24");
  return res.data as Array<{
    id: string;
    supplier_id: string;
    period: string;
    score_delta: number;
    trend: string;
    confidence: number;
    esg_score_end: number | null;
    risk_score_end: number | null;
  }>;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: string }) {
  const colour: Record<string, string> = {
    CRITICAL: "destructive",
    HIGH: "warning",
    MEDIUM: "secondary",
    LOW: "outline",
    INFO: "outline",
  };
  return <Badge variant={(colour[severity] ?? "secondary") as any}>{severity}</Badge>;
}

function StatCard({ label, value, icon: Icon, colour }: {
  label: string; value: number | string; icon: React.ElementType; colour?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className={`text-2xl font-bold mt-1 ${colour ?? "text-foreground"}`}>{value}</p>
          </div>
          <Icon className="h-8 w-8 text-muted-foreground opacity-50" />
        </div>
      </CardContent>
    </Card>
  );
}

// ── Signal row with Acknowledge / Dismiss / Create Risk ───────────────────────

function SignalRow({ signal, nameMap }: { signal: any; nameMap: Map<string, string> }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [riskCreated, setRiskCreated] = useState(false);
  const [localStatus, setLocalStatus] = useState<string>(signal.signal_status);
  const [expanded, setExpanded] = useState(false);

  const createRisk = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/risks/", {
        title: `[Signal] ${signal.title}`,
        risk_level: signal.severity === "HIGH" || signal.severity === "CRITICAL"
          ? signal.severity.charAt(0) + signal.severity.slice(1).toLowerCase()
          : "Medium",
        status: "Draft",
        category: signal.signal_type ?? "Surveillance",
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["org-risks"] });
      setRiskCreated(true);
    },
  });

  const acknowledge = useMutation({
    mutationFn: () => apiClient.post(`/surveillance/signals/${signal.id}/acknowledge`),
    onSuccess: () => {
      setLocalStatus("ACKNOWLEDGED");
      qc.invalidateQueries({ queryKey: ["surveillance-signals-active"] });
      qc.invalidateQueries({ queryKey: ["surveillance-dashboard"] });
    },
  });

  const dismiss = useMutation({
    mutationFn: () => apiClient.post(`/surveillance/signals/${signal.id}/dismiss`),
    onSuccess: () => {
      setLocalStatus("DISMISSED");
      qc.invalidateQueries({ queryKey: ["surveillance-signals-active"] });
      qc.invalidateQueries({ queryKey: ["surveillance-dashboard"] });
    },
  });

  const isDone = localStatus === "ACKNOWLEDGED" || localStatus === "DISMISSED";
  const supplierName = signal.supplier_id ? (nameMap.get(signal.supplier_id) ?? signal.supplier_id.slice(0, 10) + "…") : null;
  const expl = signal.explainability_json ?? {};

  return (
    <div className="py-3 border-b last:border-0 space-y-1.5">
      <div className="flex items-start justify-between gap-3">
        <button className="flex-1 min-w-0 text-left" onClick={() => setExpanded(v => !v)}>
          <p className={`text-sm font-medium ${expanded ? "" : "truncate"}`}>{signal.title}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {signal.signal_type}
            {supplierName ? ` · ${supplierName}` : ""}
            {" · "}{formatDateTime(signal.detected_at)}
            <span className="ml-1 text-blue-500">{expanded ? "▲" : "▼"}</span>
          </p>
        </button>
        <SeverityBadge severity={signal.severity} />
      </div>

      {expanded && (
        <div className="mt-2 rounded-lg border border-border bg-muted/40 p-3 space-y-2 text-xs">
          {signal.description && (
            <p className="text-foreground leading-relaxed whitespace-pre-wrap">{signal.description}</p>
          )}
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground pt-1 border-t border-border">
            {expl.dimension && <span><span className="font-medium">Dimension:</span> {expl.dimension}</span>}
            {expl.direction && <span><span className="font-medium">Richtung:</span> {expl.direction}</span>}
            {expl.year && <span><span className="font-medium">Jahr:</span> {expl.year}</span>}
            {signal.confidence != null && <span><span className="font-medium">Konfidenz:</span> {Math.round(signal.confidence * 100)}%</span>}
            {expl.company_name && <span><span className="font-medium">Unternehmen:</span> {expl.company_name}</span>}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-1.5">
        {isDone ? (
          <span className="flex items-center gap-1 text-[11px] text-emerald-600 font-medium">
            <CheckCircle2 className="h-3 w-3" />
            {localStatus === "ACKNOWLEDGED" ? t("surveillance.acknowledged") : t("surveillance.dismissed")}
          </span>
        ) : (
          <>
            <button
              onClick={() => acknowledge.mutate()}
              disabled={acknowledge.isPending}
              className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700 hover:bg-blue-100 transition-colors disabled:opacity-50"
            >
              {acknowledge.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle2 className="h-3 w-3" />}
              {t("surveillance.acknowledge")}
            </button>
            <button
              onClick={() => dismiss.mutate()}
              disabled={dismiss.isPending}
              className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600 hover:bg-slate-200 transition-colors disabled:opacity-50"
            >
              {dismiss.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
              {t("surveillance.dismiss")}
            </button>
          </>
        )}
        {riskCreated ? (
          <span className="flex items-center gap-1 text-[10px] text-emerald-600 font-medium ml-auto">
            <CheckCircle2 className="h-3 w-3" /> {t("surveillance.riskCreated")}
          </span>
        ) : (
          <button
            onClick={() => createRisk.mutate()}
            disabled={createRisk.isPending}
            className="inline-flex items-center gap-1 rounded bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700 hover:bg-red-100 transition-colors disabled:opacity-50 ml-auto"
          >
            {createRisk.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <ShieldAlert className="h-3 w-3" />}
            {t("surveillance.createRisk")}
          </button>
        )}
      </div>
    </div>
  );
}

// ── Episode row with Transition buttons ───────────────────────────────────────

function EpisodeRow({ episode, nameMap }: { episode: any; nameMap: Map<string, string> }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [localStatus, setLocalStatus] = useState<string>(episode.episode_status);

  const transition = useMutation({
    mutationFn: (newStatus: string) =>
      apiClient.post(`/surveillance/episodes/${episode.id}/transition`, { new_status: newStatus }),
    onSuccess: (_, newStatus) => {
      setLocalStatus(newStatus);
      qc.invalidateQueries({ queryKey: ["surveillance-episodes-open"] });
      qc.invalidateQueries({ queryKey: ["surveillance-dashboard"] });
    },
  });

  const supplierName = episode.supplier_id
    ? (nameMap.get(episode.supplier_id) ?? episode.supplier_id.slice(0, 10) + "…")
    : null;

  const nextStatuses: Record<string, string[]> = {
    OPEN: ["INVESTIGATING", "RESOLVED"],
    INVESTIGATING: ["RESOLVED"],
    RESOLVED: ["CLOSED"],
  };
  const next = nextStatuses[localStatus] ?? [];

  return (
    <div className="py-3 border-b last:border-0 space-y-1.5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{episode.title}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {episode.signal_count} {episode.signal_count === 1 ? "Signal" : "Signals"}
            {supplierName ? ` · ${supplierName}` : ""}
            {" · "}{formatDateTime(episode.started_at)}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <SeverityBadge severity={episode.severity} />
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
            {localStatus}
          </span>
        </div>
      </div>

      {next.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] text-muted-foreground">{t("surveillance.transitionTo")}:</span>
          {next.map((s) => (
            <button
              key={s}
              onClick={() => transition.mutate(s)}
              disabled={transition.isPending}
              className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-700 hover:bg-blue-50 hover:text-blue-700 transition-colors disabled:opacity-50"
            >
              {t((`surveillance.${s.toLowerCase()}`) as any) || s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Connector signal panel ────────────────────────────────────────────────────

const CONNECTOR_ICONS: Record<string, string> = {
  world_bank: "🌍",
  transparency_international: "🔍",
  ilo: "⚙️",
  unicef: "🧒",
  un_sanctions: "🚫",
  eu_sanctions: "🇪🇺",
};

const SEV_COLOUR: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high: "bg-orange-100 text-orange-700 border-orange-200",
  medium: "bg-amber-100 text-amber-700 border-amber-200",
  low: "bg-slate-100 text-slate-600 border-slate-200",
};

function ConnectorCard({ connector }: {
  connector: { source_name: string; label: string; total: number; signals: any[] };
}) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? connector.signals : connector.signals.slice(0, 3);
  const icon = CONNECTOR_ICONS[connector.source_name] ?? "📡";
  const hasSignals = connector.total > 0;

  return (
    <Card className={hasSignals ? "border-orange-200" : ""}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <span className="text-base">{icon}</span>
            {connector.label}
          </CardTitle>
          <div className="flex items-center gap-2">
            {hasSignals ? (
              <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-700">
                {connector.total} {t("surveillance.signalCount")}
              </span>
            ) : (
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                {t("surveillance.clear")}
              </span>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {!hasSignals ? (
          <p className="text-xs text-muted-foreground py-1">{t("surveillance.noSignalsForSuppliers")}</p>
        ) : (
          <div className="space-y-1.5">
            {shown.map((s: any) => (
              <div key={s.id} className={`rounded border px-2.5 py-2 ${SEV_COLOUR[(s.severity ?? "").toLowerCase()] ?? "bg-slate-50 border-slate-200"}`}>
                <p className="text-xs font-medium leading-snug line-clamp-2">{s.description}</p>
                <p className="text-[10px] opacity-70 mt-0.5">
                  {s.signal_type?.replace(/_/g, " ")}
                  {s.country_code ? ` · ${s.country_code}` : ""}
                </p>
              </div>
            ))}
            {connector.signals.length > 3 && (
              <button
                onClick={() => setExpanded((e) => !e)}
                className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground mt-1"
              >
                {expanded
                  ? <><ChevronUp className="h-3 w-3" /> {t("surveillance.showLess")}</>
                  : <><ChevronDown className="h-3 w-3" /> {t("surveillance.showMore").replace("{n}", String(connector.signals.length - 3))}</>
                }
              </button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Heatmap ───────────────────────────────────────────────────────────────────

const SEV_HEAT: Record<string, string> = {
  CRITICAL: "bg-red-600 text-white",
  HIGH: "bg-orange-400 text-white",
  MEDIUM: "bg-amber-300 text-slate-800",
  LOW: "bg-emerald-100 text-emerald-800",
};

function HeatmapSection() {
  const { t } = useLanguage();
  const [dimension, setDimension] = useState<"sector" | "country" | "risk_type">("sector");

  const { data = [], isLoading } = useQuery<Array<{ dimension: string; key: string; signal_count: number; max_severity: string }>>({
    queryKey: ["surveillance-heatmap", dimension],
    queryFn: async () => (await apiClient.get(`/surveillance/heatmaps/${dimension}`)).data,
    staleTime: 60_000,
  });

  const dims: Array<{ value: "sector" | "country" | "risk_type"; labelKey: "surveillance.heatmapBySector" | "surveillance.heatmapByCountry" | "surveillance.heatmapByRiskType" }> = [
    { value: "sector", labelKey: "surveillance.heatmapBySector" },
    { value: "country", labelKey: "surveillance.heatmapByCountry" },
    { value: "risk_type", labelKey: "surveillance.heatmapByRiskType" },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <CardTitle className="text-base">{t("surveillance.heatmap")}</CardTitle>
          <div className="flex gap-1">
            {dims.map((d) => (
              <button
                key={d.value}
                onClick={() => setDimension(d.value)}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${dimension === d.value ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
              >
                {t(d.labelKey)}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : data.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">{t("surveillance.noHeatmap")}</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {[...data].sort((a, b) => b.signal_count - a.signal_count).map((cell) => (
              <div
                key={cell.key}
                className={`rounded-lg px-3 py-2 text-center min-w-[80px] border ${SEV_HEAT[cell.max_severity] ?? "bg-slate-50 text-slate-600 border-slate-200"}`}
              >
                <p className="text-xs font-medium truncate max-w-[100px]">{cell.key || "—"}</p>
                <p className="text-lg font-bold tabular-nums">{cell.signal_count}</p>
                <p className="text-[10px] opacity-70">{t("surveillance.heatmapSignals")}</p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Risk Trends ───────────────────────────────────────────────────────────────

const TREND_COLOUR: Record<string, string> = {
  IMPROVING: "text-green-600",
  STABLE: "text-blue-500",
  DETERIORATING: "text-red-600",
  VOLATILE: "text-amber-600",
};

function TrendsSection({ nameMap }: { nameMap: Map<string, string> }) {
  const { t } = useLanguage();

  const { data = [], isLoading } = useQuery({
    queryKey: ["surveillance-trends"],
    queryFn: getRiskTrends,
    staleTime: 60_000,
  });

  if (isLoading) return <div className="flex justify-center py-8"><Spinner /></div>;
  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground py-4 text-center">{t("surveillance.noTrends")}</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            <th className="pb-2 pr-4">{t("surveillance.supplierLabel")}</th>
            <th className="pb-2 pr-4">{t("surveillance.trendPeriod")}</th>
            <th className="pb-2 pr-4">{t("surveillance.trendDelta")}</th>
            <th className="pb-2">{t("surveillance.trendDirection")}</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {data.slice(0, 20).map((r) => {
            const name = nameMap.get(r.supplier_id) ?? r.supplier_id.slice(0, 10) + "…";
            const deltaColor = r.score_delta > 0 ? "text-red-600" : r.score_delta < 0 ? "text-green-600" : "text-slate-500";
            return (
              <tr key={r.id} className="hover:bg-muted/30">
                <td className="py-2 pr-4 font-medium">{name}</td>
                <td className="py-2 pr-4 text-muted-foreground font-mono text-xs">{r.period}</td>
                <td className={`py-2 pr-4 font-mono text-xs font-semibold ${deltaColor}`}>
                  {r.score_delta > 0 ? "+" : ""}{r.score_delta.toFixed(2)}
                </td>
                <td className={`py-2 text-xs font-semibold ${TREND_COLOUR[r.trend] ?? "text-slate-500"}`}>
                  {r.trend === "IMPROVING" ? <TrendingDown className="inline h-3.5 w-3.5 mr-1" /> : r.trend === "DETERIORATING" ? <TrendingUp className="inline h-3.5 w-3.5 mr-1" /> : null}
                  {r.trend}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SurveillancePage() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  // Watchlist form state
  const [showAddWatchlist, setShowAddWatchlist] = useState(false);
  const [wlSupplierId, setWlSupplierId] = useState("");
  const [wlReason, setWlReason] = useState("");
  const [wlSeverity, setWlSeverity] = useState("HIGH");

  // Episode form state
  const [showCreateEpisode, setShowCreateEpisode] = useState(false);
  const [epTitle, setEpTitle] = useState("");
  const [epDesc, setEpDesc] = useState("");
  const [epSeverity, setEpSeverity] = useState("HIGH");
  const [epSupplierId, setEpSupplierId] = useState("");

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["surveillance-dashboard"],
    queryFn: getSurveillanceDashboard,
    refetchInterval: 60_000,
  });

  const { data: signals, isLoading: signalsLoading } = useQuery({
    queryKey: ["surveillance-signals-active"],
    queryFn: getActiveSignals,
    refetchInterval: 60_000,
  });

  const { data: watchlist } = useQuery({
    queryKey: ["surveillance-watchlist"],
    queryFn: getWatchlist,
    refetchInterval: 120_000,
  });

  const { data: episodes } = useQuery({
    queryKey: ["surveillance-episodes-open"],
    queryFn: getOpenEpisodes,
    refetchInterval: 60_000,
  });

  const { data: byConnector, isLoading: connectorLoading } = useQuery({
    queryKey: ["signals-by-connector"],
    queryFn: getSignalsByConnector,
    staleTime: 0,
    refetchInterval: 120_000,
  });

  // Supplier name map
  const { data: execSuppliers = [] } = useQuery<Array<{ id: string; name: string }>>({
    queryKey: ["exec-suppliers-names"],
    queryFn: async () => (await apiClient.get("/executive/suppliers")).data,
    staleTime: 5 * 60_000,
  });

  const nameMap = useMemo(
    () => new Map<string, string>(execSuppliers.map((s) => [s.id, s.name])),
    [execSuppliers]
  );

  // Watchlist mutations
  const addWatchlist = useMutation({
    mutationFn: () => apiClient.post("/surveillance/watchlists", {
      supplier_id: wlSupplierId,
      watch_reason: wlReason,
      severity: wlSeverity,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["surveillance-watchlist"] });
      qc.invalidateQueries({ queryKey: ["surveillance-dashboard"] });
      setShowAddWatchlist(false);
      setWlSupplierId(""); setWlReason(""); setWlSeverity("HIGH");
    },
  });

  const removeWatchlist = useMutation({
    mutationFn: (supplierId: string) => apiClient.delete(`/surveillance/watchlists/${supplierId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["surveillance-watchlist"] });
      qc.invalidateQueries({ queryKey: ["surveillance-dashboard"] });
    },
  });

  // Episode mutation
  const createEpisode = useMutation({
    mutationFn: () => apiClient.post("/surveillance/episodes", {
      title: epTitle,
      description: epDesc,
      severity: epSeverity,
      supplier_id: epSupplierId || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["surveillance-episodes-open"] });
      qc.invalidateQueries({ queryKey: ["surveillance-dashboard"] });
      setShowCreateEpisode(false);
      setEpTitle(""); setEpDesc(""); setEpSeverity("HIGH"); setEpSupplierId("");
    },
  });

  if (dashLoading) {
    return <div className="flex justify-center items-center h-64"><Spinner /></div>;
  }

  const d = dashboard ?? {};
  const supplierOptions = Array.from(nameMap.entries());

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Radio className="h-6 w-6 text-primary" />
          {t("surveillance.pageTitle")}
        </h1>
        <p className="text-muted-foreground mt-1">{t("surveillance.pageSubtitle")}</p>
      </div>

      {/* Portfolio stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label={t("surveillance.activeSignals")} value={d.active_signals ?? 0} icon={Activity}
          colour={d.active_signals > 0 ? "text-orange-600" : undefined} />
        <StatCard label={t("surveillance.criticalSignals")} value={d.critical_signals ?? 0} icon={AlertTriangle}
          colour={d.critical_signals > 0 ? "text-red-600" : undefined} />
        <StatCard label={t("surveillance.suppliersAtRisk")} value={d.suppliers_at_risk ?? 0} icon={Shield}
          colour={d.suppliers_at_risk > 0 ? "text-orange-600" : undefined} />
        <StatCard label={t("surveillance.watchlist")} value={d.watchlist_count ?? 0} icon={Eye} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label={t("surveillance.improving")} value={d.suppliers_improving ?? 0} icon={TrendingUp} colour="text-green-600" />
        <StatCard label={t("surveillance.deteriorating")} value={d.suppliers_deteriorating ?? 0} icon={TrendingDown}
          colour={d.suppliers_deteriorating > 0 ? "text-red-600" : undefined} />
        <StatCard label={t("surveillance.openEpisodes")} value={d.open_episodes ?? 0} icon={Zap}
          colour={d.open_episodes > 0 ? "text-yellow-600" : undefined} />
        <StatCard label={t("surveillance.totalSuppliers")} value={d.total_suppliers ?? 0} icon={Shield} />
      </div>

      {/* External signals by connector */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Building2 className="h-4 w-4 text-muted-foreground" />
          <h2 className="font-semibold text-base">{t("surveillance.externalSignalsBySource")}</h2>
          <span className="text-xs text-muted-foreground">— {t("surveillance.topNHint")}</span>
        </div>
        {connectorLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
            <Loader2 className="h-4 w-4 animate-spin" /> {t("surveillance.loadingSignals")}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {(byConnector?.connectors ?? []).map((c) => (
              <ConnectorCard key={c.source_name} connector={c} />
            ))}
          </div>
        )}
      </div>

      {/* Heatmap */}
      <HeatmapSection />

      <div className="grid md:grid-cols-2 gap-6">
        {/* Active Signals */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("surveillance.activeSignals")}</CardTitle>
          </CardHeader>
          <CardContent>
            {signalsLoading ? (
              <Spinner />
            ) : (signals ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("surveillance.noActiveSignals")}</p>
            ) : (
              (signals ?? []).map((s: any) => <SignalRow key={s.id} signal={s} nameMap={nameMap} />)
            )}
          </CardContent>
        </Card>

        {/* Open Risk Episodes */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">{t("surveillance.openRiskEpisodes")}</CardTitle>
              <Button size="sm" variant="outline" className="gap-1.5 h-7 text-xs"
                onClick={() => setShowCreateEpisode(!showCreateEpisode)}>
                <Plus className="h-3.5 w-3.5" /> {t("surveillance.createEpisode")}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {showCreateEpisode && (
              <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-3">
                <div>
                  <Label className="text-xs">{t("surveillance.episodeTitle")} *</Label>
                  <Input className="mt-1 text-sm" value={epTitle}
                    onChange={(e) => setEpTitle(e.target.value)} />
                </div>
                <div>
                  <Label className="text-xs">{t("surveillance.episodeDesc")}</Label>
                  <Input className="mt-1 text-sm" value={epDesc}
                    onChange={(e) => setEpDesc(e.target.value)} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">{t("surveillance.episodeSeverity")}</Label>
                    <select className="mt-1 h-9 w-full rounded-md border border-slate-200 bg-white px-2 text-sm"
                      value={epSeverity} onChange={(e) => setEpSeverity(e.target.value)}>
                      {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div>
                    <Label className="text-xs">{t("surveillance.episodeSupplier")}</Label>
                    <select className="mt-1 h-9 w-full rounded-md border border-slate-200 bg-white px-2 text-sm"
                      value={epSupplierId} onChange={(e) => setEpSupplierId(e.target.value)}>
                      <option value="">— none —</option>
                      {supplierOptions.map(([id, n]) => <option key={id} value={id}>{n}</option>)}
                    </select>
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <Button size="sm" variant="outline" onClick={() => setShowCreateEpisode(false)}>
                    {t("common.cancel")}
                  </Button>
                  <Button size="sm" disabled={!epTitle || createEpisode.isPending}
                    onClick={() => createEpisode.mutate()} className="gap-1">
                    {createEpisode.isPending && <Spinner className="h-4 w-4" />}
                    {t("surveillance.createEpisode")}
                  </Button>
                </div>
              </div>
            )}
            {(episodes ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("surveillance.noOpenEpisodes")}</p>
            ) : (
              (episodes ?? []).map((e: any) => <EpisodeRow key={e.id} episode={e} nameMap={nameMap} />)
            )}
          </CardContent>
        </Card>

        {/* Watchlist */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">{t("surveillance.watchlist")}</CardTitle>
              <Button size="sm" variant="outline" className="gap-1.5 h-7 text-xs"
                onClick={() => setShowAddWatchlist(!showAddWatchlist)}>
                <Plus className="h-3.5 w-3.5" /> {t("surveillance.addToWatchlist")}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {showAddWatchlist && (
              <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-3">
                <div>
                  <Label className="text-xs">{t("surveillance.supplierLabel")} *</Label>
                  <select className="mt-1 h-9 w-full rounded-md border border-slate-200 bg-white px-2 text-sm"
                    value={wlSupplierId} onChange={(e) => setWlSupplierId(e.target.value)}>
                    <option value="">— select —</option>
                    {supplierOptions.map(([id, n]) => <option key={id} value={id}>{n}</option>)}
                  </select>
                </div>
                <div>
                  <Label className="text-xs">{t("surveillance.watchReason")} *</Label>
                  <Input className="mt-1 text-sm" value={wlReason}
                    onChange={(e) => setWlReason(e.target.value)} />
                </div>
                <div>
                  <Label className="text-xs">{t("surveillance.episodeSeverity")}</Label>
                  <select className="mt-1 h-9 w-full rounded-md border border-slate-200 bg-white px-2 text-sm"
                    value={wlSeverity} onChange={(e) => setWlSeverity(e.target.value)}>
                    {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div className="flex justify-end gap-2">
                  <Button size="sm" variant="outline" onClick={() => setShowAddWatchlist(false)}>
                    {t("common.cancel")}
                  </Button>
                  <Button size="sm" disabled={!wlSupplierId || !wlReason || addWatchlist.isPending}
                    onClick={() => addWatchlist.mutate()} className="gap-1">
                    {addWatchlist.isPending && <Spinner className="h-4 w-4" />}
                    {t("surveillance.addToWatchlist")}
                  </Button>
                </div>
              </div>
            )}
            {(watchlist ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("surveillance.noWatchlistSuppliers")}</p>
            ) : (
              (watchlist ?? []).map((w: any) => (
                <div key={w.id} className="flex items-start justify-between py-3 border-b last:border-0">
                  <div className="flex-1 min-w-0 mr-3">
                    <p className="text-sm font-medium truncate">
                      {nameMap.get(w.supplier_id) ?? w.supplier_id.slice(0, 12) + "…"}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">{w.watch_reason}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <SeverityBadge severity={w.severity} />
                    <button
                      onClick={() => removeWatchlist.mutate(w.supplier_id)}
                      disabled={removeWatchlist.isPending}
                      className="rounded p-1 text-muted-foreground hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                      title={t("surveillance.removeFromWatchlist")}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Portfolio Health */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("surveillance.portfolioHealth")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { labelKey: "surveillance.improvingSuppliers" as const, value: d.suppliers_improving ?? 0, colour: "bg-green-500" },
              { labelKey: "surveillance.stableSuppliers" as const, value: d.suppliers_stable ?? 0, colour: "bg-blue-400" },
              { labelKey: "surveillance.deterioratingSuppliers" as const, value: d.suppliers_deteriorating ?? 0, colour: "bg-red-500" },
              { labelKey: "surveillance.needingReview" as const, value: d.suppliers_needing_review ?? 0, colour: "bg-yellow-500" },
            ].map((row) => (
              <div key={row.labelKey} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>{t(row.labelKey)}</span>
                  <span className="font-medium">{row.value}</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className={`h-full ${row.colour} rounded-full`}
                    style={{
                      width: d.total_suppliers > 0
                        ? `${Math.min(100, (row.value / d.total_suppliers) * 100)}%`
                        : "0%",
                    }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Risk Trends */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("surveillance.riskTrends")}</CardTitle>
        </CardHeader>
        <CardContent>
          <TrendsSection nameMap={nameMap} />
        </CardContent>
      </Card>
    </div>
  );
}
