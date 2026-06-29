"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Building2, ChevronDown, ChevronRight, Download, Globe, Landmark, Plus } from "lucide-react";
import {
  listEnterprises,
  listBusinessUnits,
  listLegalEntities,
  listRegions,
  getEnterpriseDashboard,
  createBusinessUnit,
  type BusinessUnit,
  type LegalEntity,
  type EnterpriseRegion,
  type BURollupItem,
} from "@/lib/api/enterprise";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";

function healthColor(score: number) {
  if (score >= 80) return "text-emerald-600";
  if (score >= 60) return "text-blue-600";
  if (score >= 40) return "text-amber-600";
  return "text-red-600";
}

function healthBarColor(score: number) {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 60) return "bg-blue-500";
  if (score >= 40) return "bg-amber-500";
  return "bg-red-500";
}

function BUTreeNode({
  bu,
  rollup,
  legalEntities,
  regions,
}: {
  bu: BusinessUnit;
  rollup: BURollupItem | undefined;
  legalEntities: LegalEntity[];
  regions: EnterpriseRegion[];
}) {
  const [open, setOpen] = useState(true);
  const health = rollup?.compliance_readiness ?? null;

  const matchedRegions = regions.filter(
    (r) => bu.region_scope && r.name.toLowerCase().includes(bu.region_scope.toLowerCase())
  );

  return (
    <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-muted/40 transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 flex-shrink-0">
          <Building2 className="h-4 w-4 text-slate-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm truncate">{bu.name}</p>
          {bu.region_scope && (
            <p className="text-xs text-muted-foreground">Scope: {bu.region_scope}</p>
          )}
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {health !== null && (
            <div className="text-right">
              <p className={`text-sm font-bold ${healthColor(health)}`}>{health.toFixed(0)}%</p>
              <p className="text-[10px] text-muted-foreground">ESG Health</p>
            </div>
          )}
          {bu.is_active ? (
            <Badge variant="outline" className="border-emerald-300 text-emerald-700 text-[10px]">Active</Badge>
          ) : (
            <Badge variant="outline" className="border-slate-300 text-slate-500 text-[10px]">Inactive</Badge>
          )}
          {open ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
        </div>
      </button>

      {open && (
        <div className="border-t bg-muted/20 px-4 py-3 space-y-3">
          {/* BU rollup stats */}
          {rollup && (
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-muted-foreground mb-0.5">
                <span>Compliance Readiness</span>
                <span className={`font-semibold ${healthColor(rollup.compliance_readiness)}`}>
                  {rollup.compliance_readiness.toFixed(0)}%
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className={`h-full rounded-full ${healthBarColor(rollup.compliance_readiness)}`}
                  style={{ width: `${Math.min(rollup.compliance_readiness, 100)}%` }}
                />
              </div>
              <div className="grid grid-cols-3 gap-2 pt-1">
                {[
                  { label: "Suppliers", value: rollup.supplier_count },
                  { label: "Open Findings", value: rollup.open_findings },
                  { label: "Critical Risks", value: rollup.critical_risks },
                ].map(({ label, value }) => (
                  <div key={label} className="text-center rounded border bg-background p-2">
                    <p className="text-sm font-bold">{value}</p>
                    <p className="text-[10px] text-muted-foreground">{label}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Matched regions */}
          {matchedRegions.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Regions</p>
              {matchedRegions.map((r) => (
                <div key={r.id} className="flex items-center gap-2 rounded border bg-background px-3 py-2">
                  <Globe className="h-3.5 w-3.5 text-blue-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs font-medium truncate">{r.name}</p>
                    <p className="text-[10px] text-muted-foreground">{r.code} · {r.data_residency}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Legal Entities scoped to this BU's region */}
          {legalEntities.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Legal Entities</p>
              {legalEntities.map((le) => (
                <div key={le.id} className="flex items-center gap-2 rounded border bg-background px-3 py-2">
                  <Landmark className="h-3.5 w-3.5 text-violet-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs font-medium truncate">{le.name}</p>
                    <p className="text-[10px] text-muted-foreground">
                      {[le.country, le.legal_form].filter(Boolean).join(" · ")}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {!rollup && matchedRegions.length === 0 && legalEntities.length === 0 && (
            <p className="text-xs text-muted-foreground italic">No linked regions or entities</p>
          )}
        </div>
      )}
    </div>
  );
}

function CreateBUModal({ enterpriseId, onClose }: { enterpriseId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [regionScope, setRegionScope] = useState("");

  const { mutate, isPending } = useMutation({
    mutationFn: () =>
      createBusinessUnit(enterpriseId, {
        name,
        description: description || undefined,
        region_scope: regionScope || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["business-units", enterpriseId] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold">Add Business Unit</h2>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium">Name *</label>
            <input
              className="w-full rounded-lg border px-3 py-2 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. EMEA Operations"
            />
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
          <div>
            <label className="mb-1 block text-sm font-medium">Region Scope</label>
            <input
              className="w-full rounded-lg border px-3 py-2 text-sm"
              value={regionScope}
              onChange={(e) => setRegionScope(e.target.value)}
              placeholder="e.g. EMEA"
            />
          </div>
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

function downloadRollupCSV(buRollups: BURollupItem[]) {
  const headers = [
    "Business Unit",
    "Suppliers",
    "Organizations",
    "Total Risks",
    "Critical Risks",
    "Total Findings",
    "Open Findings",
    "Compliance Readiness (%)",
  ];
  const rows = buRollups.map((bu) => [
    `"${bu.name}"`,
    bu.supplier_count,
    bu.organization_count,
    bu.total_risks,
    bu.critical_risks,
    bu.total_findings,
    bu.open_findings,
    bu.compliance_readiness.toFixed(1),
  ]);
  const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "enterprise-bu-rollup.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export default function BusinessUnitsPage() {
  const { data: enterprises } = useQuery({
    queryKey: ["enterprises"],
    queryFn: listEnterprises,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const activeId = selectedId ?? enterprises?.[0]?.id ?? null;

  const { data: units, isLoading: unitsLoading } = useQuery({
    queryKey: ["business-units", activeId],
    queryFn: () => listBusinessUnits(activeId!),
    enabled: !!activeId,
  });

  const { data: legalEntities } = useQuery({
    queryKey: ["legal-entities", activeId],
    queryFn: () => listLegalEntities(activeId!),
    enabled: !!activeId,
    staleTime: 300_000,
  });

  const { data: regions } = useQuery({
    queryKey: ["regions", activeId],
    queryFn: () => listRegions(activeId!),
    enabled: !!activeId,
    staleTime: 300_000,
  });

  const { data: dashboard } = useQuery({
    queryKey: ["enterprise-dashboard", activeId],
    queryFn: () => getEnterpriseDashboard(activeId!),
    enabled: !!activeId,
    staleTime: 120_000,
  });

  const buRollups = dashboard?.bu_rollups ?? [];
  const healthScore = dashboard?.health_score;

  return (
    <div className="space-y-6 p-6">
      {showCreate && activeId && (
        <CreateBUModal enterpriseId={activeId} onClose={() => setShowCreate(false)} />
      )}

      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Enterprise Hierarchy</h1>
          <p className="text-sm text-muted-foreground">
            Business units, regions, and legal entities
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
          {buRollups.length > 0 && (
            <button
              onClick={() => downloadRollupCSV(buRollups)}
              className="flex items-center gap-2 rounded-lg border px-4 py-2 text-sm hover:bg-muted/50 transition-colors"
            >
              <Download className="h-4 w-4" />
              Download Report
            </button>
          )}
          <button
            onClick={() => setShowCreate(true)}
            disabled={!activeId}
            className="flex items-center gap-2 rounded-lg bg-slate-800 px-4 py-2 text-sm text-white disabled:opacity-40"
          >
            <Plus className="h-4 w-4" />
            Add BU
          </button>
        </div>
      </div>

      {/* Enterprise health summary */}
      {healthScore && (
        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-4">
                <div className="text-center">
                  <p className={`text-3xl font-bold ${healthColor(healthScore.score)}`}>
                    {healthScore.score.toFixed(0)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Grade: <span className="font-semibold">{healthScore.grade}</span>
                  </p>
                </div>
                <div className="space-y-1 min-w-48">
                  {Object.entries(healthScore.components).map(([k, v]) => (
                    <div key={k} className="flex items-center gap-2">
                      <p className="text-[10px] text-muted-foreground capitalize w-28 truncate">{k.replace(/_/g, " ")}</p>
                      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                        <div className={`h-full rounded-full ${healthBarColor(v)}`} style={{ width: `${Math.min(v, 100)}%` }} />
                      </div>
                      <p className="text-[10px] font-medium w-8 text-right">{v.toFixed(0)}</p>
                    </div>
                  ))}
                </div>
              </div>
              {healthScore.drivers.length > 0 && (
                <div className="space-y-1">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Key Drivers</p>
                  {healthScore.drivers.slice(0, 3).map((d) => (
                    <p key={d} className="text-xs text-muted-foreground">· {d}</p>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {unitsLoading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : !units || units.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center text-muted-foreground">
            No business units yet. Add one to start structuring your enterprise.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {units.map((bu: BusinessUnit) => {
            const rollup = buRollups.find((r) => r.business_unit_id === bu.id);
            return (
              <BUTreeNode
                key={bu.id}
                bu={bu}
                rollup={rollup}
                legalEntities={legalEntities ?? []}
                regions={regions ?? []}
              />
            );
          })}
        </div>
      )}

      {/* Unassigned Legal Entities */}
      {legalEntities && legalEntities.length > 0 && (units ?? []).length === 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Landmark className="h-4 w-4 text-violet-500" />
              Legal Entities
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {legalEntities.map((le) => (
              <div key={le.id} className="flex items-center gap-2 rounded border px-3 py-2">
                <Landmark className="h-3.5 w-3.5 text-violet-500 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium">{le.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {[le.country, le.legal_form, le.registration_number].filter(Boolean).join(" · ")}
                  </p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
