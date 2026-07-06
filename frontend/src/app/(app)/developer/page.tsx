"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import { formatDateTime } from "@/lib/utils";
import {
  Key,
  Webhook,
  Code2,
  ExternalLink,
  Copy,
  Check,
  Plus,
  Trash2,
  ToggleLeft,
  ToggleRight,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  Clock,
  XCircle,
} from "lucide-react";
import {
  listApiKeys,
  createApiKey,
  revokeApiKey,
  listWebhooks,
  createWebhook,
  updateWebhook,
  deleteWebhook,
  listWebhookDeliveries,
} from "@/lib/api/platform";
import {
  API_SCOPES,
  WEBHOOK_EVENT_TYPES,
  type ApiKeyResponse,
  type ApiKeyCreatedResponse,
  type WebhookResponse,
  type WebhookDeliveryResponse,
} from "@/types/api";

// ── Helpers ───────────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const { t } = useLanguage();
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="rounded p-1 hover:bg-slate-100 transition-colors text-slate-500"
      title={t("common.copy")}
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

function SectionHeader({ icon: Icon, title, description }: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <div className="rounded-xl bg-slate-100 dark:bg-slate-800 p-2">
        <Icon className="h-5 w-5 text-slate-600 dark:text-slate-300" />
      </div>
      <div>
        <h2 className="text-base font-semibold text-gray-900 dark:text-white">{title}</h2>
        <p className="text-xs text-gray-500 dark:text-gray-400">{description}</p>
      </div>
    </div>
  );
}

// ── API Keys ──────────────────────────────────────────────────────────────────

function NewKeyBanner({ created }: { created: ApiKeyCreatedResponse; onDismiss: () => void }) {
  const { t } = useLanguage();
  return (
    <div className="rounded-xl border-2 border-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 p-4 space-y-2">
      <p className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">
        {t("dev.apiKeyCreated")}
      </p>
      <div className="flex items-center gap-2 rounded-lg bg-white dark:bg-gray-900 border border-emerald-200 px-3 py-2 font-mono text-sm">
        <span className="flex-1 break-all">{created.raw_key}</span>
        <CopyButton text={created.raw_key} />
      </div>
      <p className="text-xs text-emerald-700 dark:text-emerald-400">
        {t("dev.apiKeySaveHint")}
      </p>
    </div>
  );
}

function ApiKeysSection() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newKey, setNewKey] = useState<ApiKeyCreatedResponse | null>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
    scopes: [] as string[],
    rate_limit_per_minute: 60,
    rate_limit_per_hour: 1000,
  });

  const { data: keys = [], isLoading } = useQuery({
    queryKey: ["platform-api-keys"],
    queryFn: listApiKeys,
  });

  const createMutation = useMutation({
    mutationFn: () => createApiKey({ ...form, scopes: form.scopes }),
    onSuccess: (created) => {
      qc.invalidateQueries({ queryKey: ["platform-api-keys"] });
      setNewKey(created);
      setShowCreate(false);
      setForm({ name: "", description: "", scopes: [], rate_limit_per_minute: 60, rate_limit_per_hour: 1000 });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => revokeApiKey(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform-api-keys"] }),
  });

  function toggleScope(scope: string) {
    setForm((f) => ({
      ...f,
      scopes: f.scopes.includes(scope) ? f.scopes.filter((s) => s !== scope) : [...f.scopes, scope],
    }));
  }

  return (
    <div className="space-y-4">
      <SectionHeader
        icon={Key}
        title={t("dev.apiKeysTitle")}
        description={t("dev.apiKeysDesc")}
      />

      {newKey && (
        <NewKeyBanner created={newKey} onDismiss={() => setNewKey(null)} />
      )}

      {isLoading ? (
        <p className="text-sm text-gray-400">{t("common.loading")}</p>
      ) : keys.length === 0 ? (
        <p className="text-sm text-gray-400">{t("dev.noApiKeys")}</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3 text-left">{t("common.name")}</th>
                <th className="px-4 py-3 text-left">{t("dev.colPrefix")}</th>
                <th className="px-4 py-3 text-left">{t("dev.scopesLabel")}</th>
                <th className="px-4 py-3 text-center">{t("dev.colRequests")}</th>
                <th className="px-4 py-3 text-center">{t("dev.colLimits")}</th>
                <th className="px-4 py-3 text-center">{t("common.status")}</th>
                <th className="px-4 py-3 text-center">{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {keys.map((k: ApiKeyResponse) => (
                <tr key={k.id} className="bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="px-4 py-2.5 font-medium text-gray-800 dark:text-gray-200">
                    {k.name}
                    {k.description && (
                      <p className="text-[10px] text-gray-400 font-normal">{k.description}</p>
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-gray-500">{k.key_prefix}***</td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-wrap gap-1">
                      {k.scopes.map((s) => (
                        <span key={s} className="rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 px-1.5 py-0.5 text-[10px] font-medium">
                          {s}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-center text-xs text-gray-500">{k.requests_total.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-center text-[10px] text-gray-400">
                    {k.rate_limit_per_minute}/min · {k.rate_limit_per_hour}/h
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${k.is_active ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-600"}`}>
                      {k.is_active ? t("common.active") : t("dev.statusRevoked")}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    {k.is_active && (
                      <button
                        onClick={() => {
                          if (confirm(t("dev.revokeApiKeyConfirm").replace("{name}", k.name))) {
                            revokeMutation.mutate(k.id);
                          }
                        }}
                        className="text-red-500 hover:text-red-700 text-xs font-medium"
                      >
                        {t("dev.revoke")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate ? (
        <div className="rounded-xl border border-border bg-slate-50/60 p-4 space-y-3">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{t("dev.newApiKey")}</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-muted-foreground">{t("common.name")} *</label>
              <input
                className="h-8 w-full rounded-md border border-input bg-white px-2 text-xs"
                placeholder={t("dev.namePlaceholder")}
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-muted-foreground">{t("common.description")}</label>
              <input
                className="h-8 w-full rounded-md border border-input bg-white px-2 text-xs"
                placeholder={t("common.optional")}
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-medium text-muted-foreground">{t("dev.scopesLabel")}</label>
            <div className="flex flex-wrap gap-2">
              {API_SCOPES.map((scope) => (
                <label key={scope} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.scopes.includes(scope)}
                    onChange={() => toggleScope(scope)}
                    className="h-3.5 w-3.5 rounded"
                  />
                  <span className="text-xs text-gray-600 dark:text-gray-300">{scope}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-muted-foreground">{t("dev.rateLimitMin")}</label>
              <input
                type="number"
                className="h-8 w-full rounded-md border border-input bg-white px-2 text-xs"
                value={form.rate_limit_per_minute}
                onChange={(e) => setForm((f) => ({ ...f, rate_limit_per_minute: Number(e.target.value) }))}
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-muted-foreground">{t("dev.rateLimitHour")}</label>
              <input
                type="number"
                className="h-8 w-full rounded-md border border-input bg-white px-2 text-xs"
                value={form.rate_limit_per_hour}
                onChange={(e) => setForm((f) => ({ ...f, rate_limit_per_hour: Number(e.target.value) }))}
              />
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !form.name.trim() || form.scopes.length === 0}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
            >
              {createMutation.isPending ? t("dev.creating") : t("dev.createKey")}
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="rounded-lg border border-input px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100"
            >
              {t("common.cancel")}
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => { setShowCreate(true); setNewKey(null); }}
          className="flex items-center gap-2 rounded-lg border border-dashed border-gray-300 px-4 py-2 text-xs text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-colors"
        >
          <Plus className="h-3.5 w-3.5" /> {t("dev.newApiKeyBtn")}
        </button>
      )}
    </div>
  );
}

// ── Webhook Deliveries ────────────────────────────────────────────────────────

const STATUS_ICON: Record<string, React.ElementType> = {
  delivered:  CheckCircle2,
  pending:    Clock,
  failed:     XCircle,
  retrying:   Clock,
};
const STATUS_COLOR: Record<string, string> = {
  delivered: "text-emerald-500",
  pending:   "text-amber-500",
  failed:    "text-red-500",
  retrying:  "text-blue-500",
};

function DeliveryLogs({ webhookId }: { webhookId: string }) {
  const { t } = useLanguage();
  const { data: deliveries = [], isLoading } = useQuery({
    queryKey: ["webhook-deliveries", webhookId],
    queryFn: () => listWebhookDeliveries(webhookId, 30),
    staleTime: 30_000,
  });

  if (isLoading) return <p className="text-xs text-gray-400 py-2">{t("dev.loadingDeliveries")}</p>;
  if (deliveries.length === 0) return <p className="text-xs text-gray-400 py-2">{t("dev.noDeliveries")}</p>;

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-100 dark:border-gray-700 mt-2">
      <table className="w-full text-xs">
        <thead className="bg-gray-50 dark:bg-gray-800 text-[10px] uppercase text-gray-400">
          <tr>
            <th className="px-3 py-2 text-left">Event</th>
            <th className="px-3 py-2 text-center">Status</th>
            <th className="px-3 py-2 text-center">HTTP</th>
            <th className="px-3 py-2 text-center">ms</th>
            <th className="px-3 py-2 text-center">Retries</th>
            <th className="px-3 py-2 text-left">{t("dev.colTimestamp")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
          {deliveries.map((d: WebhookDeliveryResponse) => {
            const Icon = STATUS_ICON[d.delivery_status] ?? Clock;
            const color = STATUS_COLOR[d.delivery_status] ?? "text-gray-400";
            return (
              <tr key={d.id} className="bg-white dark:bg-gray-900">
                <td className="px-3 py-1.5 font-mono text-[10px] text-gray-600 dark:text-gray-300">{d.event_type}</td>
                <td className="px-3 py-1.5 text-center">
                  <Icon className={`h-3.5 w-3.5 mx-auto ${color}`} />
                </td>
                <td className="px-3 py-1.5 text-center text-[10px] text-gray-500">{d.response_code ?? "—"}</td>
                <td className="px-3 py-1.5 text-center text-[10px] text-gray-400">{d.duration_ms != null ? d.duration_ms.toFixed(0) : "—"}</td>
                <td className="px-3 py-1.5 text-center text-[10px] text-gray-400">{d.retry_count}</td>
                <td className="px-3 py-1.5 text-[10px] text-gray-400">
                  {formatDateTime(d.delivered_at ?? d.created_at)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Webhooks ──────────────────────────────────────────────────────────────────

function WebhooksSection() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    target_url: "",
    events: [] as string[],
    secret: "",
  });

  const { data: hooks = [], isLoading } = useQuery({
    queryKey: ["platform-webhooks"],
    queryFn: listWebhooks,
  });

  const createMutation = useMutation({
    mutationFn: () => createWebhook(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["platform-webhooks"] });
      setShowCreate(false);
      setForm({ name: "", target_url: "", events: [], secret: "" });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      updateWebhook(id, { is_active: active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform-webhooks"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteWebhook(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform-webhooks"] }),
  });

  function toggleEvent(ev: string) {
    setForm((f) => ({
      ...f,
      events: f.events.includes(ev) ? f.events.filter((e) => e !== ev) : [...f.events, ev],
    }));
  }

  return (
    <div className="space-y-4">
      <SectionHeader
        icon={Webhook}
        title={t("dev.webhooksTitle")}
        description={t("dev.webhooksDesc")}
      />

      {isLoading ? (
        <p className="text-sm text-gray-400">{t("common.loading")}</p>
      ) : hooks.length === 0 ? (
        <p className="text-sm text-gray-400">{t("dev.noWebhooks")}</p>
      ) : (
        <div className="space-y-2">
          {hooks.map((h: WebhookResponse) => (
            <div key={h.id} className="rounded-xl border border-border bg-white dark:bg-gray-900">
              <div className="flex items-center gap-3 px-4 py-3">
                <button
                  onClick={() => setExpandedId(expandedId === h.id ? null : h.id)}
                  className="text-gray-400 hover:text-gray-600 flex-shrink-0"
                >
                  {expandedId === h.id
                    ? <ChevronDown className="h-4 w-4" />
                    : <ChevronRight className="h-4 w-4" />}
                </button>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{h.name}</p>
                  <p className="text-[10px] font-mono text-gray-400 truncate">{h.target_url}</p>
                </div>
                <div className="flex flex-wrap gap-1 max-w-xs">
                  {h.events.slice(0, 3).map((ev) => (
                    <span key={ev} className="rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 px-1.5 py-0.5 text-[10px]">
                      {ev}
                    </span>
                  ))}
                  {h.events.length > 3 && (
                    <span className="text-[10px] text-gray-400">+{h.events.length - 3}</span>
                  )}
                </div>
                {h.failure_count > 0 && (
                  <span className="flex items-center gap-1 text-[10px] text-amber-600">
                    <AlertTriangle className="h-3 w-3" />
                    {t("dev.failureCount").replace("{n}", String(h.failure_count))}
                  </span>
                )}
                <button
                  onClick={() => toggleMutation.mutate({ id: h.id, active: !h.is_active })}
                  className={h.is_active ? "text-emerald-500 hover:text-emerald-700" : "text-gray-400 hover:text-gray-600"}
                  title={h.is_active ? t("common.deactivate") : t("common.activate")}
                >
                  {h.is_active ? <ToggleRight className="h-5 w-5" /> : <ToggleLeft className="h-5 w-5" />}
                </button>
                <button
                  onClick={() => {
                    if (confirm(t("dev.deleteWebhookConfirm").replace("{name}", h.name))) {
                      deleteMutation.mutate(h.id);
                    }
                  }}
                  className="text-red-400 hover:text-red-600"
                  title={t("common.delete")}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              {expandedId === h.id && (
                <div className="border-t border-border px-4 py-3">
                  <DeliveryLogs webhookId={h.id} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showCreate ? (
        <div className="rounded-xl border border-border bg-slate-50/60 p-4 space-y-3">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{t("dev.newWebhook")}</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-muted-foreground">{t("common.name")} *</label>
              <input
                className="h-8 w-full rounded-md border border-input bg-white px-2 text-xs"
                placeholder={t("dev.webhookNamePlaceholder")}
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-muted-foreground">{t("dev.targetUrl")}</label>
              <input
                className="h-8 w-full rounded-md border border-input bg-white px-2 text-xs"
                placeholder="https://your-erp.example.com/eios-hook"
                value={form.target_url}
                onChange={(e) => setForm((f) => ({ ...f, target_url: e.target.value }))}
              />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-[10px] font-medium text-muted-foreground">{t("dev.secret")}</label>
            <input
              className="h-8 w-full rounded-md border border-input bg-white px-2 text-xs font-mono"
              placeholder={t("dev.secretPlaceholder")}
              value={form.secret}
              onChange={(e) => setForm((f) => ({ ...f, secret: e.target.value }))}
            />
          </div>
          <div className="space-y-1">
            <label className="text-[10px] font-medium text-muted-foreground">{t("dev.eventsLabel")}</label>
            <div className="flex flex-wrap gap-2">
              {WEBHOOK_EVENT_TYPES.map((ev) => (
                <label key={ev} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.events.includes(ev)}
                    onChange={() => toggleEvent(ev)}
                    className="h-3.5 w-3.5 rounded"
                  />
                  <span className="text-xs text-gray-600 dark:text-gray-300">{ev}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !form.name.trim() || !form.target_url.trim() || form.events.length === 0}
              className="rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-purple-700 disabled:opacity-60"
            >
              {createMutation.isPending ? t("dev.creating") : t("dev.createWebhook")}
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="rounded-lg border border-input px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100"
            >
              {t("common.cancel")}
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg border border-dashed border-gray-300 px-4 py-2 text-xs text-gray-500 hover:border-purple-400 hover:text-purple-600 transition-colors"
        >
          <Plus className="h-3.5 w-3.5" /> {t("dev.newWebhookBtn")}
        </button>
      )}
    </div>
  );
}

// ── SDK Snippets ──────────────────────────────────────────────────────────────

const SNIPPET_PYTHON = `import httpx

API_BASE = "https://your-eios.example.com/api/v1"
API_KEY  = "eios_live_..."   # replace with your key

headers = {"X-Api-Key": API_KEY}

# List suppliers
r = httpx.get(f"{API_BASE}/suppliers", headers=headers)
suppliers = r.json()

# Create finding
finding = {
    "title": "Missing SMETA Audit",
    "severity": "High",
    "assessment_id": "<uuid>"
}
r = httpx.post(f"{API_BASE}/findings", json=finding, headers=headers)
print(r.json())`;

const SNIPPET_CURL = `# Set your credentials
export API_BASE="https://your-eios.example.com/api/v1"
export API_KEY="eios_live_..."

# List assessments
curl -s -H "X-Api-Key: $API_KEY" \\
  "$API_BASE/assessments" | jq .

# Get a single supplier
curl -s -H "X-Api-Key: $API_KEY" \\
  "$API_BASE/suppliers/{supplier_id}" | jq .

# Create a risk
curl -s -X POST \\
  -H "X-Api-Key: $API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"title":"Labour Rights Gap","severity":"High","assessment_id":"<uuid>"}' \\
  "$API_BASE/risks"`;

const SNIPPET_JS = `const API_BASE = "https://your-eios.example.com/api/v1";
const API_KEY  = "eios_live_..."; // replace with your key

const headers = { "X-Api-Key": API_KEY };

// List suppliers
const res  = await fetch(\`\${API_BASE}/suppliers\`, { headers });
const data = await res.json();

// Create recommendation
const rec = await fetch(\`\${API_BASE}/recommendations\`, {
  method: "POST",
  headers: { ...headers, "Content-Type": "application/json" },
  body: JSON.stringify({
    title: "Conduct SMETA Audit Q3",
    finding_id: "<uuid>",
    due_date:   "2026-09-30",
  }),
});
console.log(await rec.json());`;

type SnippetTab = "python" | "curl" | "javascript";

function SdkSnippetsSection() {
  const { t } = useLanguage();
  const [tab, setTab] = useState<SnippetTab>("python");
  const snippets: Record<SnippetTab, string> = {
    python: SNIPPET_PYTHON,
    curl: SNIPPET_CURL,
    javascript: SNIPPET_JS,
  };

  return (
    <div className="space-y-4">
      <SectionHeader
        icon={Code2}
        title={t("dev.sdkTitle")}
        description={t("dev.sdkDesc")}
      />

      <div className="rounded-xl border border-border overflow-hidden">
        <div className="flex border-b border-border bg-slate-50 dark:bg-gray-800">
          {(["python", "curl", "javascript"] as SnippetTab[]).map((sn) => (
            <button
              key={sn}
              onClick={() => setTab(sn)}
              className={`px-4 py-2 text-xs font-semibold capitalize transition-colors ${
                tab === sn
                  ? "bg-white dark:bg-gray-900 border-b-2 border-blue-500 text-blue-600"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {sn}
            </button>
          ))}
          <div className="ml-auto flex items-center pr-3">
            <CopyButton text={snippets[tab]} />
          </div>
        </div>
        <pre className="overflow-x-auto p-4 text-xs bg-gray-950 text-gray-200 leading-relaxed">
          <code>{snippets[tab]}</code>
        </pre>
      </div>

      <div className="rounded-xl border border-dashed border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/10 p-4 flex items-start gap-3">
        <ExternalLink className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-sm font-semibold text-blue-800 dark:text-blue-300">{t("dev.apiRefTitle")}</p>
          <p className="text-xs text-blue-600 dark:text-blue-400 mt-0.5">
            {t("dev.apiRefBefore")}{" "}
            <a
              href="/api/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="underline font-medium"
            >
              /api/docs
            </a>{" "}
            {t("dev.apiRefAfter")}
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Webhook Signature Verification Snippet ────────────────────────────────────

const SIGNATURE_SNIPPET = `import hashlib, hmac, json

def verify_eios_signature(payload: bytes, secret: str, signature: str) -> bool:
    expected = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

# In your webhook handler:
# sig = request.headers.get("X-EIOS-Signature")
# valid = verify_eios_signature(request.body, YOUR_SECRET, sig)`;

function SignatureSection() {
  const { t } = useLanguage();
  return (
    <div className="space-y-4">
      <SectionHeader
        icon={Key}
        title={t("dev.signatureTitle")}
        description={t("dev.signatureDesc")}
      />
      <div className="rounded-xl border border-border overflow-hidden">
        <div className="flex justify-between items-center border-b border-border bg-slate-50 dark:bg-gray-800 px-4 py-2">
          <span className="text-xs font-semibold text-gray-500">{t("dev.signatureLabel")}</span>
          <CopyButton text={SIGNATURE_SNIPPET} />
        </div>
        <pre className="overflow-x-auto p-4 text-xs bg-gray-950 text-gray-200 leading-relaxed">
          <code>{SIGNATURE_SNIPPET}</code>
        </pre>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DeveloperPortalPage() {
  const { t } = useLanguage();
  return (
    <div className="space-y-10">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-slate-800 p-2.5">
          <Code2 className="h-6 w-6 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">{t("nav.developer")}</h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {t("dev.subtitle")}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-10">
        <section className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
          <ApiKeysSection />
        </section>

        <section className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
          <WebhooksSection />
        </section>

        <section className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
          <SdkSnippetsSection />
        </section>

        <section className="rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
          <SignatureSection />
        </section>
      </div>
    </div>
  );
}
