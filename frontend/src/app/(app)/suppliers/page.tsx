"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Plus,
  Search,
  Briefcase,
  Globe,
  LayoutGrid,
  LayoutList,
  ChevronLeft,
  ChevronRight,
  X,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { listSuppliers, createSupplier } from "@/lib/api/suppliers";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import type { SupplierCreate, SupplierTier } from "@/types/api";

interface SupplierScore {
  id: string;
  esg_score: number | null;
  risk_score: number | null;
  risk_level: string | null;
  assessment_count: number;
  finding_count: number;
  questionnaire_pct: number | null;
  ofac_status: string | null;
}

const TIER_OPTIONS: { value: SupplierTier | ""; label: string }[] = [
  { value: "", label: "All Tiers" },
  { value: "Tier 1", label: "Tier 1" },
  { value: "Tier 2", label: "Tier 2" },
  { value: "Tier 3", label: "Tier 3" },
  { value: "Other", label: "Other" },
];

const STATUS_OPTIONS = [
  { value: "", label: "All Status" },
  { value: "Active", label: "Active" },
  { value: "Inactive", label: "Inactive" },
];

const RISK_LEVEL_COLORS: Record<string, string> = {
  Critical: "bg-red-100 text-red-800",
  High:     "bg-orange-100 text-orange-800",
  Medium:   "bg-amber-100 text-amber-800",
  Low:      "bg-emerald-100 text-emerald-800",
  Moderate: "bg-amber-100 text-amber-800",
};

function tierBadge(tier: string) {
  const colors: Record<string, string> = {
    "Tier 1": "bg-blue-100 text-blue-800",
    "Tier 2": "bg-purple-100 text-purple-800",
    "Tier 3": "bg-slate-100 text-slate-700",
    Other: "bg-gray-100 text-gray-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[tier] ?? "bg-gray-100 text-gray-700"}`}>
      {tier}
    </span>
  );
}

function statusBadge(s: string) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${s === "Active" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}`}>
      {s}
    </span>
  );
}

function OfacBadge({ status }: { status: string | null }) {
  if (!status || status === "none") return <span className="text-xs text-muted-foreground/50">—</span>;
  const colors: Record<string, string> = {
    none: "bg-emerald-50 text-emerald-700",
    low: "bg-amber-50 text-amber-700",
    medium: "bg-orange-100 text-orange-700",
    high: "bg-red-100 text-red-800",
    sanctioned: "bg-red-600 text-white",
  };
  const labels: Record<string, string> = {
    none: "Clear",
    low: "Low",
    medium: "Medium",
    high: "High",
    sanctioned: "Sanctioned",
  };
  const key = status.toLowerCase();
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${colors[key] ?? "bg-slate-100 text-slate-600"}`}>
      {labels[key] ?? status}
    </span>
  );
}

function QuestionnairePct({ pct }: { pct: number | null }) {
  if (pct == null) return <span className="text-xs text-muted-foreground/50">—</span>;
  const color = pct >= 100 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-400" : "bg-slate-300";
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs tabular-nums text-muted-foreground">{pct}%</span>
    </div>
  );
}

function EsgScoreDistribution({ scores }: { scores: SupplierScore[] }) {
  const withScore = scores.filter((s) => s.esg_score != null);
  if (withScore.length === 0) return null;

  const buckets = [
    { label: "0–25", min: 0, max: 25, color: "#ef4444" },
    { label: "26–50", min: 26, max: 50, color: "#f97316" },
    { label: "51–75", min: 51, max: 75, color: "#f59e0b" },
    { label: "76–100", min: 76, max: 100, color: "#10b981" },
  ];

  const data = buckets.map((b) => ({
    label: b.label,
    count: withScore.filter((s) => s.esg_score! >= b.min && s.esg_score! <= b.max).length,
    color: b.color,
  }));

  return (
    <Card>
      <CardContent className="pt-4 pb-3">
        <p className="text-xs font-semibold text-muted-foreground mb-2">ESG Score Distribution ({withScore.length} scored)</p>
        <ResponsiveContainer width="100%" height={90}>
          <BarChart data={data} margin={{ top: 0, right: 8, bottom: 0, left: -20 }}>
            <XAxis dataKey="label" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
            <Tooltip
              formatter={(v: number) => [`${v} suppliers`, "Count"]}
              contentStyle={{ fontSize: 11 }}
            />
            <Bar dataKey="count" radius={[3, 3, 0, 0]}>
              {data.map((d, idx) => (
                <Cell key={idx} fill={d.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function EsgScorePill({ score, riskLevel }: { score: number | null; riskLevel: string | null }) {
  if (score === null) return <span className="text-xs text-muted-foreground/50">—</span>;
  const color = score >= 70 ? "text-emerald-700 bg-emerald-50" : score >= 40 ? "text-amber-700 bg-amber-50" : "text-red-700 bg-red-50";
  return (
    <div className="flex items-center gap-1.5">
      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold tabular-nums ${color}`}>
        {score.toFixed(0)}
      </span>
      {riskLevel && (
        <span className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium ${RISK_LEVEL_COLORS[riskLevel] ?? "bg-slate-100 text-slate-600"}`}>
          {riskLevel}
        </span>
      )}
    </div>
  );
}

export default function SuppliersPage() {
  const { t } = useLanguage();
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState(() => searchParams.get("country") || searchParams.get("industry") || "");
  const [tierFilter, setTierFilter] = useState(() => searchParams.get("tier") || "");
  const [statusFilter, setStatusFilter] = useState("");
  const [viewMode, setViewMode] = useState<"table" | "grid">("table");
  const [showCreate, setShowCreate] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    const country = searchParams.get("country");
    const industry = searchParams.get("industry");
    const tier = searchParams.get("tier");
    if (country) { setSearch(country); setSearchInput(country); }
    else if (industry) { setSearch(industry); setSearchInput(industry); }
    if (tier) setTierFilter(tier);
  }, [searchParams]);

  const [form, setForm] = useState<SupplierCreate>({
    name: "", legal_name: "", country: "", industry: "",
    nace_code: "", website: "", supplier_tier: "Tier 1", notes: "",
  });

  const PAGE_SIZE = 15;

  const { data, isLoading } = useQuery({
    queryKey: ["suppliers", { page, page_size: PAGE_SIZE, search, tierFilter, statusFilter }],
    queryFn: () => listSuppliers({ page, page_size: PAGE_SIZE, search: search || undefined, supplier_tier: tierFilter || undefined, status: statusFilter || undefined }),
  });

  const { data: scoreData } = useQuery<SupplierScore[]>({
    queryKey: ["supplier-scores-overview"],
    queryFn: async () => { const r = await apiClient.get("/api/v1/executive/suppliers"); return r.data; },
    staleTime: 60_000,
  });

  const scoreMap = new Map<string, SupplierScore>(
    (scoreData ?? []).map((s) => [s.id, s])
  );

  const createMutation = useMutation({
    mutationFn: createSupplier,
    onSuccess: async (newSupplier) => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["supplier-scores-overview"] });
      setShowCreate(false);
      setCreateError(null);
      setForm({ name: "", legal_name: "", country: "", industry: "", nace_code: "", website: "", supplier_tier: "Tier 1", notes: "" });
      // #159 Auto-trigger OFAC scan if rule is enabled in automation settings
      try {
        const stored = JSON.parse(localStorage.getItem("eios_automation_rules") ?? "{}");
        if (stored?.supplier_ofac_scan?.enabled !== false && newSupplier?.id) {
          await apiClient.post(`/api/v1/integrations/sanctions/ofac/scan/supplier/${newSupplier.id}`);
        }
      } catch { /* silent — OFAC scan failure should not block supplier creation */ }
    },
    onError: (err: unknown) => {
      setCreateError(err instanceof Error ? err.message : "Failed to create supplier");
    },
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
  }

  const suppliers = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = data ? Math.ceil(total / PAGE_SIZE) : 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t("suppliers.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("dashboard.supplierPortfolioDesc")}
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          {t("suppliers.newSupplier")}
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={t("suppliers.searchPlaceholder")}
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-9 w-64"
            />
          </div>
          <Button type="submit" variant="secondary">{t("common.search")}</Button>
        </form>
        <select
          value={tierFilter}
          onChange={(e) => { setTierFilter(e.target.value); setPage(1); }}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">{t("suppliers.allTiers")}</option>
          <option value="Tier 1">Tier 1</option>
          <option value="Tier 2">Tier 2</option>
          <option value="Tier 3">Tier 3</option>
          <option value="Other">{t("materials.other")}</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">{t("suppliers.allStatus")}</option>
          <option value="Active">{t("common.active")}</option>
          <option value="Inactive">{t("common.inactive")}</option>
        </select>
        {(search || tierFilter || statusFilter) && (
          <Button variant="ghost" size="sm" onClick={() => { setSearch(""); setSearchInput(""); setTierFilter(""); setStatusFilter(""); setPage(1); }} className="gap-1 text-muted-foreground">
            <X className="h-3 w-3" /> {t("common.close")}
          </Button>
        )}
        <div className="ml-auto flex items-center gap-2">
          <span className="text-sm text-muted-foreground">{total} supplier{total !== 1 ? "s" : ""}</span>
          <div className="flex items-center rounded-md border border-border overflow-hidden">
            <button onClick={() => setViewMode("table")} className={`p-1.5 transition-colors ${viewMode === "table" ? "bg-slate-800 text-white" : "text-muted-foreground hover:bg-muted"}`} title="Table view">
              <LayoutList className="h-4 w-4" />
            </button>
            <button onClick={() => setViewMode("grid")} className={`p-1.5 transition-colors ${viewMode === "grid" ? "bg-slate-800 text-white" : "text-muted-foreground hover:bg-muted"}`} title="Grid view">
              <LayoutGrid className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* ESG Score Distribution */}
      {scoreData && scoreData.length > 0 && <EsgScoreDistribution scores={scoreData} />}

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      ) : suppliers.length === 0 ? (
        <Card>
          <CardContent className="p-0">
            <EmptyState
              icon={Briefcase}
              title={search || tierFilter || statusFilter ? t("suppliers.noSuppliers") : t("suppliers.noSuppliers")}
              description={search || tierFilter || statusFilter
                ? t("suppliers.noSuppliersDesc")
                : t("suppliers.noSuppliersDesc")}
              actions={!search && !tierFilter && !statusFilter ? [
                { label: t("suppliers.newSupplier"), onClick: () => setShowCreate(true), variant: "primary" },
                { label: t("common.import"), href: "/suppliers", variant: "outline" },
              ] : undefined}
            />
          </CardContent>
        </Card>
      ) : viewMode === "grid" ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {suppliers.map((s) => {
              const sc = scoreMap.get(s.id);
              return (
                <Link key={s.id} href={`/suppliers/${s.id}`} className="block">
                  <Card className="h-full transition-shadow hover:shadow-md hover:border-blue-300">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <p className="font-semibold text-sm leading-tight line-clamp-2">{s.name}</p>
                        {tierBadge(s.supplier_tier)}
                      </div>
                      {s.country && (
                        <p className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                          <Globe className="h-3 w-3 shrink-0" /> {s.country}
                        </p>
                      )}
                      {s.industry && <p className="text-xs text-muted-foreground mb-2 line-clamp-1">{s.industry}</p>}
                      <div className="mt-3 flex items-center justify-between">
                        {statusBadge(s.supplier_status)}
                        {sc && <EsgScorePill score={sc.esg_score} riskLevel={sc.risk_level} />}
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              );
            })}
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <p className="text-sm text-muted-foreground">{t("common.page")} {page} {t("common.of")} {totalPages}</p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}><ChevronLeft className="h-4 w-4" /></Button>
                <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}><ChevronRight className="h-4 w-4" /></Button>
              </div>
            </div>
          )}
        </>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/30">
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("common.name")}</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground hidden sm:table-cell">{t("common.country")}</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground hidden md:table-cell">{t("common.industry")}</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("suppliers.tier")}</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("suppliers.esgScore")}</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground hidden xl:table-cell">{t("suppliers.questionnaire")}</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground hidden xl:table-cell">{t("suppliers.ofac")}</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground hidden lg:table-cell">{t("assessments.title")}</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground hidden lg:table-cell">{t("findings.title")}</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("common.status")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {suppliers.map((s) => {
                    const sc = scoreMap.get(s.id);
                    return (
                      <tr key={s.id} className="hover:bg-muted/20 transition-colors">
                        <td className="px-4 py-3">
                          <Link href={`/suppliers/${s.id}`} className="font-medium text-foreground hover:text-blue-600 hover:underline">
                            {s.name}
                          </Link>
                          {s.legal_name && s.legal_name !== s.name && (
                            <p className="text-xs text-muted-foreground">{s.legal_name}</p>
                          )}
                        </td>
                        <td className="px-4 py-3 hidden sm:table-cell">
                          {s.country ? (
                            <span className="flex items-center gap-1 text-muted-foreground">
                              <Globe className="h-3 w-3" /> {s.country}
                            </span>
                          ) : <span className="text-muted-foreground/50">—</span>}
                        </td>
                        <td className="px-4 py-3 hidden md:table-cell text-muted-foreground">
                          {s.industry || <span className="text-muted-foreground/50">—</span>}
                        </td>
                        <td className="px-4 py-3">{tierBadge(s.supplier_tier)}</td>
                        <td className="px-4 py-3">
                          <EsgScorePill score={sc?.esg_score ?? null} riskLevel={sc?.risk_level ?? null} />
                        </td>
                        <td className="px-4 py-3 hidden xl:table-cell">
                          <QuestionnairePct pct={sc?.questionnaire_pct ?? null} />
                        </td>
                        <td className="px-4 py-3 hidden xl:table-cell">
                          <OfacBadge status={sc?.ofac_status ?? null} />
                        </td>
                        <td className="px-4 py-3 hidden lg:table-cell text-xs text-muted-foreground tabular-nums">
                          {sc ? sc.assessment_count : "—"}
                        </td>
                        <td className="px-4 py-3 hidden lg:table-cell text-xs tabular-nums">
                          {sc ? (
                            <span className={sc.finding_count > 0 ? "text-amber-700 font-medium" : "text-muted-foreground"}>
                              {sc.finding_count}
                            </span>
                          ) : "—"}
                        </td>
                        <td className="px-4 py-3">{statusBadge(s.supplier_status)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-border px-4 py-3">
                <p className="text-sm text-muted-foreground">{t("common.page")} {page} {t("common.of")} {totalPages}</p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}><ChevronLeft className="h-4 w-4" /></Button>
                  <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}><ChevronRight className="h-4 w-4" /></Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-xl bg-background p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">{t("suppliers.createTitle")}</h2>
              <button onClick={() => { setShowCreate(false); setCreateError(null); }} className="text-muted-foreground hover:text-foreground">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">{t("common.name")} *</label>
                <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder={t("suppliers.namePlaceholder")} />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">{t("suppliers.legalName")}</label>
                <Input value={form.legal_name ?? ""} onChange={(e) => setForm((f) => ({ ...f, legal_name: e.target.value }))} placeholder="Full legal name (if different)" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium">{t("common.country")}</label>
                  <Input value={form.country ?? ""} onChange={(e) => setForm((f) => ({ ...f, country: e.target.value }))} placeholder="DE, US, FR…" />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">NACE Code</label>
                  <Input value={form.nace_code ?? ""} onChange={(e) => setForm((f) => ({ ...f, nace_code: e.target.value }))} placeholder="C24.10" />
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">{t("common.industry")}</label>
                <Input value={form.industry ?? ""} onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))} placeholder="Steel Manufacturing, Agriculture…" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium">{t("suppliers.supplierTier")}</label>
                  <select value={form.supplier_tier} onChange={(e) => setForm((f) => ({ ...f, supplier_tier: e.target.value as SupplierTier }))} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                    <option value="Tier 1">Tier 1</option>
                    <option value="Tier 2">Tier 2</option>
                    <option value="Tier 3">Tier 3</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">{t("suppliers.website")}</label>
                  <Input value={form.website ?? ""} onChange={(e) => setForm((f) => ({ ...f, website: e.target.value }))} placeholder="https://…" />
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">{t("common.notes")}</label>
                <textarea value={form.notes ?? ""} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} rows={3} placeholder="Internal notes…" className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>
            {createError && <p className="mt-3 text-sm text-red-600">{createError}</p>}
            <div className="mt-5 flex justify-end gap-3">
              <Button variant="outline" onClick={() => { setShowCreate(false); setCreateError(null); }}>{t("common.cancel")}</Button>
              <Button
                onClick={() => {
                  if (!form.name.trim()) { setCreateError(t("common.required")); return; }
                  createMutation.mutate({ ...form, legal_name: form.legal_name || undefined, nace_code: form.nace_code || undefined, website: form.website || undefined, notes: form.notes || undefined });
                }}
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? <Spinner size="sm" className="mr-2" /> : null}
                {createMutation.isPending ? t("suppliers.creating") : t("suppliers.createTitle")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
