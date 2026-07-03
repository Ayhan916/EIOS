"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Info,
  Wind,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

// ── Types ─────────────────────────────────────────────────────────────────────

interface EmissionFactor {
  id: string;
  scope: string;
  category: string;
  subcategory: string;
  unit: string;
  factor_kgco2e_per_unit: number;
  source: string;
  region: string;
  year: number;
  description: string | null;
  is_custom: boolean;
}

interface CalcResult {
  calculation_id: string;
  scope: string;
  category: string;
  subcategory: string;
  amount: number;
  unit: string;
  factor_id: string;
  factor_kgco2e_per_unit: number;
  result_kgco2e: number;
  result_tco2e: number;
  source: string;
  region: string;
  description: string;
  notes: string | null;
  reporting_year: number | null;
  calculated_at: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function scopeBadge(scope: string) {
  switch (scope) {
    case "SCOPE1": return "bg-red-100 text-red-800";
    case "SCOPE2": return "bg-orange-100 text-orange-800";
    case "SCOPE3": return "bg-amber-100 text-amber-800";
    default:       return "bg-slate-100 text-slate-600";
  }
}

function fmt(n: number, decimals = 4) {
  return n.toLocaleString(undefined, { maximumFractionDigits: decimals });
}

// ── Sub-components ─────────────────────────────────────────────────────────

function FactorRow({
  factor,
  onSelect,
}: {
  factor: EmissionFactor;
  onSelect: (f: EmissionFactor) => void;
}) {
  const { t } = useLanguage();
  const [open, setOpen] = useState(false);

  return (
    <>
      <tr className="border-b border-slate-100 hover:bg-slate-50 text-sm">
        <td className="px-3 py-2.5">
          <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${scopeBadge(factor.scope)}`}>
            {factor.scope}
          </span>
        </td>
        <td className="px-3 py-2.5 text-slate-700">{factor.category}</td>
        <td className="px-3 py-2.5 text-slate-500">{factor.subcategory}</td>
        <td className="px-3 py-2.5 font-mono text-xs text-slate-600">{factor.unit}</td>
        <td className="px-3 py-2.5 font-mono text-xs font-semibold text-slate-900">
          {fmt(factor.factor_kgco2e_per_unit, 6)}
        </td>
        <td className="px-3 py-2.5 text-slate-500">{factor.source}</td>
        <td className="px-3 py-2.5 text-slate-500">{factor.region}</td>
        <td className="px-3 py-2.5">
          {factor.is_custom && (
            <span className="rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-semibold text-violet-700">
              {t("ghg.isCustom")}
            </span>
          )}
        </td>
        <td className="px-3 py-2.5 text-right">
          <div className="flex items-center justify-end gap-1">
            {factor.description && (
              <button
                onClick={() => setOpen((v) => !v)}
                className="rounded p-1 text-slate-400 hover:text-slate-700"
                title={t("ghg.factorDescription")}
              >
                {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              </button>
            )}
            <Button
              size="sm"
              variant="outline"
              className="h-6 px-2 text-xs"
              onClick={() => onSelect(factor)}
            >
              {t("ghg.useThisFactor")}
            </Button>
          </div>
        </td>
      </tr>
      {open && factor.description && (
        <tr className="bg-slate-50 border-b border-slate-100">
          <td colSpan={9} className="px-4 py-2 text-xs text-slate-500 italic">
            {factor.description}
          </td>
        </tr>
      )}
    </>
  );
}

function ResultCard({ result, onReset }: { result: CalcResult; onReset: () => void }) {
  const { t } = useLanguage();
  return (
    <div className="rounded-xl border-2 border-emerald-200 bg-emerald-50 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          <h3 className="font-semibold text-emerald-900">{t("ghg.result")}</h3>
        </div>
        <button
          onClick={onReset}
          className="text-xs text-emerald-700 underline hover:no-underline"
        >
          {t("ghg.newCalculation")}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-lg bg-white border border-emerald-100 p-4 text-center">
          <p className="text-3xl font-bold text-emerald-700">{fmt(result.result_tco2e, 6)}</p>
          <p className="mt-1 text-sm text-slate-500">{t("ghg.resultTco2e")}</p>
        </div>
        <div className="rounded-lg bg-white border border-emerald-100 p-4 text-center">
          <p className="text-3xl font-bold text-slate-700">{fmt(result.result_kgco2e, 3)}</p>
          <p className="mt-1 text-sm text-slate-500">{t("ghg.resultKgco2e")}</p>
        </div>
      </div>

      <div className="rounded-lg bg-white border border-slate-200 p-4 space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-500">{t("ghg.scope")}</span>
          <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${scopeBadge(result.scope)}`}>
            {result.scope}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">{t("ghg.category")}</span>
          <span className="font-medium">{result.category}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">{t("ghg.subcategory")}</span>
          <span className="font-medium">{result.subcategory}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">{t("ghg.amount")}</span>
          <span className="font-mono">{fmt(result.amount, 4)} {result.unit}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">{t("ghg.factorUsed")}</span>
          <span className="font-mono text-xs">{fmt(result.factor_kgco2e_per_unit, 6)} {t("ghg.factorKgco2e")}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">{t("ghg.source")}</span>
          <span className="text-slate-700">{result.source} / {result.region}</span>
        </div>
        {result.reporting_year && (
          <div className="flex justify-between">
            <span className="text-slate-500">{t("ghg.reportingYear")}</span>
            <span>{result.reporting_year}</span>
          </div>
        )}
        <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400 flex items-center gap-1">
          <Info className="h-3 w-3 flex-shrink-0" />
          <span>{t("ghg.auditNote")}</span>
        </div>
      </div>
    </div>
  );
}

// ── Calculator Form ────────────────────────────────────────────────────────────

const SCOPES = ["SCOPE1", "SCOPE2", "SCOPE3"];
const SOURCES = ["DEFRA_2023", "EPA_2023"];
const REGIONS = ["UK", "US", "EU", "DE", "FR", "CN", "IN", "GLOBAL"];

function CalculatorTab() {
  const { t } = useLanguage();

  const [scope, setScope] = useState("SCOPE1");
  const [category, setCategory] = useState("");
  const [subcategory, setSubcategory] = useState("");
  const [amount, setAmount] = useState("");
  const [unit, setUnit] = useState("");
  const [source, setSource] = useState("DEFRA_2023");
  const [region, setRegion] = useState("UK");
  const [notes, setNotes] = useState("");
  const [reportingYear, setReportingYear] = useState<string>(String(new Date().getFullYear()));
  const [supplierId, setSupplierId] = useState("");

  const [result, setResult] = useState<CalcResult | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const { data: factors = [] } = useQuery<EmissionFactor[]>({
    queryKey: ["ghg-factors", scope],
    queryFn: async () => {
      const res = await apiClient.get("/ghg/factors", { params: { scope } });
      return res.data;
    },
  });

  const calcMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {
        scope,
        category: category.trim(),
        subcategory: subcategory.trim(),
        amount: parseFloat(amount),
        unit: unit.trim(),
        source,
        region,
      };
      if (notes.trim()) body.notes = notes.trim();
      if (reportingYear) body.reporting_year = parseInt(reportingYear, 10);
      if (supplierId.trim()) body.supplier_id = supplierId.trim();
      const res = await apiClient.post("/ghg/calculate", body);
      return res.data as CalcResult;
    },
    onSuccess: (data) => {
      setResult(data);
      setApiError(null);
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setApiError(msg ?? t("ghg.noFactor"));
    },
  });

  function applyFactor(f: EmissionFactor) {
    setScope(f.scope);
    setCategory(f.category);
    setSubcategory(f.subcategory);
    setUnit(f.unit);
    setSource(f.source);
    setRegion(f.region);
  }

  const canSubmit =
    category.trim() &&
    subcategory.trim() &&
    unit.trim() &&
    parseFloat(amount) > 0;

  if (result) {
    return (
      <div className="max-w-xl mx-auto mt-4">
        <ResultCard result={result} onReset={() => setResult(null)} />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mt-4">
      {/* Form */}
      <div className="lg:col-span-2 space-y-4">
        <Card>
          <CardContent className="pt-5 space-y-4">
            {/* Scope */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">{t("ghg.scope")}</label>
              <div className="flex gap-2">
                {SCOPES.map((s) => (
                  <button
                    key={s}
                    onClick={() => setScope(s)}
                    className={`flex-1 rounded-lg border py-1.5 text-xs font-semibold transition-colors ${
                      scope === s
                        ? scopeBadge(s) + " border-transparent"
                        : "border-slate-200 text-slate-500 hover:bg-slate-50"
                    }`}
                  >
                    {s.replace("SCOPE", "S")}
                  </button>
                ))}
              </div>
            </div>

            {/* Category / Subcategory */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">{t("ghg.category")}</label>
                <input
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="fuel_combustion"
                  className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-400"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">{t("ghg.subcategory")}</label>
                <input
                  value={subcategory}
                  onChange={(e) => setSubcategory(e.target.value)}
                  placeholder="natural_gas"
                  className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-400"
                />
              </div>
            </div>

            {/* Amount + Unit */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">{t("ghg.amount")}</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="1000"
                  className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-400"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">{t("ghg.unit")}</label>
                <input
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  placeholder="kWh"
                  className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-400"
                />
              </div>
            </div>

            {/* Source + Region */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">{t("ghg.source")}</label>
                <select
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-400"
                >
                  {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">{t("ghg.region")}</label>
                <select
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-400"
                >
                  {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
            </div>

            {/* Reporting Year */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">{t("ghg.reportingYear")}</label>
              <input
                type="number"
                min="2000"
                max="2100"
                value={reportingYear}
                onChange={(e) => setReportingYear(e.target.value)}
                className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-400"
              />
            </div>

            {/* Notes */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">{t("ghg.notes")}</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-400 resize-none"
              />
            </div>

            {/* Supplier ID */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">{t("ghg.supplierOptional")}</label>
              <input
                value={supplierId}
                onChange={(e) => setSupplierId(e.target.value)}
                placeholder="sup_..."
                className="w-full rounded-md border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-400"
              />
            </div>

            {/* Error */}
            {apiError && (
              <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                {apiError}
              </div>
            )}

            <Button
              onClick={() => calcMutation.mutate()}
              disabled={!canSubmit || calcMutation.isPending}
              className="w-full bg-emerald-600 hover:bg-emerald-700"
            >
              {calcMutation.isPending ? (
                <><Spinner size="sm" className="mr-2" />{t("ghg.calculating")}</>
              ) : (
                t("ghg.calculate")
              )}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Factors hint panel */}
      <div className="lg:col-span-3">
        <Card className="h-full">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-slate-600 font-medium">
              {t("ghg.tabFactors")} — {scope}
              <span className="ml-2 text-[11px] font-normal text-slate-400">
                ({t("ghg.useThisFactor")} → {t("ghg.tabCalculator")})
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 overflow-x-auto">
            {factors.length === 0 ? (
              <p className="text-sm text-slate-400 py-4">{t("ghg.noFactors")}</p>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b text-left text-[11px] font-medium uppercase tracking-wide text-slate-400">
                    <th className="px-2 py-2">Scope</th>
                    <th className="px-2 py-2">{t("ghg.category")}</th>
                    <th className="px-2 py-2">{t("ghg.subcategory")}</th>
                    <th className="px-2 py-2">{t("ghg.unit")}</th>
                    <th className="px-2 py-2">{t("ghg.factorKgco2e")}</th>
                    <th className="px-2 py-2">{t("ghg.region")}</th>
                    <th className="px-2 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {factors.slice(0, 20).map((f) => (
                    <tr key={f.id} className="border-b border-slate-100 hover:bg-emerald-50">
                      <td className="px-2 py-2">
                        <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${scopeBadge(f.scope)}`}>
                          {f.scope.replace("SCOPE", "S")}
                        </span>
                      </td>
                      <td className="px-2 py-2 text-slate-700">{f.category}</td>
                      <td className="px-2 py-2 text-slate-500">{f.subcategory}</td>
                      <td className="px-2 py-2 font-mono">{f.unit}</td>
                      <td className="px-2 py-2 font-mono font-semibold">{fmt(f.factor_kgco2e_per_unit, 6)}</td>
                      <td className="px-2 py-2 text-slate-400">{f.region}</td>
                      <td className="px-2 py-2">
                        <button
                          onClick={() => applyFactor(f)}
                          className="text-emerald-600 hover:underline text-[11px] font-medium"
                        >
                          {t("ghg.useThisFactor")}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Factors Tab ────────────────────────────────────────────────────────────────

function FactorsTab() {
  const { t } = useLanguage();
  const [filterScope, setFilterScope] = useState("");
  const [filterSource, setFilterSource] = useState("");
  const [filterRegion, setFilterRegion] = useState("");

  const { data: factors = [], isLoading } = useQuery<EmissionFactor[]>({
    queryKey: ["ghg-factors-all", filterScope, filterSource, filterRegion],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (filterScope) params.scope = filterScope;
      if (filterSource) params.source = filterSource;
      if (filterRegion) params.region = filterRegion;
      const res = await apiClient.get("/ghg/factors", { params });
      return res.data;
    },
  });

  const [selected, setSelected] = useState<EmissionFactor | null>(null);

  return (
    <div className="mt-4 space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={filterScope}
          onChange={(e) => setFilterScope(e.target.value)}
          className="rounded-md border border-slate-200 px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-emerald-400"
        >
          <option value="">{t("ghg.filterScope")}</option>
          {SCOPES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select
          value={filterSource}
          onChange={(e) => setFilterSource(e.target.value)}
          className="rounded-md border border-slate-200 px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-emerald-400"
        >
          <option value="">{t("ghg.filterSource")}</option>
          {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select
          value={filterRegion}
          onChange={(e) => setFilterRegion(e.target.value)}
          className="rounded-md border border-slate-200 px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-emerald-400"
        >
          <option value="">{t("ghg.filterRegion")}</option>
          {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <span className="self-center text-sm text-slate-400">{factors.length} factors</span>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      ) : factors.length === 0 ? (
        <div className="rounded-lg border border-dashed p-10 text-center text-sm text-slate-400">
          {t("ghg.noFactors")}
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                <th className="px-3 py-3">Scope</th>
                <th className="px-3 py-3">{t("ghg.category")}</th>
                <th className="px-3 py-3">{t("ghg.subcategory")}</th>
                <th className="px-3 py-3">{t("ghg.unit")}</th>
                <th className="px-3 py-3">{t("ghg.factorKgco2e")}</th>
                <th className="px-3 py-3">{t("ghg.source")}</th>
                <th className="px-3 py-3">{t("ghg.region")}</th>
                <th className="px-3 py-3"></th>
                <th className="px-3 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {factors.map((f) => (
                <FactorRow
                  key={f.id}
                  factor={f}
                  onSelect={(fac) => setSelected(fac)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Selected factor quick info */}
      {selected && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 flex items-start justify-between gap-4">
          <div className="text-sm">
            <p className="font-semibold text-emerald-900">
              {selected.scope} — {selected.category} / {selected.subcategory}
            </p>
            <p className="text-emerald-700 text-xs mt-0.5">
              {fmt(selected.factor_kgco2e_per_unit, 6)} kg CO₂e / {selected.unit} · {selected.source} · {selected.region}
            </p>
            {selected.description && (
              <p className="text-slate-500 text-xs mt-1 italic">{selected.description}</p>
            )}
          </div>
          <button onClick={() => setSelected(null)} className="text-slate-400 hover:text-slate-600 text-lg leading-none">×</button>
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type Tab = "calculator" | "factors";

export default function GHGCalculatorPage() {
  const { t } = useLanguage();
  const [tab, setTab] = useState<Tab>("calculator");

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600 flex-shrink-0">
          <Wind className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-slate-900">{t("ghg.title")}</h1>
          <p className="mt-0.5 text-sm text-slate-500">{t("ghg.subtitle")}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 w-fit">
        {(["calculator", "factors"] as Tab[]).map((tab_) => (
          <button
            key={tab_}
            onClick={() => setTab(tab_)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              tab === tab_
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {t(tab_ === "calculator" ? "ghg.tabCalculator" : "ghg.tabFactors")}
          </button>
        ))}
      </div>

      {tab === "calculator" ? <CalculatorTab /> : <FactorsTab />}
    </div>
  );
}
