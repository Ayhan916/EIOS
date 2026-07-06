"use client";

import { useEffect, useState } from "react";
import {
  calculatePCF,
  computeInventory,
  getScope3Summary,
  listInventories,
  listOrgPCFs,
  type ProductCarbonFootprint,
  type Scope3Inventory,
  type Scope3OrgSummary,
} from "@/lib/api/scope3";
import { useLanguage } from "@/lib/i18n/context";

type Tab = "summary" | "inventories" | "pcf-list" | "calculate";

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${accent ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-gray-400">{sub}</p>}
    </div>
  );
}

function CoverageBar({ pct }: { pct: number | null }) {
  if (pct === null) return <span className="text-xs text-gray-400">—</span>;
  const color = pct >= 95 ? "bg-green-500" : pct >= 60 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 rounded-full bg-gray-100 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-600">{pct}%</span>
    </div>
  );
}

export default function Scope3Page() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<Tab>("summary");
  const [summary, setSummary] = useState<Scope3OrgSummary | null>(null);
  const [inventories, setInventories] = useState<Scope3Inventory[]>([]);
  const [pcfs, setPcfs] = useState<ProductCarbonFootprint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Calculate form state
  const [calcProductId, setCalcProductId] = useState("");
  const [calcYear, setCalcYear] = useState(new Date().getFullYear());
  const [calcNotes, setCalcNotes] = useState("");
  const [calculating, setCalculating] = useState(false);
  const [calcResult, setCalcResult] = useState<ProductCarbonFootprint | null>(null);
  const [calcError, setCalcError] = useState<string | null>(null);

  // Inventory form state
  const [invYear, setInvYear] = useState(new Date().getFullYear());
  const [computing, setComputing] = useState(false);
  const [computeError, setComputeError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getScope3Summary(),
      listInventories(),
      listOrgPCFs({ limit: 100 }),
    ])
      .then(([s, invRes, pcfRes]) => {
        setSummary(s);
        setInventories(invRes.items);
        setPcfs(pcfRes.items);
      })
      .catch((e) => setError(e.message ?? "Failed to load Scope 3 data"))
      .finally(() => setLoading(false));
  }, []);

  async function handleCalculate() {
    if (!calcProductId.trim()) return;
    setCalculating(true);
    setCalcResult(null);
    setCalcError(null);
    try {
      const result = await calculatePCF(calcProductId.trim(), calcYear, calcNotes || undefined);
      setCalcResult(result);
      setPcfs((prev) => [result, ...prev]);
    } catch (e: unknown) {
      if (e instanceof Error) setCalcError(e.message);
    } finally {
      setCalculating(false);
    }
  }

  async function handleComputeInventory() {
    setComputing(true);
    setComputeError(null);
    try {
      const inv = await computeInventory(invYear);
      setInventories((prev) => {
        const filtered = prev.filter((i) => i.reporting_year !== invYear);
        return [inv, ...filtered].sort((a, b) => b.reporting_year - a.reporting_year);
      });
    } catch (e: unknown) {
      if (e instanceof Error) setComputeError(e.message);
    } finally {
      setComputing(false);
    }
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "summary", label: t("scope3.tabSummary") },
    { key: "inventories", label: `${t("scope3.tabInventories")} (${inventories.length})` },
    { key: "pcf-list", label: `${t("scope3.tabPcf")} (${pcfs.length})` },
    { key: "calculate", label: t("scope3.tabCalculate") },
  ];

  if (loading) return <p className="text-sm text-gray-500">{t("common.loading")}</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">{t("scope3.title")}</h1>
        <p className="mt-1 text-sm text-gray-500">
          {t("scope3.subtitle")}
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`pb-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-b-2 border-blue-600 text-blue-600"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Summary */}
      {activeTab === "summary" && summary && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard
              label={t("scope3.productsCovered")}
              value={summary.total_products_with_pcf}
            />
            <StatCard
              label={t("scope3.category1")}
              value={`${summary.total_pcf_tco2e.toFixed(3)} tCO₂e`}
              sub={`${summary.total_pcf_kg_co2e.toFixed(2)} kg CO₂e`}
              accent="text-blue-700"
            />
            <StatCard
              label={t("scope3.avgPcf")}
              value={
                summary.avg_pcf_kg_co2e_per_product !== null
                  ? `${summary.avg_pcf_kg_co2e_per_product.toFixed(3)} kg CO₂e`
                  : "—"
              }
            />
            <StatCard
              label={t("scope3.lcaCoverage")}
              value={
                summary.lca_coverage_pct !== null
                  ? `${summary.lca_coverage_pct.toFixed(1)}%`
                  : "—"
              }
              accent={
                summary.lca_coverage_pct !== null && summary.lca_coverage_pct < 60
                  ? "text-amber-600"
                  : undefined
              }
            />
          </div>

          <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800">
            <strong>GHG Protocol Scope 3 Category 1</strong> — Purchased Goods &amp; Services.
            PCF = Σ (weight_pct<sub>i</sub> / 100) × CO₂e_per_kg<sub>i</sub> for each BOM material.
            LCA coverage ≥ 95% qualifies as a complete disclosure under ESRS E1 / CSRD.
          </div>
        </div>
      )}

      {/* Inventories */}
      {activeTab === "inventories" && (
        <div className="space-y-4">
          <div className="flex items-end gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("scope3.reportingYear")}</label>
              <select
                value={invYear}
                onChange={(e) => setInvYear(Number(e.target.value))}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {[2026, 2025, 2024, 2023, 2022].map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleComputeInventory}
              disabled={computing}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {computing ? t("scope3.computing") : t("scope3.computeRefresh")}
            </button>
            {computeError && <p className="text-sm text-red-600">{computeError}</p>}
          </div>

          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">{t("scope3.reportingYear")}</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-500">{t("scope3.totalKgCo2e")}</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-500">{t("scope3.totalTco2e")}</th>
                  <th className="px-4 py-3 text-center font-medium text-gray-500">{t("nav.products")}</th>
                  <th className="px-4 py-3 text-center font-medium text-gray-500">{t("scope3.fullLca")}</th>
                  <th className="px-4 py-3 text-center font-medium text-gray-500">{t("scope3.partialLca")}</th>
                  <th className="px-4 py-3 text-center font-medium text-gray-500">{t("scope3.noLca")}</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">{t("common.date")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {inventories.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                      {t("scope3.noInventories")} — {t("scope3.noInventoriesDesc")}
                    </td>
                  </tr>
                ) : (
                  inventories.map((inv) => (
                    <tr key={inv.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-semibold text-gray-900">{inv.reporting_year}</td>
                      <td className="px-4 py-3 text-right font-mono text-blue-700">
                        {inv.total_pcf_kg_co2e.toFixed(4)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-blue-900 font-medium">
                        {inv.total_pcf_tco2e.toFixed(6)}
                      </td>
                      <td className="px-4 py-3 text-center text-gray-700">{inv.products_included}</td>
                      <td className="px-4 py-3 text-center text-green-700">{inv.products_with_full_lca}</td>
                      <td className="px-4 py-3 text-center text-yellow-600">{inv.products_with_partial_lca}</td>
                      <td className="px-4 py-3 text-center text-red-600">{inv.products_without_lca}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {new Date(inv.calculated_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* PCF List */}
      {activeTab === "pcf-list" && (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("scope3.productId")}</th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">{t("scope3.year")}</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">{t("scope3.pcfKgCo2e")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("scope3.lcaCoverage")}</th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">{t("scope3.materials")}</th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">{t("scope3.withLca")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("scope3.source")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("scope3.calculated")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {pcfs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                    {t("scope3.noPcf")}
                  </td>
                </tr>
              ) : (
                pcfs.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-700">
                      {r.product_id.slice(0, 8)}…
                    </td>
                    <td className="px-4 py-3 text-center text-gray-700">{r.reporting_year}</td>
                    <td className="px-4 py-3 text-right font-mono">
                      {r.pcf_kg_co2e_per_unit !== null ? (
                        <span className="text-blue-700 font-medium">
                          {r.pcf_kg_co2e_per_unit.toFixed(4)}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <CoverageBar pct={r.weight_coverage_pct} />
                    </td>
                    <td className="px-4 py-3 text-center text-gray-700">{r.bom_materials_total}</td>
                    <td className="px-4 py-3 text-center text-gray-700">{r.bom_materials_with_lca}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{r.pcf_source}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {new Date(r.calculated_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Calculate PCF form */}
      {activeTab === "calculate" && (
        <div className="max-w-lg space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-4">
            <h2 className="text-base font-semibold text-gray-900">{t("scope3.computePcf")}</h2>
            <p className="text-sm text-gray-500">
              {t("scope3.computePcfDesc")}
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("scope3.productId")}</label>
              <input
                type="text"
                value={calcProductId}
                onChange={(e) => setCalcProductId(e.target.value)}
                placeholder="UUID of the product"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("scope3.reportingYear")}</label>
              <select
                value={calcYear}
                onChange={(e) => setCalcYear(Number(e.target.value))}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {[2026, 2025, 2024, 2023, 2022].map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t("common.notes")} ({t("common.optional")})</label>
              <input
                type="text"
                value={calcNotes}
                onChange={(e) => setCalcNotes(e.target.value)}
                placeholder="e.g. ESRS E1 disclosure baseline"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button
              onClick={handleCalculate}
              disabled={calculating || !calcProductId.trim()}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {calculating ? t("scope3.computing") : t("scope3.computePcf")}
            </button>
          </div>

          {calcError && <p className="text-sm text-red-600">{calcError}</p>}

          {calcResult && (
            <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-4">
              <h3 className="text-sm font-semibold text-gray-900">{t("scope3.pcf")}</h3>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-gray-500">{t("scope3.pcf")}</dt>
                  <dd className="font-semibold text-blue-700">
                    {calcResult.pcf_kg_co2e_per_unit !== null
                      ? `${calcResult.pcf_kg_co2e_per_unit.toFixed(6)} kg CO₂e/unit`
                      : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">{t("scope3.year")}</dt>
                  <dd className="text-gray-900">{calcResult.reporting_year}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">{t("scope3.bomMaterials")}</dt>
                  <dd className="text-gray-900">{calcResult.bom_materials_total}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">{t("scope3.withLcaData")}</dt>
                  <dd className="text-gray-900">{calcResult.bom_materials_with_lca}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">{t("scope3.weightCoverage")}</dt>
                  <dd><CoverageBar pct={calcResult.weight_coverage_pct} /></dd>
                </div>
                <div>
                  <dt className="text-gray-500">{t("scope3.source")}</dt>
                  <dd className="text-gray-700">{calcResult.pcf_source}</dd>
                </div>
              </dl>

              {calcResult.material_breakdown.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
                    {t("scope3.materialBreakdown")}
                  </h4>
                  <div className="overflow-hidden rounded border border-gray-100">
                    <table className="min-w-full divide-y divide-gray-100 text-xs">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium text-gray-500">{t("scope3.material")}</th>
                          <th className="px-3 py-2 text-right font-medium text-gray-500">{t("scope3.weightPct")}</th>
                          <th className="px-3 py-2 text-right font-medium text-gray-500">{t("scope3.co2ePerKg")}</th>
                          <th className="px-3 py-2 text-right font-medium text-gray-500">{t("scope3.contribution")}</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50 bg-white">
                        {calcResult.material_breakdown.map((item) => (
                          <tr key={item.material_id}>
                            <td className="px-3 py-2 text-gray-700">
                              {item.material_name || item.material_id.slice(0, 8)}
                            </td>
                            <td className="px-3 py-2 text-right text-gray-700">{item.weight_pct}%</td>
                            <td className="px-3 py-2 text-right text-gray-700">
                              {item.co2e_per_kg !== null ? item.co2e_per_kg.toFixed(4) : "—"}
                            </td>
                            <td className="px-3 py-2 text-right font-medium text-blue-700">
                              {item.contribution_kg_co2e !== null
                                ? item.contribution_kg_co2e.toFixed(6)
                                : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
