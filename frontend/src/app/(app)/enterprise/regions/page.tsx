"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Globe, Plus } from "lucide-react";
import {
  listEnterprises,
  listRegions,
  createRegion,
  type EnterpriseRegion,
} from "@/lib/api/enterprise";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { useLanguage } from "@/lib/i18n/context";

const RESIDENCY_OPTIONS = ["EU", "UK", "US", "APAC"];

function CreateRegionModal({
  enterpriseId,
  onClose,
}: {
  enterpriseId: string;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const { t } = useLanguage();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [residency, setResidency] = useState("EU");

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      createRegion(enterpriseId, { name, code, data_residency: residency }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["regions", enterpriseId] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold">{t("ent.addRegion")}</h2>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium">{t("common.name")} *</label>
            <input
              className="w-full rounded-lg border px-3 py-2 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Europe"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">{t("ent.unitCode")} *</label>
            <input
              className="w-full rounded-lg border px-3 py-2 text-sm"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="e.g. EU"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Data Residency</label>
            <select
              className="w-full rounded-lg border px-3 py-2 text-sm"
              value={residency}
              onChange={(e) => setResidency(e.target.value)}
            >
              {RESIDENCY_OPTIONS.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg border px-4 py-2 text-sm">
            {t("common.cancel")}
          </button>
          <button
            onClick={() => mutate()}
            disabled={!name || !code || isPending}
            className="rounded-lg bg-slate-800 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {isPending ? "Saving…" : t("common.create")}
          </button>
        </div>
      </div>
    </div>
  );
}

function residencyBadge(r: string) {
  const colors: Record<string, string> = {
    EU:   "bg-blue-100 text-blue-800",
    UK:   "bg-purple-100 text-purple-800",
    US:   "bg-amber-100 text-amber-800",
    APAC: "bg-teal-100 text-teal-800",
  };
  return colors[r] ?? "bg-slate-100 text-slate-700";
}

export default function RegionsPage() {
  const { t } = useLanguage();
  const { data: enterprises } = useQuery({
    queryKey: ["enterprises"],
    queryFn: listEnterprises,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const activeId = selectedId ?? enterprises?.[0]?.id ?? null;

  const { data: regions, isLoading } = useQuery({
    queryKey: ["regions", activeId],
    queryFn: () => listRegions(activeId!),
    enabled: !!activeId,
  });

  return (
    <div className="space-y-6 p-6">
      {showCreate && activeId && (
        <CreateRegionModal enterpriseId={activeId} onClose={() => setShowCreate(false)} />
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{t("ent.regionsTitle")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("ent.regionsSubtitle")}
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
            {t("ent.addRegion")}
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : !regions || regions.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center text-muted-foreground">
            {t("ent.noRegions")}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {regions.map((region: EnterpriseRegion) => (
            <Card key={region.id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <Globe className="h-4 w-4 text-slate-500" />
                    <CardTitle className="text-base">{region.name}</CardTitle>
                  </div>
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-semibold ${residencyBadge(region.data_residency)}`}
                  >
                    {region.data_residency}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p className="text-xs font-mono text-muted-foreground">
                  Code: {region.code}
                </p>
                <Badge
                  variant="outline"
                  className={region.is_active ? "border-emerald-300 text-emerald-700" : "border-slate-300 text-slate-500"}
                >
                  {region.is_active ? t("common.active") : t("common.inactive")}
                </Badge>
                <p className="text-xs text-muted-foreground">
                  Created {new Date(region.created_at).toLocaleDateString()}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
