"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Copy,
  Eye,
  EyeOff,
  KeyRound,
  Plus,
  RotateCcw,
  Trash2,
  Webhook,
  X,
  CheckCircle,
  AlertCircle,
  Clock,
} from "lucide-react";
import {
  createApiKey,
  createServiceAccount,
  createWebhook,
  deactivateServiceAccount,
  deleteWebhook,
  listApiKeys,
  listAllDeliveries,
  listServiceAccounts,
  listWebhooks,
  revokeApiKey,
} from "@/lib/api/platform";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import type {
  ApiKeyCreate,
  ApiKeyCreatedResponse,
  ServiceAccountCreate,
  WebhookCreate,
} from "@/types/api";
import { API_SCOPES, WEBHOOK_EVENT_TYPES } from "@/types/api";

// ── Tabs ──────────────────────────────────────────────────────────────────────

type Tab = "api-keys" | "service-accounts" | "webhooks" | "delivery-logs";

const TABS: { id: Tab; labelKey: string }[] = [
  { id: "api-keys", labelKey: "api.tabApiKeys" },
  { id: "service-accounts", labelKey: "api.tabServiceAccounts" },
  { id: "webhooks", labelKey: "api.tabWebhooks" },
  { id: "delivery-logs", labelKey: "api.tabDeliveryLogs" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function StatusBadge({ active, label }: { active: boolean; label?: string }) {
  const { t } = useLanguage();
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
        active
          ? "bg-green-100 text-green-700"
          : "bg-slate-100 text-slate-500"
      }`}
    >
      {label ?? (active ? t("api.keyActive") : t("api.keyRevoked"))}
    </span>
  );
}

function DeliveryStatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { icon: typeof CheckCircle; color: string }> = {
    delivered: { icon: CheckCircle, color: "text-green-600" },
    failed: { icon: AlertCircle, color: "text-red-500" },
    dead_letter: { icon: X, color: "text-red-700" },
    pending: { icon: Clock, color: "text-yellow-500" },
  };
  const { icon: Icon, color } = cfg[status] ?? { icon: Clock, color: "text-slate-400" };
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium ${color}`}>
      <Icon className="h-3 w-3" />
      {status}
    </span>
  );
}

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button onClick={copy} className="text-slate-400 hover:text-slate-600" title="Copy">
      {copied ? <CheckCircle className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
    </button>
  );
}

// ── Create API Key Modal ──────────────────────────────────────────────────────

function CreateApiKeyModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (data: ApiKeyCreate) => void;
}) {
  const { t } = useLanguage();
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<string[]>([]);
  const toggleScope = (s: string) =>
    setScopes((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">{t("sec.createKey")}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">{t("common.name")}</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. CI Pipeline Key"
              className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-2 block text-xs font-medium text-slate-700">{t("api.scopes")}</label>
            <div className="grid grid-cols-2 gap-2">
              {API_SCOPES.map((scope) => (
                <label key={scope} className="flex items-center gap-2 text-xs text-slate-700">
                  <input
                    type="checkbox"
                    checked={scopes.includes(scope)}
                    onChange={() => toggleScope(scope)}
                    className="rounded border-slate-300"
                  />
                  {scope}
                </label>
              ))}
            </div>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded px-4 py-2 text-sm text-slate-600 hover:bg-slate-100"
          >
            {t("common.cancel")}
          </button>
          <button
            onClick={() => onCreate({ name, scopes })}
            disabled={!name || scopes.length === 0}
            className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {t("common.create")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Created Key Banner ─────────────────────────────────────────────────────────

function CreatedKeyBanner({
  result,
  onDismiss,
}: {
  result: ApiKeyCreatedResponse;
  onDismiss: () => void;
}) {
  const { t } = useLanguage();
  const [show, setShow] = useState(false);
  return (
    <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-4">
      <div className="mb-1 flex items-center justify-between">
        <p className="text-sm font-semibold text-green-800">{t("api.keyCreated")}</p>
        <button onClick={onDismiss} className="text-green-600 hover:text-green-800">
          <X className="h-4 w-4" />
        </button>
      </div>
      <p className="mb-2 text-xs text-green-700">
        {t("api.keyNeverShown")}
      </p>
      <div className="flex items-center gap-2 rounded border border-green-200 bg-white px-3 py-2 font-mono text-xs">
        <span className="flex-1 truncate">
          {show ? result.raw_key : "eios_••••••••••••••••••••••••••••••••••••••"}
        </span>
        <button onClick={() => setShow((v) => !v)} className="text-slate-400 hover:text-slate-600">
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
        <CopyButton value={result.raw_key} />
      </div>
    </div>
  );
}

// ── Create Webhook Modal ──────────────────────────────────────────────────────

function CreateWebhookModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (data: WebhookCreate) => void;
}) {
  const { t } = useLanguage();
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [events, setEvents] = useState<string[]>([]);
  const toggleEvent = (e: string) =>
    setEvents((prev) => (prev.includes(e) ? prev.filter((x) => x !== e) : [...prev, e]));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">{t("api.createWebhook")}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">{t("common.name")}</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Slack Alerts"
              className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">{t("api.targetUrl")}</label>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://your-service.com/webhook"
              className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              {t("api.signingSecret")}
            </label>
            <input
              type="password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="Your HMAC signing secret"
              className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-2 block text-xs font-medium text-slate-700">{t("api.events")}</label>
            <div className="grid grid-cols-2 gap-1">
              {WEBHOOK_EVENT_TYPES.map((ev) => (
                <label key={ev} className="flex items-center gap-2 text-xs text-slate-700">
                  <input
                    type="checkbox"
                    checked={events.includes(ev)}
                    onChange={() => toggleEvent(ev)}
                    className="rounded border-slate-300"
                  />
                  {ev}
                </label>
              ))}
            </div>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded px-4 py-2 text-sm text-slate-600 hover:bg-slate-100"
          >
            {t("common.cancel")}
          </button>
          <button
            onClick={() => onCreate({ name, target_url: url, events, secret })}
            disabled={!name || !url || !secret || secret.length < 16 || events.length === 0}
            className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {t("common.create")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ApiPlatformPage() {
  const { user } = useAuth();
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("api-keys");
  const [showCreateKey, setShowCreateKey] = useState(false);
  const [showCreateSA, setShowCreateSA] = useState(false);
  const [showCreateHook, setShowCreateHook] = useState(false);
  const [createdKey, setCreatedKey] = useState<ApiKeyCreatedResponse | null>(null);
  const [saName, setSaName] = useState("");

  const { data: apiKeys = [] } = useQuery({
    queryKey: ["api-keys"],
    queryFn: listApiKeys,
    enabled: tab === "api-keys",
  });
  const { data: serviceAccounts = [] } = useQuery({
    queryKey: ["service-accounts"],
    queryFn: listServiceAccounts,
    enabled: tab === "service-accounts",
  });
  const { data: webhooks = [] } = useQuery({
    queryKey: ["webhooks"],
    queryFn: listWebhooks,
    enabled: tab === "webhooks",
  });
  const { data: deliveries = [] } = useQuery({
    queryKey: ["deliveries"],
    queryFn: () => listAllDeliveries(100),
    enabled: tab === "delivery-logs",
  });

  const createKeyMut = useMutation({
    mutationFn: createApiKey,
    onSuccess: (data) => {
      setCreatedKey(data);
      setShowCreateKey(false);
      qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  const revokeKeyMut = useMutation({
    mutationFn: revokeApiKey,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });

  const createSAMut = useMutation({
    mutationFn: createServiceAccount,
    onSuccess: () => {
      setShowCreateSA(false);
      setSaName("");
      qc.invalidateQueries({ queryKey: ["service-accounts"] });
    },
  });

  const deactivateSAMut = useMutation({
    mutationFn: deactivateServiceAccount,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["service-accounts"] }),
  });

  const createWebhookMut = useMutation({
    mutationFn: createWebhook,
    onSuccess: () => {
      setShowCreateHook(false);
      qc.invalidateQueries({ queryKey: ["webhooks"] });
    },
  });

  const deleteWebhookMut = useMutation({
    mutationFn: deleteWebhook,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["webhooks"] }),
  });

  if (user?.role !== "admin") {
    return (
      <div className="p-8 text-center text-slate-500">
        {t("settings.adminOnly")}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">{t("sec.apiTitle")}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {t("sec.apiSubtitle")}
        </p>
      </div>

      {/* Tab bar */}
      <div className="mb-6 flex gap-1 border-b border-slate-200">
        {TABS.map((tab_) => (
          <button
            key={tab_.id}
            onClick={() => setTab(tab_.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              tab === tab_.id
                ? "border-b-2 border-blue-600 text-blue-700"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {t(tab_.labelKey as any)}
          </button>
        ))}
      </div>

      {/* ── API Keys ── */}
      {tab === "api-keys" && (
        <div>
          {createdKey && (
            <CreatedKeyBanner result={createdKey} onDismiss={() => setCreatedKey(null)} />
          )}
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-slate-600">
              {t("api.apiKeysDesc")}
            </p>
            <button
              onClick={() => setShowCreateKey(true)}
              className="inline-flex items-center gap-2 rounded bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              {t("sec.createKey")}
            </button>
          </div>
          <div className="overflow-hidden rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs font-medium text-slate-500">
                <tr>
                  <th className="px-4 py-3 text-left">{t("common.name")}</th>
                  <th className="px-4 py-3 text-left">{t("sec.keyPrefix")}</th>
                  <th className="px-4 py-3 text-left">{t("api.scopes")}</th>
                  <th className="px-4 py-3 text-left">{t("api.requests")}</th>
                  <th className="px-4 py-3 text-left">{t("common.status")}</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {apiKeys.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                      {t("sec.noKeys")}
                    </td>
                  </tr>
                )}
                {apiKeys.map((k) => (
                  <tr key={k.id} className={k.is_active ? "" : "opacity-50"}>
                    <td className="px-4 py-3 font-medium text-slate-800">{k.name}</td>
                    <td className="px-4 py-3 font-mono text-slate-500">{k.key_prefix}***</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {k.scopes.slice(0, 3).map((s) => (
                          <span
                            key={s}
                            className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600"
                          >
                            {s}
                          </span>
                        ))}
                        {k.scopes.length > 3 && (
                          <span className="text-xs text-slate-400">
                            {t("api.moreScopes").replace("{n}", String(k.scopes.length - 3))}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {k.requests_total.toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge active={k.is_active} />
                    </td>
                    <td className="px-4 py-3">
                      {k.is_active && (
                        <button
                          onClick={() => revokeKeyMut.mutate(k.id)}
                          className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700"
                        >
                          <RotateCcw className="h-3 w-3" />
                          {t("sec.revokeKey")}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Service Accounts ── */}
      {tab === "service-accounts" && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-slate-600">
              {t("api.serviceAccountsDesc")}
            </p>
            <button
              onClick={() => setShowCreateSA(true)}
              className="inline-flex items-center gap-2 rounded bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              {t("api.newServiceAccount")}
            </button>
          </div>
          <div className="overflow-hidden rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs font-medium text-slate-500">
                <tr>
                  <th className="px-4 py-3 text-left">{t("common.name")}</th>
                  <th className="px-4 py-3 text-left">{t("common.description")}</th>
                  <th className="px-4 py-3 text-left">{t("common.status")}</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {serviceAccounts.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-6 text-center text-slate-400">
                      {t("api.noServiceAccounts")}
                    </td>
                  </tr>
                )}
                {serviceAccounts.map((sa) => (
                  <tr key={sa.id} className={sa.is_active ? "" : "opacity-50"}>
                    <td className="px-4 py-3 font-medium text-slate-800">{sa.name}</td>
                    <td className="px-4 py-3 text-slate-500">{sa.description || "—"}</td>
                    <td className="px-4 py-3">
                      <StatusBadge active={sa.is_active} label={sa.is_active ? t("common.active") : t("common.inactive")} />
                    </td>
                    <td className="px-4 py-3">
                      {sa.is_active && (
                        <button
                          onClick={() => deactivateSAMut.mutate(sa.id)}
                          className="text-xs text-red-500 hover:text-red-700"
                        >
                          {t("users.deactivate")}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Webhooks ── */}
      {tab === "webhooks" && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-slate-600">
              {t("api.webhooksDesc")}
            </p>
            <button
              onClick={() => setShowCreateHook(true)}
              className="inline-flex items-center gap-2 rounded bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              {t("api.newWebhook")}
            </button>
          </div>
          <div className="space-y-3">
            {webhooks.length === 0 && (
              <div className="rounded-lg border border-slate-200 px-4 py-8 text-center text-slate-400">
                {t("common.noData")}
              </div>
            )}
            {webhooks.map((wh) => (
              <div
                key={wh.id}
                className="rounded-lg border border-slate-200 bg-white p-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <Webhook className="h-4 w-4 text-slate-400" />
                      <span className="font-medium text-slate-800">{wh.name}</span>
                      <StatusBadge active={wh.is_active} />
                    </div>
                    <p className="mt-1 truncate font-mono text-xs text-slate-500">
                      {wh.target_url}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {wh.events.map((ev) => (
                        <span
                          key={ev}
                          className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-700"
                        >
                          {ev}
                        </span>
                      ))}
                    </div>
                    {wh.failure_count > 0 && (
                      <p className="mt-1 text-xs text-red-500">
                        {t("api.failureCount").replace("{n}", String(wh.failure_count))}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => deleteWebhookMut.mutate(wh.id)}
                    className="flex-shrink-0 text-red-400 hover:text-red-600"
                    title="Delete webhook"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Delivery Logs ── */}
      {tab === "delivery-logs" && (
        <div>
          <p className="mb-4 text-sm text-slate-600">
            {t("api.deliveryLogsDesc")}
          </p>
          <div className="overflow-hidden rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs font-medium text-slate-500">
                <tr>
                  <th className="px-4 py-3 text-left">{t("eventBus.eventType")}</th>
                  <th className="px-4 py-3 text-left">{t("common.status")}</th>
                  <th className="px-4 py-3 text-left">{t("api.http")}</th>
                  <th className="px-4 py-3 text-left">{t("api.duration")}</th>
                  <th className="px-4 py-3 text-left">{t("api.retries")}</th>
                  <th className="px-4 py-3 text-left">{t("eventBus.timestamp")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {deliveries.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                      {t("common.noData")}
                    </td>
                  </tr>
                )}
                {deliveries.map((d) => (
                  <tr key={d.id}>
                    <td className="px-4 py-3 font-mono text-xs text-slate-700">
                      {d.event_type}
                    </td>
                    <td className="px-4 py-3">
                      <DeliveryStatusBadge status={d.delivery_status} />
                    </td>
                    <td className="px-4 py-3 text-slate-500">{d.response_code ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-500">
                      {d.duration_ms != null ? `${d.duration_ms}ms` : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-500">{d.retry_count}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {new Date(d.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modals */}
      {showCreateKey && (
        <CreateApiKeyModal
          onClose={() => setShowCreateKey(false)}
          onCreate={(data) => createKeyMut.mutate(data)}
        />
      )}
      {showCreateSA && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-semibold">{t("api.createServiceAccount")}</h2>
              <button
                onClick={() => setShowCreateSA(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <input
              value={saName}
              onChange={(e) => setSaName(e.target.value)}
              placeholder={t("api.serviceAccountPlaceholder")}
              className="w-full rounded border border-slate-200 px-3 py-2 text-sm"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setShowCreateSA(false)}
                className="rounded px-4 py-2 text-sm text-slate-600 hover:bg-slate-100"
              >
                {t("common.cancel")}
              </button>
              <button
                onClick={() => createSAMut.mutate({ name: saName })}
                disabled={!saName}
                className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {t("common.create")}
              </button>
            </div>
          </div>
        </div>
      )}
      {showCreateHook && (
        <CreateWebhookModal
          onClose={() => setShowCreateHook(false)}
          onCreate={(data) => createWebhookMut.mutate(data)}
        />
      )}
    </div>
  );
}
