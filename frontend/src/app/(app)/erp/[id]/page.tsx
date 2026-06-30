"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useLanguage } from "@/lib/i18n/context";
import {
  getConnector,
  listSyncJobs,
  listFieldMappings,
  triggerSync,
  type ERPConnector,
  type ERPSyncJob,
  type ERPFieldMapping,
  type SyncDirection,
  type EntityType,
} from "@/lib/api/erp";

type Tab = "overview" | "sync" | "mappings" | "jobs";

const JOB_STATUS_COLORS: Record<string, string> = {
  PENDING: "bg-yellow-100 text-yellow-700",
  RUNNING: "bg-blue-100 text-blue-700",
  SUCCESS: "bg-green-100 text-green-700",
  FAILED: "bg-red-100 text-red-700",
};

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-sm font-medium text-gray-500">{label}</dt>
      <dd className="mt-0.5 text-sm text-gray-900">{value ?? "—"}</dd>
    </div>
  );
}

export default function ERPConnectorDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { t } = useLanguage();

  const [connector, setConnector] = useState<ERPConnector | null>(null);
  const [jobs, setJobs] = useState<ERPSyncJob[]>([]);
  const [mappings, setMappings] = useState<ERPFieldMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [syncing, setSyncing] = useState(false);
  const [syncDirection, setSyncDirection] = useState<SyncDirection>("INBOUND");
  const [syncEntityType, setSyncEntityType] = useState<EntityType>("Material");
  const [csvContent, setCsvContent] = useState("");

  useEffect(() => {
    Promise.all([
      getConnector(id),
      listSyncJobs(id, { limit: 20 }),
      listFieldMappings(id),
    ])
      .then(([conn, jobsRes, mapsRes]) => {
        setConnector(conn);
        setJobs(jobsRes.items);
        setMappings(mapsRes);
      })
      .catch((e) => setError(e.message ?? "Failed to load connector"))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleSync() {
    if (!connector) return;
    setSyncing(true);
    try {
      const job = await triggerSync(connector.id, {
        direction: syncDirection,
        entity_type: syncEntityType,
        materials_csv: connector.adapter_type === "CSV" && syncEntityType === "Material" ? csvContent : undefined,
        bom_csv: connector.adapter_type === "CSV" && syncEntityType === "BOM" ? csvContent : undefined,
      });
      setJobs((prev) => [job, ...prev]);
    } catch (e: unknown) {
      if (e instanceof Error) setError(e.message);
    } finally {
      setSyncing(false);
    }
  }

  if (loading) return <p className="text-sm text-gray-500">{t("common.loading")}</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!connector) return <p className="text-sm text-gray-500">Connector not found.</p>;

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: t("common.overview") },
    { key: "sync", label: "Trigger Sync" },
    { key: "mappings", label: `Field Mappings (${mappings.length})` },
    { key: "jobs", label: `Sync Jobs (${jobs.length})` },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{connector.name}</h1>
          <p className="mt-1 text-sm text-gray-500">{connector.adapter_type} connector</p>
          <div className="mt-2 flex items-center gap-2">
            <span
              className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                connector.connector_status === "ACTIVE"
                  ? "bg-green-100 text-green-700"
                  : "bg-gray-100 text-gray-500"
              }`}
            >
              {connector.connector_status}
            </span>
          </div>
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
          <Field label="Adapter Type" value={connector.adapter_type} />
          <Field label="Auth Scheme" value={connector.auth_scheme} />
          <Field label="Base URL" value={
            connector.base_url ? (
              <span className="font-mono text-xs">{connector.base_url}</span>
            ) : null
          } />
          <Field label={t("common.status")} value={connector.connector_status} />
          <Field label="Schedule" value={connector.schedule_cron ?? "Manual only"} />
          <Field label="Timeout" value={`${connector.timeout_seconds}s`} />
          <Field label={t("erp.lastSync")} value={
            connector.last_sync_at
              ? new Date(connector.last_sync_at).toLocaleString()
              : "Never"
          } />
          <Field label="Last Sync Status" value={connector.last_sync_status} />
          <Field label="Secret Reference" value={connector.secret_reference_id} />
          {connector.description && (
            <div className="col-span-full">
              <dt className="text-sm font-medium text-gray-500">{t("common.description")}</dt>
              <dd className="mt-0.5 text-sm text-gray-900">{connector.description}</dd>
            </div>
          )}
        </dl>
      )}

      {/* Trigger Sync */}
      {activeTab === "sync" && (
        <div className="space-y-4 max-w-lg">
          <div className="rounded-lg border border-gray-200 bg-white p-6 space-y-4">
            <h2 className="text-base font-semibold text-gray-900">Manual Sync Trigger</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Direction</label>
              <select
                value={syncDirection}
                onChange={(e) => setSyncDirection(e.target.value as SyncDirection)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="INBOUND">Inbound (ERP → EIOS)</option>
                <option value="OUTBOUND">Outbound (EIOS → ERP)</option>
              </select>
            </div>
            {syncDirection === "INBOUND" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Entity Type</label>
                <select
                  value={syncEntityType}
                  onChange={(e) => setSyncEntityType(e.target.value as EntityType)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="Material">Material</option>
                  <option value="BOM">BOM</option>
                </select>
              </div>
            )}
            {connector.adapter_type === "CSV" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  CSV Data (paste content)
                </label>
                <textarea
                  value={csvContent}
                  onChange={(e) => setCsvContent(e.target.value)}
                  rows={6}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="MATNR;MAKTX;MTART&#10;MAT001;Lithium;ROH&#10;..."
                />
              </div>
            )}
            <button
              onClick={handleSync}
              disabled={syncing || connector.connector_status !== "ACTIVE"}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {syncing ? "Running sync…" : "Run Sync"}
            </button>
          </div>
        </div>
      )}

      {/* Field Mappings */}
      {activeTab === "mappings" && (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Entity</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">ERP Field</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">EIOS Field</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Transform</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Required</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {mappings.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                    No field mappings configured yet.
                  </td>
                </tr>
              ) : (
                mappings.map((m) => (
                  <tr key={m.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-700">{m.entity_type}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-700">{m.erp_field}</td>
                    <td className="px-4 py-3 font-mono text-xs text-blue-700">{m.eios_field}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{m.transform_fn ?? "—"}</td>
                    <td className="px-4 py-3 text-center">
                      {m.is_required === "True" ? (
                        <span className="text-red-600 font-medium">{t("common.yes")}</span>
                      ) : (
                        <span className="text-gray-400">{t("common.no")}</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Sync Jobs */}
      {activeTab === "jobs" && (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Direction</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Entity</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">{t("common.status")}</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Fetched</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Created</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Updated</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Failed</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Duration</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Started</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-6 text-center text-gray-400">
                    No sync jobs yet. Trigger your first sync above.
                  </td>
                </tr>
              ) : (
                jobs.map((j) => (
                  <tr key={j.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium ${j.direction === "INBOUND" ? "text-blue-700" : "text-purple-700"}`}>
                        {j.direction}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-700">{j.entity_type}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          JOB_STATUS_COLORS[j.job_status] ?? "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {j.job_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-gray-700">{j.records_fetched}</td>
                    <td className="px-4 py-3 text-center text-green-700">{j.records_created}</td>
                    <td className="px-4 py-3 text-center text-blue-700">{j.records_updated}</td>
                    <td className="px-4 py-3 text-center">
                      {j.records_failed > 0 ? (
                        <span className="text-red-600 font-medium">{j.records_failed}</span>
                      ) : (
                        <span className="text-gray-400">0</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {j.runtime_seconds ? `${j.runtime_seconds}s` : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {j.started_at ? new Date(j.started_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
