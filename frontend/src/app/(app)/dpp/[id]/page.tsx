"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useLanguage } from "@/lib/i18n/context";
import {
  getDPP,
  refreshDPP,
  publishDPP,
  withdrawDPP,
  type DPP,
} from "@/lib/api/dpp";

type Tab = "overview" | "carbon" | "compliance" | "lifecycle";

const FORMAT_LABELS: Record<string, string> = {
  BATTERY_REGULATION: "Battery Regulation (EU 2023/1542)",
  ESPR_GENERAL: "ESPR General",
  TEXTILE: "Textile",
  ELECTRONICS: "Electronics",
  PACKAGING: "Packaging",
  CUSTOM: "Custom",
};

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-700",
  ACTIVE: "bg-green-100 text-green-700",
  WITHDRAWN: "bg-red-100 text-red-700",
  EXPIRED: "bg-amber-100 text-amber-700",
};

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-sm font-medium text-gray-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-gray-900">{value ?? "—"}</dd>
    </div>
  );
}

export default function DPPDetailPage() {
  const { t } = useLanguage();
  const params = useParams();
  const id = params.id as string;

  const [dpp, setDpp] = useState<DPP | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    getDPP(id)
      .then(setDpp)
      .catch((e) => setError(e.message ?? "Failed to load passport"))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleAction(action: "refresh" | "publish" | "withdraw") {
    if (!dpp) return;
    setActionLoading(true);
    try {
      if (action === "refresh") {
        const updated = await refreshDPP(dpp.id);
        setDpp(updated);
      } else if (action === "publish") {
        const updated = await publishDPP(dpp.id);
        setDpp(updated);
      } else {
        await withdrawDPP(dpp.id);
        setDpp({ ...dpp, dpp_status: "WITHDRAWN" });
      }
    } catch (e: unknown) {
      if (e instanceof Error) setError(e.message);
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) return <p className="text-sm text-gray-500">{t("common.loading")}</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!dpp) return <p className="text-sm text-gray-500">Passport not found.</p>;

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: t("common.overview") },
    { key: "carbon", label: "Carbon & Sustainability" },
    { key: "compliance", label: "Compliance" },
    { key: "lifecycle", label: "Lifecycle" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            Digital Product Passport
          </h1>
          <p className="mt-1 font-mono text-xs text-gray-500">{dpp.passport_uid}</p>
          <div className="mt-2 flex items-center gap-2">
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                STATUS_COLORS[dpp.dpp_status] ?? "bg-gray-100 text-gray-700"
              }`}
            >
              {dpp.dpp_status}
            </span>
            <span className="text-xs text-gray-500">
              {FORMAT_LABELS[dpp.format] ?? dpp.format}
            </span>
            {dpp.is_public && (
              <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                Public
              </span>
            )}
            {dpp.is_expired && (
              <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                Expired
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          {dpp.dpp_status !== "WITHDRAWN" && (
            <>
              <button
                onClick={() => handleAction("refresh")}
                disabled={actionLoading}
                className="rounded-md bg-white border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Refresh Snapshot
              </button>
              {dpp.dpp_status === "DRAFT" && (
                <button
                  onClick={() => handleAction("publish")}
                  disabled={actionLoading}
                  className="rounded-md bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-700 disabled:opacity-50"
                >
                  Publish
                </button>
              )}
              <button
                onClick={() => handleAction("withdraw")}
                disabled={actionLoading}
                className="rounded-md bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700 disabled:opacity-50"
              >
                Withdraw
              </button>
            </>
          )}
        </div>
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

      {/* Overview */}
      {activeTab === "overview" && (
        <dl className="grid grid-cols-2 gap-x-8 gap-y-4 md:grid-cols-3">
          <Field label="Product ID" value={dpp.product_id} />
          <Field label={t("dpp.format")} value={FORMAT_LABELS[dpp.format] ?? dpp.format} />
          <Field label={t("common.category")} value={dpp.product_category} />
          <Field label={t("products.manufacturer")} value={dpp.manufacturer_name} />
          <Field label={t("common.country")} value={dpp.manufacturer_country} />
          <Field
            label="Manufacturing Date"
            value={dpp.manufacturing_date ?? "—"}
          />
          <Field
            label="Substances of Concern"
            value={
              <span
                className={dpp.substances_of_concern_count > 0 ? "text-amber-600 font-medium" : ""}
              >
                {dpp.substances_of_concern_count}
              </span>
            }
          />
          <Field
            label="Non-Compliant Regulations"
            value={
              <span
                className={dpp.non_compliant_regulations_count > 0 ? "text-red-600 font-medium" : ""}
              >
                {dpp.non_compliant_regulations_count}
              </span>
            }
          />
          <Field label="Evidence ID" value={dpp.evidence_id} />
          {dpp.notes && (
            <div className="col-span-full">
              <dt className="text-sm font-medium text-gray-500">{t("common.notes")}</dt>
              <dd className="mt-0.5 text-sm text-gray-900">{dpp.notes}</dd>
            </div>
          )}
        </dl>
      )}

      {/* Carbon & Sustainability */}
      {activeTab === "carbon" && (
        <div className="space-y-6">
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">Carbon Footprint</h2>
            <dl className="grid grid-cols-2 gap-6 md:grid-cols-3">
              <Field
                label="PCF (kg CO₂e)"
                value={
                  dpp.carbon_footprint_kg_co2e != null ? (
                    <span className="text-lg font-semibold text-gray-900">
                      {dpp.carbon_footprint_kg_co2e.toFixed(4)}
                    </span>
                  ) : (
                    <span className="text-gray-400">Not computed</span>
                  )
                }
              />
              <Field
                label="Source"
                value={
                  dpp.carbon_footprint_source ? (
                    <span
                      className={
                        dpp.carbon_footprint_source === "computed"
                          ? "text-blue-600"
                          : "text-gray-700"
                      }
                    >
                      {dpp.carbon_footprint_source}
                    </span>
                  ) : null
                }
              />
            </dl>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">Content Metrics</h2>
            <dl className="grid grid-cols-2 gap-6">
              <div>
                <dt className="text-sm font-medium text-gray-500">Recycled Content</dt>
                <dd className="mt-1">
                  {dpp.recycled_content_pct != null ? (
                    <>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 rounded-full bg-gray-200 h-2">
                          <div
                            className="rounded-full bg-green-500 h-2"
                            style={{ width: `${dpp.recycled_content_pct}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-gray-900">
                          {dpp.recycled_content_pct.toFixed(1)}%
                        </span>
                      </div>
                    </>
                  ) : (
                    <span className="text-sm text-gray-400">—</span>
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Renewable Content</dt>
                <dd className="mt-1">
                  {dpp.renewable_content_pct != null ? (
                    <div className="flex items-center gap-2">
                      <div className="flex-1 rounded-full bg-gray-200 h-2">
                        <div
                          className="rounded-full bg-blue-500 h-2"
                          style={{ width: `${dpp.renewable_content_pct}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium text-gray-900">
                        {dpp.renewable_content_pct.toFixed(1)}%
                      </span>
                    </div>
                  ) : (
                    <span className="text-sm text-gray-400">—</span>
                  )}
                </dd>
              </div>
            </dl>
          </div>

          {dpp.format === "BATTERY_REGULATION" && (
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-4">
                Battery Specifications
              </h2>
              <dl className="grid grid-cols-2 gap-6 md:grid-cols-4">
                <Field label="Chemistry" value={dpp.battery_chemistry} />
                <Field
                  label="Capacity (Wh)"
                  value={dpp.capacity_wh?.toFixed(1)}
                />
                <Field
                  label="Nominal Voltage (V)"
                  value={dpp.nominal_voltage_v?.toFixed(2)}
                />
                <Field
                  label="Declared Cycles"
                  value={dpp.declared_capacity_cycles}
                />
              </dl>
            </div>
          )}
        </div>
      )}

      {/* Compliance */}
      {activeTab === "compliance" && (
        <div className="space-y-4">
          <div
            className={`rounded-lg border p-6 ${
              dpp.non_compliant_regulations_count > 0
                ? "border-red-200 bg-red-50"
                : "border-green-200 bg-green-50"
            }`}
          >
            <p className="text-sm font-medium text-gray-900">
              {dpp.non_compliant_regulations_count === 0
                ? "No non-compliant regulations detected."
                : `${dpp.non_compliant_regulations_count} non-compliant regulation(s) found across BOM materials.`}
            </p>
            <p className="mt-1 text-xs text-gray-600">
              Use{" "}
              <strong>Refresh Snapshot</strong> to recompute from live material compliance flags.
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <dl className="grid grid-cols-2 gap-4">
              <Field
                label="Substances of Concern"
                value={
                  <span
                    className={dpp.substances_of_concern_count > 0 ? "text-amber-600 font-semibold" : ""}
                  >
                    {dpp.substances_of_concern_count} in BOM
                  </span>
                }
              />
              <Field
                label="Non-Compliant Regulations"
                value={
                  <span
                    className={dpp.non_compliant_regulations_count > 0 ? "text-red-600 font-semibold" : ""}
                  >
                    {dpp.non_compliant_regulations_count}
                  </span>
                }
              />
            </dl>
          </div>
        </div>
      )}

      {/* Lifecycle */}
      {activeTab === "lifecycle" && (
        <dl className="grid grid-cols-2 gap-x-8 gap-y-4 md:grid-cols-3">
          <Field label="Valid From" value={dpp.valid_from} />
          <Field label="Valid Until" value={dpp.valid_until} />
          <Field
            label="Disclosed At"
            value={
              dpp.disclosed_at
                ? new Date(dpp.disclosed_at).toLocaleString()
                : "Not yet disclosed"
            }
          />
          <Field
            label="Is Public"
            value={
              <span
                className={dpp.is_public ? "text-green-600 font-medium" : "text-gray-500"}
              >
                {dpp.is_public ? "Yes" : "No"}
              </span>
            }
          />
          <Field
            label="Is Expired"
            value={
              <span
                className={dpp.is_expired ? "text-red-600 font-medium" : "text-gray-500"}
              >
                {dpp.is_expired ? "Yes" : "No"}
              </span>
            }
          />
          <Field
            label="Created At"
            value={new Date(dpp.created_at).toLocaleString()}
          />
          <Field
            label="Updated At"
            value={new Date(dpp.updated_at).toLocaleString()}
          />
          <Field label="Version" value={dpp.version} />
        </dl>
      )}
    </div>
  );
}
