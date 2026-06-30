"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  listConnectors,
  type ERPConnector,
  type AdapterType,
} from "@/lib/api/erp";

const ADAPTER_LABELS: Record<AdapterType, string> = {
  SAP_ODATA: "SAP OData (S/4HANA)",
  ORACLE_REST: "Oracle Fusion REST",
  REST: "Generic REST",
  CSV: "CSV Import",
};

const ADAPTER_COLORS: Record<AdapterType, string> = {
  SAP_ODATA: "bg-blue-100 text-blue-700",
  ORACLE_REST: "bg-red-100 text-red-700",
  REST: "bg-gray-100 text-gray-700",
  CSV: "bg-green-100 text-green-700",
};

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "bg-green-100 text-green-700",
  INACTIVE: "bg-gray-100 text-gray-500",
};

export default function ERPConnectorsPage() {
  const [items, setItems] = useState<ERPConnector[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adapterFilter, setAdapterFilter] = useState<AdapterType | "">("");
  const [statusFilter, setStatusFilter] = useState<"ACTIVE" | "INACTIVE" | "">("");

  useEffect(() => {
    setLoading(true);
    listConnectors({
      adapter_type: adapterFilter || undefined,
      connector_status: statusFilter || undefined,
    })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch((e) => setError(e.message ?? "Failed to load connectors"))
      .finally(() => setLoading(false));
  }, [adapterFilter, statusFilter]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">ERP Connectors</h1>
          <p className="mt-1 text-sm text-gray-500">
            Bidirectional data sync with SAP, Oracle, and other ERP/PLM systems
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={adapterFilter}
          onChange={(e) => setAdapterFilter(e.target.value as AdapterType | "")}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All adapter types</option>
          {Object.entries(ADAPTER_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as "ACTIVE" | "INACTIVE" | "")}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="INACTIVE">Inactive</option>
        </select>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading connectors…</p>
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center">
          <p className="text-gray-500">No ERP connectors configured yet.</p>
          <p className="mt-1 text-sm text-gray-400">
            Create a connector to start syncing material and product data.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Connector</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Adapter</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Status</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Last Sync</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Schedule</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {items.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{c.name}</div>
                    {c.base_url && (
                      <div className="text-xs text-gray-400 font-mono truncate max-w-xs">
                        {c.base_url}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        ADAPTER_COLORS[c.adapter_type] ?? "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {ADAPTER_LABELS[c.adapter_type] ?? c.adapter_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                        STATUS_COLORS[c.connector_status] ?? "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {c.connector_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {c.last_sync_at ? (
                      <span>
                        {new Date(c.last_sync_at).toLocaleDateString()}
                        {c.last_sync_status && (
                          <span
                            className={`ml-1 ${
                              c.last_sync_status === "SUCCESS"
                                ? "text-green-600"
                                : "text-red-600"
                            }`}
                          >
                            ({c.last_sync_status})
                          </span>
                        )}
                      </span>
                    ) : (
                      "Never"
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">
                    {c.schedule_cron ?? "Manual"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/erp/${c.id}`}
                      className="text-blue-600 hover:underline text-sm"
                    >
                      Configure
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="border-t border-gray-200 bg-gray-50 px-4 py-2 text-xs text-gray-500">
            {total} connector{total !== 1 ? "s" : ""}
          </div>
        </div>
      )}
    </div>
  );
}
