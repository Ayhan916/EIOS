"use client";

import { useState } from "react";
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
  Radio,
  Shield,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import apiClient from "@/lib/api/client";
import { formatDateTime } from "@/lib/utils";

// ── API ───────────────────────────────────────────────────────────────────────

async function getSurveillanceDashboard() {
  const res = await apiClient.get("/surveillance/dashboard");
  return res.data;
}

async function getActiveSignals() {
  const res = await apiClient.get(
    "/surveillance/signals?signal_status=ACTIVE&limit=20"
  );
  return res.data;
}

async function getWatchlist() {
  const res = await apiClient.get(
    "/surveillance/watchlists?active_only=true&limit=20"
  );
  return res.data;
}

async function getOpenEpisodes() {
  const res = await apiClient.get(
    "/surveillance/episodes?episode_status=OPEN&limit=10"
  );
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

// ── Sub-components ────────────────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: string }) {
  const colour: Record<string, string> = {
    CRITICAL: "destructive",
    HIGH: "warning",
    MEDIUM: "secondary",
    LOW: "outline",
    INFO: "outline",
  };
  return (
    <Badge variant={(colour[severity] ?? "secondary") as any}>
      {severity}
    </Badge>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  colour,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  colour?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p
              className={`text-2xl font-bold mt-1 ${colour ?? "text-foreground"}`}
            >
              {value}
            </p>
          </div>
          <Icon className="h-8 w-8 text-muted-foreground opacity-50" />
        </div>
      </CardContent>
    </Card>
  );
}

function SignalRow({ signal }: { signal: any }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [created, setCreated] = useState(false);

  const createRisk = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/risks/", {
        title: `[Signal] ${signal.title}`,
        risk_level: signal.severity === "HIGH" || signal.severity === "CRITICAL" ? signal.severity.charAt(0) + signal.severity.slice(1).toLowerCase() : "Medium",
        status: "Draft",
        category: signal.signal_type ?? "Surveillance",
      });
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["org-risks"] });
      setCreated(true);
    },
  });

  return (
    <div className="flex items-start justify-between py-3 border-b last:border-0">
      <div className="flex-1 min-w-0 mr-4">
        <p className="text-sm font-medium truncate">{signal.title}</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {signal.signal_type} · {formatDateTime(signal.detected_at)}
        </p>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <SeverityBadge severity={signal.severity} />
        {created ? (
          <span className="flex items-center gap-1 text-[10px] text-emerald-600 font-medium">
            <CheckCircle2 className="h-3 w-3" /> Risk created
          </span>
        ) : (
          <button
            onClick={() => createRisk.mutate()}
            disabled={createRisk.isPending}
            className="inline-flex items-center gap-1 rounded bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700 hover:bg-red-100 transition-colors disabled:opacity-50"
          >
            {createRisk.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <ShieldAlert className="h-3 w-3" />}
            {t("surveillance.createRisk")}
          </button>
        )}
      </div>
    </div>
  );
}

function EpisodeRow({ episode }: { episode: any }) {
  return (
    <div className="flex items-start justify-between py-3 border-b last:border-0">
      <div className="flex-1 min-w-0 mr-4">
        <p className="text-sm font-medium truncate">{episode.title}</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {episode.signal_count} signals · started{" "}
          {formatDateTime(episode.started_at)}
        </p>
      </div>
      <SeverityBadge severity={episode.severity} />
    </div>
  );
}

// ── Connector signal panel ────────────────────────────────────────────────────

const CONNECTOR_ICONS: Record<string, string> = {
  world_bank:                 "🌍",
  transparency_international: "🔍",
  ilo:                        "⚙️",
  unicef:                     "🧒",
  un_sanctions:               "🚫",
  eu_sanctions:               "🇪🇺",
};

const SEV_COLOUR: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high:     "bg-orange-100 text-orange-700 border-orange-200",
  medium:   "bg-amber-100 text-amber-700 border-amber-200",
  low:      "bg-slate-100 text-slate-600 border-slate-200",
};

function ConnectorCard({ connector }: { connector: { source_name: string; label: string; total: number; signals: any[] } }) {
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
                {connector.total} Signal{connector.total !== 1 ? "e" : ""}
              </span>
            ) : (
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                Klar
              </span>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {!hasSignals ? (
          <p className="text-xs text-muted-foreground py-1">Keine aktiven Signale für deine Lieferanten.</p>
        ) : (
          <div className="space-y-1.5">
            {shown.map((s: any) => (
              <div key={s.id} className={`rounded border px-2.5 py-2 ${SEV_COLOUR[(s.severity ?? "").toLowerCase()] ?? "bg-slate-50 border-slate-200"}`}>
                <p className="text-xs font-medium leading-snug line-clamp-2">{s.description}</p>
                <p className="text-[10px] opacity-70 mt-0.5">
                  {s.signal_type?.replace(/_/g, " ")}
                  {s.country_code ? ` · ${s.country_code}` : ""}
                  {s.supplier_id ? " · Lieferant" : ""}
                </p>
              </div>
            ))}
            {connector.signals.length > 3 && (
              <button
                onClick={() => setExpanded(e => !e)}
                className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground mt-1"
              >
                {expanded
                  ? <><ChevronUp className="h-3 w-3" /> Weniger anzeigen</>
                  : <><ChevronDown className="h-3 w-3" /> {connector.signals.length - 3} weitere anzeigen</>
                }
              </button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SurveillancePage() {
  const { t } = useLanguage();
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

  if (dashLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spinner />
      </div>
    );
  }

  const d = dashboard ?? {};

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Radio className="h-6 w-6 text-primary" />
          Continuous Surveillance
        </h1>
        <p className="text-muted-foreground mt-1">
          Real-time ESG risk surveillance across your supplier portfolio.
        </p>
      </div>

      {/* Portfolio stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label={t("surveillance.activeSignals")}
          value={d.active_signals ?? 0}
          icon={Activity}
          colour={d.active_signals > 0 ? "text-orange-600" : undefined}
        />
        <StatCard
          label={t("surveillance.criticalSignals")}
          value={d.critical_signals ?? 0}
          icon={AlertTriangle}
          colour={d.critical_signals > 0 ? "text-red-600" : undefined}
        />
        <StatCard
          label={t("surveillance.suppliersAtRisk")}
          value={d.suppliers_at_risk ?? 0}
          icon={Shield}
          colour={d.suppliers_at_risk > 0 ? "text-orange-600" : undefined}
        />
        <StatCard label={t("surveillance.watchlist")} value={d.watchlist_count ?? 0} icon={Eye} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label={t("surveillance.improving")}
          value={d.suppliers_improving ?? 0}
          icon={TrendingUp}
          colour="text-green-600"
        />
        <StatCard
          label="Deteriorating"
          value={d.suppliers_deteriorating ?? 0}
          icon={TrendingDown}
          colour={d.suppliers_deteriorating > 0 ? "text-red-600" : undefined}
        />
        <StatCard
          label="Open Episodes"
          value={d.open_episodes ?? 0}
          icon={Zap}
          colour={d.open_episodes > 0 ? "text-yellow-600" : undefined}
        />
        <StatCard
          label="Total Suppliers"
          value={d.total_suppliers ?? 0}
          icon={Shield}
        />
      </div>

      {/* Externe Risikosignale nach Connector */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Building2 className="h-4 w-4 text-muted-foreground" />
          <h2 className="font-semibold text-base">Externe Risikosignale nach Quelle</h2>
          <span className="text-xs text-muted-foreground">— Top 10 je Connector, bezogen auf deine Lieferanten</span>
        </div>
        {connectorLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
            <Loader2 className="h-4 w-4 animate-spin" /> Signale werden geladen…
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {(byConnector?.connectors ?? []).map((c) => (
              <ConnectorCard key={c.source_name} connector={c} />
            ))}
          </div>
        )}
      </div>

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
              <p className="text-sm text-muted-foreground">No active signals.</p>
            ) : (
              <div>
                {(signals ?? []).map((s: any) => (
                  <SignalRow key={s.id} signal={s} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Open Risk Episodes */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Open Risk Episodes</CardTitle>
          </CardHeader>
          <CardContent>
            {(episodes ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No open episodes.</p>
            ) : (
              <div>
                {(episodes ?? []).map((e: any) => (
                  <EpisodeRow key={e.id} episode={e} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Watchlist */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("surveillance.watchlist")}</CardTitle>
          </CardHeader>
          <CardContent>
            {(watchlist ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No suppliers on watchlist.
              </p>
            ) : (
              <div>
                {(watchlist ?? []).map((w: any) => (
                  <div
                    key={w.id}
                    className="flex items-start justify-between py-3 border-b last:border-0"
                  >
                    <div className="flex-1 min-w-0 mr-4">
                      <p className="text-sm font-medium truncate">
                        {w.supplier_id}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">
                        {w.watch_reason}
                      </p>
                    </div>
                    <SeverityBadge severity={w.severity} />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Signal type breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Portfolio Health</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              {
                label: "Improving suppliers",
                value: d.suppliers_improving ?? 0,
                colour: "bg-green-500",
              },
              {
                label: "Stable suppliers",
                value: d.suppliers_stable ?? 0,
                colour: "bg-blue-400",
              },
              {
                label: "Deteriorating suppliers",
                value: d.suppliers_deteriorating ?? 0,
                colour: "bg-red-500",
              },
              {
                label: "Needing review",
                value: d.suppliers_needing_review ?? 0,
                colour: "bg-yellow-500",
              },
            ].map((row) => (
              <div key={row.label} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>{row.label}</span>
                  <span className="font-medium">{row.value}</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className={`h-full ${row.colour} rounded-full`}
                    style={{
                      width:
                        d.total_suppliers > 0
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
    </div>
  );
}
