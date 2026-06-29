"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Shield } from "lucide-react";
import {
  listEnterprises,
  listPolicies,
  createPolicy,
  listRetentionRules,
  type EnterprisePolicy,
  type RetentionRule,
} from "@/lib/api/enterprise";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";

const POLICY_TYPES = [
  "retention",
  "evidence_requirements",
  "supplier_onboarding",
  "risk_acceptance",
  "custom",
];

function CreatePolicyModal({
  enterpriseId,
  onClose,
}: {
  enterpriseId: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [policyType, setPolicyType] = useState("retention");
  const [description, setDescription] = useState("");
  const [cascade, setCascade] = useState(true);

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      createPolicy(enterpriseId, {
        name,
        policy_type: policyType,
        description: description || undefined,
        cascade_to_children: cascade,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["enterprise-policies", enterpriseId] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold">Create Enterprise Policy</h2>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium">Name *</label>
            <input
              className="w-full rounded-lg border px-3 py-2 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Type *</label>
            <select
              className="w-full rounded-lg border px-3 py-2 text-sm"
              value={policyType}
              onChange={(e) => setPolicyType(e.target.value)}
            >
              {POLICY_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Description</label>
            <textarea
              className="w-full rounded-lg border px-3 py-2 text-sm"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={cascade}
              onChange={(e) => setCascade(e.target.checked)}
            />
            Cascade to child organizations
          </label>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg border px-4 py-2 text-sm">
            Cancel
          </button>
          <button
            onClick={() => mutate()}
            disabled={!name || isPending}
            className="rounded-lg bg-slate-800 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {isPending ? "Saving…" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}

function typeBadge(t: string) {
  const colors: Record<string, string> = {
    retention:             "bg-blue-100 text-blue-800",
    evidence_requirements: "bg-purple-100 text-purple-800",
    supplier_onboarding:   "bg-amber-100 text-amber-800",
    risk_acceptance:       "bg-red-100 text-red-800",
    custom:                "bg-slate-100 text-slate-700",
  };
  return colors[t] ?? "bg-slate-100 text-slate-700";
}

export default function PoliciesPage() {
  const { data: enterprises } = useQuery({
    queryKey: ["enterprises"],
    queryFn: listEnterprises,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [tab, setTab] = useState<"policies" | "retention">("policies");

  const activeId = selectedId ?? enterprises?.[0]?.id ?? null;

  const { data: policies, isLoading: loadingPolicies } = useQuery({
    queryKey: ["enterprise-policies", activeId],
    queryFn: () => listPolicies(activeId!),
    enabled: !!activeId && tab === "policies",
  });

  const { data: retention, isLoading: loadingRetention } = useQuery({
    queryKey: ["retention-rules", activeId],
    queryFn: () => listRetentionRules(activeId!),
    enabled: !!activeId && tab === "retention",
  });

  return (
    <div className="space-y-6 p-6">
      {showCreate && activeId && (
        <CreatePolicyModal enterpriseId={activeId} onClose={() => setShowCreate(false)} />
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Policies</h1>
          <p className="text-sm text-muted-foreground">
            Enterprise governance policies and retention rules
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
          {tab === "policies" && (
            <button
              onClick={() => setShowCreate(true)}
              disabled={!activeId}
              className="flex items-center gap-2 rounded-lg bg-slate-800 px-4 py-2 text-sm text-white disabled:opacity-40"
            >
              <Plus className="h-4 w-4" />
              New Policy
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {(["policies", "retention"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              tab === t
                ? "border-slate-800 text-slate-800"
                : "border-transparent text-muted-foreground hover:text-slate-700"
            }`}
          >
            {t === "retention" ? "Retention Rules" : "Governance Policies"}
          </button>
        ))}
      </div>

      {tab === "policies" && (
        loadingPolicies ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : !policies || policies.length === 0 ? (
          <Card>
            <CardContent className="py-16 text-center text-muted-foreground">
              No policies created yet.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {policies.map((p: EnterprisePolicy) => (
              <Card key={p.id}>
                <CardContent className="flex items-start justify-between py-4">
                  <div className="flex items-start gap-3">
                    <Shield className="mt-0.5 h-4 w-4 text-slate-400" />
                    <div>
                      <p className="font-medium">{p.name}</p>
                      {p.description && (
                        <p className="text-sm text-muted-foreground">{p.description}</p>
                      )}
                      <div className="mt-1 flex items-center gap-2">
                        <span className={`rounded px-2 py-0.5 text-xs font-medium ${typeBadge(p.policy_type)}`}>
                          {p.policy_type.replace(/_/g, " ")}
                        </span>
                        {p.cascade_to_children && (
                          <span className="text-xs text-muted-foreground">cascades to children</span>
                        )}
                        <span className="text-xs text-muted-foreground">
                          scope: {p.scope}
                        </span>
                      </div>
                    </div>
                  </div>
                  <Badge
                    variant="outline"
                    className={p.is_active ? "border-emerald-300 text-emerald-700" : "border-slate-300 text-slate-500"}
                  >
                    {p.is_active ? "Active" : "Inactive"}
                  </Badge>
                </CardContent>
              </Card>
            ))}
          </div>
        )
      )}

      {tab === "retention" && (
        loadingRetention ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : !retention || retention.length === 0 ? (
          <Card>
            <CardContent className="py-16 text-center text-muted-foreground">
              No retention rules configured.
            </CardContent>
          </Card>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-xs text-muted-foreground">
                  <th className="pb-2 text-left">Entity Type</th>
                  <th className="pb-2 text-right">Retention Days</th>
                  <th className="pb-2 text-center">Legal Hold</th>
                  <th className="pb-2 text-center">Cascades</th>
                  <th className="pb-2 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {retention.map((r: RetentionRule) => (
                  <tr key={r.id} className="border-b last:border-0">
                    <td className="py-3 font-medium capitalize">
                      {r.entity_type.replace(/_/g, " ")}
                    </td>
                    <td className="py-3 text-right font-mono">{r.retention_days}d</td>
                    <td className="py-3 text-center">
                      {r.legal_hold ? (
                        <span className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-800">
                          Legal Hold
                        </span>
                      ) : "—"}
                    </td>
                    <td className="py-3 text-center text-xs text-muted-foreground">
                      {r.cascade_to_children ? "Yes" : "No"}
                    </td>
                    <td className="py-3 text-center">
                      <Badge
                        variant="outline"
                        className={r.is_active ? "border-emerald-300 text-emerald-700" : "border-slate-300 text-slate-500"}
                      >
                        {r.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}
