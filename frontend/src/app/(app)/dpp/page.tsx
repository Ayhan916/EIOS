"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/lib/i18n/context";
import {
  listDPPs,
  type DPP,
  type DPPFormat,
  type DPPStatus,
} from "@/lib/api/dpp";

const FORMAT_LABELS: Record<DPPFormat, string> = {
  BATTERY_REGULATION: "Battery Regulation",
  ESPR_GENERAL: "ESPR General",
  TEXTILE: "Textile",
  ELECTRONICS: "Electronics",
  PACKAGING: "Packaging",
  CUSTOM: "Custom",
};

const STATUS_COLORS: Record<DPPStatus, string> = {
  DRAFT: "bg-gray-100 text-gray-700",
  ACTIVE: "bg-green-100 text-green-700",
  WITHDRAWN: "bg-red-100 text-red-700",
  EXPIRED: "bg-amber-100 text-amber-700",
};

export default function DPPListPage() {
  const { t } = useLanguage();
  const [items, setItems] = useState<DPP[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<DPPStatus | "">("");
  const [formatFilter, setFormatFilter] = useState<DPPFormat | "">("");
  const [showPublicOnly, setShowPublicOnly] = useState(false);

  useEffect(() => {
    setLoading(true);
    listDPPs({
      dpp_status: statusFilter || undefined,
      format: formatFilter || undefined,
      is_public: showPublicOnly || undefined,
    })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch((e) => setError(e.message ?? "Failed to load passports"))
      .finally(() => setLoading(false));
  }, [statusFilter, formatFilter, showPublicOnly]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{t("dpp.title")}</h1>
          <p className="mt-1 text-sm text-gray-500">
            {t("dpp.subtitle")}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as DPPStatus | "")}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">{t("dpp.allStatuses")}</option>
          <option value="DRAFT">{t("dpp.draft")}</option>
          <option value="ACTIVE">{t("common.active")}</option>
          <option value="WITHDRAWN">{t("dpp.withdrawn")}</option>
          <option value="EXPIRED">{t("dpp.expired")}</option>
        </select>
        <select
          value={formatFilter}
          onChange={(e) => setFormatFilter(e.target.value as DPPFormat | "")}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">{t("dpp.allFormats")}</option>
          {Object.entries(FORMAT_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={showPublicOnly}
            onChange={(e) => setShowPublicOnly(e.target.checked)}
            className="rounded"
          />
          {t("dpp.disclosed")}
        </label>
      </div>

      {/* Content */}
      {loading ? (
        <p className="text-sm text-gray-500">{t("common.loading")}</p>
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-500">{t("dpp.noPassportsFound")}</p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("dpp.passportUid")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("dpp.format")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("common.status")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">PCF (kg CO₂e)</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("dpp.substances")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("dpp.disclosed")}</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {items.map((d) => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-700">
                    {d.passport_uid.slice(0, 8)}…
                  </td>
                  <td className="px-4 py-3 text-gray-700">
                    {FORMAT_LABELS[d.format] ?? d.format}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        STATUS_COLORS[d.dpp_status] ?? "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {d.dpp_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-700">
                    {d.carbon_footprint_kg_co2e != null
                      ? `${d.carbon_footprint_kg_co2e.toFixed(2)}`
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {d.substances_of_concern_count > 0 ? (
                      <span className="text-amber-600 font-medium">
                        {d.substances_of_concern_count}
                      </span>
                    ) : (
                      <span className="text-gray-400">0</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {d.disclosed_at
                      ? new Date(d.disclosed_at).toLocaleDateString()
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/dpp/${d.id}`}
                      className="text-blue-600 hover:underline"
                    >
                      {t("common.view")}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="border-t border-gray-200 bg-gray-50 px-4 py-2 text-xs text-gray-500">
            {t("dpp.totalPassports").replace("{n}", String(total))}
          </div>
        </div>
      )}
    </div>
  );
}
