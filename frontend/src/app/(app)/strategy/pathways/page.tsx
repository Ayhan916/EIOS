"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listPathways, createPathway, type CreatePathwayPayload } from "@/lib/api/strategy";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import { Plus, X, TrendingDown, Star } from "lucide-react";
import { PathwayAreaChart } from "@/components/charts/pathway-area-chart";
import type { PathwayDataPoint } from "@/components/charts/pathway-area-chart";

// ── Constants ─────────────────────────────────────────────────────────────────

const PATHWAY_TYPES = [
  { value: "CONSERVATIVE", label: "Konservativ", color: "bg-amber-100 text-amber-700" },
  { value: "EXPECTED", label: "Erwartet", color: "bg-blue-100 text-blue-700" },
  { value: "ACCELERATED", label: "Beschleunigt", color: "bg-green-100 text-green-700" },
  { value: "CUSTOM", label: "Individuell", color: "bg-purple-100 text-purple-700" },
];

const MILESTONE_FREQS = [
  { value: "ANNUAL", label: "Jährlich (5 Meilensteine)" },
  { value: "SEMIANNUAL", label: "Halbjährlich" },
  { value: "QUARTERLY", label: "Quartalsweise" },
];

// ── Create Modal ──────────────────────────────────────────────────────────────

function CreatePathwayModal({
  orgId,
  onClose,
}: {
  orgId: string;
  onClose: () => void;
}) {
  const { t } = useLanguage();
  const queryClient = useQueryClient();
  const currentYear = new Date().getFullYear();
  const [form, setForm] = useState({
    pathway_name: "",
    pathway_type: "EXPECTED",
    target_year: String(currentYear + 10),
    baseline_emissions_tco2e: "",
    target_emissions_tco2e: "",
    milestone_frequency: "ANNUAL",
    is_primary: false,
  });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (payload: CreatePathwayPayload) => createPathway(orgId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategy", "pathways", orgId] });
      onClose();
    },
    onError: (e: unknown) => {
      setError(e instanceof Error ? e.message : "Fehler beim Erstellen");
    },
  });

  const baseline = parseFloat(form.baseline_emissions_tco2e);
  const target = parseFloat(form.target_emissions_tco2e);
  const reductionPct =
    !isNaN(baseline) && !isNaN(target) && baseline > 0
      ? (((baseline - target) / baseline) * 100).toFixed(1)
      : null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!form.pathway_name.trim()) { setError("Name ist erforderlich."); return; }
    const year = parseInt(form.target_year, 10);
    if (isNaN(year) || year < currentYear) {
      setError(`Zieljahr muss ${currentYear} oder später sein.`); return;
    }
    mutation.mutate({
      pathway_name: form.pathway_name.trim(),
      pathway_type: form.pathway_type,
      target_year: year,
      baseline_emissions_tco2e: form.baseline_emissions_tco2e ? parseFloat(form.baseline_emissions_tco2e) : undefined,
      target_emissions_tco2e: form.target_emissions_tco2e ? parseFloat(form.target_emissions_tco2e) : undefined,
      milestone_frequency: form.milestone_frequency,
      is_primary: form.is_primary,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="relative w-full max-w-lg rounded-xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2">
            <TrendingDown className="h-5 w-5 text-violet-600" />
            <h2 className="text-lg font-semibold">Neuer Transition Pathway</h2>
          </div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100">
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 px-6 py-5">
          {/* Name */}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              {t("common.name")} <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.pathway_name}
              onChange={(e) => setForm((f) => ({ ...f, pathway_name: e.target.value }))}
              placeholder="z. B. SBTi 1.5°C Pfad"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
            />
          </div>

          {/* Pathway-Typ */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">{t("common.type")}</label>
            <div className="grid grid-cols-2 gap-2">
              {PATHWAY_TYPES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, pathway_type: t.value }))}
                  className={`rounded-lg border-2 px-3 py-2 text-sm font-medium transition-colors ${
                    form.pathway_type === t.value
                      ? `${t.color} border-violet-400`
                      : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Zieljahr */}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              {t("sustain.targetYear")} <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              min={currentYear}
              max={2100}
              value={form.target_year}
              onChange={(e) => setForm((f) => ({ ...f, target_year: e.target.value }))}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
            />
          </div>

          {/* Emissionen */}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Emissionen (tCO₂e)
            </label>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="mb-1 text-xs text-slate-500">Baseline (heute)</p>
                <input
                  type="number"
                  min={0}
                  value={form.baseline_emissions_tco2e}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, baseline_emissions_tco2e: e.target.value }))
                  }
                  placeholder="84500"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
              <div>
                <p className="mb-1 text-xs text-slate-500">Ziel ({form.target_year})</p>
                <input
                  type="number"
                  min={0}
                  value={form.target_emissions_tco2e}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, target_emissions_tco2e: e.target.value }))
                  }
                  placeholder="8450"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
            </div>
            {reductionPct !== null && (
              <div className="mt-2 rounded-md bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700">
                → {reductionPct}% Reduktion bis {form.target_year}
              </div>
            )}
          </div>

          {/* Meilenstein-Frequenz */}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Meilenstein-Frequenz
            </label>
            <select
              value={form.milestone_frequency}
              onChange={(e) => setForm((f) => ({ ...f, milestone_frequency: e.target.value }))}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
            >
              {MILESTONE_FREQS.map((f) => (
                <option key={f.value} value={f.value}>{f.label}</option>
              ))}
            </select>
          </div>

          {/* Primär-Pathway */}
          <label className="flex cursor-pointer items-center gap-3">
            <input
              type="checkbox"
              checked={form.is_primary}
              onChange={(e) => setForm((f) => ({ ...f, is_primary: e.target.checked }))}
              className="h-4 w-4 rounded border-slate-300 text-violet-600 focus:ring-violet-500"
            />
            <span className="flex items-center gap-1.5 text-sm text-slate-700">
              <Star className="h-3.5 w-3.5 text-amber-500" />
              Als primären Pathway setzen
              <span className="text-xs text-slate-400">(wird auf der Übersicht hervorgehoben)</span>
            </span>
          </label>

          {error && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
          )}
        </form>

        {/* Footer */}
        <div className="flex justify-end gap-3 border-t px-6 py-4">
          <Button type="button" variant="outline" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={mutation.isPending}
            className="bg-violet-600 hover:bg-violet-700"
          >
            {mutation.isPending ? (
              <span className="flex items-center gap-2">
                <Spinner className="h-4 w-4" /> Erstelle…
              </span>
            ) : (
              "Pathway erstellen"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PathwaysPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";
  const [showCreate, setShowCreate] = useState(false);

  const { data: pathways, isLoading } = useQuery({
    queryKey: ["strategy", "pathways", orgId],
    queryFn: () => listPathways(orgId),
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const primary = (pathways ?? []).find((p) => p.is_primary);
  const milestones =
    (primary?.milestones as { milestones?: Array<{ year: number; emissions_tco2e: number }> })
      ?.milestones ?? [];

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("strategy.pathwaysTitle")}</h1>
          <p className="text-muted-foreground">
            {t("strategy.pathwaysSubtitle")}
          </p>
        </div>
        <Button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700"
        >
          <Plus className="h-4 w-4" />
          {t("strategy.addPathway")}
        </Button>
      </div>

      {/* Primary Pathway */}
      {primary && milestones.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Emissionspfad</CardTitle></CardHeader>
          <CardContent>
            <PathwayAreaChart
              data={[
                {
                  year: new Date().getFullYear(),
                  emissions: primary.baseline_emissions_tco2e ?? null,
                  target_pathway: primary.baseline_emissions_tco2e ?? null,
                },
                ...milestones.map((m) => ({
                  year: m.year,
                  emissions: m.emissions_tco2e,
                  target_pathway: primary.target_emissions_tco2e ?? null,
                })),
              ] satisfies PathwayDataPoint[]}
              unit="tCO₂e"
              height={300}
            />
          </CardContent>
        </Card>
      )}

      {primary && (
        <Card className="border-green-200 bg-green-50">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Star className="h-4 w-4 text-amber-500" />
              <CardTitle className="text-base text-green-800">
                Primärer Pathway — {primary.pathway_name}
              </CardTitle>
              <span
                className={`rounded px-2 py-0.5 text-xs font-medium ${
                  PATHWAY_TYPES.find((t) => t.value === primary.pathway_type)?.color ??
                  "bg-muted text-muted-foreground"
                }`}
              >
                {PATHWAY_TYPES.find((t) => t.value === primary.pathway_type)?.label ??
                  primary.pathway_type}
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-xs text-green-700">{t("sustain.targetYear")}</p>
                <p className="text-2xl font-bold text-green-800">{primary.target_year}</p>
              </div>
              <div>
                <p className="text-xs text-green-700">{t("sustain.reductionPct")}</p>
                <p className="text-2xl font-bold text-green-800">
                  {primary.reduction_pct !== null
                    ? `${primary.reduction_pct.toFixed(1)}%`
                    : "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-green-700">Ziel-Emissionen</p>
                <p className="text-2xl font-bold text-green-800">
                  {primary.target_emissions_tco2e !== null
                    ? `${primary.target_emissions_tco2e.toLocaleString("de-DE")} tCO₂e`
                    : "—"}
                </p>
              </div>
            </div>
            {milestones.length > 0 && (
              <div className="mt-4">
                <p className="mb-2 text-xs font-medium text-green-700">Meilensteine</p>
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {milestones.map((m, i) => (
                    <div
                      key={i}
                      className="min-w-[80px] rounded-lg bg-white px-2 py-2 text-center text-xs shadow-sm"
                    >
                      <p className="font-semibold text-slate-700">{m.year}</p>
                      <p className="mt-0.5 font-bold text-green-600">
                        {m.emissions_tco2e.toLocaleString("de-DE")}
                      </p>
                      <p className="text-muted-foreground">tCO₂e</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* All Pathways */}
      <Card>
        <CardHeader>
          <CardTitle>Alle Pathways</CardTitle>
        </CardHeader>
        <CardContent>
          {(pathways ?? []).length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <TrendingDown className="h-10 w-10 text-slate-300" />
              <p className="text-sm font-medium text-slate-600">{t("strategy.noPathways")}</p>
              <Button
                onClick={() => setShowCreate(true)}
                className="mt-1 bg-violet-600 hover:bg-violet-700"
              >
                <Plus className="mr-2 h-4 w-4" />
                {t("strategy.addPathway")}
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {(pathways ?? []).map((p) => {
                const typeInfo = PATHWAY_TYPES.find((t) => t.value === p.pathway_type);
                return (
                  <div
                    key={p.id}
                    className="flex items-center justify-between rounded-lg border px-4 py-3 transition-colors hover:bg-slate-50"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{p.pathway_name}</p>
                        {p.is_primary && (
                          <Star className="h-3.5 w-3.5 flex-shrink-0 text-amber-500" />
                        )}
                        {p.is_final && (
                          <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700">
                            FINAL
                          </span>
                        )}
                      </div>
                      <span
                        className={`mt-1 inline-block rounded px-2 py-0.5 text-xs font-medium ${
                          typeInfo?.color ?? "bg-muted text-muted-foreground"
                        }`}
                      >
                        {typeInfo?.label ?? p.pathway_type}
                      </span>
                    </div>
                    <div className="ml-4 flex-shrink-0 text-right">
                      <p className="font-semibold">
                        {p.reduction_pct !== null
                          ? `${p.reduction_pct.toFixed(1)}% Reduktion`
                          : "—"}
                      </p>
                      <p className="text-xs text-muted-foreground">bis {p.target_year}</p>
                      {p.baseline_emissions_tco2e !== null && (
                        <p className="text-xs text-muted-foreground">
                          von {p.baseline_emissions_tco2e.toLocaleString("de-DE")} tCO₂e
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {showCreate && (
        <CreatePathwayModal orgId={orgId} onClose={() => setShowCreate(false)} />
      )}
    </div>
  );
}
