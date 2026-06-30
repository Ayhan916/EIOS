"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listScenarios,
  listExecutions,
  listDigitalTwins,
  createScenario,
  runScenario,
  type CreateScenarioPayload,
  type ScenarioExecution,
} from "@/lib/api/strategy";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { Play, Plus, X, GitBranch, Lightbulb } from "lucide-react";
import { ScenarioRadarChart } from "@/components/charts/scenario-radar-chart";
import type { ScenarioKpiPoint } from "@/components/charts/scenario-radar-chart";
import { useLanguage } from "@/lib/i18n/context";

// ── Constants ─────────────────────────────────────────────────────────────────

const SCENARIO_TYPES = [
  { value: "CLIMATE", label: "Klima" },
  { value: "REGULATORY", label: "Regulierung" },
  { value: "FINANCIAL", label: "Finanziell" },
  { value: "SUPPLY_CHAIN", label: "Lieferkette" },
  { value: "COMBINED", label: "Kombiniert" },
];

const TYPE_COLORS: Record<string, string> = {
  CLIMATE: "bg-blue-100 text-blue-700",
  REGULATORY: "bg-purple-100 text-purple-700",
  FINANCIAL: "bg-green-100 text-green-700",
  SUPPLY_CHAIN: "bg-amber-100 text-amber-700",
  COMBINED: "bg-slate-100 text-slate-700",
};

const STATUS_COLORS: Record<string, string> = {
  Draft: "bg-slate-100 text-slate-600",
  Active: "bg-green-100 text-green-700",
  Archived: "bg-orange-100 text-orange-700",
};

// ── Create Modal ──────────────────────────────────────────────────────────────

function CreateScenarioModal({
  orgId,
  onClose,
}: {
  orgId: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const { t } = useLanguage();
  const [form, setForm] = useState({
    name: "",
    scenario_type: "CLIMATE",
    description: "",
    baseline_twin_id: "",
    time_horizon_years: "5",
    is_template: false,
  });
  const [error, setError] = useState<string | null>(null);

  const { data: twins } = useQuery({
    queryKey: ["strategy", "digital-twin", orgId],
    queryFn: () => listDigitalTwins(orgId),
  });

  const mutation = useMutation({
    mutationFn: (payload: CreateScenarioPayload) => createScenario(orgId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategy", "scenarios", orgId] });
      onClose();
    },
    onError: (e: unknown) => {
      setError(e instanceof Error ? e.message : "Fehler beim Erstellen");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!form.name.trim()) {
      setError("Name ist erforderlich.");
      return;
    }
    const horizon = parseInt(form.time_horizon_years, 10);
    if (isNaN(horizon) || horizon < 1) {
      setError("Zeithorizont muss mindestens 1 Jahr sein.");
      return;
    }
    mutation.mutate({
      name: form.name.trim(),
      scenario_type: form.scenario_type,
      description: form.description.trim() || undefined,
      baseline_twin_id: form.baseline_twin_id || undefined,
      time_horizon_years: horizon,
      is_template: form.is_template,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="relative w-full max-w-lg rounded-xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-violet-600" />
            <h2 className="text-lg font-semibold">Neues Szenario</h2>
          </div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100">
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5 px-6 py-5">
          {/* Name */}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="z. B. EU-Taxonomie Verschärfung 2027"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
            />
          </div>

          {/* Szenario-Typ */}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Typ <span className="text-red-500">*</span>
            </label>
            <div className="flex flex-wrap gap-2">
              {SCENARIO_TYPES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setForm((f) => ({ ...f, scenario_type: t.value }))}
                  className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
                    form.scenario_type === t.value
                      ? TYPE_COLORS[t.value] + " ring-2 ring-offset-1 ring-violet-400"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Beschreibung */}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Beschreibung
            </label>
            <textarea
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="Was wird in diesem Szenario modelliert?"
              rows={2}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
            />
          </div>

          {/* Zeithorizont & Baseline Twin */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Zeithorizont (Jahre)
              </label>
              <input
                type="number"
                min={1}
                max={30}
                value={form.time_horizon_years}
                onChange={(e) =>
                  setForm((f) => ({ ...f, time_horizon_years: e.target.value }))
                }
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">
                Baseline Digital Twin
              </label>
              <select
                value={form.baseline_twin_id}
                onChange={(e) =>
                  setForm((f) => ({ ...f, baseline_twin_id: e.target.value }))
                }
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
              >
                <option value="">— Keiner —</option>
                {(twins ?? []).map((twin) => (
                  <option key={twin.id} value={twin.id}>
                    {twin.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Als Template */}
          <label className="flex cursor-pointer items-center gap-3">
            <input
              type="checkbox"
              checked={form.is_template}
              onChange={(e) => setForm((f) => ({ ...f, is_template: e.target.checked }))}
              className="h-4 w-4 rounded border-slate-300 text-violet-600 focus:ring-violet-500"
            />
            <span className="text-sm text-slate-700">
              Als Vorlage speichern{" "}
              <span className="text-xs text-slate-400">(wiederverwendbar für andere Szenarien)</span>
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
              t("strategy.addScenario")
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── KPI Impact Table ─────────────────────────────────────────────────────────

function KpiImpactTable({ exec }: { exec: ScenarioExecution }) {
  const kpis = exec.projected_kpis as Record<string, { baseline?: number; projected?: number; change_pct?: number }> | null;
  if (!kpis || Object.keys(kpis).length === 0) {
    return (
      <p className="text-xs text-muted-foreground px-1 py-2">
        No KPI impact data returned by this execution.
      </p>
    );
  }

  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="border-b text-muted-foreground">
          <th className="py-1 pr-4 text-left font-medium">KPI</th>
          <th className="py-1 pr-4 text-right font-medium">Baseline</th>
          <th className="py-1 pr-4 text-right font-medium">Projected</th>
          <th className="py-1 text-right font-medium">Δ</th>
        </tr>
      </thead>
      <tbody>
        {Object.entries(kpis).map(([name, vals]) => {
          const delta = vals.change_pct ?? (
            vals.baseline != null && vals.projected != null
              ? ((vals.projected - vals.baseline) / (Math.abs(vals.baseline) || 1)) * 100
              : null
          );
          return (
            <tr key={name} className="border-b border-border/40 last:border-0">
              <td className="py-1 pr-4 font-medium">{name.replace(/_/g, " ")}</td>
              <td className="py-1 pr-4 text-right text-muted-foreground">
                {vals.baseline != null ? vals.baseline.toFixed(1) : "—"}
              </td>
              <td className="py-1 pr-4 text-right">
                {vals.projected != null ? vals.projected.toFixed(1) : "—"}
              </td>
              <td className={`py-1 text-right font-semibold ${
                delta == null ? "text-muted-foreground"
                  : delta > 0 ? "text-emerald-600"
                  : delta < 0 ? "text-red-600"
                  : "text-muted-foreground"
              }`}>
                {delta != null ? `${delta > 0 ? "+" : ""}${delta.toFixed(1)}%` : "—"}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// ── Run Scenario Panel ────────────────────────────────────────────────────────

function RunScenarioPanel({ scenarioId, orgId }: { scenarioId: string; orgId: string }) {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<ScenarioExecution | null>(null);

  const mutation = useMutation({
    mutationFn: () => runScenario(orgId, scenarioId),
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ["strategy", "executions", orgId] });
    },
  });

  if (result) {
    return (
      <div className="mt-3 rounded-lg border border-border bg-muted/20 p-3 space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold">KPI Impact — Execution {result.id.slice(0, 8)}</p>
          <span className={`text-[10px] rounded-full px-2 py-0.5 font-medium ${
            result.execution_status === "completed" ? "bg-green-100 text-green-700"
              : result.execution_status === "failed" ? "bg-red-100 text-red-700"
              : "bg-blue-100 text-blue-700"
          }`}>
            {result.execution_status}
          </span>
        </div>
        <KpiImpactTable exec={result} />
        <button
          onClick={() => setResult(null)}
          className="text-[10px] text-muted-foreground hover:text-foreground"
        >
          Close
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending}
      className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100 transition-colors disabled:opacity-60"
    >
      {mutation.isPending ? (
        <span className="h-3 w-3 animate-spin rounded-full border border-emerald-700 border-t-transparent" />
      ) : (
        <Play className="h-3 w-3" />
      )}
      {mutation.isPending ? "Running…" : "Run Scenario"}
    </button>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ScenariosPage() {
  const { user } = useAuth();
  const { t } = useLanguage();
  const orgId = user?.organization_id ?? "default";
  const [showCreate, setShowCreate] = useState(false);
  const queryClient = useQueryClient();

  const examplesMut = useMutation({
    mutationFn: async () => {
      const examples: CreateScenarioPayload[] = [
        { name: "Net-Zero 2030", scenario_type: "CLIMATE", description: "2°C-aligned decarbonization pathway to 2030", time_horizon_years: 5, is_template: true },
        { name: "CSRD Compliance", scenario_type: "REGULATORY", description: "Full CSRD Article 29 compliance scenario", time_horizon_years: 3, is_template: false },
        { name: "Supply Chain Disruption", scenario_type: "SUPPLY_CHAIN", description: "Tier-1 supplier concentration risk shock", time_horizon_years: 2, is_template: false },
      ];
      for (const ex of examples) await createScenario(orgId, ex);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["strategy", "scenarios", orgId] }),
  });

  const { data: scenarios, isLoading: l1 } = useQuery({
    queryKey: ["strategy", "scenarios", orgId],
    queryFn: () => listScenarios(orgId),
  });
  const { data: executions, isLoading: l2 } = useQuery({
    queryKey: ["strategy", "executions", orgId],
    queryFn: () => listExecutions(orgId),
  });

  if (l1 || l2) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const execByScenario = (executions ?? []).reduce<Record<string, number>>((acc, e) => {
    acc[e.scenario_id] = (acc[e.scenario_id] ?? 0) + 1;
    return acc;
  }, {});

  const activeCount = (scenarios ?? []).filter((s) => s.scenario_status === "Active").length;

  const firstScenario = (scenarios ?? [])[0];
  const radarData: ScenarioKpiPoint[] = firstScenario
    ? [
        { kpi: "Zeithorizont", baseline: 50, scenario: Math.min(100, (firstScenario.time_horizon_years / 30) * 100) },
        { kpi: "Klimarisiko", baseline: 65, scenario: firstScenario.scenario_type === "CLIMATE" ? 88 : 55 },
        { kpi: "Regulierung", baseline: 60, scenario: firstScenario.scenario_type === "REGULATORY" ? 92 : 58 },
        { kpi: "Finanzen", baseline: 70, scenario: firstScenario.scenario_type === "FINANCIAL" ? 85 : 68 },
        { kpi: "Lieferkette", baseline: 55, scenario: firstScenario.scenario_type === "SUPPLY_CHAIN" ? 80 : 52 },
      ]
    : [];

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Scenario Framework</h1>
          <p className="text-muted-foreground">
            Klima-, Regulierungs-, Finanz- und kombinierte Szenarien
          </p>
        </div>
        <Button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700"
        >
          <Plus className="h-4 w-4" />
          Neues Szenario
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Szenarien gesamt</p>
            <p className="mt-1 text-3xl font-bold">{(scenarios ?? []).length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Ausführungen</p>
            <p className="mt-1 text-3xl font-bold">{(executions ?? []).length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">{t("common.active")}</p>
            <p className="mt-1 text-3xl font-bold text-green-600">{activeCount}</p>
          </CardContent>
        </Card>
      </div>

      {radarData.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Szenario-Risikoprofil — {firstScenario?.name}</CardTitle></CardHeader>
          <CardContent>
            <ScenarioRadarChart
              data={radarData}
              scenarioLabel={firstScenario?.name ?? "Szenario"}
              height={320}
            />
          </CardContent>
        </Card>
      )}

      {/* Scenario List */}
      <Card>
        <CardHeader>
          <CardTitle>{t("strategy.scenariosTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {(scenarios ?? []).length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <GitBranch className="h-10 w-10 text-slate-300" />
              <p className="text-sm font-medium text-slate-600">{t("strategy.noScenarios")}</p>
              <p className="text-xs text-muted-foreground max-w-xs">
                Erstelle dein erstes Szenario manuell oder lade Beispiel-Szenarien, um direkt loszulegen.
              </p>
              <div className="flex gap-2 mt-1">
                <Button
                  onClick={() => setShowCreate(true)}
                  className="bg-violet-600 hover:bg-violet-700"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  {t("strategy.addScenario")}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => examplesMut.mutate()}
                  disabled={examplesMut.isPending}
                >
                  <Lightbulb className="mr-2 h-4 w-4" />
                  {examplesMut.isPending ? "Wird geladen…" : "Beispiele laden"}
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {(scenarios ?? []).map((s) => (
                <div
                  key={s.id}
                  className="rounded-lg border px-4 py-3 transition-colors hover:bg-slate-50"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{s.name}</p>
                        {s.is_template && (
                          <span className="rounded bg-violet-100 px-1.5 py-0.5 text-xs font-medium text-violet-700">
                            Vorlage
                          </span>
                        )}
                      </div>
                      {s.description && (
                        <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1">
                          {s.description}
                        </p>
                      )}
                      <div className="mt-2 flex items-center gap-2 flex-wrap">
                        <span
                          className={`rounded px-2 py-0.5 text-xs font-medium ${
                            TYPE_COLORS[s.scenario_type] ?? "bg-muted text-muted-foreground"
                          }`}
                        >
                          {SCENARIO_TYPES.find((t) => t.value === s.scenario_type)?.label ??
                            s.scenario_type}
                        </span>
                        <span
                          className={`rounded px-2 py-0.5 text-xs font-medium ${
                            STATUS_COLORS[s.scenario_status] ?? "bg-muted text-muted-foreground"
                          }`}
                        >
                          {s.scenario_status}
                        </span>
                        <RunScenarioPanel scenarioId={s.id} orgId={orgId} />
                      </div>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <p className="text-sm font-semibold">{s.time_horizon_years} Jahre</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {execByScenario[s.id] ?? 0} Ausführung(en)
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {showCreate && (
        <CreateScenarioModal orgId={orgId} onClose={() => setShowCreate(false)} />
      )}
    </div>
  );
}
