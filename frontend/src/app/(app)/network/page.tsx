"use client";

import { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  GitBranch,
  Network,
  Shield,
  Share2,
  TrendingDown,
  Users,
  X,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import apiClient from "@/lib/api/client";
import { SupplierGraph } from "@/components/network/supplier-graph";
import type { GraphSupplier, GraphRelationship } from "@/components/network/supplier-graph";

// ── #115 Guided tour ─────────────────────────────────────────────────────────

const TOUR_KEY = "eios_network_tour_seen";

const TOUR_STEPS = [
  { title: "Supplier Network Graph", desc: "This interactive graph shows your suppliers as nodes, connected by their relationships. Zoom and pan to explore." },
  { title: "Exposure Signals", desc: "Active exposure signals highlight indirect risk propagation across your supply chain network." },
  { title: "Incident Clusters", desc: "Clusters group suppliers that share common root-cause incidents for efficient remediation." },
  { title: "Filters", desc: "Use the Tier, Risk Level, and Country filters above the graph to focus on specific subsets of your network." },
];

function NetworkTour() {
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
            <p className="text-sm font-semibold text-white">{current.title}</p>
          </div>
          <button onClick={dismiss} className="text-slate-400 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed mb-4">{current.desc}</p>
        <div className="flex items-center justify-between">
          <div className="flex gap-1">
            {TOUR_STEPS.map((_, i) => (
              <div key={i} className={`h-1.5 rounded-full transition-all ${i === step ? "w-6 bg-blue-500" : "w-1.5 bg-slate-600"}`} />
            ))}
          </div>
          <div className="flex gap-2">
            {step > 0 && (
              <button onClick={() => setStep((s) => s - 1)} className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800">
                Back
              </button>
            )}
            {isLast ? (
              <button onClick={dismiss} className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700">
                Done <ArrowRight className="h-3 w-3" />
              </button>
            ) : (
              <button onClick={() => setStep((s) => s + 1)} className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700">
                Next <ArrowRight className="h-3 w-3" />
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
  const res = await apiClient.get("/api/v1/network/dashboard");
  return res.data;
}

async function getRelationships() {
  const res = await apiClient.get("/api/v1/network/relationships?limit=20");
  return res.data;
}

async function getPendingSuggestions() {
  const res = await apiClient.get(
    "/api/v1/network/suggested-relationships?suggestion_status=PENDING&limit=20"
  );
  return res.data;
}

async function getExposureSignals() {
  const res = await apiClient.get(
    "/api/v1/network/exposure-signals?exposure_status=ACTIVE&limit=10"
  );
  return res.data;
}

async function getClusters() {
  const res = await apiClient.get(
    "/api/v1/network/clusters?cluster_status=ACTIVE&limit=10"
  );
  return res.data;
}

async function getGraphData(): Promise<{
  suppliers: GraphSupplier[];
  relationships: GraphRelationship[];
}> {
  const [suppRes, relRes] = await Promise.all([
    apiClient.get("/api/v1/suppliers?limit=200"),
    apiClient.get("/api/v1/network/relationships?limit=500"),
  ]);
  const tierNum: Record<string, number> = { "Tier 1": 1, "Tier 2": 2, "Tier 3": 3 };
  const suppliers: GraphSupplier[] = (suppRes.data.items ?? suppRes.data ?? []).map((s: any) => ({
    id: s.id,
    name: s.name,
    tier: tierNum[s.supplier_tier] ?? 4,
    overall_risk_level: s.overall_risk_level,
    country: s.country ?? null,
    score: s.overall_esg_score ?? null,
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
  const { data, isLoading } = useQuery({
    queryKey: ["network-graph"],
    queryFn: getGraphData,
    refetchInterval: 120_000,
  });

  const [tierFilter, setTierFilter] = useState<string>("");
  const [riskFilter, setRiskFilter] = useState<string>("");
  const [countryFilter, setCountryFilter] = useState<string>("");

  const allSuppliers = data?.suppliers ?? [];

  const countries = useMemo(
    () => [...new Set(allSuppliers.map((s) => s.country).filter(Boolean))].sort() as string[],
    [allSuppliers]
  );

  const filteredSuppliers = useMemo(() => {
    return allSuppliers.filter((s) => {
      if (tierFilter && s.tier !== Number(tierFilter)) return false;
      if (riskFilter && (s.overall_risk_level ?? "LOW") !== riskFilter) return false;
      if (countryFilter && s.country !== countryFilter) return false;
      return true;
    });
  }, [allSuppliers, tierFilter, riskFilter, countryFilter]);

  const filteredIds = new Set(filteredSuppliers.map((s) => s.id));
  const filteredRelationships = (data?.relationships ?? []).filter(
    (r) => filteredIds.has(r.source) && filteredIds.has(r.target)
  );

  const hasFilter = tierFilter || riskFilter || countryFilter;

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
          <option value="">All Tiers</option>
          <option value="1">Tier 1</option>
          <option value="2">Tier 2</option>
          <option value="3">Tier 3</option>
        </select>
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200"
        >
          <option value="">All Risk Levels</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>
        {countries.length > 0 && (
          <select
            value={countryFilter}
            onChange={(e) => setCountryFilter(e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200"
          >
            <option value="">All Countries</option>
            {countries.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        )}
        {hasFilter && (
          <button
            onClick={() => { setTierFilter(""); setRiskFilter(""); setCountryFilter(""); }}
            className="flex items-center gap-1 rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X className="h-3 w-3" /> Clear filters
          </button>
        )}
        <span className="ml-auto text-xs text-slate-500">
          {filteredSuppliers.length} of {allSuppliers.length} suppliers
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

function RelationshipsSection() {
  const { data, isLoading } = useQuery({
    queryKey: ["network-relationships"],
    queryFn: getRelationships,
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
        No active relationships. Add one or run discovery.
      </p>
    );

  return (
    <div className="divide-y divide-slate-800">
      {data.map((rel: any) => (
        <div key={rel.id} className="flex items-center gap-3 py-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium text-slate-100 truncate max-w-[120px]">
                {rel.supplier_id.slice(0, 8)}…
              </span>
              <RelationshipTypeBadge type={rel.relationship_type} />
              <span className="text-sm font-medium text-slate-100 truncate max-w-[120px]">
                {rel.related_supplier_id.slice(0, 8)}…
              </span>
            </div>
            <p className="mt-0.5 text-xs text-slate-500 truncate">
              {rel.rationale || "—"}
            </p>
          </div>
          <div className="flex-shrink-0 text-right">
            <p className="text-xs text-slate-400">
              {Math.round(rel.confidence * 100)}% confidence
            </p>
            <p className="text-xs text-slate-500">{rel.source}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function SuggestionsSection() {
  const { data, isLoading } = useQuery({
    queryKey: ["network-suggestions-pending"],
    queryFn: getPendingSuggestions,
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
        No pending suggestions. Run discovery to generate proposals.
      </p>
    );

  return (
    <div className="divide-y divide-slate-800">
      {data.map((s: any) => (
        <div key={s.id} className="py-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-slate-100">
              {s.supplier_id.slice(0, 8)}…
            </span>
            <RelationshipTypeBadge type={s.relationship_type} />
            <span className="text-sm font-medium text-slate-100">
              {s.related_supplier_id.slice(0, 8)}…
            </span>
            <Badge variant="outline" className="text-yellow-400 border-yellow-700 ml-auto">
              PENDING
            </Badge>
          </div>
          <p className="mt-1 text-xs text-slate-400 truncate">{s.rationale}</p>
          <p className="mt-0.5 text-xs text-slate-500">
            Source: {s.suggestion_source} · {Math.round(s.confidence * 100)}% confidence
          </p>
        </div>
      ))}
    </div>
  );
}

function ExposuresSection() {
  const { data, isLoading } = useQuery({
    queryKey: ["network-exposures"],
    queryFn: getExposureSignals,
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
        No active exposure signals.
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
              {Math.round(e.confidence * 100)}% · {e.path_length} hop(s)
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400 truncate">{e.rationale}</p>
          <p className="mt-0.5 text-xs text-slate-500">
            Origin: {e.origin_supplier_id.slice(0, 8)}… → Impacted: {e.impacted_supplier_id.slice(0, 8)}…
          </p>
        </div>
      ))}
    </div>
  );
}

function ClustersSection() {
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
        No active incident clusters.
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
            {c.affected_supplier_ids.length} suppliers · {c.finding_ids.length} findings
          </p>
        </div>
      ))}
    </div>
  );
}

// ── Dashboard Overview ────────────────────────────────────────────────────────

function DashboardOverview() {
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
        title="Relationships"
        value={d.total_relationships ?? 0}
        icon={Share2}
        sub="Active"
      />
      <StatCard
        title="Pending Suggestions"
        value={d.pending_suggestions ?? 0}
        icon={GitBranch}
        sub="Awaiting review"
      />
      <StatCard
        title="Active Exposures"
        value={d.active_exposures ?? 0}
        icon={AlertTriangle}
        sub="Network signals"
      />
      <StatCard
        title="Incident Clusters"
        value={d.active_clusters ?? 0}
        icon={Zap}
        sub="Active clusters"
      />
      <StatCard
        title="Critical Suppliers"
        value={d.critical_suppliers ?? 0}
        icon={Shield}
        sub="Highest risk nodes"
      />
      <StatCard
        title="Resilience Score"
        value={
          d.resilience_score !== null && d.resilience_score !== undefined
            ? `${Math.round(d.resilience_score * 100)}%`
            : "—"
        }
        icon={Activity}
        sub="Org-wide resilience"
      />
      <StatCard
        title="Dependency Score"
        value={
          d.dependency_score !== null && d.dependency_score !== undefined
            ? `${Math.round(d.dependency_score * 100)}%`
            : "—"
        }
        icon={TrendingDown}
        sub="Critical concentration"
      />
      <StatCard
        title="Network Nodes"
        value={
          (d.total_relationships ?? 0) > 0
            ? "Connected"
            : "No graph yet"
        }
        icon={Network}
        sub="Supplier graph"
      />
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function NetworkPage() {
  return (
    <div className="space-y-6 p-6">
      {/* #115 First-time guided tour */}
      <NetworkTour />
      <div>
        <h1 className="text-2xl font-bold text-slate-100">
          Supplier Network Intelligence
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Relationship graph, indirect exposure, cascading risk, and resilience
          metrics across your supplier ecosystem.
        </p>
      </div>

      <DashboardOverview />

      <Card className="border-slate-800 bg-slate-900 text-slate-100">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
            <Network className="h-4 w-4" aria-hidden="true" />
            Supplier Network Graph
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
              Active Relationships
            </CardTitle>
          </CardHeader>
          <CardContent>
            <RelationshipsSection />
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900 text-slate-100">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
              <GitBranch className="h-4 w-4" />
              Pending Suggestions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <SuggestionsSection />
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900 text-slate-100">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
              <AlertTriangle className="h-4 w-4 text-orange-400" />
              Active Exposure Signals
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ExposuresSection />
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900 text-slate-100">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
              <Zap className="h-4 w-4 text-yellow-400" />
              Incident Clusters
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
