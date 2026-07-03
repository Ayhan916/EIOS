"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { AlertTriangle, ArrowRight, GitBranch, Info, RefreshCw, Zap, Network, Eye } from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ResilienceData {
  resilience_score: number;
  diversification_score: number;
  concentration_score: number;
  redundancy_score: number;
  calculated_at: string;
}

interface DependencyData {
  dependency_score: number;
  concentration_score: number;
  diversification_score: number;
  critical_supplier_count: number;
  single_point_of_failure_count: number;
  calculated_at: string;
}

interface CentralityRecord {
  supplier_id: string;
  inbound_degree: number;
  outbound_degree: number;
  degree_centrality: number;
  connected_component_size: number;
}

interface CriticalityRecord {
  supplier_id: string;
  criticality: string;
  criticality_score: number;
  degree_centrality: number;
  inbound_degree: number;
  outbound_degree: number;
  dependency_score: number;
  finding_count: number;
  open_remediation_count: number;
}

interface ExecSupplier {
  id: string;
  name: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function pct(v: number) {
  return `${Math.round(v * 100)}%`;
}

function scoreColor(v: number, higherIsBetter: boolean): string {
  const good = higherIsBetter ? v >= 0.7 : v <= 0.3;
  const warn = higherIsBetter ? v >= 0.4 : v <= 0.6;
  if (good) return "text-emerald-700";
  if (warn) return "text-amber-600";
  return "text-red-600";
}

function barColor(v: number, higherIsBetter: boolean): string {
  const good = higherIsBetter ? v >= 0.7 : v <= 0.3;
  const warn = higherIsBetter ? v >= 0.4 : v <= 0.6;
  if (good) return "bg-emerald-500";
  if (warn) return "bg-amber-400";
  return "bg-red-500";
}

function critBadge(level: string): string {
  switch (level) {
    case "Critical": return "bg-red-100 text-red-800";
    case "High":     return "bg-orange-100 text-orange-800";
    case "Medium":   return "bg-amber-100 text-amber-800";
    default:         return "bg-slate-100 text-slate-600";
  }
}

// ── Score meter ───────────────────────────────────────────────────────────────

function ScoreMeter({
  label,
  value,
  higherIsBetter,
  hint,
}: {
  label: string;
  value: number;
  higherIsBetter: boolean;
  hint?: string;
}) {
  const color = barColor(value, higherIsBetter);
  const textColor = scoreColor(value, higherIsBetter);
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-500 flex items-center gap-1">
          {label}
          {hint && (
            <span title={hint}><Info className="h-3 w-3 text-slate-300 cursor-help" /></span>
          )}
        </span>
        <span className={`text-sm font-bold ${textColor}`}>{pct(value)}</span>
      </div>
      <div className="h-2.5 rounded-full bg-slate-100 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: pct(value) }}
        />
      </div>
    </div>
  );
}

// ── Big score ring ─────────────────────────────────────────────────────────────

function ScoreRing({ value, higherIsBetter, label }: { value: number; higherIsBetter: boolean; label: string }) {
  const color = scoreColor(value, higherIsBetter);
  const r = 36;
  const circ = 2 * Math.PI * r;
  const dash = circ * value;
  const trackColor = higherIsBetter
    ? value >= 0.7 ? "#10b981" : value >= 0.4 ? "#f59e0b" : "#ef4444"
    : value <= 0.3 ? "#10b981" : value <= 0.6 ? "#f59e0b" : "#ef4444";

  return (
    <div className="flex flex-col items-center">
      <div className="relative h-24 w-24">
        <svg className="h-24 w-24 -rotate-90" viewBox="0 0 88 88">
          <circle cx="44" cy="44" r={r} fill="none" stroke="#e2e8f0" strokeWidth="8" />
          <circle
            cx="44" cy="44" r={r}
            fill="none"
            stroke={trackColor}
            strokeWidth="8"
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-xl font-bold ${color}`}>{pct(value)}</span>
        </div>
      </div>
      <p className="mt-2 text-xs font-medium text-slate-600 text-center">{label}</p>
    </div>
  );
}

// ── Tab: Overview ─────────────────────────────────────────────────────────────

function OverviewTab() {
  const { t } = useLanguage();

  const { data: res, isLoading: resLoading } = useQuery<ResilienceData>({
    queryKey: ["network-resilience"],
    queryFn: async () => (await apiClient.get("/network/resilience")).data,
  });

  const { data: dep, isLoading: depLoading } = useQuery<DependencyData>({
    queryKey: ["network-dependency"],
    queryFn: async () => (await apiClient.get("/network/dependency-analysis")).data,
  });

  if (resLoading || depLoading) {
    return <div className="flex justify-center py-16"><Spinner size="lg" /></div>;
  }

  return (
    <div className="mt-4 grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Resilience card */}
      <Card className="border-2 border-emerald-100">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">{t("netres.resilience")}</CardTitle>
            {res && (
              <span className="text-[11px] text-slate-400">
                {t("netres.calcAt")}: {new Date(res.calculated_at).toLocaleDateString()}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">{t("netres.resilienceDesc")}</p>
        </CardHeader>
        <CardContent className="space-y-5">
          {!res ? (
            <p className="text-sm text-slate-400">{t("netres.noData")}</p>
          ) : (
            <>
              <div className="flex justify-center pb-2">
                <ScoreRing value={res.resilience_score} higherIsBetter label={t("netres.resilience")} />
              </div>
              <div className="space-y-3">
                <ScoreMeter
                  label={t("netres.diversification")}
                  value={res.diversification_score}
                  higherIsBetter
                  hint={t("netres.higherBetter")}
                />
                <ScoreMeter
                  label={t("netres.concentration")}
                  value={res.concentration_score}
                  higherIsBetter={false}
                  hint={t("netres.higherWorse")}
                />
                <ScoreMeter
                  label={t("netres.redundancy")}
                  value={res.redundancy_score}
                  higherIsBetter
                  hint={t("netres.higherBetter")}
                />
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Dependency card */}
      <Card className="border-2 border-orange-100">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">{t("netres.dependency")}</CardTitle>
            {dep && (
              <span className="text-[11px] text-slate-400">
                {t("netres.calcAt")}: {new Date(dep.calculated_at).toLocaleDateString()}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">{t("netres.dependencyDesc")}</p>
        </CardHeader>
        <CardContent className="space-y-5">
          {!dep ? (
            <p className="text-sm text-slate-400">{t("netres.noDep")}</p>
          ) : (
            <>
              <div className="flex justify-center pb-2">
                <ScoreRing value={dep.dependency_score} higherIsBetter={false} label={t("netres.dependency")} />
              </div>
              <div className="space-y-3">
                <ScoreMeter
                  label={t("netres.concentration")}
                  value={dep.concentration_score}
                  higherIsBetter={false}
                  hint={t("netres.higherWorse")}
                />
                <ScoreMeter
                  label={t("netres.diversification")}
                  value={dep.diversification_score}
                  higherIsBetter
                  hint={t("netres.higherBetter")}
                />
              </div>
              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100">
                <div className="rounded-lg bg-red-50 border border-red-100 p-3 text-center">
                  <p className="text-2xl font-bold text-red-700">{dep.critical_supplier_count}</p>
                  <p className="text-xs text-red-600 mt-0.5">{t("netres.criticalSuppliers")}</p>
                </div>
                <div className="rounded-lg bg-orange-50 border border-orange-100 p-3 text-center">
                  <p className="text-2xl font-bold text-orange-700">{dep.single_point_of_failure_count}</p>
                  <p className="text-xs text-orange-600 mt-0.5">{t("netres.spof")}</p>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Tab: Centrality ───────────────────────────────────────────────────────────

function CentralityTab({ nameMap }: { nameMap: Map<string, string> }) {
  const { t } = useLanguage();

  const { data = [], isLoading } = useQuery<CentralityRecord[]>({
    queryKey: ["network-centrality"],
    queryFn: async () => (await apiClient.get("/network/centrality", { params: { limit: 50 } })).data,
  });

  if (isLoading) return <div className="flex justify-center py-16"><Spinner size="lg" /></div>;

  if (data.length === 0) {
    return (
      <div className="mt-4 rounded-lg border border-dashed p-12 text-center text-sm text-slate-400">
        <GitBranch className="mx-auto mb-3 h-8 w-8 text-slate-300" />
        {t("netres.centralityEmpty")}
      </div>
    );
  }

  const sorted = [...data].sort((a, b) => b.degree_centrality - a.degree_centrality);

  return (
    <div className="mt-4 rounded-xl border border-slate-200 bg-white overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            <th className="px-4 py-3 w-8">#</th>
            <th className="px-4 py-3">{t("analytics.supplier")}</th>
            <th className="px-4 py-3">{t("netres.degCentrality")}</th>
            <th className="px-4 py-3">{t("netres.inbound")}</th>
            <th className="px-4 py-3">{t("netres.outbound")}</th>
            <th className="px-4 py-3">{t("netres.componentSize")}</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => {
            const name = nameMap.get(r.supplier_id);
            const maxCentrality = sorted[0]?.degree_centrality ?? 1;
            const barW = maxCentrality > 0 ? (r.degree_centrality / maxCentrality) * 100 : 0;
            return (
              <tr key={r.supplier_id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                <td className="px-4 py-3 font-bold text-slate-300 text-center">{i + 1}</td>
                <td className="px-4 py-3">
                  {name ? (
                    <p className="font-medium text-slate-900">{name}</p>
                  ) : (
                    <p className="font-mono text-xs text-slate-500">{r.supplier_id.slice(0, 12)}…</p>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-20 rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-blue-500"
                        style={{ width: `${barW}%` }}
                      />
                    </div>
                    <span className="font-mono text-xs text-slate-700">{r.degree_centrality.toFixed(3)}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-center text-slate-600">{r.inbound_degree}</td>
                <td className="px-4 py-3 text-center text-slate-600">{r.outbound_degree}</td>
                <td className="px-4 py-3 text-center text-slate-600">{r.connected_component_size}</td>
                <td className="px-4 py-3">
                  <Link
                    href={`/suppliers/${r.supplier_id}`}
                    className="text-blue-500 hover:text-blue-700"
                  >
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Tab: Criticality ──────────────────────────────────────────────────────────

const CRITICALITY_LEVELS = ["Critical", "High", "Medium", "Low"];

function CriticalityTab({ nameMap }: { nameMap: Map<string, string> }) {
  const { t } = useLanguage();
  const [filterLevel, setFilterLevel] = useState("");

  const { data = [], isLoading } = useQuery<CriticalityRecord[]>({
    queryKey: ["network-criticality", filterLevel],
    queryFn: async () => {
      const params: Record<string, string> = { limit: "50" };
      if (filterLevel) params.criticality_level = filterLevel;
      return (await apiClient.get("/network/criticality", { params })).data;
    },
  });

  return (
    <div className="mt-4 space-y-4">
      {/* Filter */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-slate-500">{t("netres.criticalityLevel")}:</span>
        <select
          value={filterLevel}
          onChange={(e) => setFilterLevel(e.target.value)}
          className="rounded-md border border-slate-200 px-2.5 py-1.5 text-sm outline-none focus:ring-2 focus:ring-blue-400"
        >
          <option value="">{t("netres.filterLevel")}</option>
          {CRITICALITY_LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        {!isLoading && <span className="text-xs text-slate-400">{data.length} suppliers</span>}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : data.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-sm text-slate-400">
          <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-slate-300" />
          {t("netres.criticalityEmpty")}
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3">{t("analytics.supplier")}</th>
                <th className="px-4 py-3">{t("netres.criticalityLevel")}</th>
                <th className="px-4 py-3">{t("netres.criticalityScore")}</th>
                <th className="px-4 py-3">{t("netres.degCentrality")}</th>
                <th className="px-4 py-3">{t("netres.depScore")}</th>
                <th className="px-4 py-3">{t("netres.inbound")} / {t("netres.outbound")}</th>
                <th className="px-4 py-3">{t("netres.findings")}</th>
                <th className="px-4 py-3">{t("netres.remediations")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {data.map((r) => {
                const name = nameMap.get(r.supplier_id);
                return (
                  <tr key={r.supplier_id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                    <td className="px-4 py-3">
                      {name ? (
                        <p className="font-medium text-slate-900">{name}</p>
                      ) : (
                        <p className="font-mono text-xs text-slate-500">{r.supplier_id.slice(0, 12)}…</p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${critBadge(r.criticality)}`}>
                        {r.criticality}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-sm font-semibold text-slate-800">
                      {r.criticality_score.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">
                      {r.degree_centrality.toFixed(3)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">
                      {r.dependency_score.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {r.inbound_degree} / {r.outbound_degree}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {r.finding_count > 0
                        ? <span className="font-semibold text-red-600">{r.finding_count}</span>
                        : <span className="text-slate-300">—</span>}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {r.open_remediation_count > 0
                        ? <span className="font-semibold text-orange-600">{r.open_remediation_count}</span>
                        : <span className="text-slate-300">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/suppliers/${r.supplier_id}`}
                        className="text-blue-500 hover:text-blue-700"
                      >
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Types (extra) ─────────────────────────────────────────────────────────────

interface ExposureSignal {
  id: string;
  origin_supplier_id: string;
  impacted_supplier_id: string;
  exposure_type: string;
  path_length: number;
  severity: string;
  rationale: string;
  exposure_status: string;
  detected_at: string;
}

interface IncidentCluster {
  id: string;
  cluster_name: string;
  root_cause: string;
  severity: string;
  cluster_status: string;
  affected_supplier_ids: string[];
  created_at: string;
}

interface WatchlistEntry {
  id: string;
  watched_supplier_id: string;
  related_supplier_id: string;
  distance: number;
  has_active_alert: boolean;
  created_at: string;
}

// ── Severity badge ─────────────────────────────────────────────────────────────

function SevBadge({ level }: { level: string }) {
  const map: Record<string, string> = {
    CRITICAL: "bg-red-100 text-red-800",
    HIGH: "bg-orange-100 text-orange-800",
    MEDIUM: "bg-amber-100 text-amber-800",
    LOW: "bg-slate-100 text-slate-600",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${map[level.toUpperCase()] ?? "bg-slate-100 text-slate-600"}`}>
      {level}
    </span>
  );
}

// ── Tab: Exposure Signals ─────────────────────────────────────────────────────

function ExposuresTab({ nameMap }: { nameMap: Map<string, string> }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("ACTIVE");

  const { data: signals = [], isLoading } = useQuery<ExposureSignal[]>({
    queryKey: ["network-exposures", statusFilter],
    queryFn: async () => {
      const params: Record<string, string> = { limit: "100" };
      if (statusFilter) params.exposure_status = statusFilter;
      return (await apiClient.get("/network/exposure-signals", { params })).data;
    },
  });

  const detect = useMutation({
    mutationFn: () => apiClient.post("/network/cascade/detect"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["network-exposures"] }),
  });

  const name = (id: string) => nameMap.get(id) ?? id.slice(0, 10) + "…";

  return (
    <div className="mt-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border border-slate-200 px-2.5 py-1.5 text-sm outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="">All</option>
            <option value="ACTIVE">Active</option>
            <option value="RESOLVED">Resolved</option>
          </select>
          {!isLoading && <span className="text-xs text-slate-400">{signals.length} signals</span>}
        </div>
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5"
          disabled={detect.isPending}
          onClick={() => detect.mutate()}
        >
          {detect.isPending ? <Spinner className="h-4 w-4" /> : <Zap className="h-4 w-4" />}
          {detect.isPending ? t("netres.detecting") : t("netres.detectCascade")}
        </Button>
      </div>

      {detect.isSuccess && (
        <div className="rounded-md bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-700">
          {t("netres.detected")}
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : signals.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-sm text-slate-400">
          <Network className="mx-auto mb-3 h-8 w-8 text-slate-300" />
          {t("netres.exposureEmpty")}
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3">{t("netres.exposureOrigin")}</th>
                <th className="px-4 py-3">{t("netres.exposureImpacted")}</th>
                <th className="px-4 py-3">{t("netres.exposureType")}</th>
                <th className="px-4 py-3">{t("netres.exposureSeverity")}</th>
                <th className="px-4 py-3 text-center">{t("netres.pathLength")}</th>
                <th className="px-4 py-3">Rationale</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((s) => (
                <tr key={s.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link href={`/suppliers/${s.origin_supplier_id}`} className="font-medium text-slate-800 hover:text-blue-600">
                      {name(s.origin_supplier_id)}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <Link href={`/suppliers/${s.impacted_supplier_id}`} className="font-medium text-slate-800 hover:text-blue-600">
                      {name(s.impacted_supplier_id)}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-700 font-mono">
                      {s.exposure_type.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3"><SevBadge level={s.severity} /></td>
                  <td className="px-4 py-3 text-center text-slate-600 tabular-nums">{s.path_length}</td>
                  <td className="px-4 py-3 text-xs text-slate-500 max-w-[200px] truncate">{s.rationale}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Tab: Incident Clusters ────────────────────────────────────────────────────

function ClustersTab({ nameMap }: { nameMap: Map<string, string> }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("ACTIVE");

  const { data: clusters = [], isLoading } = useQuery<IncidentCluster[]>({
    queryKey: ["network-clusters", statusFilter],
    queryFn: async () => {
      const params: Record<string, string> = { limit: "50" };
      if (statusFilter) params.cluster_status = statusFilter;
      return (await apiClient.get("/network/clusters", { params })).data;
    },
  });

  const detect = useMutation({
    mutationFn: () => apiClient.post("/network/clusters/detect"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["network-clusters"] }),
  });

  const name = (id: string) => nameMap.get(id) ?? id.slice(0, 10) + "…";

  return (
    <div className="mt-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border border-slate-200 px-2.5 py-1.5 text-sm outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="">All</option>
            <option value="ACTIVE">Active</option>
            <option value="RESOLVED">Resolved</option>
          </select>
          {!isLoading && <span className="text-xs text-slate-400">{clusters.length} clusters</span>}
        </div>
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5"
          disabled={detect.isPending}
          onClick={() => detect.mutate()}
        >
          {detect.isPending ? <Spinner className="h-4 w-4" /> : <RefreshCw className="h-4 w-4" />}
          {detect.isPending ? t("netres.detecting") : t("netres.detectClusters")}
        </Button>
      </div>

      {detect.isSuccess && (
        <div className="rounded-md bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-700">
          {t("netres.detected")}
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : clusters.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-sm text-slate-400">
          <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-slate-300" />
          {t("netres.clustersEmpty")}
        </div>
      ) : (
        <div className="space-y-3">
          {clusters.map((c) => (
            <Card key={c.id}>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <p className="font-semibold text-slate-800">{c.cluster_name}</p>
                      <SevBadge level={c.severity} />
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${c.cluster_status === "ACTIVE" ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"}`}>
                        {c.cluster_status}
                      </span>
                    </div>
                    <p className="text-sm text-slate-600 mb-2">
                      <span className="font-medium text-slate-500">{t("netres.rootCause")}:</span> {c.root_cause}
                    </p>
                    {c.affected_supplier_ids.length > 0 && (
                      <div>
                        <p className="text-xs text-slate-400 mb-1">{t("netres.affectedSuppliers")} ({c.affected_supplier_ids.length})</p>
                        <div className="flex flex-wrap gap-1">
                          {c.affected_supplier_ids.slice(0, 8).map((id) => (
                            <Link key={id} href={`/suppliers/${id}`}
                              className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600 hover:bg-blue-50 hover:text-blue-700 transition-colors">
                              {name(id)}
                            </Link>
                          ))}
                          {c.affected_supplier_ids.length > 8 && (
                            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-400">
                              +{c.affected_supplier_ids.length - 8}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                  <span className="shrink-0 text-xs text-slate-400">
                    {new Date(c.created_at).toLocaleDateString()}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Tab: Watchlist ────────────────────────────────────────────────────────────

function WatchlistTab({ nameMap }: { nameMap: Map<string, string> }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [expandTarget, setExpandTarget] = useState("");

  const { data: entries = [], isLoading } = useQuery<WatchlistEntry[]>({
    queryKey: ["network-watchlist"],
    queryFn: async () => (await apiClient.get("/network/watchlists")).data,
    staleTime: 30_000,
  });

  const expand = useMutation({
    mutationFn: (supplierId: string) => apiClient.post(`/network/watchlists/${supplierId}/expand`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["network-watchlist"] });
      setExpandTarget("");
    },
  });

  const collapse = useMutation({
    mutationFn: (supplierId: string) => apiClient.delete(`/network/watchlists/${supplierId}/expand`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["network-watchlist"] }),
  });

  const name = (id: string) => nameMap.get(id) ?? id.slice(0, 10) + "…";

  const watchedIds = [...new Set(entries.map((e) => e.watched_supplier_id))];

  return (
    <div className="mt-4 space-y-4">
      {/* Expand new supplier */}
      <Card className="border-blue-100 bg-blue-50/30">
        <CardContent className="pt-4 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-600 mb-1">{t("netres.expandWatchlist")}</p>
              <select
                className="h-9 w-full rounded-md border border-slate-200 bg-white px-2 text-sm"
                value={expandTarget}
                onChange={(e) => setExpandTarget(e.target.value)}
              >
                <option value="">— select supplier —</option>
                {Array.from(nameMap.entries()).map(([id, n]) => (
                  <option key={id} value={id}>{n}</option>
                ))}
              </select>
            </div>
            <Button
              size="sm"
              className="shrink-0 mt-5 gap-1.5"
              disabled={!expandTarget || expand.isPending}
              onClick={() => expand.mutate(expandTarget)}
            >
              {expand.isPending ? <Spinner className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              {t("netres.expandWatchlist")}
            </Button>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : entries.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-sm text-slate-400">
          <Eye className="mx-auto mb-3 h-8 w-8 text-slate-300" />
          {t("netres.watchlistEmpty")}
        </div>
      ) : (
        <div className="space-y-4">
          {watchedIds.map((watchedId) => {
            const group = entries.filter((e) => e.watched_supplier_id === watchedId);
            return (
              <Card key={watchedId}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-slate-400">{t("netres.watchedSupplier")}</p>
                      <Link href={`/suppliers/${watchedId}`} className="font-semibold text-slate-800 hover:text-blue-600">
                        {name(watchedId)}
                      </Link>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 text-xs gap-1 text-red-600 border-red-200 hover:bg-red-50"
                      disabled={collapse.isPending}
                      onClick={() => collapse.mutate(watchedId)}
                    >
                      {collapse.isPending ? <Spinner className="h-3 w-3" /> : null}
                      {t("netres.collapse")}
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                        <th className="pb-2">{t("netres.relatedSupplier")}</th>
                        <th className="pb-2 text-center">{t("netres.distance")}</th>
                        <th className="pb-2 text-center">{t("netres.hasAlert")}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {group.map((e) => (
                        <tr key={e.id} className="hover:bg-slate-50">
                          <td className="py-2">
                            <Link href={`/suppliers/${e.related_supplier_id}`} className="text-slate-700 hover:text-blue-600">
                              {name(e.related_supplier_id)}
                            </Link>
                          </td>
                          <td className="py-2 text-center tabular-nums text-slate-500">{e.distance}</td>
                          <td className="py-2 text-center">
                            {e.has_active_alert ? (
                              <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-bold text-red-700">!</span>
                            ) : (
                              <span className="text-slate-300">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type Tab = "overview" | "centrality" | "criticality" | "exposures" | "clusters" | "watchlist";

const TABS: { id: Tab; labelKey: "netres.tabOverview" | "netres.tabCentrality" | "netres.tabCriticality" | "netres.tabExposures" | "netres.tabClusters" | "netres.tabWatchlist" }[] = [
  { id: "overview",    labelKey: "netres.tabOverview" },
  { id: "centrality",  labelKey: "netres.tabCentrality" },
  { id: "criticality", labelKey: "netres.tabCriticality" },
  { id: "exposures",   labelKey: "netres.tabExposures" },
  { id: "clusters",    labelKey: "netres.tabClusters" },
  { id: "watchlist",   labelKey: "netres.tabWatchlist" },
];

export default function NetworkResiliencePage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  // Pre-fetch supplier names for centrality + criticality tabs
  const { data: execSuppliers = [] } = useQuery<ExecSupplier[]>({
    queryKey: ["exec-suppliers-names"],
    queryFn: async () => {
      const res = await apiClient.get("/executive/suppliers");
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });

  const nameMap = new Map<string, string>(execSuppliers.map((s) => [s.id, s.name]));

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 flex-shrink-0">
          <GitBranch className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t("netres.title")}</h1>
          <p className="mt-0.5 text-sm text-slate-500">{t("netres.subtitle")}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 w-fit">
        {TABS.map((tab_) => (
          <button
            key={tab_.id}
            onClick={() => setActiveTab(tab_.id)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              activeTab === tab_.id
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {t(tab_.labelKey)}
          </button>
        ))}
      </div>

      {activeTab === "overview"    && <OverviewTab />}
      {activeTab === "centrality"  && <CentralityTab nameMap={nameMap} />}
      {activeTab === "criticality" && <CriticalityTab nameMap={nameMap} />}
      {activeTab === "exposures"   && <ExposuresTab nameMap={nameMap} />}
      {activeTab === "clusters"    && <ClustersTab nameMap={nameMap} />}
      {activeTab === "watchlist"   && <WatchlistTab nameMap={nameMap} />}
    </div>
  );
}
