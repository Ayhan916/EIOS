"use client";

import { useEffect, useState } from "react";
import { useLanguage } from "@/lib/i18n/context";
import {
  getSupplyChainSummary,
  listNonCompliantProducts,
  triggerProductScan,
  type AtRiskRegulation,
  type DPPStats,
  type MaterialStats,
  type ProductComplianceScan,
  type ProductStats,
  type ScanResult,
  type SupplyChainComplianceSummary,
} from "@/lib/api/supply_chain_compliance";

const SCAN_RESULT_COLORS: Record<ScanResult, string> = {
  COMPLIANT: "bg-green-100 text-green-700",
  NON_COMPLIANT: "bg-red-100 text-red-700",
  PARTIAL: "bg-yellow-100 text-yellow-700",
  UNKNOWN: "bg-gray-100 text-gray-500",
};

function StatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: number | string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className={`mt-1 text-3xl font-semibold ${accent ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-gray-400">{sub}</p>}
    </div>
  );
}

type Tab = "summary" | "non-compliant" | "scan";

export default function SupplyChainCompliancePage() {
  const { t } = useLanguage();
  const [summary, setSummary] = useState<SupplyChainComplianceSummary | null>(null);
  const [nonCompliant, setNonCompliant] = useState<ProductComplianceScan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("summary");

  // Scan trigger state
  const [scanProductId, setScanProductId] = useState("");
  const [scanRegulation, setScanRegulation] = useState("REACH");
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<ProductComplianceScan | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getSupplyChainSummary(), listNonCompliantProducts()])
      .then(([s, nc]) => {
        setSummary(s);
        setNonCompliant(nc.items);
      })
      .catch((e) => setError(e.message ?? "Failed to load data"))
      .finally(() => setLoading(false));
  }, []);

  async function handleScan() {
    if (!scanProductId.trim() || !scanRegulation.trim()) return;
    setScanning(true);
    setScanResult(null);
    setScanError(null);
    try {
      const result = await triggerProductScan(scanProductId.trim(), scanRegulation.trim());
      setScanResult(result);
    } catch (e: unknown) {
      if (e instanceof Error) setScanError(e.message);
    } finally {
      setScanning(false);
    }
  }

  if (loading) return <p className="text-sm text-gray-500">{t("common.loading")}</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;

  const tabs: { key: Tab; label: string }[] = [
    { key: "summary", label: t("scCompliance.summary") },
    { key: "non-compliant", label: `${t("scCompliance.nonCompliant")} (${nonCompliant.length})` },
    { key: "scan", label: t("scCompliance.triggerScan") },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">{t("scCompliance.title")}</h1>
        <p className="mt-1 text-sm text-gray-500">
          {t("scCompliance.subtitle")}
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={`pb-2 text-sm font-medium transition-colors ${
                activeTab === t.key
                  ? "border-b-2 border-blue-600 text-blue-600"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Summary Tab */}
      {activeTab === "summary" && summary && (
        <div className="space-y-6">
          {/* Material stats */}
          <div>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-400">
              Material Twins
            </h2>
            <div className="grid grid-cols-3 gap-4">
              <StatCard label="Active Materials" value={summary.materials.total_active} />
              <StatCard
                label={t("scCompliance.nonCompliant")}
                value={summary.materials.non_compliant}
                accent={summary.materials.non_compliant > 0 ? "text-red-600" : undefined}
              />
              <StatCard
                label="Substances of Concern in BOM"
                value={summary.materials.substances_of_concern_in_bom}
                accent={summary.materials.substances_of_concern_in_bom > 0 ? "text-amber-600" : undefined}
              />
            </div>
          </div>

          {/* Product stats */}
          <div>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-400">
              Product Twins
            </h2>
            <div className="grid grid-cols-3 gap-4">
              <StatCard label="Active Products" value={summary.products.total_active} />
              <StatCard
                label="Scanned Products"
                value={summary.products.scanned}
                sub={`of ${summary.products.total_active} active`}
              />
              <StatCard
                label={t("scCompliance.nonCompliant")}
                value={summary.products.non_compliant}
                accent={summary.products.non_compliant > 0 ? "text-red-600" : undefined}
              />
            </div>
          </div>

          {/* DPP stats */}
          <div>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-400">
              Digital Product Passports
            </h2>
            <div className="grid grid-cols-3 gap-4">
              <StatCard label="Total DPPs" value={summary.digital_product_passports.total} />
              <StatCard
                label={t("dpp.disclosed")}
                value={summary.digital_product_passports.disclosed}
              />
              <StatCard
                label="DPPs with Non-Compliant Regulations"
                value={summary.digital_product_passports.non_compliant}
                accent={summary.digital_product_passports.non_compliant > 0 ? "text-red-600" : undefined}
              />
            </div>
          </div>

          {/* Top at-risk regulations */}
          {summary.top_at_risk_regulations.length > 0 && (
            <div>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-400">
                Top At-Risk Regulations
              </h2>
              <div className="overflow-hidden rounded-lg border border-gray-200">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-medium text-gray-500">{t("scCompliance.regulation")}</th>
                      <th className="px-4 py-3 text-right font-medium text-gray-500">{t("scCompliance.nonCompliant")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {summary.top_at_risk_regulations.map((r) => (
                      <tr key={r.regulation_code} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-900">{r.regulation_code}</td>
                        <td className="px-4 py-3 text-right">
                          <span className="inline-flex rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700">
                            {r.non_compliant_materials}
                          </span>
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

      {/* Non-Compliant Products Tab */}
      {activeTab === "non-compliant" && (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Product ID</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("scCompliance.regulation")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("scCompliance.scanResult")}</th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">{t("common.total")}</th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">{t("scCompliance.compliant")}</th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">{t("scCompliance.nonCompliantStatus")}</th>
                <th className="px-4 py-3 text-center font-medium text-gray-500">{t("scCompliance.unknown")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("scCompliance.lastScan")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {nonCompliant.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                    No non-compliant product scans found. Trigger a scan to detect issues.
                  </td>
                </tr>
              ) : (
                nonCompliant.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-700">{s.product_id.slice(0, 8)}…</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{s.regulation_code}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          SCAN_RESULT_COLORS[s.scan_result] ?? "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {s.scan_result}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-700">{s.total_materials}</td>
                    <td className="px-4 py-3 text-center text-green-700">{s.compliant_count}</td>
                    <td className="px-4 py-3 text-center text-red-700 font-medium">{s.non_compliant_count}</td>
                    <td className="px-4 py-3 text-center text-gray-400">{s.unknown_count}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {new Date(s.scanned_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Trigger Scan Tab */}
      {activeTab === "scan" && (
        <div className="max-w-lg space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-4">
            <h2 className="text-base font-semibold text-gray-900">BOM Compliance Scan</h2>
            <p className="text-sm text-gray-500">
              Scan a product&apos;s bill of materials against a regulation to detect non-compliant materials.
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Product ID</label>
              <input
                type="text"
                value={scanProductId}
                onChange={(e) => setScanProductId(e.target.value)}
                placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Regulation Code</label>
              <select
                value={scanRegulation}
                onChange={(e) => setScanRegulation(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="REACH">REACH</option>
                <option value="EU_BATTERY">EU Battery Regulation</option>
                <option value="RoHS">RoHS</option>
                <option value="PFAS">PFAS</option>
                <option value="ESPR">ESPR / Ecodesign</option>
                <option value="CONFLICT_MINERALS">Conflict Minerals</option>
              </select>
            </div>
            <button
              onClick={handleScan}
              disabled={scanning || !scanProductId.trim()}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {scanning ? "Scanning BOM…" : "Run Compliance Scan"}
            </button>
          </div>

          {scanError && (
            <p className="text-sm text-red-600">{scanError}</p>
          )}

          {scanResult && (
            <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-3">
              <div className="flex items-center gap-3">
                <h3 className="text-sm font-semibold text-gray-900">Scan Result</h3>
                <span
                  className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    SCAN_RESULT_COLORS[scanResult.scan_result]
                  }`}
                >
                  {scanResult.scan_result}
                </span>
              </div>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-gray-500">Regulation</dt>
                  <dd className="font-medium text-gray-900">{scanResult.regulation_code}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Total Materials</dt>
                  <dd className="font-medium text-gray-900">{scanResult.total_materials}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Compliant</dt>
                  <dd className="font-medium text-green-700">{scanResult.compliant_count}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Non-Compliant</dt>
                  <dd className="font-medium text-red-700">{scanResult.non_compliant_count}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Unknown</dt>
                  <dd className="font-medium text-gray-500">{scanResult.unknown_count}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Scanned</dt>
                  <dd className="text-gray-700">{new Date(scanResult.scanned_at).toLocaleString()}</dd>
                </div>
              </dl>
              {scanResult.flagged_material_ids.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-1">Flagged Material IDs</p>
                  <ul className="space-y-0.5">
                    {scanResult.flagged_material_ids.map((id) => (
                      <li key={id} className="font-mono text-xs text-red-700">{id}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
