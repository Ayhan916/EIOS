"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  RefreshCw,
  Trash2,
  Plus,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { formatDateTime } from "@/lib/utils";
import {
  listEnterprises,
  listIdentityProviders,
  listSCIMTokens,
  createSCIMToken,
  revokeSCIMToken,
  rotateSCIMToken,
  getSCIMUsage,
  getSecretsHealth,
  type Enterprise,
  type IdentityProvider,
  type SCIMToken,
  type SCIMTokenCreateResponse,
  type SCIMTokenRotateResponse,
  type SCIMUsageResponse,
  type SecretHealthResponse,
} from "@/lib/api/enterprise";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  return formatDateTime(iso);
}

function ScopeBadge({ scope }: { scope: string }) {
  const map: Record<string, string> = {
    FULL_ADMIN: "bg-red-100 text-red-700",
    PROVISIONING: "bg-blue-100 text-blue-700",
    READ_ONLY: "bg-slate-100 text-slate-600",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${map[scope] ?? "bg-slate-100 text-slate-600"}`}>
      {scope.replace(/_/g, " ")}
    </span>
  );
}

function CopyButton({ value }: { value: string }) {
  const { t } = useLanguage();
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <Button variant="outline" size="sm" className="h-7 gap-1 text-xs" onClick={handleCopy}>
      {copied ? <Check className="h-3 w-3 text-green-600" /> : <Copy className="h-3 w-3" />}
      {copied ? t("sso.tokenCopied") : t("sso.copyToken")}
    </Button>
  );
}

function RawTokenBanner({ rawToken }: { rawToken: string }) {
  const { t } = useLanguage();
  return (
    <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 space-y-2">
      <p className="text-xs font-semibold text-amber-800">{t("sso.rawTokenWarning")}</p>
      <div className="flex items-center gap-2">
        <code className="flex-1 rounded bg-amber-100 px-2 py-1 text-xs font-mono text-amber-900 break-all select-all">
          {rawToken}
        </code>
        <CopyButton value={rawToken} />
      </div>
    </div>
  );
}

// ── SCIM Tokens Tab ───────────────────────────────────────────────────────────

function TokensTab({
  enterpriseId,
  idpMap,
}: {
  enterpriseId: string;
  idpMap: Map<string, string>;
}) {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const [showCreate, setShowCreate] = useState(false);
  const [createLabel, setCreateLabel] = useState("");
  const [createTtl, setCreateTtl] = useState(365);
  const [createIdp, setCreateIdp] = useState("");
  const [createScope, setCreateScope] = useState("FULL_ADMIN");
  const [newRaw, setNewRaw] = useState<string | null>(null);

  const [expandedRotate, setExpandedRotate] = useState<string | null>(null);
  const [rotateLabel, setRotateLabel] = useState("");
  const [rotateTtl, setRotateTtl] = useState(365);
  const [rotatedRaw, setRotatedRaw] = useState<Record<string, string>>({});

  const { data: tokens, isLoading } = useQuery<SCIMToken[]>({
    queryKey: ["scim-tokens", enterpriseId],
    queryFn: () => listSCIMTokens(enterpriseId),
    staleTime: 30_000,
  });

  const create = useMutation({
    mutationFn: () =>
      createSCIMToken(enterpriseId, {
        label: createLabel || undefined,
        ttl_days: createTtl,
        idp_id: createIdp || undefined,
        scope: createScope,
      }),
    onSuccess: (data: SCIMTokenCreateResponse) => {
      qc.invalidateQueries({ queryKey: ["scim-tokens", enterpriseId] });
      setNewRaw(data.raw_token);
      setCreateLabel("");
      setCreateTtl(365);
      setCreateIdp("");
      setCreateScope("FULL_ADMIN");
      setShowCreate(false);
    },
  });

  const revoke = useMutation({
    mutationFn: (tokenId: string) => revokeSCIMToken(enterpriseId, tokenId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scim-tokens", enterpriseId] }),
  });

  const rotate = useMutation({
    mutationFn: (tokenId: string) =>
      rotateSCIMToken(enterpriseId, tokenId, {
        label: rotateLabel || undefined,
        ttl_days: rotateTtl,
      }),
    onSuccess: (data: SCIMTokenRotateResponse) => {
      qc.invalidateQueries({ queryKey: ["scim-tokens", enterpriseId] });
      setRotatedRaw((prev) => ({ ...prev, [data.revoked_token_id]: data.new_token.raw_token }));
      setExpandedRotate(null);
      setRotateLabel("");
      setRotateTtl(365);
    },
  });

  const idpOptions = Array.from(idpMap.entries());

  return (
    <div className="space-y-5">
      {/* Create form */}
      <div className="flex justify-end">
        <Button size="sm" className="gap-1.5" onClick={() => setShowCreate(!showCreate)}>
          <Plus className="h-4 w-4" />
          {t("sso.createToken")}
        </Button>
      </div>

      {showCreate && (
        <Card className="border-blue-200 bg-blue-50/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">{t("sso.createToken")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">{t("sso.tokenLabel")}</Label>
                <Input
                  className="mt-1 text-sm"
                  value={createLabel}
                  onChange={(e) => setCreateLabel(e.target.value)}
                  placeholder={t("sso.tokenLabelPlaceholder")}
                />
              </div>
              <div>
                <Label className="text-xs">{t("sso.tokenTtl")}</Label>
                <Input
                  type="number"
                  min={0}
                  className="mt-1 text-sm"
                  value={createTtl}
                  onChange={(e) => setCreateTtl(Number(e.target.value))}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">{t("sso.tokenScope")}</Label>
                <select
                  className="mt-1 h-9 w-full rounded-md border border-slate-200 bg-white px-2 text-sm"
                  value={createScope}
                  onChange={(e) => setCreateScope(e.target.value)}
                >
                  <option value="FULL_ADMIN">{t("sso.scopeFull")}</option>
                  <option value="PROVISIONING">{t("sso.scopeProv")}</option>
                  <option value="READ_ONLY">{t("sso.scopeRead")}</option>
                </select>
              </div>
              <div>
                <Label className="text-xs">{t("sso.tokenIdp")}</Label>
                <select
                  className="mt-1 h-9 w-full rounded-md border border-slate-200 bg-white px-2 text-sm"
                  value={createIdp}
                  onChange={(e) => setCreateIdp(e.target.value)}
                >
                  <option value="">{t("sso.tokenNone")}</option>
                  {idpOptions.map(([id, name]) => (
                    <option key={id} value={id}>{name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowCreate(false)}>
                {t("common.cancel")}
              </Button>
              <Button size="sm" disabled={create.isPending} onClick={() => create.mutate()} className="gap-1">
                {create.isPending && <Spinner className="h-4 w-4" />}
                {t("sso.createToken")}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* New token raw banner */}
      {newRaw && <RawTokenBanner rawToken={newRaw} />}

      {/* Token list */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : !tokens || tokens.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-16 text-center">
            <p className="font-medium text-slate-600">{t("sso.noTokens")}</p>
            <p className="mt-1 text-sm text-slate-400">{t("sso.noTokensDesc")}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {tokens.map((tok) => (
            <Card key={tok.id} className={tok.is_active ? "" : "opacity-60"}>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <p className="font-semibold text-slate-800 text-sm">
                        {tok.label ?? <span className="italic text-slate-400">{t("sso.unlabeled")}</span>}
                      </p>
                      <ScopeBadge scope={tok.scope} />
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${tok.is_active ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                        {tok.is_active ? t("sso.tokenActive") : t("sso.tokenRevoked")}
                      </span>
                      {tok.idp_id && (
                        <span className="text-xs text-slate-400">
                          {idpMap.get(tok.idp_id) ?? tok.idp_id.slice(0, 8) + "…"}
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-4 text-xs text-slate-400">
                      <span>{t("sso.tokenCreated")}: {fmt(tok.created_at)}</span>
                      <span>{t("sso.tokenExpires")}: {fmt(tok.expires_at)}</span>
                      <span>{t("sso.tokenLastUsed")}: {fmt(tok.last_used_at)}</span>
                      <span>{t("sso.tokenUses")}: {tok.use_count}</span>
                    </div>
                  </div>

                  {tok.is_active && (
                    <div className="shrink-0 flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 gap-1 text-xs"
                        onClick={() => setExpandedRotate(expandedRotate === tok.id ? null : tok.id)}
                      >
                        <RefreshCw className="h-3 w-3" />
                        {t("sso.rotateToken")}
                        {expandedRotate === tok.id ? (
                          <ChevronDown className="h-3 w-3" />
                        ) : (
                          <ChevronRight className="h-3 w-3" />
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 gap-1 text-xs text-red-600 border-red-200 hover:bg-red-50"
                        disabled={revoke.isPending}
                        onClick={() => {
                          if (confirm(t("sso.revokeConfirm").replace("{label}", tok.label ?? tok.id))) {
                            revoke.mutate(tok.id);
                          }
                        }}
                      >
                        <Trash2 className="h-3 w-3" />
                        {t("sso.revokeToken")}
                      </Button>
                    </div>
                  )}
                </div>

                {/* Rotate sub-form */}
                {expandedRotate === tok.id && (
                  <div className="mt-3 rounded-lg bg-slate-50 p-3 space-y-3 border border-slate-200">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs">{t("sso.rotateLabel")}</Label>
                        <Input
                          className="mt-1 text-sm"
                          value={rotateLabel}
                          onChange={(e) => setRotateLabel(e.target.value)}
                          placeholder={tok.label ?? ""}
                        />
                      </div>
                      <div>
                        <Label className="text-xs">{t("sso.rotateTtl")}</Label>
                        <Input
                          type="number"
                          min={0}
                          className="mt-1 text-sm"
                          value={rotateTtl}
                          onChange={(e) => setRotateTtl(Number(e.target.value))}
                        />
                      </div>
                    </div>
                    <div className="flex justify-end">
                      <Button
                        size="sm"
                        disabled={rotate.isPending}
                        onClick={() => rotate.mutate(tok.id)}
                        className="gap-1"
                      >
                        {rotate.isPending && <Spinner className="h-4 w-4" />}
                        {t("sso.rotateConfirm")}
                      </Button>
                    </div>
                  </div>
                )}

                {/* Rotated raw token banner */}
                {rotatedRaw[tok.id] && <RawTokenBanner rawToken={rotatedRaw[tok.id]} />}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── SCIM Usage Tab ────────────────────────────────────────────────────────────

function UsageTab({ enterpriseId, idpMap }: { enterpriseId: string; idpMap: Map<string, string> }) {
  const { t } = useLanguage();

  const { data, isLoading, refetch, isFetching } = useQuery<SCIMUsageResponse>({
    queryKey: ["scim-usage", enterpriseId],
    queryFn: () => getSCIMUsage(enterpriseId),
    staleTime: 30_000,
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  if (!data) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-12 text-center text-slate-500">{t("sso.noUsage")}</CardContent>
      </Card>
    );
  }

  const kpis = [
    { label: t("sso.totalTokens"), value: data.token_count },
    { label: t("sso.activeTokens"), value: data.active_tokens },
    { label: t("sso.lastProvisioning"), value: fmt(data.last_provisioning) },
    { label: t("sso.lastSync"), value: fmt(data.last_sync) },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? <Spinner className="h-4 w-4" /> : <RefreshCw className="h-4 w-4" />}
          {t("common.refresh")}
        </Button>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {kpis.map((k) => (
          <Card key={k.label}>
            <CardContent className="py-4 text-center">
              <p className="text-xs text-slate-400 mb-1">{k.label}</p>
              <p className="text-xl font-bold text-slate-800">{k.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Per-IdP breakdown */}
      {data.per_idp_usage.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold">{t("sso.perIdpUsage")}</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-xs text-slate-400">
                  <th className="pb-2 text-left font-medium">{t("sso.idpId")}</th>
                  <th className="pb-2 text-right font-medium">{t("sso.totalCount")}</th>
                  <th className="pb-2 text-right font-medium">{t("sso.activeCount")}</th>
                  <th className="pb-2 text-right font-medium">{t("sso.tokenLastUsed")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {data.per_idp_usage.map((row, i) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="py-2 text-slate-700">
                      {row.idp_id ? (idpMap.get(row.idp_id) ?? row.idp_id.slice(0, 8) + "…") : "—"}
                    </td>
                    <td className="py-2 text-right tabular-nums text-slate-600">{row.token_count}</td>
                    <td className="py-2 text-right tabular-nums">
                      <span className={`font-medium ${row.active_count > 0 ? "text-green-700" : "text-slate-400"}`}>
                        {row.active_count}
                      </span>
                    </td>
                    <td className="py-2 text-right text-slate-400 text-xs">{fmt(row.last_used_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Secrets Health Tab ────────────────────────────────────────────────────────

function HealthTab() {
  const { t } = useLanguage();

  const { data, isLoading, refetch, isFetching } = useQuery<SecretHealthResponse>({
    queryKey: ["secrets-health"],
    queryFn: getSecretsHealth,
    staleTime: 60_000,
  });

  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => refetch()} disabled={isFetching}>
          {isFetching ? <Spinner className="h-4 w-4" /> : <RefreshCw className="h-4 w-4" />}
          {t("sso.recheck")}
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : data ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">{t("sso.healthTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              {/* Status badge */}
              <div className={`flex items-center gap-3 rounded-xl p-5 flex-1 ${data.is_connected ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"}`}>
                {data.is_connected ? (
                  <CheckCircle2 className="h-8 w-8 text-green-600" />
                ) : (
                  <XCircle className="h-8 w-8 text-red-600" />
                )}
                <div>
                  <p className={`text-lg font-bold ${data.is_connected ? "text-green-700" : "text-red-700"}`}>
                    {data.is_connected ? t("sso.connected") : t("sso.disconnected")}
                  </p>
                  <p className="text-sm text-slate-500">{t("sso.providerType")}: <strong className="font-mono text-slate-700">{data.provider_type}</strong></p>
                </div>
              </div>

              {/* Meta */}
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 flex-1">
                <p className="text-xs text-slate-400 mb-1">{t("sso.lastProbe")}</p>
                <p className="text-sm font-medium text-slate-700">{fmt(data.last_probe_at)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center text-slate-500">
            {t("sso.noUsage")}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

const tab_sso = ["tokens", "usage", "health"] as const;

export default function EnterpriseSSOPage() {
  const { t } = useLanguage();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: enterprises } = useQuery<Enterprise[]>({
    queryKey: ["enterprises"],
    queryFn: listEnterprises,
  });

  const activeId = selectedId ?? enterprises?.[0]?.id ?? null;

  const { data: idps } = useQuery<IdentityProvider[]>({
    queryKey: ["identity-providers", activeId],
    queryFn: () => listIdentityProviders(activeId!),
    enabled: !!activeId,
    staleTime: 120_000,
  });

  const idpMap = new Map<string, string>(
    (idps ?? []).map((idp) => [idp.id, idp.name])
  );

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t("sso.pageTitle")}</h1>
          <p className="mt-1 text-sm text-slate-500">{t("sso.pageSubtitle")}</p>
        </div>

        {enterprises && enterprises.length > 1 && (
          <div className="flex items-center gap-2 shrink-0">
            <Label className="text-xs text-slate-500">{t("sso.enterprise")}</Label>
            <select
              className="h-8 rounded-md border border-slate-200 bg-white px-2 text-sm"
              value={activeId ?? ""}
              onChange={(e) => setSelectedId(e.target.value)}
            >
              {enterprises.map((e) => (
                <option key={e.id} value={e.id}>{e.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {!activeId ? (
        <Card className="border-dashed">
          <CardContent className="py-16 text-center text-slate-500">
            {t("sso.noEnterprise")}
          </CardContent>
        </Card>
      ) : (
        <Tabs defaultValue={tab_sso[0]}>
          <TabsList>
            <TabsTrigger value="tokens">{t("sso.tabTokens")}</TabsTrigger>
            <TabsTrigger value="usage">{t("sso.tabUsage")}</TabsTrigger>
            <TabsTrigger value="health">{t("sso.tabHealth")}</TabsTrigger>
          </TabsList>

          <TabsContent value="tokens" className="mt-6">
            <TokensTab enterpriseId={activeId} idpMap={idpMap} />
          </TabsContent>
          <TabsContent value="usage" className="mt-6">
            <UsageTab enterpriseId={activeId} idpMap={idpMap} />
          </TabsContent>
          <TabsContent value="health" className="mt-6">
            <HealthTab />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
