"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import apiClient from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChevronDown, ChevronRight, AlertTriangle, Globe, BarChart3, Database, Zap } from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface RiskSignal {
  id: string;
  signal_type: string;
  severity: string;
  description: string;
  source_name: string;
  source_version: string;
  observed_at: string;
  country_code: string;
  sector_code: string;
  supplier_id: string;
  is_active: boolean;
}

interface ConnectorGroup {
  source_name: string;
  label: string;
  total: number;
  signals: RiskSignal[];
}

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
  source_name: string;
  data_date: string;
}

interface SectorBenchmark {
  id: string;
  sector_id: string;
  sector_name: string;
  nace_code: string;
  average_esg_score: number;
  average_risk_score: number;
  average_compliance_coverage: number;
  p25_esg_score: number;
  p50_esg_score: number;
  p75_esg_score: number;
  supplier_count: number;
  source_name: string;
  benchmark_date: string;
}

interface SupplierEnrichment {
  id: string;
  supplier_id: string;
  country_code: string;
  country_risk_level: string;
  country_risk_score: number;
  sanctions_exposure: string;
  sector_percentile: number;
  percentile_rank: string;
  benchmark_score: number;
  external_risk_score: number;
  combined_risk_score: number;
  active_signal_count: number;
  enriched_at: string;
  dataset_version: string;
}

interface Dataset {
  id: string;
  source_name: string;
  source_version: string;
  dataset_status: string;
  valid_from: string;
  valid_until?: string;
  record_count?: number;
}

// ── Shared helpers ────────────────────────────────────────────────────────────

const SEV_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high: "bg-orange-100 text-orange-700 border-orange-200",
  medium: "bg-amber-100 text-amber-700 border-amber-200",
  low: "bg-slate-100 text-slate-600 border-slate-200",
};

const RISK_LEVEL_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-green-100 text-green-700",
};

function SeverityBadge({ severity }: { severity: string }) {
  const s = severity.toLowerCase();
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${SEV_COLORS[s] ?? "bg-slate-100 text-slate-500 border-slate-200"}`}>
      {s}
    </span>
  );
}

function RiskBadge({ level }: { level: string }) {
  const l = level.toLowerCase();
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${RISK_LEVEL_COLORS[l] ?? "bg-slate-100 text-slate-500"}`}>
      {l}
    </span>
  );
}

function ScoreCell({ value, invert = false }: { value: number; invert?: boolean }) {
  const pct = value <= 1 ? value * 100 : value;
  const good = invert ? pct < 40 : pct >= 60;
  const warn = invert ? pct < 70 : pct >= 40;
  const color = good ? "text-green-700" : warn ? "text-amber-700" : "text-red-700";
  return <span className={`font-medium tabular-nums ${color}`}>{pct.toFixed(0)}</span>;
}

// ── Signals Tab ───────────────────────────────────────────────────────────────

function SignalsTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";
  const [expanded, setExpanded] = useState<string | null>(null);
  const [severity, setSeverity] = useState<string>("");

  const { data: byConnector, isLoading: connLoading } = useQuery<{ connectors: ConnectorGroup[] }>({
    queryKey: ["ext-intel", "by-connector", orgId],
    queryFn: async () => (await apiClient.get("/external-intelligence/signals/by-connector?top_n=10")).data,
    staleTime: 60_000,
    enabled: !!orgId,
  });

  const { data: flatSignals, isLoading: flatLoading } = useQuery<{ signals: RiskSignal[]; total: number }>({
    queryKey: ["ext-intel", "signals", orgId, severity],
    queryFn: async () => {
      const params: Record<string, string> = { limit: "100" };
      if (severity) params.severity = severity;
      return (await apiClient.get("/external-intelligence/signals", { params })).data;
    },
    staleTime: 60_000,
    enabled: !!orgId,
  });

  const isLoading = connLoading || flatLoading;
  const connectors = byConnector?.connectors ?? [];
  const totalSignals = flatSignals?.total ?? 0;
  const criticalCount = (flatSignals?.signals ?? []).filter((s) => s.severity.toLowerCase() === "critical").length;

  return (
    <div className="space-y-6">
      {/* Summary bar */}
      <div className="flex flex-wrap gap-3">
        {["", "critical", "high", "medium", "low"].map((s) => (
          <button
            key={s || "all"}
            onClick={() => setSeverity(s)}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              severity === s
                ? "bg-slate-800 text-white border-slate-800"
                : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"
            }`}
          >
            {s ? s.charAt(0).toUpperCase() + s.slice(1) : t("extint.allSignals")}
            {!s && totalSignals > 0 && <span className="ml-1.5 text-slate-400">{totalSignals}</span>}
            {s === "critical" && criticalCount > 0 && <span className="ml-1.5 text-red-500">{criticalCount}</span>}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : connectors.length === 0 ? (
        <Card>
          <CardContent className="py-14 text-center">
            <Zap className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="font-medium text-slate-600">{t("extint.noSignals")}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {connectors.map((conn) => {
            const open = expanded === conn.source_name;
            const filteredSignals = severity
              ? conn.signals.filter((s) => s.severity.toLowerCase() === severity)
              : conn.signals;
            return (
              <Card key={conn.source_name} className={open ? "border-blue-200" : ""}>
                <CardContent className="pt-4 pb-4">
                  <button
                    className="flex w-full items-center justify-between gap-4 text-left"
                    onClick={() => setExpanded(open ? null : conn.source_name)}
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-slate-900">{conn.label}</span>
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                        {conn.total} {t("extint.signals")}
                      </span>
                      {conn.signals.some((s) => s.severity.toLowerCase() === "critical") && (
                        <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                          {t("extint.critical")}
                        </span>
                      )}
                    </div>
                    {open
                      ? <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />
                      : <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />}
                  </button>

                  {open && (
                    <div className="mt-4 border-t border-slate-100 pt-4 space-y-2">
                      {filteredSignals.length === 0 ? (
                        <p className="text-sm text-slate-400">{t("extint.noMatchingSignals")}</p>
                      ) : (
                        filteredSignals.map((sig) => (
                          <div key={sig.id} className="rounded-md border border-slate-100 bg-slate-50 p-3">
                            <div className="flex flex-wrap items-center gap-2 mb-1.5">
                              <SeverityBadge severity={sig.severity} />
                              <span className="text-xs text-slate-400 capitalize">{sig.signal_type.replace(/_/g, " ")}</span>
                              {sig.country_code && (
                                <span className="text-xs text-slate-400">{sig.country_code}</span>
                              )}
                              <span className="ml-auto text-xs text-slate-400">
                                {new Date(sig.observed_at).toLocaleDateString()}
                              </span>
                            </div>
                            <p className="text-sm text-slate-700">{sig.description}</p>
                          </div>
                        ))
                      )}
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

// ── Countries Tab ─────────────────────────────────────────────────────────────

function CountriesTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";
  const [riskLevel, setRiskLevel] = useState("");

  const { data, isLoading } = useQuery<{ profiles: CountryRisk[]; total: number }>({
    queryKey: ["ext-intel", "countries", orgId, riskLevel],
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
          <button
            key={level || "all"}
            onClick={() => setRiskLevel(level)}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              riskLevel === level
                ? "bg-slate-800 text-white border-slate-800"
                : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"
            }`}
          >
            {level ? level.charAt(0).toUpperCase() + level.slice(1) : t("extint.allCountries")}
          </button>
        ))}
        <span className="ml-auto self-center text-xs text-slate-400">{data?.total ?? 0} {t("extint.countries")}</span>
      </div>

      {isLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : profiles.length === 0 ? (
        <Card>
          <CardContent className="py-14 text-center">
            <Globe className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="font-medium text-slate-600">{t("extint.noCountries")}</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="pt-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  {[
                    t("extint.country"),
                    t("extint.riskLevel"),
                    t("extint.overall"),
                    t("extint.governance"),
                    t("extint.corruption"),
                    t("extint.labourRights"),
                    t("extint.humanRights"),
                    t("extint.environment"),
                    t("extint.sanctions"),
                  ].map((h) => (
                    <th key={h} className="py-3 pr-4 text-left text-xs font-medium text-slate-400 first:pl-0 whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {profiles.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/50">
                    <td className="py-2.5 pr-4">
                      <span className="font-medium text-slate-800">{p.country_name}</span>
                      <span className="ml-1.5 text-xs text-slate-400">{p.country_code}</span>
                    </td>
                    <td className="py-2.5 pr-4"><RiskBadge level={p.risk_level} /></td>
                    <td className="py-2.5 pr-4"><ScoreCell value={p.overall_risk_score} invert /></td>
                    <td className="py-2.5 pr-4"><ScoreCell value={p.governance_score} /></td>
                    <td className="py-2.5 pr-4"><ScoreCell value={p.corruption_score} invert /></td>
                    <td className="py-2.5 pr-4"><ScoreCell value={p.labour_rights_score} /></td>
                    <td className="py-2.5 pr-4"><ScoreCell value={p.human_rights_score} /></td>
                    <td className="py-2.5 pr-4"><ScoreCell value={p.environmental_risk_score} invert /></td>
                    <td className="py-2.5">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${p.sanctions_status === "none" ? "bg-green-50 text-green-700" : "bg-red-100 text-red-700"}`}>
                        {p.sanctions_status}
                      </span>
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

// ── Sectors Tab ───────────────────────────────────────────────────────────────

function SectorsTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";

  const { data, isLoading } = useQuery<{ benchmarks: SectorBenchmark[]; total: number }>({
    queryKey: ["ext-intel", "sectors", orgId],
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
        <Card>
          <CardContent className="py-14 text-center">
            <BarChart3 className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="font-medium text-slate-600">{t("extint.noSectors")}</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="pt-0 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  {[
                    t("extint.sector"),
                    t("extint.nace"),
                    t("extint.avgEsg"),
                    t("extint.esgRange"),
                    t("extint.avgRisk"),
                    t("extint.compliance"),
                    t("extint.supplierCount"),
                  ].map((h) => (
                    <th key={h} className="py-3 pr-4 text-left text-xs font-medium text-slate-400 first:pl-0 whitespace-nowrap">
                      {h}
                    </th>
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
                      <td className="py-2.5 pr-4">
                        <span className="font-medium text-slate-800">{b.sector_name}</span>
                      </td>
                      <td className="py-2.5 pr-4">
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-mono text-slate-600">{b.nace_code}</span>
                      </td>
                      <td className="py-2.5 pr-4">
                        <ScoreCell value={b.average_esg_score} />
                      </td>
                      <td className="py-2.5 pr-4">
                        <div className="flex items-center gap-1 text-xs text-slate-500">
                          <span>{p25.toFixed(0)}</span>
                          <div className="relative h-1.5 w-16 rounded-full bg-slate-100">
                            <div
                              className="absolute h-1.5 rounded-full bg-blue-400"
                              style={{ left: `${p25}%`, width: `${p75 - p25}%` }}
                            />
                            <div
                              className="absolute h-3 w-0.5 -top-0.5 rounded bg-blue-700"
                              style={{ left: `${p50}%` }}
                            />
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

// ── High-Risk Suppliers Tab ───────────────────────────────────────────────────

function HighRiskTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";

  const { data, isLoading } = useQuery<{ enrichments: SupplierEnrichment[]; total: number }>({
    queryKey: ["ext-intel", "high-risk", orgId],
    queryFn: async () =>
      (await apiClient.get("/external-intelligence/enrichments/high-risk?min_combined_risk=60&limit=50")).data,
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
        <Card>
          <CardContent className="py-14 text-center">
            <AlertTriangle className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="font-medium text-slate-600">{t("extint.noHighRisk")}</p>
          </CardContent>
        </Card>
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
                  <div className="rounded bg-slate-50 p-2">
                    <p className="text-slate-400">{t("extint.combinedRisk")}</p>
                    <p className="font-bold text-red-700 text-base">{e.combined_risk_score.toFixed(0)}</p>
                  </div>
                  <div className="rounded bg-slate-50 p-2">
                    <p className="text-slate-400">{t("extint.externalRisk")}</p>
                    <p className="font-bold text-orange-700 text-base">{e.external_risk_score.toFixed(0)}</p>
                  </div>
                  <div className="rounded bg-slate-50 p-2">
                    <p className="text-slate-400">{t("extint.sectorPercentile")}</p>
                    <p className="font-semibold text-slate-700">{e.sector_percentile.toFixed(0)}
                      <span className="text-xs font-normal text-slate-400 ml-1">({e.percentile_rank})</span>
                    </p>
                  </div>
                  <div className="rounded bg-slate-50 p-2">
                    <p className="text-slate-400">{t("extint.activeSignals")}</p>
                    <p className={`font-semibold ${e.active_signal_count > 0 ? "text-amber-700" : "text-slate-700"}`}>
                      {e.active_signal_count}
                    </p>
                  </div>
                </div>

                {e.sanctions_exposure !== "none" && (
                  <div className="rounded bg-red-50 px-2.5 py-1.5">
                    <p className="text-xs font-medium text-red-700">
                      {t("extint.sanctionsExposure")}: <span className="capitalize">{e.sanctions_exposure}</span>
                    </p>
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

// ── Datasets Tab ──────────────────────────────────────────────────────────────

function DatasetsTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";

  const { data, isLoading } = useQuery<{ datasets: Dataset[]; total: number }>({
    queryKey: ["ext-intel", "datasets", orgId],
    queryFn: async () => (await apiClient.get("/external-intelligence/datasets?limit=50")).data,
    staleTime: 300_000,
    enabled: !!orgId,
  });

  const datasets = data?.datasets ?? [];

  const CONNECTOR_LABELS: Record<string, string> = {
    world_bank: "World Bank",
    transparency_international: "Transparency International",
    ilo: "ILO",
    unicef: "UNICEF",
    un_sanctions: "UN Sanctions",
    eu_sanctions: "EU Sanctions",
  };

  return (
    <div className="space-y-4">
      {isLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : datasets.length === 0 ? (
        <Card>
          <CardContent className="py-14 text-center">
            <Database className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="font-medium text-slate-600">{t("extint.noDatasets")}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {datasets.map((d) => (
            <Card key={d.id}>
              <CardContent className="pt-4">
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <p className="font-semibold text-slate-800 text-sm">
                      {CONNECTOR_LABELS[d.source_name] ?? d.source_name}
                    </p>
                    <p className="text-xs text-slate-400 font-mono">{d.source_version}</p>
                  </div>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize shrink-0 ${
                    d.dataset_status === "active" ? "bg-green-100 text-green-700"
                    : d.dataset_status === "pending" ? "bg-amber-100 text-amber-700"
                    : "bg-slate-100 text-slate-500"
                  }`}>
                    {d.dataset_status}
                  </span>
                </div>
                <div className="space-y-1 text-xs text-slate-500">
                  <div className="flex justify-between">
                    <span>{t("extint.validFrom")}</span>
                    <span className="text-slate-700">{new Date(d.valid_from).toLocaleDateString()}</span>
                  </div>
                  {d.valid_until && (
                    <div className="flex justify-between">
                      <span>{t("extint.validUntil")}</span>
                      <span className="text-slate-700">{new Date(d.valid_until).toLocaleDateString()}</span>
                    </div>
                  )}
                  {d.record_count != null && (
                    <div className="flex justify-between">
                      <span>{t("extint.records")}</span>
                      <span className="text-slate-700">{d.record_count.toLocaleString()}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ExternalIntelligencePage() {
  const { t } = useLanguage();

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t("extint.pageTitle")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("extint.pageSubtitle")}</p>
      </div>

      <Tabs defaultValue="signals">
        <TabsList>
          <TabsTrigger value="signals">{t("extint.tabSignals")}</TabsTrigger>
          <TabsTrigger value="countries">{t("extint.tabCountries")}</TabsTrigger>
          <TabsTrigger value="sectors">{t("extint.tabSectors")}</TabsTrigger>
          <TabsTrigger value="high-risk">{t("extint.tabHighRisk")}</TabsTrigger>
          <TabsTrigger value="datasets">{t("extint.tabDatasets")}</TabsTrigger>
        </TabsList>
        <TabsContent value="signals" className="mt-6"><SignalsTab /></TabsContent>
        <TabsContent value="countries" className="mt-6"><CountriesTab /></TabsContent>
        <TabsContent value="sectors" className="mt-6"><SectorsTab /></TabsContent>
        <TabsContent value="high-risk" className="mt-6"><HighRiskTab /></TabsContent>
        <TabsContent value="datasets" className="mt-6"><DatasetsTab /></TabsContent>
      </Tabs>
    </div>
  );
}
