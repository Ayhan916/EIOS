"use client";

import { useEffect, useRef, useState } from "react";
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
  Trash2,
  AlertTriangle,
  Building2,
  CheckCircle2,
  SlidersHorizontal,
  ArrowLeft,
  MapPin,
  ExternalLink,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { ReadinessBanner } from "@/components/layout/readiness-banner";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { listSuppliers, createSupplier, archiveSupplier } from "@/lib/api/suppliers";
import { collectIntelligence, collectIntelligenceBatch, type CollectIntelligenceResponse } from "@/lib/api/supplier-twin";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import type { SupplierCreate, SupplierResponse, SupplierTier, SupplierType } from "@/types/api";
import type { Page } from "@/types/api";

interface GleifCompany {
  lei: string;
  name: string;
  country: string;
  city: string;
  jurisdiction: string;
}

interface CompanyDetail {
  company: {
    lei: string; name: string; country: string; city: string;
    postal_code: string; address_lines: string[];
    hq_city: string; hq_country: string;
    status: string; category: string; jurisdiction: string;
    legal_form: string; registration_date: string;
  };
  children: { lei: string; name: string; country: string; city: string; status: string; category: string }[];
  total_children: number;
}

const COMMODITIES = [
  { code: "cobalt",    label: "Kobalt",     icon: "⚫", sector: "Bergbau (Metall)",       nace: "B07.29", origins: "DRC, Sambia, Australien" },
  { code: "lithium",   label: "Lithium",    icon: "🔋", sector: "Bergbau (Metall)",       nace: "B07.29", origins: "Chile, Argentinien, Australien" },
  { code: "copper",    label: "Kupfer",     icon: "🟤", sector: "Bergbau (Metall)",       nace: "B07.29", origins: "Chile, Peru, DRC" },
  { code: "cotton",    label: "Baumwolle",  icon: "🌿", sector: "Landwirtschaft",         nace: "A01.16", origins: "Usbekistan, China, Indien" },
  { code: "soy",       label: "Soja",       icon: "🌱", sector: "Landwirtschaft",         nace: "A01.11", origins: "Brasilien, Argentinien, USA" },
  { code: "palm_oil",  label: "Palmöl",     icon: "🌴", sector: "Landwirtschaft",         nace: "A01.26", origins: "Indonesien, Malaysia" },
];

const LEGAL_FORMS = [
  { value: "", label: "Alle Rechtsformen" },
  { value: "GmbH", label: "GmbH" },
  { value: "AG", label: "AG" },
  { value: "SE", label: "SE" },
  { value: "KGaA", label: "KGaA" },
  { value: "GmbH & Co. KG", label: "GmbH & Co. KG" },
  { value: "Limited", label: "Limited (Ltd.)" },
  { value: "LLC", label: "LLC" },
  { value: "Inc", label: "Inc." },
  { value: "S.A.", label: "S.A." },
  { value: "B.V.", label: "B.V." },
  { value: "NV", label: "N.V." },
  { value: "SAS", label: "SAS" },
  { value: "SRL", label: "SRL / S.r.l." },
];

const GLEIF_CATEGORIES = [
  { value: "", label: "Alle Kategorien" },
  { value: "GENERAL", label: "Unternehmen (GENERAL)" },
  { value: "BRANCH", label: "Niederlassung (BRANCH)" },
  { value: "FUND", label: "Fonds (FUND)" },
];

function toTitleCase(s: string): string {
  return s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

async function searchGleif(query: string, options?: { country?: string; legalForm?: string; category?: string }): Promise<GleifCompany[]> {
  const params: Record<string, string> = { q: query };
  if (options?.country) params.country = options.country;
  if (options?.legalForm) params.legal_form = options.legalForm;
  if (options?.category) params.category = options.category;
  try {
    const res = await apiClient.get("/suppliers/company-search", { params });
    return res.data;
  } catch {
    return [];
  }
}

async function fetchCompanyDetail(lei: string): Promise<CompanyDetail | null> {
  try {
    const res = await apiClient.get("/suppliers/company-detail", { params: { lei } });
    return res.data;
  } catch {
    return null;
  }
}

async function enrichCompany(lei: string, name: string) {
  try {
    const res = await apiClient.get("/suppliers/company-enrich", { params: { lei, name } });
    return res.data;
  } catch {
    return null;
  }
}

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
  if (!status) return <span className="text-xs text-muted-foreground/50">—</span>;
  if (status === "unavailable") return <span className="inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-500">N/A</span>;
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
  const [riskFilter, setRiskFilter] = useState(() => searchParams.get("risk_level") || "");
  const [viewMode, setViewMode] = useState<"table" | "grid">("table");
  const [showCreate, setShowCreate] = useState(false);
  const [createTab, setCreateTab] = useState<"search" | "manual" | "commodity">("search");
  const [createError, setCreateError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [collecting, setCollecting] = useState(false);
  const [collectResult, setCollectResult] = useState<CollectIntelligenceResponse | null>(null);

  // ── Company search state (Tab 1) ──────────────────────────
  const [quickQuery, setQuickQuery] = useState("");
  const [quickResults, setQuickResults] = useState<GleifCompany[]>([]);
  const [quickSearching, setQuickSearching] = useState(false);
  const [quickDropdownOpen, setQuickDropdownOpen] = useState(false);

  // Advanced filter panel
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [advQ, setAdvQ] = useState("");
  const [advCountry, setAdvCountry] = useState("");
  const [advLegalForm, setAdvLegalForm] = useState("");
  const [advCategory, setAdvCategory] = useState("");
  const [advResults, setAdvResults] = useState<GleifCompany[]>([]);
  const [advSearching, setAdvSearching] = useState(false);
  const [advSearched, setAdvSearched] = useState(false);

  // Detail modal (after clicking any result)
  const [detailTarget, setDetailTarget] = useState<GleifCompany | null>(null);
  const [detailData, setDetailData] = useState<CompanyDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailEnriched, setDetailEnriched] = useState<{ website: string; industry: string; nace_code: string; nace_label?: string; notes: string; supplier_tier?: string } | null>(null);
  const [detailEnrichLoading, setDetailEnrichLoading] = useState(false);
  const [detailEntityFilter, setDetailEntityFilter] = useState("");

  // Final selected company
  const [companySelected, setCompanySelected] = useState<GleifCompany | null>(null);
  const [enrichedData, setEnrichedData] = useState<{ website: string; industry: string; nace_code: string; nace_label?: string; notes: string } | null>(null);

  // Manual-tab auto-enrichment
  const [manualEnriching, setManualEnriching] = useState(false);
  const [manualEnrichedFields, setManualEnrichedFields] = useState<Set<string>>(new Set());

  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const country = searchParams.get("country");
    const industry = searchParams.get("industry");
    const tier = searchParams.get("tier");
    const risk = searchParams.get("risk_level");
    if (country) { setSearch(country); setSearchInput(country); }
    else if (industry) { setSearch(industry); setSearchInput(industry); }
    if (tier) setTierFilter(tier);
    if (risk) setRiskFilter(risk);
  }, [searchParams]);

  const [form, setForm] = useState<SupplierCreate>({
    name: "", legal_name: "", country: "", industry: "",
    nace_code: "", website: "", supplier_tier: "Tier 1", notes: "",
    supplier_type: "manufacturing", commodity: null, commodity_code: null,
  });

  const PAGE_SIZE = 15;

  const { data, isLoading } = useQuery({
    queryKey: ["suppliers", { page, page_size: PAGE_SIZE, search, tierFilter, statusFilter }],
    queryFn: () => listSuppliers({ page, page_size: PAGE_SIZE, search: search || undefined, supplier_tier: tierFilter || undefined, status: statusFilter || undefined }),
  });

  const { data: scoreData } = useQuery<SupplierScore[]>({
    queryKey: ["supplier-scores-overview"],
    queryFn: async () => { const r = await apiClient.get("/executive/suppliers"); return r.data; },
    staleTime: 60_000,
  });

  const scoreMap = new Map<string, SupplierScore>(
    (scoreData ?? []).map((s) => [s.id, s])
  );

  const createMutation = useMutation({
    mutationFn: createSupplier,
    onSuccess: async (newSupplier) => {
      // Write directly into the active query's cache using the EXACT key —
      // partial-key setQueriesData can race against the concurrent invalidation refetch.
      if (newSupplier) {
        queryClient.setQueryData<Page<SupplierResponse>>(
          ["suppliers", { page, page_size: PAGE_SIZE, search, tierFilter, statusFilter }],
          (old) => {
            if (!old) return old;
            if (old.items.some((s) => s.id === newSupplier.id)) return old;
            return {
              ...old,
              items: [newSupplier, ...old.items].slice(0, PAGE_SIZE),
              total: old.total + 1,
            };
          },
        );
      }
      // Close modal + reset form
      setShowCreate(false);
      setCreateError(null);
      setCreateTab("search");
      setForm({ name: "", legal_name: "", country: "", industry: "", nace_code: "", website: "", supplier_tier: "Tier 1", notes: "", supplier_type: "manufacturing", commodity: null, commodity_code: null });
      resetCompanySearch();
      // Mark stale without an immediate network refetch — React Query will auto-refetch
      // on the next focus/mount so the optimistic entry above is rendered first.
      queryClient.invalidateQueries({ queryKey: ["suppliers"], refetchType: "none" });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["supplier-scores-overview"] });
      // #159 Auto-trigger OFAC scan in background — must not block the list update
      try {
        const stored = JSON.parse(localStorage.getItem("eios_automation_rules") ?? "{}");
        if (stored?.supplier_ofac_scan?.enabled !== false && newSupplier?.id) {
          await apiClient.post(`/integrations/sanctions/ofac/scan/supplier/${newSupplier.id}`);
          // Re-invalidate after the scan has persisted its result to DB
          queryClient.invalidateQueries({ queryKey: ["supplier-scores-overview"] });
        }
      } catch { /* silent — OFAC scan failure must not block supplier creation */ }
    },
    onError: (err: unknown) => {
      const axiosErr = err as { response?: { data?: { detail?: string | { msg: string }[] } } };
      const detail = axiosErr.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg).join("; ")
        : typeof detail === "string"
          ? detail
          : err instanceof Error
            ? err.message
            : "Lieferant konnte nicht erstellt werden.";
      setCreateError(msg);
    },
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
    setSelectedIds(new Set());
  }

  // Quick search debounce (≥3 chars)
  useEffect(() => {
    if (!showCreate || quickQuery.trim().length < 3) {
      setQuickResults([]);
      setQuickDropdownOpen(false);
      return;
    }
    const timer = setTimeout(async () => {
      setQuickSearching(true);
      try {
        const results = await searchGleif(quickQuery.trim());
        setQuickResults(results);
        setQuickDropdownOpen(results.length > 0);
      } catch {
        setQuickResults([]);
      } finally {
        setQuickSearching(false);
      }
    }, 280);
    return () => clearTimeout(timer);
  }, [quickQuery, showCreate]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setQuickDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Auto-enrich on manual tab: when name >= 4 chars, fetch industry/NACE/website in background
  useEffect(() => {
    if (createTab !== "manual" || form.name.trim().length < 4) return;
    const timer = setTimeout(async () => {
      setManualEnriching(true);
      try {
        const result = await enrichCompany("", form.name.trim());
        if (!result) return;
        const filled = new Set<string>();
        setForm((f) => {
          const next = { ...f };
          if (!f.industry && result.industry)   { next.industry   = result.industry;   filled.add("industry"); }
          if (!f.nace_code && result.nace_code) { next.nace_code  = result.nace_code;  filled.add("nace_code"); }
          if (!f.website && result.website)     { next.website    = result.website;    filled.add("website"); }
          if (!f.notes && result.notes)         { next.notes      = result.notes; }
          return next;
        });
        setManualEnrichedFields(filled);
      } catch { /* silent */ }
      finally { setManualEnriching(false); }
    }, 800);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.name, createTab]);

  // Open the detail modal for any clicked company
  async function openDetail(c: GleifCompany) {
    setDetailTarget(c);
    setDetailData(null);
    setDetailEnriched(null);
    setDetailEntityFilter("");
    setQuickDropdownOpen(false);
    setDetailLoading(true);
    setDetailEnrichLoading(true);
    try {
      const [detail, enriched] = await Promise.all([
        fetchCompanyDetail(c.lei),
        enrichCompany(c.lei, toTitleCase(c.name)),
      ]);
      setDetailData(detail);
      setDetailEnriched(enriched);
    } catch { /* silent */ }
    finally {
      setDetailLoading(false);
      setDetailEnrichLoading(false);
    }
  }

  // Confirm selection of a specific entity from the detail modal
  function confirmEntity(entity: { lei: string; name: string; country: string; city: string; category?: string }) {
    const displayName = toTitleCase(entity.name);
    const selected: GleifCompany = { lei: entity.lei, name: entity.name, country: entity.country, city: entity.city, jurisdiction: "" };
    setCompanySelected(selected);
    setEnrichedData(detailEnriched);

    // Tier: use enriched tier for main company; derive from GLEIF category for subsidiaries
    let autoTier: string = detailEnriched?.supplier_tier || "Tier 1";
    if (entity.category !== undefined) {
      // User selected a subsidiary from the children list — derive tier from its category
      if (entity.category === "BRANCH") autoTier = "Tier 3";
      else autoTier = "Tier 2"; // GENERAL child = direct subsidiary
    }

    setForm((f) => ({
      ...f,
      name: displayName,
      legal_name: displayName,
      country: entity.country,
      website: detailEnriched?.website || f.website,
      industry: detailEnriched?.industry || f.industry,
      nace_code: detailEnriched?.nace_code || f.nace_code,
      notes: detailEnriched?.notes || f.notes,
      supplier_tier: autoTier as import("@/types/api").SupplierTier,
    }));
    setDetailTarget(null);
    setDetailData(null);
    setQuickQuery("");
    setQuickResults([]);
    setAdvResults([]);
    setAdvSearched(false);
  }

  async function runAdvancedSearch() {
    if (!advQ.trim() && !advCountry && !advLegalForm && !advCategory) return;
    setAdvSearching(true);
    setAdvSearched(false);
    try {
      const results = await searchGleif(advQ.trim() || "a", {
        country: advCountry || undefined,
        legalForm: advLegalForm || undefined,
        category: advCategory || undefined,
      });
      setAdvResults(results);
    } catch {
      setAdvResults([]);
    } finally {
      setAdvSearching(false);
      setAdvSearched(true);
    }
  }

  function resetCompanySearch() {
    setQuickQuery("");
    setQuickResults([]);
    setQuickDropdownOpen(false);
    setAdvQ(""); setAdvCountry(""); setAdvLegalForm(""); setAdvCategory("");
    setAdvResults([]); setAdvSearched(false);
    setShowAdvanced(false);
    setDetailTarget(null); setDetailData(null); setDetailEnriched(null);
    setCompanySelected(null);
    setEnrichedData(null);
    setManualEnrichedFields(new Set());
    setManualEnriching(false);
  }

  const allSuppliers = data?.items ?? [];
  const suppliers = riskFilter
    ? allSuppliers.filter((s) => scoreMap.get(s.id)?.risk_level === riskFilter)
    : allSuppliers;

  const isAllSelected = suppliers.length > 0 && suppliers.every((s) => selectedIds.has(s.id));
  const isPartialSelected = suppliers.some((s) => selectedIds.has(s.id)) && !isAllSelected;

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (isAllSelected) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        suppliers.forEach((s) => next.delete(s.id));
        return next;
      });
    } else {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        suppliers.forEach((s) => next.add(s.id));
        return next;
      });
    }
  }

  async function handleDeleteSelected() {
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      for (const id of selectedIds) {
        await archiveSupplier(id);
      }
      setSelectedIds(new Set());
      setShowDeleteConfirm(false);
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      queryClient.invalidateQueries({ queryKey: ["supplier-scores-overview"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    } catch {
      setDeleteError("Einige Lieferanten konnten nicht gelöscht werden.");
    } finally {
      setDeleteBusy(false);
    }
  }
  const total = data?.total ?? 0;
  const totalPages = data ? Math.ceil(total / PAGE_SIZE) : 1;

  return (
    <div className="space-y-6">
      <ReadinessBanner stepKey="onboard" />

      {/* Sub-page navigation */}
      <div className="flex flex-wrap gap-2">
        {[
          { href: "/suppliers/analytics",    label: "Analytics" },
          { href: "/suppliers/geo-heatmap",  label: "Geo Heatmap" },
          { href: "/suppliers/segmentation", label: "Segmentation" },
          { href: "/suppliers/certificates", label: "Certificates" },
          { href: "/suppliers/portal",       label: "Supplier Portal" },
          { href: "/network/resilience",     label: "Network Resilience" },
        ].map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className="rounded-full border border-border px-3 py-1 text-xs font-medium text-muted-foreground hover:border-blue-400 hover:text-blue-600 transition-colors"
          >
            {label}
          </Link>
        ))}
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t("suppliers.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("dashboard.supplierPortfolioDesc")}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={collecting}
            onClick={async () => {
              setCollecting(true);
              setCollectResult(null);
              try {
                const r = await collectIntelligence();
                setCollectResult(r);
              } catch { /* silent */ } finally {
                setCollecting(false);
              }
            }}
            className="gap-2"
          >
            <Globe className={`h-4 w-4 ${collecting ? "animate-spin" : ""}`} />
            {collecting ? "Sammle…" : "Intelligence sammeln"}
          </Button>
          <Button onClick={() => setShowCreate(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            {t("suppliers.newSupplier")}
          </Button>
        </div>
      </div>
      {collectResult && (
        <div className={`rounded-lg border px-4 py-2.5 text-sm flex items-center justify-between ${collectResult.signals_created > 0 ? "border-blue-300 bg-blue-50 text-blue-800" : "border-slate-200 bg-slate-50 text-slate-600"}`}>
          <span>{collectResult.message} · {collectResult.sources_ok}/{collectResult.sources_attempted} Quellen · {collectResult.duration_seconds.toFixed(1)}s</span>
          <button onClick={() => setCollectResult(null)} className="ml-4 text-slate-400 hover:text-slate-600">✕</button>
        </div>
      )}

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
        <select
          value={riskFilter}
          onChange={(e) => { setRiskFilter(e.target.value); setPage(1); }}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="">All Risk Levels</option>
          <option value="Critical">Critical</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        {(search || tierFilter || statusFilter || riskFilter) && (
          <Button variant="ghost" size="sm" onClick={() => { setSearch(""); setSearchInput(""); setTierFilter(""); setStatusFilter(""); setRiskFilter(""); setPage(1); }} className="gap-1 text-muted-foreground">
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

      {/* Selection action bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2.5">
          <span className="text-sm font-medium text-blue-800">
            {selectedIds.size} Lieferant{selectedIds.size !== 1 ? "en" : ""} ausgewählt
          </span>
          <button
            disabled={collecting}
            onClick={async () => {
              setCollecting(true);
              setCollectResult(null);
              try {
                const r = await collectIntelligenceBatch(Array.from(selectedIds));
                setCollectResult(r);
              } catch { /* silent */ } finally {
                setCollecting(false);
              }
            }}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Globe className={`h-3.5 w-3.5 ${collecting ? "animate-spin" : ""}`} />
            {collecting ? "Sammle…" : "Intelligence sammeln"}
          </button>
          <button
            onClick={() => { setDeleteError(null); setShowDeleteConfirm(true); }}
            className="flex items-center gap-1.5 rounded-md bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700"
          >
            <Trash2 className="h-3.5 w-3.5" /> Löschen
          </button>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-xs text-blue-700 hover:text-blue-900 underline"
          >
            Abwählen
          </button>
        </div>
      )}

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
              title={search || tierFilter || statusFilter || riskFilter ? "Keine Treffer" : t("suppliers.noSuppliers")}
              description={search || tierFilter || statusFilter || riskFilter
                ? "Keine Lieferanten entsprechen den gewählten Filtern. Filter zurücksetzen und erneut versuchen."
                : t("suppliers.noSuppliersDesc")}
              actions={!search && !tierFilter && !statusFilter && !riskFilter ? [
                { label: t("suppliers.newSupplier"), onClick: () => setShowCreate(true), variant: "primary" },
              ] : [
                { label: "Filter zurücksetzen", onClick: () => { setSearch(""); setSearchInput(""); setTierFilter(""); setStatusFilter(""); setRiskFilter(""); setPage(1); }, variant: "outline" },
              ]}
            />
          </CardContent>
        </Card>
      ) : viewMode === "grid" ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {suppliers.map((s) => {
              const sc = scoreMap.get(s.id);
              return (
                <div key={s.id} className="relative">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(s.id)}
                    onChange={() => toggleSelect(s.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="absolute top-3 left-3 z-10 h-4 w-4 rounded border-gray-300 cursor-pointer"
                  />
                  <Link href={`/suppliers/${s.id}`} className="block">
                  <Card className={`h-full transition-shadow hover:shadow-md hover:border-blue-300 ${selectedIds.has(s.id) ? "border-blue-400 bg-blue-50" : ""}`}>
                    <CardContent className="p-4 pl-8">
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
                </div>
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
                    <th className="w-10 px-4 py-3">
                      <input
                        type="checkbox"
                        checked={isAllSelected}
                        ref={(el) => { if (el) el.indeterminate = isPartialSelected; }}
                        onChange={toggleSelectAll}
                        className="h-4 w-4 rounded border-gray-300 cursor-pointer"
                      />
                    </th>
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
                      <tr key={s.id} className={`hover:bg-muted/20 transition-colors ${selectedIds.has(s.id) ? "bg-blue-50" : ""}`}>
                        <td className="w-10 px-4 py-3" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={selectedIds.has(s.id)}
                            onChange={() => toggleSelect(s.id)}
                            className="h-4 w-4 rounded border-gray-300 cursor-pointer"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Link href={`/suppliers/${s.id}`} className="font-medium text-foreground hover:text-blue-600 hover:underline">
                              {s.name}
                            </Link>
                            {s.supplier_type === "commodity" && s.commodity && (
                              <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800">
                                ⛏ {s.commodity}
                              </span>
                            )}
                          </div>
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
                        <td className="px-4 py-3 hidden lg:table-cell text-xs tabular-nums">
                          {sc ? (
                            <Link href={`/assessments?supplier_id=${s.id}`} className="text-muted-foreground hover:text-blue-600 hover:underline">
                              {sc.assessment_count}
                            </Link>
                          ) : "—"}
                        </td>
                        <td className="px-4 py-3 hidden lg:table-cell text-xs tabular-nums">
                          {sc ? (
                            <Link
                              href={`/findings?supplier_id=${s.id}`}
                              className={sc.finding_count > 0 ? "text-amber-700 font-medium hover:underline" : "text-muted-foreground hover:underline"}
                            >
                              {sc.finding_count}
                            </Link>
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

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-sm rounded-xl bg-background p-6 shadow-2xl">
            <div className="flex items-start gap-3 mb-4">
              <AlertTriangle className="h-6 w-6 text-red-500 shrink-0 mt-0.5" />
              <div>
                <h2 className="text-base font-semibold">Lieferanten löschen</h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Möchten Sie <strong>{selectedIds.size} Lieferant{selectedIds.size !== 1 ? "en" : ""}</strong> wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.
                </p>
              </div>
            </div>
            {deleteError && <p className="mb-3 text-sm text-red-600">{deleteError}</p>}
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setShowDeleteConfirm(false)} disabled={deleteBusy}>
                Abbrechen
              </Button>
              <Button
                onClick={handleDeleteSelected}
                disabled={deleteBusy}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                {deleteBusy ? <Spinner size="sm" className="mr-2" /> : <Trash2 className="h-4 w-4 mr-1.5" />}
                {deleteBusy ? "Wird gelöscht…" : `${selectedIds.size} löschen`}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-xl bg-background shadow-2xl flex flex-col max-h-[92vh]">

            {/* Modal header */}
            <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-border shrink-0">
              <h2 className="text-lg font-semibold">{t("suppliers.createTitle")}</h2>
              <button
                onClick={() => { setShowCreate(false); setCreateError(null); resetCompanySearch(); setCreateTab("search"); setForm({ name: "", legal_name: "", country: "", industry: "", nace_code: "", website: "", supplier_tier: "Tier 1", notes: "", supplier_type: "manufacturing", commodity: null, commodity_code: null }); }}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Tab bar */}
            <div className="flex border-b border-border shrink-0">
              <button
                onClick={() => setCreateTab("search")}
                className={`flex-1 py-2.5 text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${
                  createTab === "search"
                    ? "border-b-2 border-blue-600 text-blue-600"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Search className="h-3.5 w-3.5" />
                Unternehmenssuche
              </button>
              <button
                onClick={() => setCreateTab("manual")}
                className={`flex-1 py-2.5 text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${
                  createTab === "manual"
                    ? "border-b-2 border-blue-600 text-blue-600"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Building2 className="h-3.5 w-3.5" />
                Manuelle Eingabe
              </button>
              <button
                onClick={() => {
                  setCreateTab("commodity");
                  setForm((f) => ({ ...f, supplier_type: "commodity" }));
                }}
                className={`flex-1 py-2.5 text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${
                  createTab === "commodity"
                    ? "border-b-2 border-amber-600 text-amber-600"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <span className="text-sm">⛏</span>
                Rohstofflieferant
              </button>
            </div>

            {/* Tab content — scrollable */}
            <div className="overflow-y-auto flex-1 px-6 py-5">

              {/* ── TAB 1: Unternehmenssuche ── */}
              {createTab === "search" && (
                <div className="space-y-4">

                  {/* Selected company preview */}
                  {companySelected && (
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0">
                          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                          <span className="text-sm font-semibold text-emerald-800 truncate">{toTitleCase(companySelected.name)}</span>
                          <span className="shrink-0 rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-mono text-emerald-700">{companySelected.country}</span>
                          {companySelected.city && <span className="text-[11px] text-emerald-700 truncate hidden sm:block">{companySelected.city}</span>}
                        </div>
                        <button type="button" onClick={() => { setCompanySelected(null); setEnrichedData(null); setForm({ name: "", legal_name: "", country: "", industry: "", nace_code: "", website: "", supplier_tier: "Tier 1", notes: "", supplier_type: "manufacturing", commodity: null, commodity_code: null }); }} className="text-emerald-400 hover:text-emerald-700 shrink-0 ml-2">
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
                        {enrichedData?.website && (
                          <div><p className="text-muted-foreground font-medium">Webseite</p><p className="text-blue-600 truncate">{enrichedData.website.replace(/^https?:\/\//,"")}</p></div>
                        )}
                        {enrichedData?.nace_code && (
                          <div><p className="text-muted-foreground font-medium">NACE</p><p className="font-mono text-[11px]">{enrichedData.nace_code}{enrichedData.nace_label ? ` – ${enrichedData.nace_label}` : ""}</p></div>
                        )}
                        {enrichedData?.industry && (
                          <div className="col-span-2"><p className="text-muted-foreground font-medium">Branche</p><p>{enrichedData.industry}</p></div>
                        )}
                        {enrichedData?.notes && (
                          <div className="col-span-2"><p className="text-muted-foreground font-medium">Zusammenfassung</p><p className="line-clamp-2">{enrichedData.notes}</p></div>
                        )}
                      </div>
                      <div className="pt-1 border-t border-emerald-200 flex items-center gap-3">
                        <div className="flex-1">
                          <label className="mb-1 block text-xs font-medium text-emerald-800">Lieferanten-Tier</label>
                          <select value={form.supplier_tier} onChange={(e) => setForm((f) => ({ ...f, supplier_tier: e.target.value as SupplierTier }))} className="w-full rounded border border-emerald-300 bg-white px-2 py-1.5 text-sm">
                            <option>Tier 1</option><option>Tier 2</option><option>Tier 3</option><option>Other</option>
                          </select>
                        </div>
                        <button type="button" onClick={() => setCreateTab("manual")} className="text-xs text-emerald-700 hover:underline mt-4">Felder bearbeiten →</button>
                      </div>
                    </div>
                  )}

                  {/* Quick search */}
                  {!companySelected && (
                    <>
                      <div className="relative" ref={dropdownRef}>
                        <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                        <input
                          type="text"
                          value={quickQuery}
                          onChange={(e) => { setQuickQuery(e.target.value); }}
                          placeholder="Unternehmen suchen… (ab 3 Zeichen)"
                          className="w-full rounded-md border border-input bg-background py-2 pl-10 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                          autoFocus
                        />
                        {quickSearching && <Spinner size="sm" className="absolute right-2.5 top-2.5" />}
                        {quickQuery && !quickSearching && (
                          <button onClick={() => { setQuickQuery(""); setQuickResults([]); setQuickDropdownOpen(false); }} className="absolute right-2.5 top-2.5 text-muted-foreground hover:text-foreground">
                            <X className="h-4 w-4" />
                          </button>
                        )}

                        {/* Quick results dropdown */}
                        {quickDropdownOpen && quickResults.length > 0 && (
                          <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-64 overflow-y-auto rounded-md border border-border bg-background shadow-xl">
                            {quickResults.map((c) => (
                              <button
                                key={c.lei}
                                type="button"
                                onMouseDown={(e) => { e.preventDefault(); openDetail(c); }}
                                className="flex w-full items-center justify-between px-3 py-2.5 text-left hover:bg-muted transition-colors border-b border-border/40 last:border-0"
                              >
                                <div className="min-w-0">
                                  <p className="text-sm font-medium truncate">{toTitleCase(c.name)}</p>
                                  {c.city && <p className="text-[11px] text-muted-foreground">{c.city}</p>}
                                </div>
                                <span className="ml-3 shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-mono text-slate-600">{c.country}</span>
                              </button>
                            ))}
                          </div>
                        )}
                        {quickDropdownOpen && quickResults.length === 0 && !quickSearching && (
                          <div className="absolute left-0 right-0 top-full z-50 mt-1 rounded-md border border-border bg-background shadow-xl px-3 py-3 text-xs text-muted-foreground">
                            Kein Ergebnis — nutzen Sie die <button type="button" className="text-blue-600 hover:underline" onClick={() => { setQuickDropdownOpen(false); setShowAdvanced(true); }}>erweiterte Suche</button>.
                          </div>
                        )}
                      </div>

                      {/* Advanced filter toggle */}
                      <button
                        type="button"
                        onClick={() => setShowAdvanced((v) => !v)}
                        className="flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 font-medium"
                      >
                        <SlidersHorizontal className="h-3.5 w-3.5" />
                        {showAdvanced ? "Erweiterte Suche ausblenden" : "Erweiterte Suche / Filter"}
                      </button>

                      {/* Advanced filter panel */}
                      {showAdvanced && (
                        <div className="rounded-lg border border-blue-100 bg-blue-50/60 p-4 space-y-3">
                          <p className="text-xs font-semibold text-blue-800 flex items-center gap-1.5"><SlidersHorizontal className="h-3.5 w-3.5" /> Erweiterte Suche</p>
                          <div className="grid grid-cols-2 gap-3">
                            <div className="col-span-2">
                              <label className="mb-1 block text-xs font-medium text-slate-600">Unternehmensname</label>
                              <input type="text" value={advQ} onChange={(e) => setAdvQ(e.target.value)} placeholder="z.B. Siemens, BASF…" className="w-full rounded border border-input bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" onKeyDown={(e) => { if (e.key === "Enter") runAdvancedSearch(); }} />
                            </div>
                            <div>
                              <label className="mb-1 block text-xs font-medium text-slate-600">Land (ISO)</label>
                              <div className="relative">
                                <Globe className="absolute left-2 top-2 h-3.5 w-3.5 text-muted-foreground" />
                                <input type="text" value={advCountry} onChange={(e) => setAdvCountry(e.target.value.toUpperCase().slice(0,2))} placeholder="DE, US…" maxLength={2} className="w-full rounded border border-input bg-white py-1.5 pl-7 pr-2 text-sm uppercase focus:outline-none focus:ring-2 focus:ring-blue-400" />
                              </div>
                            </div>
                            <div>
                              <label className="mb-1 block text-xs font-medium text-slate-600">Rechtsform</label>
                              <select value={advLegalForm} onChange={(e) => setAdvLegalForm(e.target.value)} className="w-full rounded border border-input bg-white px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
                                {LEGAL_FORMS.map((lf) => <option key={lf.value} value={lf.value}>{lf.label}</option>)}
                              </select>
                            </div>
                            <div>
                              <label className="mb-1 block text-xs font-medium text-slate-600">Kategorie</label>
                              <select value={advCategory} onChange={(e) => setAdvCategory(e.target.value)} className="w-full rounded border border-input bg-white px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
                                {GLEIF_CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                              </select>
                            </div>
                            <div className="flex items-end">
                              <Button onClick={runAdvancedSearch} disabled={advSearching} size="sm" className="w-full">
                                {advSearching ? <Spinner size="sm" className="mr-1.5" /> : <Search className="h-3.5 w-3.5 mr-1.5" />}
                                Suchen
                              </Button>
                            </div>
                          </div>

                          {/* Advanced results list */}
                          {advSearched && (
                            <div className="mt-2 space-y-1 max-h-56 overflow-y-auto">
                              {advResults.length === 0 && (
                                <p className="text-xs text-muted-foreground py-2 text-center">Keine Ergebnisse gefunden.</p>
                              )}
                              {advResults.map((c) => (
                                <button
                                  key={c.lei}
                                  type="button"
                                  onClick={() => openDetail(c)}
                                  className="flex w-full items-center justify-between rounded-md border border-border bg-white px-3 py-2 text-left hover:bg-muted/60 transition-colors"
                                >
                                  <div className="min-w-0">
                                    <p className="text-sm font-medium truncate">{toTitleCase(c.name)}</p>
                                    {c.city && <p className="text-[11px] text-muted-foreground">{c.city}</p>}
                                  </div>
                                  <span className="ml-3 shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-mono text-slate-600">{c.country}</span>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Empty state */}
                      {!quickQuery && !showAdvanced && (
                        <div className="rounded-lg border border-dashed border-border p-6 text-center">
                          <Building2 className="mx-auto h-8 w-8 text-muted-foreground/40 mb-2" />
                          <p className="text-sm text-muted-foreground font-medium">Weltweite Unternehmenssuche</p>
                          <p className="mt-1 text-xs text-muted-foreground">Tippen Sie einen Firmennamen — ab 3 Zeichen erscheinen sofort Vorschläge aus dem globalen GLEIF LEI-Register.</p>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* ── TAB 2: Manuelle Eingabe ── */}
              {createTab === "manual" && (
                <div className="space-y-4">
                  <div>
                    <label className="mb-1 block text-sm font-medium">{t("common.name")} *</label>
                    <div className="relative">
                      <Input
                        value={form.name}
                        onChange={(e) => {
                          setManualEnrichedFields(new Set());
                          setForm((f) => ({ ...f, name: e.target.value, industry: "", nace_code: "", website: "" }));
                        }}
                        placeholder={t("suppliers.namePlaceholder")}
                      />
                      {manualEnriching && (
                        <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-[11px] text-muted-foreground">
                          <Spinner size="sm" /> Anreicherung…
                        </span>
                      )}
                    </div>
                    {manualEnrichedFields.size > 0 && !manualEnriching && (
                      <p className="mt-1 text-[11px] text-emerald-600 flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" /> Branche, NACE &amp; Webseite automatisch befüllt · anpassbar
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium">{t("suppliers.legalName")}</label>
                    <Input value={form.legal_name ?? ""} onChange={(e) => setForm((f) => ({ ...f, legal_name: e.target.value }))} placeholder="Vollständiger Firmenname (falls abweichend)" />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1 block text-sm font-medium">{t("common.country")}</label>
                      <Input value={form.country ?? ""} onChange={(e) => setForm((f) => ({ ...f, country: e.target.value }))} placeholder="DE, US, FR…" />
                    </div>
                    <div>
                      <label className="mb-1 flex items-center gap-1.5 text-sm font-medium">
                        NACE Code
                        {manualEnrichedFields.has("nace_code") && <span className="text-[10px] font-normal text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-full">Auto</span>}
                      </label>
                      <Input value={form.nace_code ?? ""} onChange={(e) => setForm((f) => ({ ...f, nace_code: e.target.value }))} placeholder="C27, C29.32…" />
                    </div>
                  </div>
                  <div>
                    <label className="mb-1 flex items-center gap-1.5 text-sm font-medium">
                      {t("common.industry")}
                      {manualEnrichedFields.has("industry") && <span className="text-[10px] font-normal text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-full">Auto</span>}
                    </label>
                    <Input value={form.industry ?? ""} onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))} placeholder="Maschinenbau, Chemie…" />
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
                      <label className="mb-1 flex items-center gap-1.5 text-sm font-medium">
                        {t("suppliers.website")}
                        {manualEnrichedFields.has("website") && <span className="text-[10px] font-normal text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-full">Auto</span>}
                      </label>
                      <Input value={form.website ?? ""} onChange={(e) => setForm((f) => ({ ...f, website: e.target.value }))} placeholder="https://…" />
                    </div>
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium">{t("common.notes")}</label>
                    <textarea
                      value={form.notes ?? ""}
                      onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                      rows={3}
                      placeholder="Interne Notizen…"
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              )}

              {/* ── TAB 3: Rohstofflieferant ── */}
              {createTab === "commodity" && (
                <div className="space-y-5">
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
                    <strong>Rohstofflieferanten</strong> werden mit einer speziellen Commodity Risk Matrix analysiert —
                    statt NACE-Codes nutzt EIOS rohstoffspezifische CSDDD-Risikoprofile für Metalle und Agrarprodukte.
                  </div>

                  {/* Commodity selector */}
                  <div>
                    <label className="mb-2 block text-sm font-medium">Rohstoff auswählen *</label>
                    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                      {COMMODITIES.map((c) => (
                        <button
                          key={c.code}
                          type="button"
                          onClick={() => setForm((f) => ({
                            ...f,
                            commodity_code: c.code,
                            commodity: c.label,
                            industry: c.sector,
                            nace_code: c.nace,
                            name: f.name || "",
                          }))}
                          className={`rounded-lg border p-3 text-left transition-all ${
                            form.commodity_code === c.code
                              ? "border-amber-400 bg-amber-100 ring-2 ring-amber-300"
                              : "border-border bg-background hover:border-amber-300 hover:bg-amber-50"
                          }`}
                        >
                          <div className="text-xl mb-1">{c.icon}</div>
                          <div className="text-xs font-semibold">{c.label}</div>
                          <div className="text-[10px] text-muted-foreground mt-0.5">{c.sector}</div>
                          <div className="text-[10px] text-muted-foreground font-mono mt-0.5">{c.nace}</div>
                        </button>
                      ))}
                    </div>
                    {form.commodity_code && (
                      <div className="mt-2 rounded-md border border-amber-200 bg-amber-50/60 px-3 py-2 text-xs text-amber-700">
                        Typische Herkunftsländer: {COMMODITIES.find((c) => c.code === form.commodity_code)?.origins}
                      </div>
                    )}
                  </div>

                  {/* Supplier name */}
                  <div>
                    <label className="mb-1 block text-sm font-medium">Lieferantenname *</label>
                    <input
                      type="text"
                      value={form.name}
                      onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                      placeholder="z.B. Congo DRC Minerals SA, Atacama Lithium Corp."
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
                    />
                  </div>

                  {/* Country */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="mb-1 block text-sm font-medium">Herkunftsland (ISO)</label>
                      <input
                        type="text"
                        value={form.country ?? ""}
                        onChange={(e) => setForm((f) => ({ ...f, country: e.target.value.toUpperCase().slice(0, 2) }))}
                        placeholder="CD, CL, UZ…"
                        maxLength={2}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm uppercase focus:outline-none focus:ring-2 focus:ring-amber-500"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium">Lieferanten-Tier</label>
                      <select
                        value={form.supplier_tier}
                        onChange={(e) => setForm((f) => ({ ...f, supplier_tier: e.target.value as SupplierTier }))}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      >
                        <option value="Tier 1">Tier 1</option>
                        <option value="Tier 2">Tier 2</option>
                        <option value="Tier 3">Tier 3</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="mb-1 block text-sm font-medium">{t("common.notes")}</label>
                    <textarea
                      value={form.notes ?? ""}
                      onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                      rows={2}
                      placeholder="Interne Notizen, Zertifizierungen, Vertragsinfo…"
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-amber-500"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Modal footer — always visible */}
            <div className="border-t border-border px-6 py-4 shrink-0">
              {createError && <p className="mb-3 text-sm text-red-600">{createError}</p>}
              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={() => { setShowCreate(false); setCreateError(null); resetCompanySearch(); setCreateTab("search"); setForm({ name: "", legal_name: "", country: "", industry: "", nace_code: "", website: "", supplier_tier: "Tier 1", notes: "", supplier_type: "manufacturing", commodity: null, commodity_code: null }); }}
                >
                  {t("common.cancel")}
                </Button>
                <Button
                  onClick={() => {
                    const name = form.name.trim();
                    if (!name) { setCreateError("Name ist erforderlich."); return; }
                    if (createTab === "commodity" && !form.commodity_code) {
                      setCreateError("Bitte einen Rohstoff auswählen.");
                      return;
                    }
                    createMutation.mutate({
                      ...form,
                      legal_name: form.legal_name || undefined,
                      nace_code: form.nace_code || undefined,
                      website: form.website || undefined,
                      notes: form.notes || undefined,
                      supplier_type: (form.supplier_type || "manufacturing") as SupplierType,
                      commodity: form.commodity || undefined,
                      commodity_code: form.commodity_code || undefined,
                    });
                  }}
                  disabled={
                    createMutation.isPending ||
                    (createTab === "search" && !companySelected) ||
                    (createTab === "manual" && manualEnriching) ||
                    (createTab === "commodity" && !form.name.trim())
                  }
                  className={createTab === "commodity" ? "bg-amber-600 hover:bg-amber-700 text-white" : ""}
                >
                  {createMutation.isPending ? <Spinner size="sm" className="mr-2" /> : null}
                  {createMutation.isPending ? t("suppliers.creating") : t("suppliers.createTitle")}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Company Detail Modal ───────────────────────────────── */}
      {detailTarget && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-2xl rounded-xl bg-background shadow-2xl flex flex-col max-h-[90vh]">

            {/* Header */}
            <div className="flex items-center gap-3 px-6 pt-5 pb-4 border-b border-border shrink-0">
              <button type="button" onClick={() => { setDetailTarget(null); setDetailData(null); }} className="text-muted-foreground hover:text-foreground shrink-0">
                <ArrowLeft className="h-5 w-5" />
              </button>
              <div className="min-w-0 flex-1">
                <h3 className="text-base font-semibold truncate">{toTitleCase(detailTarget.name)}</h3>
                <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                  <MapPin className="h-3 w-3" />
                  {[detailTarget.city, detailTarget.country].filter(Boolean).join(", ")}
                  <span className="mx-1.5 text-border">·</span>
                  <span className="font-mono text-[10px]">LEI: {detailTarget.lei}</span>
                </p>
              </div>
              <button type="button" onClick={() => { setDetailTarget(null); setDetailData(null); }} className="text-muted-foreground hover:text-foreground shrink-0">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="overflow-y-auto flex-1 px-6 py-5 space-y-5">

              {/* Loading */}
              {(detailLoading || detailEnrichLoading) && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-4 justify-center">
                  <Spinner size="sm" /> Daten werden geladen…
                </div>
              )}

              {/* Enriched info */}
              {!detailEnrichLoading && detailEnriched && (
                <div className="grid grid-cols-2 gap-4 rounded-lg border border-border p-4">
                  {detailEnriched.supplier_tier && (
                    <div>
                      <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wide">Auto-Tier</p>
                      <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${
                        detailEnriched.supplier_tier === "Tier 1" ? "bg-emerald-100 text-emerald-700" :
                        detailEnriched.supplier_tier === "Tier 2" ? "bg-blue-100 text-blue-700" :
                        "bg-purple-100 text-purple-700"
                      }`}>
                        {detailEnriched.supplier_tier}
                      </span>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {detailEnriched.supplier_tier === "Tier 1" ? "Muttergesellschaft" :
                         detailEnriched.supplier_tier === "Tier 2" ? "Tochtergesellschaft" : "Niederlassung"}
                      </p>
                    </div>
                  )}
                  {detailEnriched.website && (
                    <div>
                      <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wide">Webseite</p>
                      <a href={detailEnriched.website} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline flex items-center gap-1 truncate">
                        {detailEnriched.website.replace(/^https?:\/\//, "")} <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    </div>
                  )}
                  {detailEnriched.nace_code && (
                    <div>
                      <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wide">NACE Code</p>
                      <p className="text-sm font-mono">{detailEnriched.nace_code}{detailEnriched.nace_label ? <span className="font-sans text-muted-foreground"> – {detailEnriched.nace_label}</span> : ""}</p>
                    </div>
                  )}
                  {detailEnriched.industry && (
                    <div className="col-span-2">
                      <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wide">Branche</p>
                      <p className="text-sm">{detailEnriched.industry}</p>
                    </div>
                  )}
                  {detailEnriched.notes && (
                    <div className="col-span-2">
                      <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wide">Unternehmensbeschreibung</p>
                      <p className="text-sm text-muted-foreground leading-relaxed">{detailEnriched.notes}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Select THIS company */}
              <div>
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Diesen Eintrag auswählen</p>
                <button
                  type="button"
                  disabled={detailEnrichLoading}
                  onClick={() => confirmEntity({ lei: detailTarget.lei, name: detailTarget.name, country: detailTarget.country, city: detailTarget.city })}
                  className="flex w-full items-center justify-between rounded-lg border-2 border-blue-400 bg-blue-50 px-4 py-3 hover:bg-blue-100 transition-colors disabled:opacity-60 disabled:cursor-wait"
                >
                  <div className="text-left">
                    <p className="text-sm font-semibold text-blue-900">{toTitleCase(detailTarget.name)}</p>
                    <p className="text-xs text-blue-700">
                      {[detailTarget.city, detailTarget.country].filter(Boolean).join(", ")} · Hauptgesellschaft
                    </p>
                  </div>
                  {detailEnrichLoading
                    ? <Spinner size="sm" />
                    : <CheckCircle2 className="h-5 w-5 text-blue-500 shrink-0" />}
                </button>
              </div>

              {/* Children / related entities */}
              {!detailLoading && detailData && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      Tochtergesellschaften & Standorte
                      {detailData.total_children > 0 && <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-[10px] normal-case">{detailData.total_children} gesamt</span>}
                    </p>
                    {detailData.children.length > 8 && (
                      <div className="relative">
                        <Search className="absolute left-2 top-1.5 h-3.5 w-3.5 text-muted-foreground" />
                        <input
                          type="text"
                          value={detailEntityFilter}
                          onChange={(e) => setDetailEntityFilter(e.target.value)}
                          placeholder="Filtern…"
                          className="rounded border border-input bg-background py-1 pl-7 pr-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400 w-36"
                        />
                      </div>
                    )}
                  </div>

                  {detailData.children.length === 0 && (
                    <p className="text-xs text-muted-foreground text-center py-3 rounded border border-dashed border-border">
                      Keine verknüpften Tochtergesellschaften in GLEIF gefunden.
                    </p>
                  )}

                  <div className="space-y-1.5 max-h-64 overflow-y-auto pr-0.5">
                    {detailData.children
                      .filter((ch) => !detailEntityFilter || ch.name.toLowerCase().includes(detailEntityFilter.toLowerCase()) || ch.country.toLowerCase().includes(detailEntityFilter.toLowerCase()) || ch.city.toLowerCase().includes(detailEntityFilter.toLowerCase()))
                      .map((ch) => (
                        <button
                          key={ch.lei}
                          type="button"
                          disabled={detailEnrichLoading}
                          onClick={() => confirmEntity(ch)}
                          className="flex w-full items-center justify-between rounded-md border border-border bg-background px-3 py-2.5 text-left hover:bg-muted/70 hover:border-blue-300 transition-colors group disabled:opacity-60 disabled:cursor-wait"
                        >
                          <div className="min-w-0">
                            <p className="text-sm font-medium truncate group-hover:text-blue-700">{toTitleCase(ch.name)}</p>
                            <p className="text-[11px] text-muted-foreground">{[ch.city, ch.country].filter(Boolean).join(", ")}</p>
                          </div>
                          <div className="flex items-center gap-2 ml-3 shrink-0">
                            {ch.category === "BRANCH"
                              ? <span className="rounded bg-purple-100 px-1.5 py-0.5 text-[9px] font-medium text-purple-700">Tier 3 · Niederlassung</span>
                              : <span className="rounded bg-blue-100 px-1.5 py-0.5 text-[9px] font-medium text-blue-700">Tier 2</span>
                            }
                            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-mono text-slate-600">{ch.country}</span>
                          </div>
                        </button>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
