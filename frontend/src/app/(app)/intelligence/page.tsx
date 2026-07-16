"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Cpu,
  Database,
  Eye,
  Globe,
  Layers,
  Lightbulb,
  Loader2,
  Plus,
  Radio,
  RefreshCw,
  Shield,
  ShieldAlert,
  Trash2,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import apiClient from "@/lib/api/client";
import {
  crossAnalyze,
  listCrossAlerts,
  listDocQuality,
  listExternalSignalsForSupplier,
  listMetrics,
  listSignals,
  updateCrossAlertStatus,
  formatValue,
  NACE_LABELS,
  RELATION_LABELS,
  IMPACT_TYPE_LABELS,
  DIMENSION_LABELS,
  SEVERITY_ORDER,
  type CrossAlert,
  type CrossAnalyzeRequest,
  type CompanyMetric,
  type CompanySignal,
  type DocQuality,
} from "@/lib/api/intelligence";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import { formatDateTime } from "@/lib/utils";

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

// ── Surveillance ──────────────────────────────────────────────────────────────
interface SurvDashboard {
  active_signals: number;
  critical_signals: number;
  suppliers_at_risk: number;
  watchlist_count: number;
  suppliers_improving: number;
  suppliers_deteriorating: number;
  suppliers_stable: number;
  suppliers_needing_review: number;
  open_episodes: number;
  total_suppliers: number;
}

// ── Digital Twin (Supplier Intelligence) ─────────────────────────────────────
interface HealthDimension { name: string; label: string; score: number; status: string }
interface DigitalTwin {
  id: string;
  supplier_id: string;
  overall_health: number;
  health_trend: string;
  ai_confidence: number;
  open_recommendations: number;
  open_actions: number;
  event_count: number;
  critical_event_count: number;
  last_event_at: string | null;
  last_updated_at: string;
  twin_version: number;
  dimensions: HealthDimension[];
}
interface TimelineEvent {
  id: string;
  event_type: string;
  event_category: string;
  severity: string;
  title: string;
  summary: string;
  why_important: string;
  regulatory_impact: string;
  recommended_action: string;
  source_name: string;
  twin_dimension_affected: string;
  health_delta: number;
  confidence: number;
  occurred_at: string;
}
interface ExecSupplier { id: string; name: string }
interface CollectResult {
  sources_attempted: number;
  sources_ok: number;
  signals_created: number;
  twins_updated: number;
  events_created: number;
  duration_seconds: number;
  errors: string[];
  message: string;
}

// ── External Intelligence ─────────────────────────────────────────────────────
interface RiskSignal {
  id: string;
  signal_type: string;
  severity: string;
  description: string;
  source_name: string;
  observed_at: string;
  country_code: string;
  supplier_id: string;
}
interface ConnectorGroup { source_name: string; label: string; total: number; signals: RiskSignal[] }
interface CountryRisk {
  id: string;
  country_code: string;
  country_name: string;
  governance_score: number;
  corruption_score: number;
  labour_rights_score: number;
  environmental_risk_score: number;
  human_rights_score: number;
  overall_risk_score: number;
  risk_level: string;
  sanctions_status: string;
}
interface SectorBenchmark {
  id: string;
  sector_name: string;
  nace_code: string;
  average_esg_score: number;
  average_risk_score: number;
  average_compliance_coverage: number;
  p25_esg_score: number;
  p50_esg_score: number;
  p75_esg_score: number;
  supplier_count: number;
}
interface SupplierEnrichment {
  id: string;
  supplier_id: string;
  country_code: string;
  country_risk_level: string;
  sanctions_exposure: string;
  sector_percentile: number;
  percentile_rank: string;
  external_risk_score: number;
  combined_risk_score: number;
  active_signal_count: number;
  enriched_at: string;
}
interface ExtDataset {
  id: string;
  source_name: string;
  source_version: string;
  dataset_status: string;
  valid_from: string;
  valid_until?: string;
  record_count?: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// SHARED HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

const SURV_SEV_COLOUR: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high:     "bg-orange-100 text-orange-700 border-orange-200",
  medium:   "bg-amber-100 text-amber-700 border-amber-200",
  low:      "bg-slate-100 text-slate-600 border-slate-200",
};

const EXT_RISK_LEVEL_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high:     "bg-orange-100 text-orange-700",
  medium:   "bg-amber-100 text-amber-700",
  low:      "bg-green-100 text-green-700",
};

const TWIN_SEV_COLORS: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-700 border-red-200",
  HIGH:     "bg-orange-100 text-orange-700 border-orange-200",
  MEDIUM:   "bg-amber-100 text-amber-700 border-amber-200",
  LOW:      "bg-slate-100 text-slate-600 border-slate-200",
};

const HEALTH_STATUS_COLORS: Record<string, { bg: string; text: string; ring: string }> = {
  HEALTHY:  { bg: "bg-green-50",  text: "text-green-700",  ring: "stroke-green-500" },
  MODERATE: { bg: "bg-blue-50",   text: "text-blue-700",   ring: "stroke-blue-400" },
  AT_RISK:  { bg: "bg-amber-50",  text: "text-amber-700",  ring: "stroke-amber-400" },
  CRITICAL: { bg: "bg-red-50",    text: "text-red-700",    ring: "stroke-red-500" },
};

const TREND_COLOUR: Record<string, string> = {
  IMPROVING:    "text-green-600",
  STABLE:       "text-blue-500",
  DETERIORATING:"text-red-600",
  VOLATILE:     "text-amber-600",
};

const SURV_CONNECTOR_ICONS: Record<string, string> = {
  world_bank:                "🌍",
  transparency_international:"🔍",
  ilo:                       "⚙️",
  unicef:                    "🧒",
  un_sanctions:              "🚫",
  eu_sanctions:              "🇪🇺",
};

const EXT_CONNECTOR_LABELS: Record<string, string> = {
  world_bank:                "World Bank",
  transparency_international:"Transparency International",
  ilo:                       "ILO",
  unicef:                    "UNICEF",
  un_sanctions:              "UN Sanctions",
  eu_sanctions:              "EU Sanctions",
};

// Severity badge for surveillance (uses Badge component variant)
function SurvSevBadge({ severity }: { severity: string }) {
  const variantMap: Record<string, string> = {
    CRITICAL: "destructive", HIGH: "warning", MEDIUM: "secondary", LOW: "outline", INFO: "outline",
  };
  return <Badge variant={(variantMap[severity] ?? "secondary") as any}>{severity}</Badge>;
}

// Severity badge for ext-intel (inline span)
function ExtSevBadge({ severity }: { severity: string }) {
  const s = severity.toLowerCase();
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${SURV_SEV_COLOUR[s] ?? "bg-slate-100 text-slate-500 border-slate-200"}`}>
      {s}
    </span>
  );
}

// Severity badge for twin feed (inline span, uppercase)
function TwinSevBadge({ severity }: { severity: string }) {
  const s = severity.toUpperCase();
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${TWIN_SEV_COLORS[s] ?? "bg-slate-100 text-slate-500 border-slate-200"}`}>
      {s}
    </span>
  );
}

function RiskBadge({ level }: { level: string }) {
  const l = level.toLowerCase();
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${EXT_RISK_LEVEL_COLORS[l] ?? "bg-slate-100 text-slate-500"}`}>
      {l}
    </span>
  );
}

function ScoreCell({ value, invert = false }: { value: number; invert?: boolean }) {
  const pct = value <= 1 ? value * 100 : value;
  const good = invert ? pct < 40 : pct >= 60;
  const warn = invert ? pct < 70 : pct >= 40;
  return <span className={`font-medium tabular-nums ${good ? "text-green-700" : warn ? "text-amber-700" : "text-red-700"}`}>{pct.toFixed(0)}</span>;
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

// Shared supplier name hook
function useSupplierNameMap() {
  const { data: suppliers = [] } = useQuery<ExecSupplier[]>({
    queryKey: ["exec-suppliers-names"],
    queryFn: async () => (await apiClient.get("/executive/suppliers")).data,
    staleTime: 5 * 60_000,
  });
  return useMemo(() => new Map<string, string>(suppliers.map((s) => [s.id, s.name])), [suppliers]);
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 1 — SIGNALE & EPISODEN (Surveillance)
// ═══════════════════════════════════════════════════════════════════════════════

function SurvSignalRow({ signal, nameMap }: { signal: any; nameMap: Map<string, string> }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [riskCreated, setRiskCreated] = useState(false);
  const [localStatus, setLocalStatus] = useState<string>(signal.signal_status);
  const [expanded, setExpanded] = useState(false);

  const createRisk = useMutation({
    mutationFn: async () =>
      (await apiClient.post("/risks/", {
        title: `[Signal] ${signal.title}`,
        risk_level: signal.severity === "HIGH" || signal.severity === "CRITICAL"
          ? signal.severity.charAt(0) + signal.severity.slice(1).toLowerCase()
          : "Medium",
        status: "Draft",
        category: signal.signal_type ?? "Surveillance",
      })).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["org-risks"] }); setRiskCreated(true); },
  });

  const acknowledge = useMutation({
    mutationFn: () => apiClient.post(`/surveillance/signals/${signal.id}/acknowledge`),
    onSuccess: () => {
      setLocalStatus("ACKNOWLEDGED");
      qc.invalidateQueries({ queryKey: ["surv-signals-active"] });
      qc.invalidateQueries({ queryKey: ["surv-dashboard"] });
    },
  });

  const dismiss = useMutation({
    mutationFn: () => apiClient.post(`/surveillance/signals/${signal.id}/dismiss`),
    onSuccess: () => {
      setLocalStatus("DISMISSED");
      qc.invalidateQueries({ queryKey: ["surv-signals-active"] });
      qc.invalidateQueries({ queryKey: ["surv-dashboard"] });
    },
  });

  const isDone = localStatus === "ACKNOWLEDGED" || localStatus === "DISMISSED";
  const supplierName = signal.supplier_id ? (nameMap.get(signal.supplier_id) ?? signal.supplier_id.slice(0, 10) + "…") : null;

  const expl = signal.explainability_json ?? {};

  return (
    <div className="py-3 border-b last:border-0 space-y-1.5">
      <div className="flex items-start justify-between gap-3">
        <button
          className="flex-1 min-w-0 text-left"
          onClick={() => setExpanded(v => !v)}
        >
          <p className={`text-sm font-medium ${expanded ? "" : "truncate"}`}>{signal.title}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {signal.signal_type}{supplierName ? ` · ${supplierName}` : ""}{" · "}{formatDateTime(signal.detected_at)}
            <span className="ml-1 text-blue-500">{expanded ? "▲" : "▼"}</span>
          </p>
        </button>
        <SurvSevBadge severity={signal.severity} />
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
            <button onClick={() => acknowledge.mutate()} disabled={acknowledge.isPending}
              className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700 hover:bg-blue-100 transition-colors disabled:opacity-50">
              {acknowledge.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle2 className="h-3 w-3" />}
              {t("surveillance.acknowledge")}
            </button>
            <button onClick={() => dismiss.mutate()} disabled={dismiss.isPending}
              className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600 hover:bg-slate-200 transition-colors disabled:opacity-50">
              {dismiss.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
              {t("surveillance.dismiss")}
            </button>
          </>
        )}
        {/* Szenario-Analyse Link */}
        <Link
          href={`/intelligence/scenario?signal=${encodeURIComponent(signal.title)}&company=${encodeURIComponent(supplierName ?? "")}`}
          className="inline-flex items-center gap-1 rounded bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700 hover:bg-amber-100 transition-colors border border-amber-200"
        >
          <Zap className="h-3 w-3" /> Szenario projizieren
        </Link>

        {riskCreated ? (
          <span className="flex items-center gap-2 ml-auto">
            <span className="flex items-center gap-1 text-[10px] text-emerald-600 font-medium">
              <CheckCircle2 className="h-3 w-3" /> {t("surveillance.riskCreated")}
            </span>
            {signal.supplier_id && (
              <Link
                href={`/suppliers/${signal.supplier_id}`}
                className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700 hover:bg-blue-100 transition-colors"
              >
                <ShieldAlert className="h-3 w-3" /> {t("surveillance.supplierReassess")}
              </Link>
            )}
          </span>
        ) : (
          <button onClick={() => createRisk.mutate()} disabled={createRisk.isPending}
            className="inline-flex items-center gap-1 rounded bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700 hover:bg-red-100 transition-colors disabled:opacity-50 ml-auto">
            {createRisk.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <ShieldAlert className="h-3 w-3" />}
            {t("surveillance.createRisk")}
          </button>
        )}
      </div>
    </div>
  );
}

function SurvEpisodeRow({ episode, nameMap }: { episode: any; nameMap: Map<string, string> }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [localStatus, setLocalStatus] = useState<string>(episode.episode_status);

  const transition = useMutation({
    mutationFn: (newStatus: string) =>
      apiClient.post(`/surveillance/episodes/${episode.id}/transition`, { new_status: newStatus }),
    onSuccess: (_, newStatus) => {
      setLocalStatus(newStatus);
      qc.invalidateQueries({ queryKey: ["surv-episodes-open"] });
      qc.invalidateQueries({ queryKey: ["surv-dashboard"] });
    },
  });

  const supplierName = episode.supplier_id ? (nameMap.get(episode.supplier_id) ?? episode.supplier_id.slice(0, 10) + "…") : null;
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
            {episode.signal_count} {episode.signal_count === 1 ? t("surveillance.signalSingular") : t("surveillance.signalPlural")}
            {supplierName ? ` · ${supplierName}` : ""}{" · "}{formatDateTime(episode.started_at)}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <SurvSevBadge severity={episode.severity} />
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">{localStatus}</span>
        </div>
      </div>
      {next.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] text-muted-foreground">{t("surveillance.transitionTo")}:</span>
          {next.map((s) => (
            <button key={s} onClick={() => transition.mutate(s)} disabled={transition.isPending}
              className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-700 hover:bg-blue-50 hover:text-blue-700 transition-colors disabled:opacity-50">
              {t((`surveillance.${s.toLowerCase()}`) as Parameters<typeof t>[0]) || s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SurvConnectorCard({ connector }: {
  connector: { source_name: string; label: string; total: number; signals: any[] };
}) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? connector.signals : connector.signals.slice(0, 3);
  const icon = SURV_CONNECTOR_ICONS[connector.source_name] ?? "📡";
  const hasSignals = connector.total > 0;

  return (
    <Card className={hasSignals ? "border-orange-200" : ""}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <span className="text-base">{icon}</span>{connector.label}
          </CardTitle>
          {hasSignals
            ? <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-700">{connector.total} {t("surveillance.signalCount")}</span>
            : <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">{t("surveillance.clear")}</span>}
        </div>
      </CardHeader>
      <CardContent>
        {!hasSignals ? (
          <p className="text-xs text-muted-foreground py-1">{t("surveillance.noSignalsForSuppliers")}</p>
        ) : (
          <div className="space-y-1.5">
            {shown.map((s: any) => (
              <div key={s.id} className={`rounded border px-2.5 py-2 ${SURV_SEV_COLOUR[(s.severity ?? "").toLowerCase()] ?? "bg-slate-50 border-slate-200"}`}>
                <p className="text-xs font-medium leading-snug line-clamp-2">{s.description}</p>
                <p className="text-[10px] opacity-70 mt-0.5">{s.signal_type?.replace(/_/g, " ")}{s.country_code ? ` · ${s.country_code}` : ""}</p>
              </div>
            ))}
            {connector.signals.length > 3 && (
              <button onClick={() => setExpanded((e) => !e)} className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground mt-1">
                {expanded
                  ? <><ChevronUp className="h-3 w-3" /> {t("surveillance.showLess")}</>
                  : <><ChevronDown className="h-3 w-3" /> {t("surveillance.showMore").replace("{n}", String(connector.signals.length - 3))}</>}
              </button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

const SEV_HEAT: Record<string, string> = {
  CRITICAL: "bg-red-600 text-white",
  HIGH:     "bg-orange-400 text-white",
  MEDIUM:   "bg-amber-300 text-slate-800",
  LOW:      "bg-emerald-100 text-emerald-800",
};

function SurvHeatmapSection() {
  const { t } = useLanguage();
  const [dimension, setDimension] = useState<"sector" | "country" | "risk_type">("sector");

  const { data = [], isLoading } = useQuery<Array<{ dimension: string; key: string; signal_count: number; max_severity: string }>>({
    queryKey: ["surv-heatmap", dimension],
    queryFn: async () => (await apiClient.get(`/surveillance/heatmaps/${dimension}`)).data,
    staleTime: 60_000,
  });

  const dims: Array<{ value: "sector" | "country" | "risk_type"; labelKey: "surveillance.heatmapBySector" | "surveillance.heatmapByCountry" | "surveillance.heatmapByRiskType" }> = [
    { value: "sector",    labelKey: "surveillance.heatmapBySector" },
    { value: "country",   labelKey: "surveillance.heatmapByCountry" },
    { value: "risk_type", labelKey: "surveillance.heatmapByRiskType" },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <CardTitle className="text-base">{t("surveillance.heatmap")}</CardTitle>
          <div className="flex gap-1">
            {dims.map((d) => (
              <button key={d.value} onClick={() => setDimension(d.value)}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${dimension === d.value ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
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
              <div key={cell.key}
                className={`rounded-lg px-3 py-2 text-center min-w-[80px] border ${SEV_HEAT[cell.max_severity] ?? "bg-slate-50 text-slate-600 border-slate-200"}`}>
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

function SurvTrendsSection({ nameMap }: { nameMap: Map<string, string> }) {
  const { t } = useLanguage();
  const { data = [], isLoading } = useQuery({
    queryKey: ["surv-trends"],
    queryFn: async () => (await apiClient.get("/surveillance/trends?limit=24")).data as Array<{
      id: string; supplier_id: string; period: string; score_delta: number; trend: string; confidence: number;
    }>,
    staleTime: 60_000,
  });

  if (isLoading) return <div className="flex justify-center py-8"><Spinner /></div>;
  if (data.length === 0) return <p className="text-sm text-muted-foreground py-4 text-center">{t("surveillance.noTrends")}</p>;

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
                  {r.trend === "IMPROVING"
                    ? <TrendingDown className="inline h-3.5 w-3.5 mr-1" />
                    : r.trend === "DETERIORATING"
                    ? <TrendingUp className="inline h-3.5 w-3.5 mr-1" />
                    : null}
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

function SurveillanceTab({ nameMap }: { nameMap: Map<string, string> }) {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const [showAddWatchlist, setShowAddWatchlist] = useState(false);
  const [wlSupplierId, setWlSupplierId] = useState("");
  const [wlReason, setWlReason] = useState("");
  const [wlSeverity, setWlSeverity] = useState("HIGH");

  const [showCreateEpisode, setShowCreateEpisode] = useState(false);
  const [epTitle, setEpTitle] = useState("");
  const [epDesc, setEpDesc] = useState("");
  const [epSeverity, setEpSeverity] = useState("HIGH");
  const [epSupplierId, setEpSupplierId] = useState("");

  const { data: dashboard, isLoading: dashLoading } = useQuery<SurvDashboard>({
    queryKey: ["surv-dashboard"],
    queryFn: async () => (await apiClient.get("/surveillance/dashboard")).data,
    refetchInterval: 60_000,
  });

  const { data: signals, isLoading: signalsLoading } = useQuery({
    queryKey: ["surv-signals-active"],
    queryFn: async () => (await apiClient.get("/surveillance/signals?signal_status=ACTIVE&limit=20")).data,
    refetchInterval: 60_000,
  });

  const { data: watchlist } = useQuery({
    queryKey: ["surv-watchlist"],
    queryFn: async () => (await apiClient.get("/surveillance/watchlists?active_only=true&limit=50")).data,
    refetchInterval: 120_000,
  });

  const { data: episodes } = useQuery({
    queryKey: ["surv-episodes-open"],
    queryFn: async () => (await apiClient.get("/surveillance/episodes?episode_status=OPEN&limit=20")).data,
    refetchInterval: 60_000,
  });

  const { data: byConnector, isLoading: connectorLoading } = useQuery({
    queryKey: ["surv-signals-by-connector"],
    queryFn: async () => (await apiClient.get("/external-intelligence/signals/by-connector?top_n=10")).data as { connectors: any[] },
    staleTime: 0,
    refetchInterval: 120_000,
  });

  const addWatchlist = useMutation({
    mutationFn: () => apiClient.post("/surveillance/watchlists", { supplier_id: wlSupplierId, watch_reason: wlReason, severity: wlSeverity }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["surv-watchlist"] });
      qc.invalidateQueries({ queryKey: ["surv-dashboard"] });
      setShowAddWatchlist(false);
      setWlSupplierId(""); setWlReason(""); setWlSeverity("HIGH");
    },
  });

  const removeWatchlist = useMutation({
    mutationFn: (supplierId: string) => apiClient.delete(`/surveillance/watchlists/${supplierId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["surv-watchlist"] });
      qc.invalidateQueries({ queryKey: ["surv-dashboard"] });
    },
  });

  const createEpisode = useMutation({
    mutationFn: () => apiClient.post("/surveillance/episodes", {
      title: epTitle, description: epDesc, severity: epSeverity, supplier_id: epSupplierId || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["surv-episodes-open"] });
      qc.invalidateQueries({ queryKey: ["surv-dashboard"] });
      setShowCreateEpisode(false);
      setEpTitle(""); setEpDesc(""); setEpSeverity("HIGH"); setEpSupplierId("");
    },
  });

  if (dashLoading) return <div className="flex justify-center items-center h-64"><Spinner /></div>;

  const d = dashboard ?? ({} as SurvDashboard);
  const supplierOptions = Array.from(nameMap.entries());

  return (
    <div className="space-y-6">
      {/* Portfolio KPIs — row 1 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label={t("surveillance.activeSignals")} value={d.active_signals ?? 0} icon={Activity} colour={d.active_signals > 0 ? "text-orange-600" : undefined} />
        <StatCard label={t("surveillance.criticalSignals")} value={d.critical_signals ?? 0} icon={AlertTriangle} colour={d.critical_signals > 0 ? "text-red-600" : undefined} />
        <StatCard label={t("surveillance.suppliersAtRisk")} value={d.suppliers_at_risk ?? 0} icon={Shield} colour={d.suppliers_at_risk > 0 ? "text-orange-600" : undefined} />
        <StatCard label={t("surveillance.watchlist")} value={d.watchlist_count ?? 0} icon={Eye} />
      </div>
      {/* Portfolio KPIs — row 2 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label={t("surveillance.improving")} value={d.suppliers_improving ?? 0} icon={TrendingUp} colour="text-green-600" />
        <StatCard label={t("surveillance.deteriorating")} value={d.suppliers_deteriorating ?? 0} icon={TrendingDown} colour={d.suppliers_deteriorating > 0 ? "text-red-600" : undefined} />
        <StatCard label={t("surveillance.openEpisodes")} value={d.open_episodes ?? 0} icon={Zap} colour={d.open_episodes > 0 ? "text-yellow-600" : undefined} />
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
            {(byConnector?.connectors ?? []).map((c) => <SurvConnectorCard key={c.source_name} connector={c} />)}
          </div>
        )}
      </div>

      {/* Heatmap */}
      <SurvHeatmapSection />

      <div className="grid md:grid-cols-2 gap-6">
        {/* Active Signals */}
        <Card>
          <CardHeader><CardTitle className="text-base">{t("surveillance.activeSignals")}</CardTitle></CardHeader>
          <CardContent>
            {signalsLoading ? <Spinner /> : (signals ?? []).length === 0
              ? <p className="text-sm text-muted-foreground">{t("surveillance.noActiveSignals")}</p>
              : (signals ?? []).map((s: any) => <SurvSignalRow key={s.id} signal={s} nameMap={nameMap} />)}
          </CardContent>
        </Card>

        {/* Open Episodes */}
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
                  <Input className="mt-1 text-sm" value={epTitle} onChange={(e) => setEpTitle(e.target.value)} />
                </div>
                <div>
                  <Label className="text-xs">{t("surveillance.episodeDesc")}</Label>
                  <Input className="mt-1 text-sm" value={epDesc} onChange={(e) => setEpDesc(e.target.value)} />
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
                      <option value="">— {t("common.none")} —</option>
                      {supplierOptions.map(([id, n]) => <option key={id} value={id}>{n}</option>)}
                    </select>
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <Button size="sm" variant="outline" onClick={() => setShowCreateEpisode(false)}>{t("common.cancel")}</Button>
                  <Button size="sm" disabled={!epTitle || createEpisode.isPending}
                    onClick={() => createEpisode.mutate()} className="gap-1">
                    {createEpisode.isPending && <Spinner className="h-4 w-4" />}
                    {t("surveillance.createEpisode")}
                  </Button>
                </div>
              </div>
            )}
            {(episodes ?? []).length === 0
              ? <p className="text-sm text-muted-foreground">{t("surveillance.noOpenEpisodes")}</p>
              : (episodes ?? []).map((e: any) => <SurvEpisodeRow key={e.id} episode={e} nameMap={nameMap} />)}
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
                    <option value="">— {t("common.none")} —</option>
                    {supplierOptions.map(([id, n]) => <option key={id} value={id}>{n}</option>)}
                  </select>
                </div>
                <div>
                  <Label className="text-xs">{t("surveillance.watchReason")} *</Label>
                  <Input className="mt-1 text-sm" value={wlReason} onChange={(e) => setWlReason(e.target.value)} />
                </div>
                <div>
                  <Label className="text-xs">{t("surveillance.episodeSeverity")}</Label>
                  <select className="mt-1 h-9 w-full rounded-md border border-slate-200 bg-white px-2 text-sm"
                    value={wlSeverity} onChange={(e) => setWlSeverity(e.target.value)}>
                    {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div className="flex justify-end gap-2">
                  <Button size="sm" variant="outline" onClick={() => setShowAddWatchlist(false)}>{t("common.cancel")}</Button>
                  <Button size="sm" disabled={!wlSupplierId || !wlReason || addWatchlist.isPending}
                    onClick={() => addWatchlist.mutate()} className="gap-1">
                    {addWatchlist.isPending && <Spinner className="h-4 w-4" />}
                    {t("surveillance.addToWatchlist")}
                  </Button>
                </div>
              </div>
            )}
            {(watchlist ?? []).length === 0
              ? <p className="text-sm text-muted-foreground">{t("surveillance.noWatchlistSuppliers")}</p>
              : (watchlist ?? []).map((w: any) => (
                <div key={w.id} className="flex items-start justify-between py-3 border-b last:border-0">
                  <div className="flex-1 min-w-0 mr-3">
                    <p className="text-sm font-medium truncate">{nameMap.get(w.supplier_id) ?? w.supplier_id.slice(0, 12) + "…"}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">{w.watch_reason}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <SurvSevBadge severity={w.severity} />
                    <button onClick={() => removeWatchlist.mutate(w.supplier_id)} disabled={removeWatchlist.isPending}
                      className="rounded p-1 text-muted-foreground hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                      title={t("surveillance.removeFromWatchlist")}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
          </CardContent>
        </Card>

        {/* Portfolio Health */}
        <Card>
          <CardHeader><CardTitle className="text-base">{t("surveillance.portfolioHealth")}</CardTitle></CardHeader>
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
                  <div className={`h-full ${row.colour} rounded-full`}
                    style={{ width: d.total_suppliers > 0 ? `${Math.min(100, (row.value / d.total_suppliers) * 100)}%` : "0%" }} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Risk Trends */}
      <Card>
        <CardHeader><CardTitle className="text-base">{t("surveillance.riskTrends")}</CardTitle></CardHeader>
        <CardContent><SurvTrendsSection nameMap={nameMap} /></CardContent>
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 2 — SUPPLIER INTELLIGENCE (Digital Twin)
// ═══════════════════════════════════════════════════════════════════════════════

function TwinHealthRing({ score, status, size = 80 }: { score: number; status: string; size?: number }) {
  const r = (size / 2) - 8;
  const circ = 2 * Math.PI * r;
  const dash = circ * Math.min(1, score / 100);
  const c = HEALTH_STATUS_COLORS[status] ?? HEALTH_STATUS_COLORS.MODERATE;
  return (
    <svg width={size} height={size} className="rotate-[-90deg]">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#f1f5f9" strokeWidth={6} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none"
        className={c.ring} strokeWidth={6}
        strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" />
    </svg>
  );
}

function TwinHealthBadge({ status }: { status: string }) {
  const c = HEALTH_STATUS_COLORS[status] ?? HEALTH_STATUS_COLORS.MODERATE;
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${c.bg} ${c.text}`}>{status.replace("_", " ")}</span>;
}

function TwinDimCard({ dim }: { dim: HealthDimension }) {
  const c = HEALTH_STATUS_COLORS[dim.status] ?? HEALTH_STATUS_COLORS.MODERATE;
  return (
    <div className={`rounded-lg border p-3 ${c.bg}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-600">{dim.label}</span>
        <TwinHealthBadge status={dim.status} />
      </div>
      <div className="flex items-center gap-2">
        <div className="h-1.5 flex-1 rounded-full bg-white/60">
          <div className={`h-1.5 rounded-full ${c.ring.replace("stroke-", "bg-")}`} style={{ width: `${Math.min(100, dim.score)}%` }} />
        </div>
        <span className={`text-sm font-bold tabular-nums ${c.text}`}>{dim.score.toFixed(0)}</span>
      </div>
    </div>
  );
}

function TwinFeedSection({ orgId }: { orgId: string }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [minSeverity, setMinSeverity] = useState("MEDIUM");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [collectResult, setCollectResult] = useState<CollectResult | null>(null);

  const { data: feed, isLoading, refetch } = useQuery<{ events: TimelineEvent[]; total: number }>({
    queryKey: ["twin-feed", orgId, minSeverity],
    queryFn: async () => (await apiClient.get(`/intelligence/feed?limit=50&min_severity=${minSeverity}`)).data,
    staleTime: 60_000,
    enabled: !!orgId,
  });

  const collect = useMutation({
    mutationFn: async (): Promise<CollectResult> => (await apiClient.post("/intelligence/collect")).data,
    onSuccess: (data) => { setCollectResult(data); qc.invalidateQueries({ queryKey: ["twin-feed"] }); },
  });

  const events = feed?.events ?? [];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex gap-1.5">
          {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => (
            <button key={s} onClick={() => setMinSeverity(s)}
              className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${minSeverity === s ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"}`}>
              {t("twin.minSev")} {s}
            </button>
          ))}
        </div>
        <div className="ml-auto flex gap-2">
          <Button variant="outline" size="sm" className="gap-1.5 h-8" onClick={() => refetch()}>
            <RefreshCw className="h-3.5 w-3.5" /> {t("twin.refresh")}
          </Button>
          <Button size="sm" className="gap-1.5 h-8" onClick={() => collect.mutate()} disabled={collect.isPending}>
            {collect.isPending ? <Spinner className="h-3.5 w-3.5" /> : <Cpu className="h-3.5 w-3.5" />}
            {t("twin.collectIntelligence")}
          </Button>
        </div>
      </div>

      {collectResult && (
        <Card className={collectResult.errors.length > 0 ? "border-amber-200 bg-amber-50" : "border-green-200 bg-green-50"}>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm font-medium text-slate-800 mb-2">{collectResult.message}</p>
            <div className="flex flex-wrap gap-4 text-xs text-slate-600">
              <span>{t("twin.sourcesOk")}: <strong>{collectResult.sources_ok}/{collectResult.sources_attempted}</strong></span>
              <span>{t("twin.signalsCreated")}: <strong>{collectResult.signals_created}</strong></span>
              <span>{t("twin.twinsUpdated")}: <strong>{collectResult.twins_updated}</strong></span>
              <span>{t("twin.eventsCreated")}: <strong>{collectResult.events_created}</strong></span>
              <span>{t("twin.duration")}: <strong>{collectResult.duration_seconds.toFixed(1)}s</strong></span>
            </div>
            {collectResult.errors.length > 0 && (
              <div className="mt-2 space-y-0.5">
                {collectResult.errors.map((e, i) => <p key={i} className="text-xs text-amber-700">{e}</p>)}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : events.length === 0 ? (
        <Card>
          <CardContent className="py-14 text-center">
            <Cpu className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="font-medium text-slate-600">{t("twin.noFeedEvents")}</p>
            <p className="mt-1 text-sm text-slate-400">{t("twin.noFeedEventsDesc")}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {events.map((ev) => {
            const open = expanded === ev.id;
            return (
              <Card key={ev.id} className={open ? "border-blue-200" : ""}>
                <CardContent className="pt-3 pb-3">
                  <button className="flex w-full items-start gap-3 text-left" onClick={() => setExpanded(open ? null : ev.id)}>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <TwinSevBadge severity={ev.severity} />
                        <span className="text-xs text-slate-400 capitalize">{ev.event_category?.replace(/_/g, " ")}</span>
                        {ev.twin_dimension_affected && (
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500 capitalize">{ev.twin_dimension_affected.replace(/_/g, " ")}</span>
                        )}
                        <span className="ml-auto text-xs text-slate-400 shrink-0">{ev.occurred_at ? new Date(ev.occurred_at).toLocaleDateString() : "—"}</span>
                      </div>
                      <p className="font-semibold text-slate-800 text-sm">{ev.title}</p>
                      <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{ev.summary}</p>
                    </div>
                    <span className="shrink-0 mt-0.5 text-slate-400">{open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}</span>
                  </button>
                  {open && (
                    <div className="mt-3 border-t border-slate-100 pt-3 space-y-3 text-sm">
                      {ev.why_important && (
                        <div>
                          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">{t("twin.whyImportant")}</p>
                          <p className="text-slate-700">{ev.why_important}</p>
                        </div>
                      )}
                      {ev.regulatory_impact && (
                        <div>
                          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">{t("twin.regulatoryImpact")}</p>
                          <p className="text-slate-700">{ev.regulatory_impact}</p>
                        </div>
                      )}
                      {ev.recommended_action && (
                        <div className="rounded-md bg-blue-50 border border-blue-100 px-3 py-2">
                          <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-0.5">{t("twin.recommendedAction")}</p>
                          <p className="text-slate-800">{ev.recommended_action}</p>
                        </div>
                      )}
                      <div className="flex flex-wrap gap-4 text-xs text-slate-400">
                        {ev.source_name && <span>{t("twin.source")}: {ev.source_name}</span>}
                        {ev.health_delta != null && ev.health_delta !== 0 && (
                          <span className={ev.health_delta < 0 ? "text-red-500" : "text-green-600"}>
                            Δ {ev.health_delta > 0 ? "+" : ""}{ev.health_delta.toFixed(1)} {t("twin.healthDelta")}
                          </span>
                        )}
                        {ev.confidence != null && ev.confidence > 0 && <span>{t("twin.confidence")}: {(ev.confidence * 100).toFixed(0)}%</span>}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function TwinDetailSection({ nameMap, orgId }: { nameMap: Map<string, string>; orgId: string }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState("");
  const [search, setSearch] = useState("");
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null);
  const [sevFilter, setSevFilter] = useState("");
  const [processResult, setProcessResult] = useState<{ events_created: number; message: string } | null>(null);

  const { data: suppliersData } = useQuery<{ items: ExecSupplier[] }>({
    queryKey: ["twin-suppliers-search", search],
    queryFn: async () => {
      const params: Record<string, string> = { page_size: "20", status: "Active" };
      if (search.trim()) params.search = search.trim();
      return (await apiClient.get("/suppliers/", { params })).data;
    },
    enabled: search.trim().length >= 1,
    staleTime: 30_000,
  });

  const filtered = suppliersData?.items ?? [];

  const { data: twin, isLoading: twinLoading } = useQuery<DigitalTwin>({
    queryKey: ["twin-state", selectedId],
    queryFn: async () => (await apiClient.get(`/suppliers/${selectedId}/twin`)).data,
    enabled: !!selectedId,
    staleTime: 60_000,
  });

  const { data: timeline, isLoading: timelineLoading } = useQuery<{ events: TimelineEvent[]; total: number }>({
    queryKey: ["twin-timeline", selectedId, sevFilter],
    queryFn: async () => {
      const params: Record<string, string> = { limit: "50" };
      if (sevFilter) params.severity = sevFilter;
      return (await apiClient.get(`/suppliers/${selectedId}/twin/timeline`, { params })).data;
    },
    enabled: !!selectedId,
    staleTime: 60_000,
  });

  const processSignals = useMutation({
    mutationFn: async () => (await apiClient.post(`/suppliers/${selectedId}/twin/process`)).data,
    onSuccess: (data) => {
      setProcessResult(data);
      qc.invalidateQueries({ queryKey: ["twin-state", selectedId] });
      qc.invalidateQueries({ queryKey: ["twin-timeline", selectedId] });
    },
  });

  const [activateResult, setActivateResult] = useState<{ twin_events_created: number; surveillance_signals_created: number; message: string } | null>(null);
  const activateIntelligence = useMutation({
    mutationFn: async () => (await apiClient.post(`/intelligence/activate/${selectedId}`)).data,
    onSuccess: (data) => {
      setActivateResult(data);
      qc.invalidateQueries({ queryKey: ["twin-state", selectedId] });
      qc.invalidateQueries({ queryKey: ["twin-timeline", selectedId] });
      qc.invalidateQueries({ queryKey: ["twin-signals", selectedId] });
      qc.invalidateQueries({ queryKey: ["surv-signals-active"] });
      qc.invalidateQueries({ queryKey: ["surv-dashboard"] });
    },
  });

  const trendIcon = twin?.health_trend === "improving" ? "↑" : twin?.health_trend === "deteriorating" ? "↓" : "→";
  const trendColor = twin?.health_trend === "improving" ? "text-green-600" : twin?.health_trend === "deteriorating" ? "text-red-600" : "text-slate-400";

  return (
    <div className="space-y-5">
      <Card>
        <CardContent className="pt-4 pb-4">
          <p className="text-xs font-medium text-slate-500 mb-2">{t("twin.selectSupplier")}</p>
          <Input
            placeholder={t("twin.searchSupplier")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9"
          />
          {search && filtered.length > 0 && (
            <div className="mt-2 max-h-48 overflow-y-auto rounded-md border border-slate-200 bg-white shadow-sm">
              {filtered.slice(0, 10).map((s) => (
                <button key={s.id}
                  className={`flex w-full items-center justify-between px-3 py-2 text-sm text-left hover:bg-slate-50 ${selectedId === s.id ? "bg-blue-50 text-blue-700" : "text-slate-700"}`}
                  onClick={() => { setSelectedId(s.id); setSearch(""); setProcessResult(null); }}>
                  <span className="font-medium">{s.name}</span>
                  <span className="text-xs text-slate-400 font-mono">{s.id.slice(0, 8)}…</span>
                </button>
              ))}
            </div>
          )}
          {selectedId && !search && (
            <p className="mt-2 text-xs text-slate-500">
              {t("twin.viewing")}: <strong className="text-slate-700">{nameMap.get(selectedId) ?? selectedId}</strong>
            </p>
          )}
        </CardContent>
      </Card>

      {!selectedId ? (
        <Card>
          <CardContent className="py-14 text-center">
            <Cpu className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="text-slate-500">{t("twin.selectSupplierPrompt")}</p>
          </CardContent>
        </Card>
      ) : twinLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : twin ? (
        <>
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-1">
              <CardContent className="pt-5 flex flex-col items-center text-center">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">{t("twin.overallHealth")}</p>
                <div className="relative inline-flex items-center justify-center">
                  <TwinHealthRing score={twin.overall_health} status={
                    twin.overall_health < 40 ? "CRITICAL" : twin.overall_health < 60 ? "AT_RISK" : twin.overall_health < 75 ? "MODERATE" : "HEALTHY"
                  } size={110} />
                  <div className="absolute flex flex-col items-center">
                    <span className="text-2xl font-bold text-slate-900">{twin.overall_health.toFixed(0)}</span>
                  </div>
                </div>
                <span className={`mt-2 text-sm font-semibold ${trendColor}`}>{trendIcon} {twin.health_trend}</span>
                <p className="text-xs text-slate-400 mt-1">{t("twin.confidence")}: {(twin.ai_confidence * 100).toFixed(0)}% · v{twin.twin_version}</p>
              </CardContent>
            </Card>
            <Card className="lg:col-span-2">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold">{t("twin.overview")}</CardTitle>
                  <div className="flex gap-2">
                    <Button size="sm" variant="default" className="gap-1.5 h-7 text-xs bg-blue-600 hover:bg-blue-700 text-white"
                      onClick={() => activateIntelligence.mutate()} disabled={activateIntelligence.isPending}>
                      {activateIntelligence.isPending ? <Spinner className="h-3 w-3" /> : <span>⚡</span>}
                      Aktivieren
                    </Button>
                    <Button size="sm" variant="outline" className="gap-1.5 h-7 text-xs"
                      onClick={() => processSignals.mutate()} disabled={processSignals.isPending}>
                      {processSignals.isPending ? <Spinner className="h-3 w-3" /> : <RefreshCw className="h-3 w-3" />}
                      {t("twin.processSignals")}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {activateResult && (
                  <div className="mb-3 rounded-md bg-blue-50 border border-blue-200 px-3 py-2 text-xs text-blue-700">
                    ⚡ {activateResult.message}
                    <span className="ml-2 text-blue-500">({activateResult.twin_events_created} Twin-Events · {activateResult.surveillance_signals_created} Surveillance-Signale)</span>
                  </div>
                )}
                {processResult && (
                  <div className="mb-3 rounded-md bg-green-50 border border-green-200 px-3 py-2 text-xs text-green-700">
                    {processResult.message}
                  </div>
                )}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[
                    { label: t("twin.openRecs"), value: twin.open_recommendations, anchor: "recommendations" },
                    { label: t("twin.openActions"), value: twin.open_actions },
                    { label: t("twin.totalEvents"), value: twin.event_count },
                    { label: t("twin.criticalEvents"), value: twin.critical_event_count, red: twin.critical_event_count > 0 },
                  ].map((c) => (
                    <div key={c.label}
                      className={`rounded-md bg-slate-50 p-3 text-center ${c.anchor ? "cursor-pointer hover:bg-blue-50 transition-colors" : ""}`}
                      onClick={c.anchor ? () => document.getElementById(c.anchor!)?.scrollIntoView({ behavior: "smooth" }) : undefined}
                    >
                      <p className={`text-xl font-bold ${c.red ? "text-red-600" : c.anchor ? "text-blue-600" : "text-slate-900"}`}>{c.value}</p>
                      <p className="text-xs text-slate-400 mt-0.5">{c.label}</p>
                    </div>
                  ))}
                </div>
                {twin.last_event_at && (
                  <p className="mt-3 text-xs text-slate-400">{t("twin.lastEvent")}: {new Date(twin.last_event_at).toLocaleString()}</p>
                )}
              </CardContent>
            </Card>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-3">{t("twin.dimensions")}</h3>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {twin.dimensions.map((dim) => <TwinDimCard key={dim.name} dim={dim} />)}
            </div>
          </div>

          {twin.open_recommendations > 0 && (
            <TwinRecommendationsSection supplierId={selectedId} total={twin.open_recommendations} />
          )}

          <div>
            <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
              <h3 className="text-sm font-semibold text-slate-700">{t("twin.timeline")}</h3>
              <div className="flex gap-1.5">
                {["", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => (
                  <button key={s || "all"} onClick={() => setSevFilter(s)}
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors ${sevFilter === s ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-500 border-slate-200 hover:border-slate-400"}`}>
                    {s || t("twin.all")}
                  </button>
                ))}
              </div>
            </div>
            {timelineLoading ? (
              <div className="flex h-20 items-center justify-center"><Spinner /></div>
            ) : !timeline || timeline.events.length === 0 ? (
              <Card>
                <CardContent className="py-10 text-center">
                  <AlertTriangle className="mx-auto mb-2 h-8 w-8 text-slate-300" />
                  <p className="text-sm text-slate-400">{t("twin.noTimeline")}</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-2">
                {timeline.events.map((ev) => {
                  const open = expandedEvent === ev.id;
                  return (
                    <Card key={ev.id} className={open ? "border-blue-200" : ""}>
                      <CardContent className="pt-3 pb-3">
                        <button className="flex w-full items-start gap-3 text-left" onClick={() => setExpandedEvent(open ? null : ev.id)}>
                          <div className="flex-1 min-w-0">
                            <div className="flex flex-wrap items-center gap-2 mb-1">
                              <TwinSevBadge severity={ev.severity} />
                              <span className="text-xs text-slate-400 capitalize">{ev.event_category?.replace(/_/g, " ")}</span>
                              {ev.twin_dimension_affected && (
                                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500 capitalize">{ev.twin_dimension_affected.replace(/_/g, " ")}</span>
                              )}
                              {ev.health_delta != null && ev.health_delta !== 0 && (
                                <span className={`text-xs font-medium ${ev.health_delta < 0 ? "text-red-500" : "text-green-600"}`}>
                                  {ev.health_delta > 0 ? "+" : ""}{ev.health_delta.toFixed(1)}
                                </span>
                              )}
                              <span className="ml-auto text-xs text-slate-400 shrink-0">{ev.occurred_at ? new Date(ev.occurred_at).toLocaleDateString() : "—"}</span>
                            </div>
                            <p className="font-medium text-slate-800 text-sm">{ev.title}</p>
                            <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{ev.summary}</p>
                          </div>
                          <span className="shrink-0 mt-0.5 text-slate-400">{open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}</span>
                        </button>
                        {open && (
                          <div className="mt-3 border-t border-slate-100 pt-3 space-y-3 text-sm">
                            {ev.why_important && (
                              <div>
                                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">{t("twin.whyImportant")}</p>
                                <p className="text-slate-700">{ev.why_important}</p>
                              </div>
                            )}
                            {ev.recommended_action && (
                              <div className="rounded-md bg-blue-50 border border-blue-100 px-3 py-2">
                                <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-0.5">{t("twin.recommendedAction")}</p>
                                <p className="text-slate-800">{ev.recommended_action}</p>
                              </div>
                            )}
                            <div className="flex flex-wrap gap-4 text-xs text-slate-400">
                              {ev.source_name && <span>{t("twin.source")}: {ev.source_name}</span>}
                              {ev.confidence != null && ev.confidence > 0 && <span>{t("twin.confidence")}: {(ev.confidence * 100).toFixed(0)}%</span>}
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>

        </>
      ) : null}

      {/* ── 360° Data Sections — unabhängig vom Twin-Load ── */}
      {selectedId && (
        <div className="space-y-6 mt-2">
          <TwinDocumentsSection supplierId={selectedId} />
          <TwinMetricsSection supplierId={selectedId} />
          <TwinSignalsSection supplierId={selectedId} />
          <TwinCrossSourceSection supplierId={selectedId} supplierName={nameMap.get(selectedId) ?? selectedId} />
          <TwinExternalSection supplierId={selectedId} />
        </div>
      )}
    </div>
  );
}

// ── Empfehlungen ──────────────────────────────────────────────────────────────

const DIM_LABELS: Record<string, string> = {
  financial_health: "Financial",
  esg_health: "ESG",
  compliance_health: "Compliance",
  operational_health: "Operational",
  geopolitical_health: "Geopolitical",
  cyber_health: "Cyber",
  human_rights_health: "Human Rights",
  environmental_health: "Environmental",
};

function TwinRecommendationsSection({ supplierId, total }: { supplierId: string; total: number }) {
  const [dimFilter, setDimFilter] = useState("all");
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 25;

  const { data, isLoading } = useQuery({
    queryKey: ["twin-recs", supplierId],
    queryFn: async () => {
      const res = await apiClient.get(
        `/suppliers/${supplierId}/twin/timeline?severity=HIGH&limit=250`
      );
      return (res.data?.events ?? []) as any[];
    },
    enabled: !!supplierId,
    staleTime: 120_000,
  });

  const dims = useMemo(() => {
    if (!data) return [];
    const s = new Set(data.map((e: any) => e.twin_dimension_affected).filter(Boolean));
    return Array.from(s) as string[];
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return [];
    return dimFilter === "all" ? data : data.filter((e: any) => e.twin_dimension_affected === dimFilter);
  }, [data, dimFilter]);

  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);

  return (
    <div id="recommendations">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <Lightbulb className="h-4 w-4 text-amber-500" />
          {total} Empfehlungen
        </h3>
        <div className="flex flex-wrap gap-1.5">
          {["all", ...dims].map((d) => (
            <button key={d} onClick={() => { setDimFilter(d); setPage(0); }}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors ${dimFilter === d ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-500 border-slate-200 hover:border-slate-400"}`}>
              {d === "all" ? "Alle" : DIM_LABELS[d] ?? d}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex h-16 items-center justify-center"><Spinner /></div>
      ) : (
        <>
          <div className="space-y-2">
            {paged.map((ev: any) => (
              <div key={ev.id} className="rounded-lg border border-amber-100 bg-amber-50/40 p-3 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-slate-800 leading-snug">{ev.title}</p>
                  {ev.twin_dimension_affected && (
                    <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
                      {DIM_LABELS[ev.twin_dimension_affected] ?? ev.twin_dimension_affected}
                    </span>
                  )}
                </div>

                {ev.recommended_action && (
                  <div className="rounded-md bg-blue-50 border border-blue-100 px-3 py-2">
                    <p className="text-[10px] font-semibold text-blue-500 uppercase tracking-wide mb-0.5">Empfohlene Maßnahme</p>
                    <p className="text-xs text-slate-800">{ev.recommended_action}</p>
                  </div>
                )}

                {ev.regulatory_impact && (
                  <p className="text-[11px] text-slate-500">
                    <span className="font-semibold">Regulatorisch:</span> {ev.regulatory_impact}
                  </p>
                )}

                <div className="flex items-center gap-3 text-[10px] text-slate-400">
                  {ev.occurred_at && <span>{new Date(ev.occurred_at).toLocaleDateString()}</span>}
                  {ev.health_delta != null && (
                    <span className={ev.health_delta < 0 ? "text-red-500" : "text-green-600"}>
                      {ev.health_delta > 0 ? "+" : ""}{ev.health_delta.toFixed(1)} Score
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-3">
              <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
                className="rounded px-2 py-1 text-xs border disabled:opacity-40 hover:bg-slate-50">← Zurück</button>
              <span className="text-xs text-slate-500">{page + 1} / {totalPages}</span>
              <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
                className="rounded px-2 py-1 text-xs border disabled:opacity-40 hover:bg-slate-50">Weiter →</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Twin 360° Sub-Sections ────────────────────────────────────────────────────

const QUALITY_COLOR = (score: number) =>
  score >= 80 ? "text-green-700 bg-green-50 border-green-200"
  : score >= 50 ? "text-yellow-700 bg-yellow-50 border-yellow-200"
  : "text-red-700 bg-red-50 border-red-200";

function TwinDocumentsSection({ supplierId }: { supplierId: string }) {
  const { data = [], isLoading } = useQuery<DocQuality[]>({
    queryKey: ["twin-doc-quality", supplierId],
    queryFn: () => listDocQuality({ supplier_id: supplierId }),
    enabled: !!supplierId,
    staleTime: 120_000,
  });

  if (isLoading) return <div className="flex h-12 items-center gap-2 text-sm text-muted-foreground"><Spinner className="h-4 w-4" /> Dokumente laden…</div>;
  if (!data.length) return null;

  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
        <Database className="h-4 w-4 text-slate-400" /> Dokumente & Datenqualität
      </h3>
      <div className="grid gap-2 sm:grid-cols-2">
        {data.map(doc => (
          <div key={doc.doc_id} className={`rounded-xl border px-4 py-3 flex items-center justify-between gap-3 ${QUALITY_COLOR(doc.quality_score)}`}>
            <div className="min-w-0">
              <p className="font-medium text-sm truncate">{doc.title}</p>
              <p className="text-xs opacity-70 mt-0.5">{doc.doc_type.replace(/_/g," ")} · {doc.report_year ?? "—"} · {doc.metrics_count} Metriken</p>
            </div>
            <div className="shrink-0 text-right">
              <p className="text-xl font-bold tabular-nums">{doc.quality_score.toFixed(0)}</p>
              <p className="text-xs opacity-60">{doc.found_core}/{doc.total_core} Kern-KPIs</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const METRIC_TYPE_LABELS: Record<string, string> = {
  revenue: "Umsatz", ebitda: "EBITDA", ebitda_margin: "EBITDA-Marge",
  net_income: "Nettogewinn", employees: "Mitarbeiter", capex: "CapEx",
  co2_scope1: "CO₂ Scope 1", co2_scope2: "CO₂ Scope 2", co2_scope3: "CO₂ Scope 3",
  water_m3: "Wasserverbrauch", energy_gwh: "Energieverbrauch",
  renewable_energy_pct: "Erneuerbare Energie", women_leadership_pct: "Frauen in Führung",
  supplier_audited_pct: "Lieferanten auditiert", free_cashflow: "Free Cashflow",
  debt_ratio: "Verschuldungsgrad", roce: "ROCE",
};

function TwinMetricsSection({ supplierId }: { supplierId: string }) {
  const { data = [], isLoading } = useQuery<CompanyMetric[]>({
    queryKey: ["twin-metrics", supplierId],
    queryFn: () => listMetrics({ supplier_id: supplierId }),
    enabled: !!supplierId,
    staleTime: 120_000,
  });

  if (isLoading) return <div className="flex h-12 items-center gap-2 text-sm text-muted-foreground"><Spinner className="h-4 w-4" /> Metriken laden…</div>;
  if (!data.length) return null;

  // Neueste pro metric_type
  const latestByType = new Map<string, CompanyMetric>();
  for (const m of data) {
    const existing = latestByType.get(m.metric_type);
    if (!existing || m.year > existing.year) latestByType.set(m.metric_type, m);
  }
  const metrics = [...latestByType.values()].sort((a,b) => a.metric_type.localeCompare(b.metric_type));

  const CONF_ICON: Record<string, string> = { exact: "✓", estimated: "~", calculated: "?" };

  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
        <BarChart3 className="h-4 w-4 text-slate-400" /> Extrahierte Metriken
        <span className="ml-auto text-xs font-normal text-muted-foreground">{metrics.length} Kennzahlen</span>
      </h3>
      <div className="rounded-xl border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs text-slate-500">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Kennzahl</th>
              <th className="text-right px-4 py-2 font-medium">Wert</th>
              <th className="text-center px-4 py-2 font-medium">Jahr</th>
              <th className="text-center px-4 py-2 font-medium">Seite</th>
              <th className="text-left px-4 py-2 font-medium">Quelle</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {metrics.map(m => (
              <tr key={m.id} className="hover:bg-slate-50/50">
                <td className="px-4 py-2.5 font-medium">{METRIC_TYPE_LABELS[m.metric_type] ?? m.metric_type}</td>
                <td className="px-4 py-2.5 text-right tabular-nums font-semibold">
                  {formatValue(m.value, m.unit)}
                  <span className="ml-1 text-xs text-slate-400 font-normal">{CONF_ICON[m.confidence] ?? "?"}</span>
                </td>
                <td className="px-4 py-2.5 text-center text-slate-500">{m.year}</td>
                <td className="px-4 py-2.5 text-center">
                  {(m as any).page_number ? (
                    <span className="inline-flex items-center rounded-md bg-violet-50 border border-violet-200 px-2 py-0.5 text-xs font-semibold text-violet-700">
                      S.{(m as any).page_number}
                    </span>
                  ) : <span className="text-slate-300">—</span>}
                </td>
                <td className="px-4 py-2.5 text-xs text-slate-400 truncate max-w-[140px]">
                  {(m as any).scope ? <span className="text-slate-500">{(m as any).scope}</span> : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const SIG_DIR_ICON: Record<string, string> = { up: "↑", down: "↓", flat: "→", negative: "↓", positive: "↑" };
const SIG_DIR_COLOR: Record<string, string> = {
  up: "text-green-600", down: "text-red-600", flat: "text-slate-400",
  negative: "text-red-600", positive: "text-green-600",
};

function TwinSignalsSection({ supplierId }: { supplierId: string }) {
  const { data = [], isLoading } = useQuery<CompanySignal[]>({
    queryKey: ["twin-signals", supplierId],
    queryFn: () => listSignals({ supplier_id: supplierId }),
    enabled: !!supplierId,
    staleTime: 120_000,
  });

  if (isLoading) return <div className="flex h-12 items-center gap-2 text-sm text-muted-foreground"><Spinner className="h-4 w-4" /> Signale laden…</div>;
  if (!data.length) return null;

  const sorted = [...data].sort((a,b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9));

  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-orange-400" /> Signale aus Dokumenten
        <span className="ml-auto text-xs font-normal text-muted-foreground">{data.length} Signale</span>
      </h3>
      <div className="space-y-2">
        {sorted.slice(0, 8).map(sig => (
          <div key={sig.id} className="rounded-xl border border-border bg-background px-4 py-3">
            <div className="flex items-start gap-3">
              <span className={`text-base font-bold ${SIG_DIR_COLOR[sig.direction] ?? "text-slate-400"}`}>
                {SIG_DIR_ICON[sig.direction] ?? "→"}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span className={`text-xs font-semibold rounded px-1.5 py-0.5 ${
                    sig.severity === "critical" ? "bg-red-100 text-red-700" :
                    sig.severity === "high" ? "bg-orange-100 text-orange-700" :
                    sig.severity === "medium" ? "bg-yellow-100 text-yellow-700" : "bg-slate-100 text-slate-600"
                  }`}>{sig.severity}</span>
                  <span className="text-xs text-muted-foreground">{DIMENSION_LABELS[sig.dimension] ?? sig.dimension}</span>
                  <span className="text-xs text-muted-foreground">· {sig.signal_type.replace(/_/g," ")}</span>
                  {sig.year && <span className="ml-auto text-xs text-muted-foreground">{sig.year}</span>}
                </div>
                <p className="text-sm text-slate-700 line-clamp-2">{sig.description}</p>
              </div>
            </div>
          </div>
        ))}
        {sorted.length > 8 && <p className="text-xs text-center text-muted-foreground pt-1">+{sorted.length - 8} weitere Signale</p>}
      </div>
    </div>
  );
}

function TwinCrossSourceSection({ supplierId, supplierName }: { supplierId: string; supplierName: string }) {
  const qc = useQueryClient();
  const [analyzing, setAnalyzing] = useState(false);
  const [bulkResult, setBulkResult] = useState<{ created: number; skipped: number; message: string } | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["twin-cross-alerts", supplierId],
    queryFn: () => listCrossAlerts({ supplier_id: supplierId, limit: 20 }),
    enabled: !!supplierId,
    staleTime: 60_000,
  });

  const analyzeMut = useMutation({
    mutationFn: (req: CrossAnalyzeRequest) => crossAnalyze(req),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["twin-cross-alerts", supplierId] }); qc.invalidateQueries({ queryKey: ["cross-alerts"] }); setAnalyzing(false); },
  });

  const bulkMut = useMutation({
    mutationFn: () => apiClient.post(`/intelligence/cross-analyze-bulk?supplier_id=${supplierId}`).then(r => r.data),
    onSuccess: (result) => {
      setBulkResult(result);
      qc.invalidateQueries({ queryKey: ["twin-cross-alerts", supplierId] });
      qc.invalidateQueries({ queryKey: ["cross-alerts"] });
    },
  });

  const alerts = data?.alerts ?? [];

  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
        <Globe className="h-4 w-4 text-blue-400" /> Cross-Source Exposition
        <span className="ml-auto text-xs font-normal text-muted-foreground">{alerts.length} Alerts</span>
        <button onClick={() => bulkMut.mutate()} disabled={bulkMut.isPending}
          className="text-xs px-2.5 py-1 rounded-lg border border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100 transition-colors disabled:opacity-50 flex items-center gap-1">
          {bulkMut.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Zap className="h-3 w-3" />}
          Alle analysieren
        </button>
        <button onClick={() => setAnalyzing(v => !v)}
          className="text-xs px-2.5 py-1 rounded-lg border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors">
          + Einzeln
        </button>
      </h3>

      {bulkResult && (
        <div className="mb-3 rounded-md bg-purple-50 border border-purple-200 px-3 py-2 text-xs text-purple-700">
          ⚡ {bulkResult.message}
        </div>
      )}

      {analyzing && (
        <CrossAnalyzeInlineForm
          defaultCompany={supplierName}
          onSubmit={(req) => analyzeMut.mutate(req)}
          onCancel={() => setAnalyzing(false)}
          pending={analyzeMut.isPending}
        />
      )}

      {isLoading ? <div className="flex h-10 items-center gap-2 text-sm text-muted-foreground"><Spinner className="h-4 w-4" /></div>
      : alerts.length === 0 ? (
        <p className="text-sm text-muted-foreground py-2">Keine Cross-Source Alerts für diesen Lieferanten.</p>
      ) : (
        <div className="space-y-2">
          {alerts.map(alert => (
            <div key={alert.id} className={`rounded-xl border px-4 py-3 ${
              alert.severity === "critical" ? "border-red-200 bg-red-50/40" :
              alert.severity === "high" ? "border-orange-200 bg-orange-50/40" : "border-border bg-background"
            }`}>
              <div className="flex items-start gap-2">
                <span className={`mt-0.5 text-xs font-bold rounded px-1.5 py-0.5 uppercase ${
                  alert.severity === "critical" ? "bg-red-100 text-red-700" :
                  alert.severity === "high" ? "bg-orange-100 text-orange-700" :
                  alert.severity === "medium" ? "bg-yellow-100 text-yellow-700" : "bg-blue-100 text-blue-700"
                }`}>{alert.severity}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{alert.trigger_company} · <span className="font-normal text-muted-foreground">{alert.trigger_signal_type.replace(/_/g," ")}</span></p>
                  <p className="text-xs text-slate-600 mt-0.5 line-clamp-2">{alert.reasoning}</p>
                  <p className="text-xs text-muted-foreground mt-1">{IMPACT_TYPE_LABELS[alert.impact_type] ?? alert.impact_type}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CrossAnalyzeInlineForm({ defaultCompany, onSubmit, onCancel, pending }: {
  defaultCompany: string;
  onSubmit: (req: CrossAnalyzeRequest) => void;
  onCancel: () => void;
  pending: boolean;
}) {
  const [form, setForm] = useState<Partial<CrossAnalyzeRequest>>({ trigger_company: defaultCompany });

  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-4 mb-3 space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-xs">Unternehmen</Label>
          <Input value={form.trigger_company ?? ""} onChange={e => setForm(f => ({...f, trigger_company: e.target.value}))} className="mt-1 text-sm h-8" />
        </div>
        <div>
          <Label className="text-xs">Signal-Typ</Label>
          <select value={form.trigger_signal_type ?? ""} onChange={e => setForm(f => ({...f, trigger_signal_type: e.target.value}))}
            className="mt-1 w-full text-sm rounded-lg border border-border bg-background px-2 py-1.5 h-8">
            <option value="">Auswählen…</option>
            {[["plant_closure","Werksschließung"],["layoffs","Stellenabbau"],["restructuring","Restrukturierung"],
              ["insolvency_risk","Insolvenzrisiko"],["rating_downgrade","Rating-Abstufung"],
              ["supply_chain_disruption","Lieferkettenunterbrechung"],["esg_controversy","ESG-Kontroverse"],
              ["esg_target_missed","ESG-Ziel verfehlt"],["legal_action","Rechtliche Klage"]
            ].map(([v,l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
      </div>
      <div>
        <Label className="text-xs">Beschreibung</Label>
        <textarea value={form.trigger_description ?? ""} onChange={e => setForm(f => ({...f, trigger_description: e.target.value}))}
          rows={2} className="mt-1 w-full text-sm rounded-lg border border-border bg-background px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-primary" />
      </div>
      <div className="flex gap-2">
        <button onClick={() => { if (form.trigger_company && form.trigger_signal_type && form.trigger_description) onSubmit(form as CrossAnalyzeRequest); }}
          disabled={pending || !form.trigger_company || !form.trigger_signal_type || !form.trigger_description}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
          {pending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Cpu className="h-3 w-3" />} Analysieren
        </button>
        <button onClick={onCancel} className="text-xs px-3 py-1.5 rounded-lg border border-border hover:bg-accent">Abbrechen</button>
      </div>
    </div>
  );
}

function TwinExternalSection({ supplierId }: { supplierId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["twin-external-signals", supplierId],
    queryFn: () => listExternalSignalsForSupplier(supplierId),
    enabled: !!supplierId,
    staleTime: 120_000,
  });

  const signals = (data?.signals ?? []).slice(0, 6);
  if (isLoading) return <div className="flex h-12 items-center gap-2 text-sm text-muted-foreground"><Spinner className="h-4 w-4" /> Externe Daten laden…</div>;
  if (!signals.length) return null;

  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
        <Layers className="h-4 w-4 text-cyan-400" /> Externe Signale
        <span className="text-xs font-normal text-muted-foreground">(World Bank, GNews, Sanktionen)</span>
      </h3>
      <div className="space-y-2">
        {signals.map((sig: any) => (
          <div key={sig.id} className="rounded-xl border border-border bg-background px-4 py-3">
            <div className="flex items-start gap-2">
              <span className={`shrink-0 mt-0.5 h-2 w-2 rounded-full ${
                sig.severity?.toLowerCase() === "critical" ? "bg-red-500" :
                sig.severity?.toLowerCase() === "high" ? "bg-orange-400" :
                sig.severity?.toLowerCase() === "medium" ? "bg-yellow-400" : "bg-blue-400"
              }`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">{sig.source_name ?? sig.signal_type}</span>
                  {sig.country_code && <span className="text-xs text-muted-foreground">{sig.country_code}</span>}
                  <span className="ml-auto text-xs text-muted-foreground">{sig.observed_at ? new Date(sig.observed_at).toLocaleDateString("de-DE") : "—"}</span>
                </div>
                <p className="text-sm text-slate-700 line-clamp-2">{sig.description}</p>
              </div>
            </div>
          </div>
        ))}
        {(data?.total ?? 0) > 6 && <p className="text-xs text-center text-muted-foreground">+{(data?.total ?? 0) - 6} weitere externe Signale</p>}
      </div>
    </div>
  );
}

// Sub-tabs inside "Supplier Intelligence"
const INTEL_SUB_TABS = [
  { key: "feed",  labelKey: "twin.tabFeed" as const },
  { key: "twin",  labelKey: "twin.tabTwin" as const },
] as const;
type IntelSubTab = (typeof INTEL_SUB_TABS)[number]["key"];

function IntelligenceTab({ nameMap, orgId }: { nameMap: Map<string, string>; orgId: string }) {
  const { t } = useLanguage();
  const [sub, setSub] = useState<IntelSubTab>("feed");
  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {INTEL_SUB_TABS.map((tab) => (
          <button key={tab.key} onClick={() => setSub(tab.key)}
            className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-colors ${sub === tab.key ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
            {t(tab.labelKey)}
          </button>
        ))}
      </div>
      {sub === "feed" && <TwinFeedSection orgId={orgId} />}
      {sub === "twin" && <TwinDetailSection nameMap={nameMap} orgId={orgId} />}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 3 — EXTERNE DATEN (External Intelligence)
// ═══════════════════════════════════════════════════════════════════════════════

function ExtSignalsSection({ orgId }: { orgId: string }) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [severity, setSeverity] = useState("");

  const { data: byConnector, isLoading } = useQuery<{ connectors: ConnectorGroup[] }>({
    queryKey: ["ext-intel-by-connector", orgId],
    queryFn: async () => (await apiClient.get("/external-intelligence/signals/by-connector?top_n=10")).data,
    staleTime: 60_000,
    enabled: !!orgId,
  });

  const { data: flatSignals } = useQuery<{ signals: RiskSignal[]; total: number }>({
    queryKey: ["ext-intel-signals", orgId, severity],
    queryFn: async () => {
      const params: Record<string, string> = { limit: "100" };
      if (severity) params.severity = severity;
      return (await apiClient.get("/external-intelligence/signals", { params })).data;
    },
    staleTime: 60_000,
    enabled: !!orgId,
  });

  const connectors = byConnector?.connectors ?? [];
  const totalSignals = flatSignals?.total ?? 0;
  const criticalCount = (flatSignals?.signals ?? []).filter((s) => s.severity.toLowerCase() === "critical").length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-3">
        {["", "critical", "high", "medium", "low"].map((s) => (
          <button key={s || "all"} onClick={() => setSeverity(s)}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${severity === s ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"}`}>
            {s ? s.charAt(0).toUpperCase() + s.slice(1) : t("extint.allSignals")}
            {!s && totalSignals > 0 && <span className="ml-1.5 text-slate-400">{totalSignals}</span>}
            {s === "critical" && criticalCount > 0 && <span className="ml-1.5 text-red-500">{criticalCount}</span>}
          </button>
        ))}
      </div>
      {isLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : connectors.length === 0 ? (
        <Card><CardContent className="py-14 text-center"><Zap className="mx-auto mb-3 h-10 w-10 text-slate-300" /><p className="font-medium text-slate-600">{t("extint.noSignals")}</p></CardContent></Card>
      ) : (
        <div className="space-y-2">
          {connectors.map((conn) => {
            const open = expanded === conn.source_name;
            const filteredSignals = severity ? conn.signals.filter((s) => s.severity.toLowerCase() === severity) : conn.signals;
            return (
              <Card key={conn.source_name} className={open ? "border-blue-200" : ""}>
                <CardContent className="pt-4 pb-4">
                  <button className="flex w-full items-center justify-between gap-4 text-left"
                    onClick={() => setExpanded(open ? null : conn.source_name)}>
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-slate-900">{conn.label}</span>
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">{conn.total} {t("extint.signals")}</span>
                      {conn.signals.some((s) => s.severity.toLowerCase() === "critical") && (
                        <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">{t("extint.critical")}</span>
                      )}
                    </div>
                    {open ? <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" /> : <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />}
                  </button>
                  {open && (
                    <div className="mt-4 border-t border-slate-100 pt-4 space-y-2">
                      {filteredSignals.length === 0
                        ? <p className="text-sm text-slate-400">{t("extint.noMatchingSignals")}</p>
                        : filteredSignals.map((sig) => (
                          <div key={sig.id} className="rounded-md border border-slate-100 bg-slate-50 p-3">
                            <div className="flex flex-wrap items-center gap-2 mb-1.5">
                              <ExtSevBadge severity={sig.severity} />
                              <span className="text-xs text-slate-400 capitalize">{sig.signal_type.replace(/_/g, " ")}</span>
                              {sig.country_code && <span className="text-xs text-slate-400">{sig.country_code}</span>}
                              <span className="ml-auto text-xs text-slate-400">{new Date(sig.observed_at).toLocaleDateString()}</span>
                            </div>
                            <p className="text-sm text-slate-700">{sig.description}</p>
                          </div>
                        ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ExtCountriesSection({ orgId }: { orgId: string }) {
  const { t } = useLanguage();
  const [riskLevel, setRiskLevel] = useState("");
  const { data, isLoading } = useQuery<{ profiles: CountryRisk[]; total: number }>({
    queryKey: ["ext-intel-countries", orgId, riskLevel],
    queryFn: async () => {
      const params: Record<string, string> = { limit: "100" };
      if (riskLevel) params.risk_level = riskLevel;
      return (await apiClient.get("/external-intelligence/countries", { params })).data;
    },
    staleTime: 120_000,
    enabled: !!orgId,
  });
  const profiles = data?.profiles ?? [];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {["", "critical", "high", "medium", "low"].map((level) => (
          <button key={level || "all"} onClick={() => setRiskLevel(level)}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${riskLevel === level ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"}`}>
            {level ? level.charAt(0).toUpperCase() + level.slice(1) : t("extint.allCountries")}
          </button>
        ))}
        <span className="ml-auto self-center text-xs text-slate-400">{data?.total ?? 0} {t("extint.countries")}</span>
      </div>
      {isLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : profiles.length === 0 ? (
        <Card><CardContent className="py-14 text-center"><Globe className="mx-auto mb-3 h-10 w-10 text-slate-300" /><p className="font-medium text-slate-600">{t("extint.noCountries")}</p></CardContent></Card>
      ) : (
        <Card>
          <CardContent className="pt-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  {[t("extint.country"), t("extint.riskLevel"), t("extint.overall"), t("extint.governance"), t("extint.corruption"), t("extint.labourRights"), t("extint.humanRights"), t("extint.environment"), t("extint.sanctions")].map((h) => (
                    <th key={h} className="py-3 pr-4 text-left text-xs font-medium text-slate-400 first:pl-0 whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {profiles.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/50">
                    <td className="py-2.5 pr-4"><span className="font-medium text-slate-800">{p.country_name}</span><span className="ml-1.5 text-xs text-slate-400">{p.country_code}</span></td>
                    <td className="py-2.5 pr-4"><RiskBadge level={p.risk_level} /></td>
                    <td className="py-2.5 pr-4"><ScoreCell value={p.overall_risk_score} invert /></td>
                    <td className="py-2.5 pr-4"><ScoreCell value={p.governance_score} /></td>
                    <td className="py-2.5 pr-4"><ScoreCell value={p.corruption_score} invert /></td>
                    <td className="py-2.5 pr-4"><ScoreCell value={p.labour_rights_score} /></td>
                    <td className="py-2.5 pr-4"><ScoreCell value={p.human_rights_score} /></td>
                    <td className="py-2.5 pr-4"><ScoreCell value={p.environmental_risk_score} invert /></td>
                    <td className="py-2.5">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${p.sanctions_status === "none" ? "bg-green-50 text-green-700" : "bg-red-100 text-red-700"}`}>{p.sanctions_status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ExtSectorsSection({ orgId }: { orgId: string }) {
  const { t } = useLanguage();
  const { data, isLoading } = useQuery<{ benchmarks: SectorBenchmark[]; total: number }>({
    queryKey: ["ext-intel-sectors", orgId],
    queryFn: async () => (await apiClient.get("/external-intelligence/sectors?limit=100")).data,
    staleTime: 300_000,
    enabled: !!orgId,
  });
  const benchmarks = data?.benchmarks ?? [];
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">{t("extint.sectorsDesc")}</p>
        <span className="text-xs text-slate-400">{data?.total ?? 0} {t("extint.sectors")}</span>
      </div>
      {isLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : benchmarks.length === 0 ? (
        <Card><CardContent className="py-14 text-center"><BarChart3 className="mx-auto mb-3 h-10 w-10 text-slate-300" /><p className="font-medium text-slate-600">{t("extint.noSectors")}</p></CardContent></Card>
      ) : (
        <Card>
          <CardContent className="pt-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  {[t("extint.sector"), t("extint.nace"), t("extint.avgEsg"), t("extint.esgRange"), t("extint.avgRisk"), t("extint.compliance"), t("extint.supplierCount")].map((h) => (
                    <th key={h} className="py-3 pr-4 text-left text-xs font-medium text-slate-400 first:pl-0 whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {benchmarks.map((b) => {
                  const p25 = b.p25_esg_score <= 1 ? b.p25_esg_score * 100 : b.p25_esg_score;
                  const p50 = b.p50_esg_score <= 1 ? b.p50_esg_score * 100 : b.p50_esg_score;
                  const p75 = b.p75_esg_score <= 1 ? b.p75_esg_score * 100 : b.p75_esg_score;
                  return (
                    <tr key={b.id} className="hover:bg-slate-50/50">
                      <td className="py-2.5 pr-4 font-medium text-slate-800">{b.sector_name}</td>
                      <td className="py-2.5 pr-4"><span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-mono text-slate-600">{b.nace_code}</span></td>
                      <td className="py-2.5 pr-4"><ScoreCell value={b.average_esg_score} /></td>
                      <td className="py-2.5 pr-4">
                        <div className="flex items-center gap-1 text-xs text-slate-500">
                          <span>{p25.toFixed(0)}</span>
                          <div className="relative h-1.5 w-16 rounded-full bg-slate-100">
                            <div className="absolute h-1.5 rounded-full bg-blue-400" style={{ left: `${p25}%`, width: `${p75 - p25}%` }} />
                            <div className="absolute h-3 w-0.5 -top-0.5 rounded bg-blue-700" style={{ left: `${p50}%` }} />
                          </div>
                          <span>{p75.toFixed(0)}</span>
                        </div>
                      </td>
                      <td className="py-2.5 pr-4"><ScoreCell value={b.average_risk_score} invert /></td>
                      <td className="py-2.5 pr-4"><ScoreCell value={b.average_compliance_coverage} /></td>
                      <td className="py-2.5">{b.supplier_count}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ExtHighRiskSection({ orgId }: { orgId: string }) {
  const { t } = useLanguage();
  const { data, isLoading } = useQuery<{ enrichments: SupplierEnrichment[]; total: number }>({
    queryKey: ["ext-intel-high-risk", orgId],
    queryFn: async () => (await apiClient.get("/external-intelligence/enrichments/high-risk?min_combined_risk=60&limit=50")).data,
    staleTime: 120_000,
    enabled: !!orgId,
  });
  const enrichments = data?.enrichments ?? [];
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">{t("extint.highRiskDesc")}</p>
        <span className="text-xs text-slate-400">{data?.total ?? 0} {t("extint.suppliers")}</span>
      </div>
      {isLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : enrichments.length === 0 ? (
        <Card><CardContent className="py-14 text-center"><AlertTriangle className="mx-auto mb-3 h-10 w-10 text-slate-300" /><p className="font-medium text-slate-600">{t("extint.noHighRisk")}</p></CardContent></Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {enrichments.map((e) => (
            <Card key={e.id}>
              <CardContent className="pt-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold text-slate-800 text-sm">{e.supplier_id}</p>
                    <p className="text-xs text-slate-400">{e.country_code} · {t("extint.enriched")} {new Date(e.enriched_at).toLocaleDateString()}</p>
                  </div>
                  <RiskBadge level={e.country_risk_level} />
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded bg-slate-50 p-2"><p className="text-slate-400">{t("extint.combinedRisk")}</p><p className="font-bold text-red-700 text-base">{e.combined_risk_score.toFixed(0)}</p></div>
                  <div className="rounded bg-slate-50 p-2"><p className="text-slate-400">{t("extint.externalRisk")}</p><p className="font-bold text-orange-700 text-base">{e.external_risk_score.toFixed(0)}</p></div>
                  <div className="rounded bg-slate-50 p-2"><p className="text-slate-400">{t("extint.sectorPercentile")}</p><p className="font-semibold text-slate-700">{e.sector_percentile.toFixed(0)}<span className="text-xs font-normal text-slate-400 ml-1">({e.percentile_rank})</span></p></div>
                  <div className="rounded bg-slate-50 p-2"><p className="text-slate-400">{t("extint.activeSignals")}</p><p className={`font-semibold ${e.active_signal_count > 0 ? "text-amber-700" : "text-slate-700"}`}>{e.active_signal_count}</p></div>
                </div>
                {e.sanctions_exposure !== "none" && (
                  <div className="rounded bg-red-50 px-2.5 py-1.5">
                    <p className="text-xs font-medium text-red-700">{t("extint.sanctionsExposure")}: <span className="capitalize">{e.sanctions_exposure}</span></p>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function ExtDatasetsSection({ orgId }: { orgId: string }) {
  const { t } = useLanguage();
  const { data, isLoading } = useQuery<{ datasets: ExtDataset[]; total: number }>({
    queryKey: ["ext-intel-datasets", orgId],
    queryFn: async () => (await apiClient.get("/external-intelligence/datasets?limit=50")).data,
    staleTime: 300_000,
    enabled: !!orgId,
  });
  const datasets = data?.datasets ?? [];
  return (
    <div className="space-y-4">
      {isLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : datasets.length === 0 ? (
        <Card><CardContent className="py-14 text-center"><Database className="mx-auto mb-3 h-10 w-10 text-slate-300" /><p className="font-medium text-slate-600">{t("extint.noDatasets")}</p></CardContent></Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {datasets.map((d) => (
            <Card key={d.id}>
              <CardContent className="pt-4">
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <p className="font-semibold text-slate-800 text-sm">{EXT_CONNECTOR_LABELS[d.source_name] ?? d.source_name}</p>
                    <p className="text-xs text-slate-400 font-mono">{d.source_version}</p>
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize shrink-0 ${d.dataset_status === "active" ? "bg-green-100 text-green-700" : d.dataset_status === "pending" ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500"}`}>
                    {d.dataset_status}
                  </span>
                </div>
                <div className="space-y-1 text-xs text-slate-500">
                  <div className="flex justify-between"><span>{t("extint.validFrom")}</span><span className="text-slate-700">{new Date(d.valid_from).toLocaleDateString()}</span></div>
                  {d.valid_until && <div className="flex justify-between"><span>{t("extint.validUntil")}</span><span className="text-slate-700">{new Date(d.valid_until).toLocaleDateString()}</span></div>}
                  {d.record_count != null && <div className="flex justify-between"><span>{t("extint.records")}</span><span className="text-slate-700">{d.record_count.toLocaleString()}</span></div>}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// Sub-tabs inside "Externe Daten"
const EXT_SUB_TABS = [
  { key: "signals",   labelKey: "extint.tabSignals" as const,   icon: Zap },
  { key: "countries", labelKey: "extint.tabCountries" as const, icon: Globe },
  { key: "sectors",   labelKey: "extint.tabSectors" as const,   icon: Layers },
  { key: "high-risk", labelKey: "extint.tabHighRisk" as const,  icon: AlertTriangle },
  { key: "datasets",  labelKey: "extint.tabDatasets" as const,  icon: Database },
] as const;
type ExtSubTab = (typeof EXT_SUB_TABS)[number]["key"];

function ExternalDataTab({ orgId }: { orgId: string }) {
  const { t } = useLanguage();
  const [sub, setSub] = useState<ExtSubTab>("signals");
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {EXT_SUB_TABS.map((tab) => (
          <button key={tab.key} onClick={() => setSub(tab.key)}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${sub === tab.key ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
            <tab.icon className="h-3.5 w-3.5" /> {t(tab.labelKey)}
          </button>
        ))}
      </div>
      {sub === "signals"   && <ExtSignalsSection orgId={orgId} />}
      {sub === "countries" && <ExtCountriesSection orgId={orgId} />}
      {sub === "sectors"   && <ExtSectorsSection orgId={orgId} />}
      {sub === "high-risk" && <ExtHighRiskSection orgId={orgId} />}
      {sub === "datasets"  && <ExtDatasetsSection orgId={orgId} />}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// TAB 4 — CROSS-SOURCE INTELLIGENCE
// ═══════════════════════════════════════════════════════════════════════════════

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-800 border-red-200",
  high:     "bg-orange-100 text-orange-800 border-orange-200",
  medium:   "bg-yellow-100 text-yellow-800 border-yellow-200",
  low:      "bg-blue-100 text-blue-800 border-blue-200",
};

const STATUS_COLORS: Record<string, string> = {
  open:         "bg-red-50 text-red-700",
  acknowledged: "bg-yellow-50 text-yellow-700",
  resolved:     "bg-green-50 text-green-700",
};

const STATUS_LABELS: Record<string, string> = {
  open: "Offen", acknowledged: "Zur Kenntnis genommen", resolved: "Erledigt",
};

function CrossAlertCard({ alert, onStatusChange }: { alert: CrossAlert; onStatusChange: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const qc = useQueryClient();

  const statusMut = useMutation({
    mutationFn: (status: "open" | "acknowledged" | "resolved") =>
      updateCrossAlertStatus(alert.id, status),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["cross-alerts"] }); onStatusChange(); },
  });

  const naceLabel = NACE_LABELS[alert.trigger_nace ?? ""] ?? alert.trigger_nace ?? "–";
  const impactLabel = IMPACT_TYPE_LABELS[alert.impact_type] ?? alert.impact_type;

  return (
    <div className={`rounded-xl border ${alert.severity === "critical" ? "border-red-200 bg-red-50/30" : "border-border bg-background"} p-4 space-y-3`}>
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${SEVERITY_COLORS[alert.severity]}`}>
              {alert.severity.toUpperCase()}
            </span>
            <span className="text-xs rounded bg-slate-100 px-2 py-0.5 text-slate-600 font-mono">{naceLabel}</span>
            <span className="text-xs text-muted-foreground">{impactLabel}</span>
          </div>
          <p className="mt-1.5 font-semibold text-sm">
            {alert.trigger_company}
            <span className="font-normal text-muted-foreground ml-2">· {alert.trigger_signal_type}</span>
          </p>
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{alert.trigger_description}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-xs rounded px-2 py-0.5 font-medium ${STATUS_COLORS[alert.status]}`}>
            {STATUS_LABELS[alert.status]}
          </span>
          <button onClick={() => setExpanded(v => !v)} className="text-muted-foreground hover:text-foreground p-1">
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Reasoning */}
      <div className="text-sm text-slate-700 bg-slate-50 rounded-lg px-3 py-2.5 border border-slate-100">
        <p className="text-xs font-semibold text-slate-500 mb-1">Analyse</p>
        <p>{alert.reasoning}</p>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="space-y-3">
          {/* Affected suppliers */}
          {alert.affected_suppliers.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground mb-2">Betroffene Lieferanten ({alert.affected_suppliers.length})</p>
              <div className="grid gap-1.5">
                {alert.affected_suppliers.map(s => (
                  <div key={s.id} className="flex items-center gap-2 text-sm">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${
                      s.relation === "sector_stress" ? "bg-red-500" :
                      s.relation === "upstream_pressure" ? "bg-orange-400" : "bg-yellow-400"
                    }`} />
                    <span className="font-medium">{s.name}</span>
                    <span className="text-xs text-muted-foreground font-mono">{NACE_LABELS[s.nace_code] ?? s.nace_code}</span>
                    <span className="ml-auto text-xs text-muted-foreground">{RELATION_LABELS[s.relation]}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended actions */}
          {alert.recommended_actions.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground mb-1.5">Empfohlene Maßnahmen</p>
              <ul className="space-y-1">
                {alert.recommended_actions.map((a, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Status actions */}
          <div className="flex gap-2 pt-1 border-t border-border">
            {alert.status === "open" && (
              <button
                onClick={() => statusMut.mutate("acknowledged")}
                disabled={statusMut.isPending}
                className="text-xs px-3 py-1.5 rounded-lg border border-yellow-300 bg-yellow-50 text-yellow-700 hover:bg-yellow-100 disabled:opacity-50 transition-colors"
              >
                Zur Kenntnis nehmen
              </button>
            )}
            {alert.status !== "resolved" && (
              <button
                onClick={() => statusMut.mutate("resolved")}
                disabled={statusMut.isPending}
                className="text-xs px-3 py-1.5 rounded-lg border border-green-300 bg-green-50 text-green-700 hover:bg-green-100 disabled:opacity-50 transition-colors"
              >
                Als erledigt markieren
              </button>
            )}
          </div>
        </div>
      )}

      <p className="text-xs text-muted-foreground">{formatDateTime(alert.created_at)}</p>
    </div>
  );
}

function CrossSourceTab({ nameMap }: { nameMap: Map<string, string> }) {
  const qc = useQueryClient();
  const [filterStatus, setFilterStatus] = useState<string>("open");
  const [filterSeverity, setFilterSeverity] = useState<string>("");
  const [form, setForm] = useState<Partial<CrossAnalyzeRequest>>({});
  const [showForm, setShowForm] = useState(false);
  const [bulkSupplierId, setBulkSupplierId] = useState<string>("");
  const [bulkResult, setBulkResult] = useState<{ created: number; skipped: number; message: string } | null>(null);

  const bulkMut = useMutation({
    mutationFn: (supplierId: string) =>
      apiClient.post(`/intelligence/cross-analyze-bulk?supplier_id=${supplierId}`).then(r => r.data),
    onSuccess: (result) => {
      setBulkResult(result);
      qc.invalidateQueries({ queryKey: ["cross-alerts"] });
    },
  });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["cross-alerts", filterStatus, filterSeverity],
    queryFn: () => listCrossAlerts({
      status: filterStatus || undefined,
      severity: filterSeverity || undefined,
      limit: 50,
    }),
  });

  const analyzeMut = useMutation({
    mutationFn: (req: CrossAnalyzeRequest) => crossAnalyze(req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cross-alerts"] });
      setShowForm(false);
      setForm({});
    },
  });

  const alerts = data?.alerts ?? [];

  const bySeverity: Record<string, number> = {};
  alerts.forEach(a => { bySeverity[a.severity] = (bySeverity[a.severity] ?? 0) + 1; });

  return (
    <div className="space-y-5">
      {/* Stats row */}
      <div className="grid grid-cols-4 gap-3">
        {(["critical","high","medium","low"] as const).map(sev => (
          <div key={sev} className={`rounded-xl border p-3 text-center ${SEVERITY_COLORS[sev]}`}>
            <p className="text-2xl font-bold">{bySeverity[sev] ?? 0}</p>
            <p className="text-xs mt-0.5 capitalize">{sev}</p>
          </div>
        ))}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          className="text-sm rounded-lg border border-border bg-background px-3 py-1.5"
        >
          <option value="">Alle Status</option>
          <option value="open">Offen</option>
          <option value="acknowledged">Zur Kenntnis</option>
          <option value="resolved">Erledigt</option>
        </select>
        <select
          value={filterSeverity}
          onChange={e => setFilterSeverity(e.target.value)}
          className="text-sm rounded-lg border border-border bg-background px-3 py-1.5"
        >
          <option value="">Alle Schweregrade</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border border-border hover:bg-accent transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Aktualisieren
        </button>
        <button
          onClick={() => setShowForm(v => !v)}
          className="ml-auto flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-3.5 w-3.5" /> Analyse starten
        </button>
      </div>

      {/* Bulk analyze row */}
      <div className="flex items-center gap-3 rounded-xl border border-purple-200 bg-purple-50 p-3">
        <Zap className="h-4 w-4 text-purple-500 shrink-0" />
        <span className="text-sm font-medium text-purple-700">Alle Risiko-Signale analysieren:</span>
        <select
          value={bulkSupplierId}
          onChange={e => { setBulkSupplierId(e.target.value); setBulkResult(null); }}
          className="text-sm rounded-lg border border-purple-200 bg-white px-3 py-1.5 flex-1 min-w-0"
        >
          <option value="">— Lieferant wählen —</option>
          {Array.from(nameMap.entries()).map(([id, name]) => (
            <option key={id} value={id}>{name}</option>
          ))}
        </select>
        <button
          onClick={() => bulkSupplierId && bulkMut.mutate(bulkSupplierId)}
          disabled={!bulkSupplierId || bulkMut.isPending}
          className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg bg-purple-600 text-white hover:bg-purple-700 transition-colors disabled:opacity-50"
        >
          {bulkMut.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
          Starten
        </button>
        {bulkResult && (
          <span className="text-xs text-purple-700">⚡ {bulkResult.message}</span>
        )}
      </div>

      {/* Manual analysis form */}
      {showForm && (
        <div className="rounded-xl border border-border bg-card p-4 space-y-3">
          <p className="text-sm font-semibold">Neue Cross-Source-Analyse</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Unternehmen *</Label>
              <Input
                value={form.trigger_company ?? ""}
                onChange={e => setForm(f => ({ ...f, trigger_company: e.target.value }))}
                placeholder="z.B. Volkswagen AG"
                className="mt-1 text-sm"
              />
            </div>
            <div>
              <Label className="text-xs">Signal-Typ *</Label>
              <select
                value={form.trigger_signal_type ?? ""}
                onChange={e => setForm(f => ({ ...f, trigger_signal_type: e.target.value }))}
                className="mt-1 w-full text-sm rounded-lg border border-border bg-background px-3 py-2"
              >
                <option value="">Auswählen…</option>
                <option value="plant_closure">Werksschließung</option>
                <option value="layoffs">Stellenabbau</option>
                <option value="restructuring">Restrukturierung</option>
                <option value="insolvency_risk">Insolvenzrisiko</option>
                <option value="rating_downgrade">Rating-Abstufung</option>
                <option value="supply_chain_disruption">Lieferkettenunterbrechung</option>
                <option value="esg_controversy">ESG-Kontroverse</option>
                <option value="esg_target_missed">ESG-Ziel verfehlt</option>
                <option value="legal_action">Rechtliche Klage</option>
                <option value="contradiction">Datenwiderspruch</option>
              </select>
            </div>
            <div>
              <Label className="text-xs">NACE-Code (optional)</Label>
              <Input
                value={form.trigger_nace ?? ""}
                onChange={e => setForm(f => ({ ...f, trigger_nace: e.target.value }))}
                placeholder="z.B. C29"
                className="mt-1 text-sm"
              />
            </div>
          </div>
          <div>
            <Label className="text-xs">Beschreibung *</Label>
            <textarea
              value={form.trigger_description ?? ""}
              onChange={e => setForm(f => ({ ...f, trigger_description: e.target.value }))}
              placeholder="Was ist passiert? Gib eine kurze Beschreibung des Events…"
              rows={3}
              className="mt-1 w-full text-sm rounded-lg border border-border bg-background px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => {
                if (!form.trigger_company || !form.trigger_signal_type || !form.trigger_description) return;
                analyzeMut.mutate(form as CrossAnalyzeRequest);
              }}
              disabled={analyzeMut.isPending || !form.trigger_company || !form.trigger_signal_type || !form.trigger_description}
              className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {analyzeMut.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Cpu className="h-3.5 w-3.5" />}
              Analysieren
            </button>
            <button
              onClick={() => { setShowForm(false); setForm({}); }}
              className="text-sm px-3 py-2 rounded-lg border border-border hover:bg-accent transition-colors"
            >
              Abbrechen
            </button>
          </div>
          {analyzeMut.error && (
            <p className="text-xs text-red-600">Fehler: {String(analyzeMut.error)}</p>
          )}
        </div>
      )}

      {/* Alert list */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Globe className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="font-medium">Keine Cross-Source-Alerts</p>
          <p className="text-sm mt-1">Starte eine Analyse oder ändere die Filter.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map(alert => (
            <CrossAlertCard key={alert.id} alert={alert} onStatusChange={() => refetch()} />
          ))}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN HUB
// ═══════════════════════════════════════════════════════════════════════════════

const tab_defs = [
  { key: "signals",      labelKey: "surveillance.tabSignals" as const },
  { key: "intelligence", labelKey: "surveillance.tabIntelligence" as const },
  { key: "external",     labelKey: "surveillance.tabExternal" as const },
  { key: "cross",        labelKey: "surveillance.tabCross" as const },
] as const;
type TabKey = (typeof tab_defs)[number]["key"];

export default function IntelligenceHubPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<TabKey>("signals");

  const orgId = user?.organization_id ?? "";
  const nameMap = useSupplierNameMap();

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Radio className="h-6 w-6 text-cyan-500" />
            {t("nav.monitoring")}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("twin.pageSubtitle")}</p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="border-b border-border">
        <nav className="-mb-px flex gap-0">
          {tab_defs.map((tab) => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
              }`}>
              {t(tab.labelKey)}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      {activeTab === "signals"      && <SurveillanceTab nameMap={nameMap} />}
      {activeTab === "intelligence" && <IntelligenceTab nameMap={nameMap} orgId={orgId} />}
      {activeTab === "external"     && <ExternalDataTab orgId={orgId} />}
      {activeTab === "cross"        && <CrossSourceTab nameMap={nameMap} />}
    </div>
  );
}
