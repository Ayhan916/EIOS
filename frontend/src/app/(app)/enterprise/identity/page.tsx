"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import { KeyRound, Plus, ChevronDown, ChevronRight } from "lucide-react";
import {
  listEnterprises,
  listIdentityProviders,
  createIdentityProvider,
  listGroupMappings,
  createGroupMapping,
  type IdentityProvider,
  type GroupMapping,
} from "@/lib/api/enterprise";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";

function CreateIdPModal({
  enterpriseId,
  onClose,
}: {
  enterpriseId: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { t } = useLanguage();
  const [name, setName] = useState("");
  const [providerType, setProviderType] = useState("oidc");
  const [issuer, setIssuer] = useState("");
  const [metadataUrl, setMetadataUrl] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      createIdentityProvider(enterpriseId, {
        name,
        provider_type: providerType,
        issuer: issuer || undefined,
        metadata_url: metadataUrl || undefined,
        client_id: clientId || undefined,
        client_secret: clientSecret || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["identity-providers", enterpriseId] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold">{t("ent.addIdp")}</h2>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium">{t("common.name")} *</label>
              <input
                className="w-full rounded-lg border px-3 py-2 text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Corporate Azure AD"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">{t("common.type")} *</label>
              <select
                className="w-full rounded-lg border px-3 py-2 text-sm"
                value={providerType}
                onChange={(e) => setProviderType(e.target.value)}
              >
                <option value="oidc">OpenID Connect</option>
                <option value="saml">SAML 2.0</option>
              </select>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">{t("ent.issuerEntityId")}</label>
            <input
              className="w-full rounded-lg border px-3 py-2 text-sm"
              value={issuer}
              onChange={(e) => setIssuer(e.target.value)}
              placeholder="https://login.example.com/tenant-id/v2.0"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">{t("ent.metadataUrl")}</label>
            <input
              className="w-full rounded-lg border px-3 py-2 text-sm"
              value={metadataUrl}
              onChange={(e) => setMetadataUrl(e.target.value)}
              placeholder="https://login.example.com/.well-known/openid-configuration"
            />
          </div>
          {providerType === "oidc" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium">{t("ent.clientId")}</label>
                <input
                  className="w-full rounded-lg border px-3 py-2 text-sm"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">{t("ent.clientSecret")}</label>
                <input
                  type="password"
                  className="w-full rounded-lg border px-3 py-2 text-sm"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                />
              </div>
            </div>
          )}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg border px-4 py-2 text-sm">
            {t("common.cancel")}
          </button>
          <button
            onClick={() => mutate()}
            disabled={!name || isPending}
            className="rounded-lg bg-slate-800 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {isPending ? t("common.loading") : t("ent.addIdp")}
          </button>
        </div>
      </div>
    </div>
  );
}

function GroupMappingsSection({
  enterpriseId,
  idpId,
}: {
  enterpriseId: string;
  idpId: string;
}) {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [idpGroup, setIdpGroup] = useState("");
  const [mappedRole, setMappedRole] = useState("viewer");

  const { data: mappings, isLoading } = useQuery({
    queryKey: ["group-mappings", enterpriseId, idpId],
    queryFn: () => listGroupMappings(enterpriseId, idpId),
  });

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      createGroupMapping(enterpriseId, idpId, { idp_group: idpGroup, mapped_role: mappedRole }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["group-mappings", enterpriseId, idpId] });
      setShowAdd(false);
      setIdpGroup("");
    },
  });

  const { t } = useLanguage();
  if (isLoading) return <Spinner />;

  return (
    <div className="mt-3 rounded-lg bg-slate-50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-semibold text-muted-foreground">{t("ent.groupMappings")}</p>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="text-xs text-blue-600 hover:underline"
        >
          {t("ent.addMapping")}
        </button>
      </div>

      {showAdd && (
        <div className="mb-3 flex items-end gap-2">
          <div className="flex-1">
            <input
              className="w-full rounded border px-2 py-1 text-xs"
              placeholder="IdP group name"
              value={idpGroup}
              onChange={(e) => setIdpGroup(e.target.value)}
            />
          </div>
          <div>
            <select
              className="rounded border px-2 py-1 text-xs"
              value={mappedRole}
              onChange={(e) => setMappedRole(e.target.value)}
            >
              {["viewer", "analyst", "admin", "executive", "enterprise_admin", "bu_admin", "regional_admin"].map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
          <button
            onClick={() => mutate()}
            disabled={!idpGroup || isPending}
            className="rounded bg-slate-800 px-2 py-1 text-xs text-white disabled:opacity-50"
          >
            {t("common.create")}
          </button>
        </div>
      )}

      {!mappings || mappings.length === 0 ? (
        <p className="text-xs text-muted-foreground">{t("ent.noMappings")}</p>
      ) : (
        <div className="space-y-1">
          {mappings.map((m: GroupMapping) => (
            <div
              key={m.id}
              className="flex items-center justify-between rounded border bg-white px-2 py-1"
            >
              <span className="font-mono text-xs text-slate-700">{m.idp_group}</span>
              <span className="text-xs text-muted-foreground">→ {m.mapped_role}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function IdentityPage() {
  const { t } = useLanguage();
  const { data: enterprises } = useQuery({
    queryKey: ["enterprises"],
    queryFn: listEnterprises,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [expandedIdp, setExpandedIdp] = useState<string | null>(null);

  const activeId = selectedId ?? enterprises?.[0]?.id ?? null;

  const { data: providers, isLoading } = useQuery({
    queryKey: ["identity-providers", activeId],
    queryFn: () => listIdentityProviders(activeId!),
    enabled: !!activeId,
  });

  return (
    <div className="space-y-6 p-6">
      {showCreate && activeId && (
        <CreateIdPModal enterpriseId={activeId} onClose={() => setShowCreate(false)} />
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{t("ent.identityTitle")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("ent.identitySubtitle")}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {enterprises && enterprises.length > 1 && (
            <select
              className="rounded-lg border px-3 py-2 text-sm"
              value={activeId ?? ""}
              onChange={(e) => setSelectedId(e.target.value)}
            >
              {enterprises.map((e) => (
                <option key={e.id} value={e.id}>{e.name}</option>
              ))}
            </select>
          )}
          <button
            onClick={() => setShowCreate(true)}
            disabled={!activeId}
            className="flex items-center gap-2 rounded-lg bg-slate-800 px-4 py-2 text-sm text-white disabled:opacity-40"
          >
            <Plus className="h-4 w-4" />
            {t("ent.addIdp")}
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : !providers || providers.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center text-muted-foreground">
            {t("ent.noIdpDesc")}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {providers.map((idp: IdentityProvider) => (
            <Card key={idp.id}>
              <CardContent className="py-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <KeyRound className="mt-0.5 h-4 w-4 text-slate-500" />
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{idp.name}</p>
                        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs uppercase text-slate-600">
                          {idp.provider_type}
                        </span>
                        <Badge
                          variant="outline"
                          className={idp.is_active ? "border-emerald-300 text-emerald-700" : "border-slate-300 text-slate-500"}
                        >
                          {idp.is_active ? t("common.active") : t("common.inactive")}
                        </Badge>
                      </div>
                      {idp.issuer && (
                        <p className="mt-1 font-mono text-xs text-muted-foreground">
                          {idp.issuer}
                        </p>
                      )}
                      {idp.has_client_secret && (
                        <p className="mt-0.5 text-xs text-emerald-600">
                          ● {t("ent.clientSecretConfigured")}
                        </p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => setExpandedIdp(expandedIdp === idp.id ? null : idp.id)}
                    className="text-muted-foreground hover:text-slate-700"
                  >
                    {expandedIdp === idp.id ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </button>
                </div>

                {expandedIdp === idp.id && activeId && (
                  <GroupMappingsSection enterpriseId={activeId} idpId={idp.id} />
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
