"use client";

import { useState, useMemo, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Check,
  GitBranch,
  Network,
  Plus,
  Shield,
  Share2,
  TrendingDown,
  X,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { SupplierGraph } from "@/components/network/supplier-graph";
import type { GraphSupplier, GraphRelationship } from "@/components/network/supplier-graph";

// ── #115 Guided tour ─────────────────────────────────────────────────────────

const TOUR_KEY = "eios_network_tour_seen";

const TOUR_STEPS = [
  { titleKey: "network.tourStep1Title", descKey: "network.tourStep1Desc" },
  { titleKey: "network.tourStep2Title", descKey: "network.tourStep2Desc" },
  { titleKey: "network.tourStep3Title", descKey: "network.tourStep3Desc" },
  { titleKey: "network.tourStep4Title", descKey: "network.tourStep4Desc" },
];

function NetworkTour() {
  const { t } = useLanguage();
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (typeof window !== "undefined" && !localStorage.getItem(TOUR_KEY)) {
      setVisible(true);
    }
  }, []);

  function dismiss() {
    localStorage.setItem(TOUR_KEY, "1");
    setVisible(false);
  }

  if (!visible) return null;

  const current = TOUR_STEPS[step];
  const isLast = step === TOUR_STEPS.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center pb-8 px-4 pointer-events-none">
      <div className="pointer-events-auto w-full max-w-md rounded-2xl bg-slate-900 border border-slate-700 shadow-2xl p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white">
              {step + 1}
            </span>
            <p className="text-sm font-semibold text-white">{t(current.titleKey as any)}</p>
          </div>
          <button onClick={dismiss} className="text-slate-400 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed mb-4">{t(current.descKey as any)}</p>
        <div className="flex items-center justify-between">
          <div className="flex gap-1">
            {TOUR_STEPS.map((_, i) => (
              <div key={i} className={`h-1.5 rounded-full transition-all ${i === step ? "w-6 bg-blue-500" : "w-1.5 bg-slate-600"}`} />
            ))}
          </div>
          <div className="flex gap-2">
            {step > 0 && (
              <button onClick={() => setStep((s) => s - 1)} className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800">
                {t("common.back")}
              </button>
            )}
            {isLast ? (
              <button onClick={dismiss} className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700">
                {t("common.done")} <ArrowRight className="h-3 w-3" />
              </button>
            ) : (
              <button onClick={() => setStep((s) => s + 1)} className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700">
                {t("common.next")} <ArrowRight className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── API ───────────────────────────────────────────────────────────────────────

async function getNetworkDashboard() {
  const res = await apiClient.get("/network/dashboard");
  return res.data;
}

async function getRelationships() {
  const res = await apiClient.get("/network/relationships?limit=20");
  return res.data;
}

async function getPendingSuggestions() {
  const res = await apiClient.get(
    "/network/suggested-relationships?suggestion_status=PENDING&limit=20"
  );
  return res.data;
}

async function getExposureSignals() {
  const res = await apiClient.get(
    "/network/exposure-signals?exposure_status=ACTIVE&limit=10"
  );
  return res.data;
}

async function getClusters() {
  const res = await apiClient.get(
    "/network/clusters?cluster_status=ACTIVE&limit=10"
  );
  return res.data;
}

async function getGraphData(): Promise<{
  suppliers: GraphSupplier[];
  relationships: GraphRelationship[];
}> {
  const [suppRes, relRes] = await Promise.all([
    apiClient.get("/executive/suppliers"),
    apiClient.get("/network/relationships?limit=500"),
  ]);
  const tierNum: Record<string, number> = { "Tier 1": 1, "Tier 2": 2, "Tier 3": 3 };
  const suppliers: GraphSupplier[] = (suppRes.data ?? []).map((s: any) => ({
    id: s.id,
    name: s.name,
    tier: tierNum[s.supplier_tier] ?? 4,
    overall_risk_level: s.risk_level ? String(s.risk_level).toUpperCase() : null,
    country: s.country ?? null,
    score: s.esg_score ?? null,
    industry: s.industry ?? null,
  }));
  const relationships: GraphRelationship[] = (relRes.data ?? []).map((r: any) => ({
    source: r.supplier_id,
    target: r.related_supplier_id,
    relationship_type: r.relationship_type,
  }));
  return { suppliers, relationships };
}

function NetworkGraphSection() {
  const { t } = useLanguage();
  const { data, isLoading } = useQuery({
    queryKey: ["network-graph"],
    queryFn: getGraphData,
    refetchInterval: 120_000,
  });

  const [tierFilter, setTierFilter] = useState<string>("");
  const [riskFilter, setRiskFilter] = useState<string>("");
  const [countryFilter, setCountryFilter] = useState<string>("");
  const [sectorFilter, setSectorFilter] = useState<string>("");

  const allSuppliers = data?.suppliers ?? [];

  const countries = useMemo(
    () => [...new Set(allSuppliers.map((s) => s.country).filter(Boolean))].sort() as string[],
    [allSuppliers]
  );

  const sectors = useMemo(
    () => [...new Set(allSuppliers.map((s) => s.industry).filter(Boolean))].sort() as string[],
    [allSuppliers]
  );

  const filteredSuppliers = useMemo(() => {
    return allSuppliers.filter((s) => {
      if (tierFilter && s.tier !== Number(tierFilter)) return false;
      if (riskFilter && (s.overall_risk_level ?? "LOW") !== riskFilter) return false;
      if (countryFilter && s.country !== countryFilter) return false;
      if (sectorFilter && s.industry !== sectorFilter) return false;
      return true;
    });
  }, [allSuppliers, tierFilter, riskFilter, countryFilter, sectorFilter]);

  const filteredIds = new Set(filteredSuppliers.map((s) => s.id));
  const filteredRelationships = (data?.relationships ?? []).filter(
    (r) => filteredIds.has(r.source) && filteredIds.has(r.target)
  );

  const hasFilter = tierFilter || riskFilter || countryFilter || sectorFilter;

  if (isLoading) return <div className="flex justify-center p-12"><Spinner /></div>;

  return (
    <div className="space-y-3">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
          className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200"
        >
          <option value="">{t("network.allTiers")}</option>
          <option value="1">Tier 1</option>
          <option value="2">Tier 2</option>
          <option value="3">Tier 3</option>
        </select>
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200"
        >
          <option value="">{t("network.allRisks")}</option>
          <option value="CRITICAL">{t("findings.critical")}</option>
          <option value="HIGH">{t("suppliers.high")}</option>
          <option value="MEDIUM">{t("suppliers.medium")}</option>
          <option value="LOW">{t("suppliers.low")}</option>
        </select>
        {countries.length > 0 && (
          <select
            value={countryFilter}
            onChange={(e) => setCountryFilter(e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200"
          >
            <option value="">{t("network.allCountries")}</option>
            {countries.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        )}
        {sectors.length > 0 && (
          <select
            value={sectorFilter}
            onChange={(e) => setSectorFilter(e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200"
          >
            <option value="">{t("network.allSectors")}</option>
            {sectors.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        )}
        {hasFilter && (
          <button
            onClick={() => { setTierFilter(""); setRiskFilter(""); setCountryFilter(""); setSectorFilter(""); }}
            className="flex items-center gap-1 rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X className="h-3 w-3" /> {t("network.clearFilters")}
          </button>
        )}
        <span className="ml-auto text-xs text-slate-500">
          {t("network.suppliersOf").replace("{n}", String(filteredSuppliers.length)).replace("{total}", String(allSuppliers.length))}
        </span>
      </div>
      <SupplierGraph
        suppliers={filteredSuppliers}
        relationships={filteredRelationships}
      />
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    CRITICAL: "bg-red-600 text-white",
    HIGH: "bg-orange-500 text-white",
    MEDIUM: "bg-yellow-500 text-black",
    LOW: "bg-blue-500 text-white",
    NONE: "bg-slate-500 text-white",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${map[severity] ?? "bg-slate-500 text-white"}`}
    >
      {severity}
    </span>
  );
}

function RelationshipTypeBadge({ type }: { type: string }) {
  const label = type.replace(/_/g, " ");
  return (
    <span className="inline-flex items-center rounded-full bg-slate-700 px-2 py-0.5 text-xs font-medium text-slate-200">
      {label}
    </span>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  sub,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  sub?: string;
}) {
  return (
    <Card className="border-slate-800 bg-slate-900 text-slate-100">
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
              {title}
            </p>
            <p className="mt-1 text-2xl font-bold">{value}</p>
            {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
          </div>
          <Icon className="h-8 w-8 text-blue-500 opacity-60" />
        </div>
      </CardContent>
    </Card>
  );
}

// ── Sections ──────────────────────────────────────────────────────────────────

const REL_TYPES = [
  "TIER_1_SUPPLIER", "TIER_2_SUPPLIER", "SUB_SUPPLIER",
  "CO_SUPPLIER", "CONTRACT_MANUFACTURER", "RAW_MATERIAL_SUPPLIER",
  "LOGISTICS_PARTNER", "SERVICE_PROVIDER",
];

function RelationshipsSection({ nameMap }: { nameMap: Map<string, string> }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [sup1, setSup1] = useState("");
  const [sup2, setSup2] = useState("");
  const [relType, setRelType] = useState("TIER_1_SUPPLIER");
  const [confidence, setConfidence] = useState(1.0);
  const [rationale, setRationale] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["network-relationships"],
    queryFn: getRelationships,
    refetchInterval: 60_000,
  });

  const create = useMutation({
    mutationFn: () => apiClient.post("/network/relationships", {
      supplier_id: sup1,
      related_supplier_id: sup2,
      relationship_type: relType,
      confidence,
      rationale,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["network-relationships"] });
      qc.invalidateQueries({ queryKey: ["network-graph"] });
      qc.invalidateQueries({ queryKey: ["network-dashboard"] });
      setShowCreate(false);
      setSup1(""); setSup2(""); setRationale(""); setConfidence(1.0);
    },
  });

  const supplierOptions = Array.from(nameMap.entries());
  const name = (id: string) => nameMap.get(id) ?? id.slice(0, 10) + "…";

  return (
    <div>
      {/* Create form toggle */}
      <div className="mb-3 flex justify-end">
        <Button size="sm" variant="outline" className="gap-1.5 border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white"
          onClick={() => setShowCreate(!showCreate)}>
          <Plus className="h-3.5 w-3.5" />
          {t("network.createRelationship")}
        </Button>
      </div>

      {showCreate && (
        <div className="mb-4 rounded-lg border border-slate-700 bg-slate-800/60 p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-slate-400">{t("network.supplier1")} *</Label>
              <select className="mt-1 h-9 w-full rounded-md border border-slate-700 bg-slate-900 px-2 text-sm text-slate-200"
                value={sup1} onChange={(e) => setSup1(e.target.value)}>
                <option value="">— select —</option>
                {supplierOptions.map(([id, n]) => <option key={id} value={id}>{n}</option>)}
              </select>
            </div>
            <div>
              <Label className="text-xs text-slate-400">{t("network.supplier2")} *</Label>
              <select className="mt-1 h-9 w-full rounded-md border border-slate-700 bg-slate-900 px-2 text-sm text-slate-200"
                value={sup2} onChange={(e) => setSup2(e.target.value)}>
                <option value="">— select —</option>
                {supplierOptions.map(([id, n]) => <option key={id} value={id}>{n}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-slate-400">{t("network.relationshipType")}</Label>
              <select className="mt-1 h-9 w-full rounded-md border border-slate-700 bg-slate-900 px-2 text-sm text-slate-200"
                value={relType} onChange={(e) => setRelType(e.target.value)}>
                {REL_TYPES.map((r) => <option key={r} value={r}>{r.replace(/_/g, " ")}</option>)}
              </select>
            </div>
            <div>
              <Label className="text-xs text-slate-400">Confidence (0–1)</Label>
              <Input type="number" min={0} max={1} step={0.05}
                className="mt-1 bg-slate-900 border-slate-700 text-slate-200 text-sm"
                value={confidence} onChange={(e) => setConfidence(parseFloat(e.target.value))} />
            </div>
          </div>
          <div>
            <Label className="text-xs text-slate-400">{t("network.rationale")}</Label>
            <Input className="mt-1 bg-slate-900 border-slate-700 text-slate-200 text-sm"
              value={rationale} onChange={(e) => setRationale(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="outline" className="border-slate-700 text-slate-400 hover:bg-slate-800"
              onClick={() => setShowCreate(false)}>{t("common.cancel")}</Button>
            <Button size="sm" disabled={!sup1 || !sup2 || sup1 === sup2 || create.isPending}
              onClick={() => create.mutate()} className="gap-1">
              {create.isPending && <Spinner className="h-4 w-4" />}
              {t("network.createRelationship")}
            </Button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center p-8"><Spinner /></div>
      ) : !data?.length ? (
        <p className="text-center text-sm text-slate-500 py-6">{t("network.noRelationships")}</p>
      ) : (
        <div className="divide-y divide-slate-800">
          {data.map((rel: any) => (
            <div key={rel.id} className="flex items-center gap-3 py-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <Link href={`/suppliers/${rel.supplier_id}`}
                    className="text-sm font-medium text-slate-100 hover:text-blue-400 truncate max-w-[140px]">
                    {name(rel.supplier_id)}
                  </Link>
                  <RelationshipTypeBadge type={rel.relationship_type} />
                  <Link href={`/suppliers/${rel.related_supplier_id}`}
                    className="text-sm font-medium text-slate-100 hover:text-blue-400 truncate max-w-[140px]">
                    {name(rel.related_supplier_id)}
                  </Link>
                </div>
                <p className="mt-0.5 text-xs text-slate-500 truncate">{rel.rationale || "—"}</p>
              </div>
              <div className="flex-shrink-0 text-right">
                <p className="text-xs text-slate-400">{Math.round(rel.confidence * 100)}{t("network.confidence")}</p>
                <p className="text-xs text-slate-500">{rel.source}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SuggestionsSection({ nameMap }: { nameMap: Map<string, string> }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [reviewNote, setReviewNote] = useState<Record<string, string>>({});
  const [reviewed, setReviewed] = useState<Record<string, "approved" | "rejected">>({});
  const [discoveryResult, setDiscoveryResult] = useState<{ total: number } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["network-suggestions-pending"],
    queryFn: getPendingSuggestions,
    refetchInterval: 60_000,
  });

  const discover = useMutation({
    mutationFn: () => apiClient.post("/network/discovery/run"),
    onSuccess: (res) => {
      setDiscoveryResult({ total: res.data?.total ?? 0 });
      qc.invalidateQueries({ queryKey: ["network-suggestions-pending"] });
      qc.invalidateQueries({ queryKey: ["network-dashboard"] });
    },
  });

  const approve = useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) =>
      apiClient.post(`/network/suggested-relationships/${id}/approve`, { review_note: note }),
    onSuccess: (_, { id }) => {
      setReviewed((prev) => ({ ...prev, [id]: "approved" }));
      qc.invalidateQueries({ queryKey: ["network-suggestions-pending"] });
      qc.invalidateQueries({ queryKey: ["network-relationships"] });
      qc.invalidateQueries({ queryKey: ["network-dashboard"] });
    },
  });

  const reject = useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) =>
      apiClient.post(`/network/suggested-relationships/${id}/reject`, { review_note: note }),
    onSuccess: (_, { id }) => {
      setReviewed((prev) => ({ ...prev, [id]: "rejected" }));
      qc.invalidateQueries({ queryKey: ["network-suggestions-pending"] });
    },
  });

  const name = (id: string) => nameMap.get(id) ?? id.slice(0, 10) + "…";

  return (
    <div>
      {/* Discovery button */}
      <div className="mb-3 flex items-center justify-between">
        {discoveryResult && (
          <p className="text-xs text-green-400">
            {t("network.discoveryResult").replace("{n}", String(discoveryResult.total))}
          </p>
        )}
        <Button size="sm" variant="outline"
          className="ml-auto gap-1.5 border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white"
          disabled={discover.isPending}
          onClick={() => { setDiscoveryResult(null); discover.mutate(); }}>
          {discover.isPending ? <Spinner className="h-3.5 w-3.5" /> : <GitBranch className="h-3.5 w-3.5" />}
          {discover.isPending ? "Running…" : t("network.runDiscovery")}
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center p-8"><Spinner /></div>
      ) : !data?.length ? (
        <p className="text-center text-sm text-slate-500 py-6">{t("network.noSuggestions")}</p>
      ) : (
        <div className="divide-y divide-slate-800">
          {data.map((s: any) => {
            const result = reviewed[s.id];
            return (
              <div key={s.id} className="py-3 space-y-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <Link href={`/suppliers/${s.supplier_id}`}
                    className="text-sm font-medium text-slate-100 hover:text-blue-400 truncate max-w-[130px]">
                    {name(s.supplier_id)}
                  </Link>
                  <RelationshipTypeBadge type={s.relationship_type} />
                  <Link href={`/suppliers/${s.related_supplier_id}`}
                    className="text-sm font-medium text-slate-100 hover:text-blue-400 truncate max-w-[130px]">
                    {name(s.related_supplier_id)}
                  </Link>
                  {result ? (
                    <span className={`ml-auto rounded-full px-2 py-0.5 text-[11px] font-bold ${result === "approved" ? "bg-green-800 text-green-300" : "bg-red-900 text-red-300"}`}>
                      {result === "approved" ? t("network.approved") : t("network.rejected")}
                    </span>
                  ) : (
                    <Badge variant="outline" className="text-yellow-400 border-yellow-700 ml-auto">PENDING</Badge>
                  )}
                </div>
                <p className="text-xs text-slate-400 truncate">{s.rationale}</p>
                <p className="text-xs text-slate-500">
                  {t("network.source")}: {s.suggestion_source} · {Math.round(s.confidence * 100)}{t("network.confidence")}
                </p>
                {!result && (
                  <div className="flex items-center gap-2 pt-1">
                    <input
                      className="flex-1 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-300 placeholder:text-slate-600"
                      placeholder={t("network.reviewNote")}
                      value={reviewNote[s.id] ?? ""}
                      onChange={(e) => setReviewNote((prev) => ({ ...prev, [s.id]: e.target.value }))}
                    />
                    <Button size="sm"
                      className="h-7 gap-1 bg-green-700 hover:bg-green-600 text-white text-xs px-2"
                      disabled={approve.isPending}
                      onClick={() => approve.mutate({ id: s.id, note: reviewNote[s.id] ?? "" })}>
                      <Check className="h-3 w-3" /> {t("network.approve")}
                    </Button>
                    <Button size="sm" variant="outline"
                      className="h-7 gap-1 border-red-800 text-red-400 hover:bg-red-900/30 text-xs px-2"
                      disabled={reject.isPending}
                      onClick={() => reject.mutate({ id: s.id, note: reviewNote[s.id] ?? "" })}>
                      <X className="h-3 w-3" /> {t("network.reject")}
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ExposuresSection({ nameMap }: { nameMap: Map<string, string> }) {
  const { t } = useLanguage();
  const { data, isLoading } = useQuery({
    queryKey: ["network-exposures"],
    queryFn: getExposureSignals,
    refetchInterval: 60_000,
  });

  const name = (id: string) => nameMap.get(id) ?? id.slice(0, 8) + "…";

  if (isLoading)
    return (
      <div className="flex justify-center p-8">
        <Spinner />
      </div>
    );
  if (!data?.length)
    return (
      <p className="text-center text-sm text-slate-500 py-6">
        {t("network.noExposures")}
      </p>
    );

  return (
    <div className="divide-y divide-slate-800">
      {data.map((e: any) => (
        <div key={e.id} className="py-3">
          <div className="flex items-center gap-2 flex-wrap">
            <SeverityBadge severity={e.severity} />
            <span className="text-sm font-medium text-slate-100">
              {e.exposure_type.replace(/_/g, " ")}
            </span>
            <span className="ml-auto text-xs text-slate-500">
              {Math.round(e.confidence * 100)}{t("network.confidence")} · {e.path_length} {t("network.hops")}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400 truncate">{e.rationale}</p>
          <p className="mt-0.5 text-xs text-slate-500 flex items-center gap-1 flex-wrap">
            {t("network.origin")}:{" "}
            <Link href={`/suppliers/${e.origin_supplier_id}`} className="text-blue-400 hover:underline font-mono">
              {name(e.origin_supplier_id)}
            </Link>
            {" → "}{t("network.impacted")}:{" "}
            <Link href={`/suppliers/${e.impacted_supplier_id}`} className="text-blue-400 hover:underline font-mono">
              {name(e.impacted_supplier_id)}
            </Link>
          </p>
        </div>
      ))}
    </div>
  );
}

function ClustersSection() {
  const { t } = useLanguage();
  const { data, isLoading } = useQuery({
    queryKey: ["network-clusters"],
    queryFn: getClusters,
    refetchInterval: 60_000,
  });

  if (isLoading)
    return (
      <div className="flex justify-center p-8">
        <Spinner />
      </div>
    );
  if (!data?.length)
    return (
      <p className="text-center text-sm text-slate-500 py-6">
        {t("network.noClusters")}
      </p>
    );

  return (
    <div className="divide-y divide-slate-800">
      {data.map((c: any) => (
        <div key={c.id} className="py-3">
          <div className="flex items-center gap-2">
            <SeverityBadge severity={c.severity} />
            <span className="text-sm font-medium text-slate-100 truncate">
              {c.cluster_name}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400 truncate">{c.root_cause}</p>
          <p className="mt-0.5 text-xs text-slate-500">
            {t("network.suppliersPlural").replace("{n}", String(c.affected_supplier_ids.length))} · {t("network.findingsPlural").replace("{n}", String(c.finding_ids.length))}
          </p>
        </div>
      ))}
    </div>
  );
}

// ── Dashboard Overview ────────────────────────────────────────────────────────

function DashboardOverview() {
  const { t } = useLanguage();
  const { data, isLoading } = useQuery({
    queryKey: ["network-dashboard"],
    queryFn: getNetworkDashboard,
    refetchInterval: 60_000,
  });

  if (isLoading)
    return (
      <div className="flex justify-center p-8">
        <Spinner />
      </div>
    );

  const d = data ?? {};

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <StatCard
        title={t("network.relationships")}
        value={d.total_relationships ?? 0}
        icon={Share2}
        sub={t("common.active")}
      />
      <StatCard
        title={t("network.pendingSuggestions")}
        value={d.pending_suggestions ?? 0}
        icon={GitBranch}
        sub={t("network.awaitingReview")}
      />
      <StatCard
        title={t("network.activeExposures")}
        value={d.active_exposures ?? 0}
        icon={AlertTriangle}
        sub={t("network.networkSignals")}
      />
      <StatCard
        title={t("network.incidentClusters")}
        value={d.active_clusters ?? 0}
        icon={Zap}
        sub={t("network.activeClusters")}
      />
      <StatCard
        title={t("network.criticalSuppliers")}
        value={d.critical_suppliers ?? 0}
        icon={Shield}
        sub={t("network.highestRiskNodes")}
      />
      <StatCard
        title={t("network.resilienceScore")}
        value={
          d.resilience_score !== null && d.resilience_score !== undefined
            ? `${Math.round(d.resilience_score * 100)}%`
            : "—"
        }
        icon={Activity}
        sub={t("network.orgWideResilience")}
      />
      <StatCard
        title={t("network.dependencyScore")}
        value={
          d.dependency_score !== null && d.dependency_score !== undefined
            ? `${Math.round(d.dependency_score * 100)}%`
            : "—"
        }
        icon={TrendingDown}
        sub={t("network.criticalConcentration")}
      />
      <StatCard
        title={t("network.networkNodes")}
        value={
          (d.total_relationships ?? 0) > 0
            ? t("network.connected")
            : t("network.noGraph")
        }
        icon={Network}
        sub={t("network.supplierGraphSub")}
      />
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function NetworkPage() {
  const { t } = useLanguage();

  // Pre-fetch supplier names for relationship + suggestion sections
  const { data: graphData } = useQuery({
    queryKey: ["network-graph"],
    queryFn: getGraphData,
    staleTime: 5 * 60_000,
  });
  const nameMap = useMemo(
    () => new Map<string, string>((graphData?.suppliers ?? []).map((s) => [s.id, s.name])),
    [graphData]
  );

  return (
    <div className="space-y-6 p-6">
      {/* #115 First-time guided tour */}
      <NetworkTour />
      <div>
        <h1 className="text-2xl font-bold text-slate-100">
          {t("network.pageTitle")}
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          {t("network.pageSubtitle")}
        </p>
      </div>

      <DashboardOverview />

      <Card className="border-slate-800 bg-slate-900 text-slate-100">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
            <Network className="h-4 w-4" aria-hidden="true" />
            {t("network.supplierGraph")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <NetworkGraphSection />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="border-slate-800 bg-slate-900 text-slate-100">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
              <Share2 className="h-4 w-4" />
              {t("network.activeRelationships")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <RelationshipsSection nameMap={nameMap} />
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900 text-slate-100">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
              <GitBranch className="h-4 w-4" />
              {t("network.pendingSuggestions")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <SuggestionsSection nameMap={nameMap} />
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900 text-slate-100">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
              <AlertTriangle className="h-4 w-4 text-orange-400" />
              {t("network.exposureSignals")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ExposuresSection nameMap={nameMap} />
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900 text-slate-100">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
              <Zap className="h-4 w-4 text-yellow-400" />
              {t("network.incidentClusters")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ClustersSection />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
