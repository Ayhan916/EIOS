"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listForecastModels, listForecastResults, listScenarios,
  createForecastModel, runForecast,
  type CreateForecastModelPayload, type RunForecastPayload, type ForecastResult,
} from "@/lib/api/strategy";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import { ArrowRight, ArrowRightLeft, Plus, X, LineChart, Play } from "lucide-react";

// ── #114 First-forecast wizard ────────────────────────────────────────────────

const FORECAST_WIZARD_KEY = "eios_forecast_wizard_seen";

function FirstForecastWizard({ onCreateModel }: { onCreateModel: () => void }) {
  const { t } = useLanguage();

  const WIZARD_STEPS = [
    { title: t("strategy.wizardStep1Title"), desc: t("strategy.wizardStep1Desc") },
    { title: t("strategy.wizardStep2Title"), desc: t("strategy.wizardStep2Desc") },
    { title: t("strategy.wizardStep3Title"), desc: t("strategy.wizardStep3Desc") },
    { title: t("strategy.wizardStep4Title"), desc: t("strategy.wizardStep4Desc") },
  ];
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (typeof window !== "undefined" && !localStorage.getItem(FORECAST_WIZARD_KEY)) {
      setVisible(true);
    }
  }, []);

  function dismiss() {
    localStorage.setItem(FORECAST_WIZARD_KEY, "1");
    setVisible(false);
  }

  if (!visible) return null;

  const current = WIZARD_STEPS[step];
  const isLast = step === WIZARD_STEPS.length - 1;

  return (
    <div className="rounded-2xl border border-violet-200 bg-violet-50/60 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-violet-600 text-xs font-bold text-white">
            {step + 1}
          </div>
          <p className="font-semibold text-sm text-violet-900">{current.title}</p>
        </div>
        <button onClick={dismiss} className="text-muted-foreground hover:text-foreground">
          <X className="h-4 w-4" />
        </button>
      </div>
      <p className="text-sm text-violet-800 leading-relaxed">{current.desc}</p>
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {WIZARD_STEPS.map((_, i) => (
            <div key={i} className={`h-1.5 rounded-full transition-all ${i === step ? "w-6 bg-violet-500" : "w-1.5 bg-violet-200"}`} />
          ))}
        </div>
        <div className="flex gap-2">
          {step > 0 && (
            <button onClick={() => setStep((s) => s - 1)} className="rounded-lg border border-violet-300 px-3 py-1.5 text-xs text-violet-700 hover:bg-violet-100">
              {t("common.back")}
            </button>
          )}
          {isLast ? (
            <button
              onClick={() => { dismiss(); onCreateModel(); }}
              className="flex items-center gap-1 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-700"
            >
              {t("strategy.createFirstModel")} <ArrowRight className="h-3 w-3" />
            </button>
          ) : (
            <button
              onClick={() => setStep((s) => s + 1)}
              className="flex items-center gap-1 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-700"
            >
              {t("common.next")} <ArrowRight className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
import { ForecastLineChart } from "@/components/charts/forecast-line-chart";
import type { ForecastDataPoint } from "@/components/charts/forecast-line-chart";

const METHODOLOGIES = [
  { value: "LINEAR_TREND" },
  { value: "WEIGHTED_MOVING_AVERAGE" },
  { value: "SCENARIO_PROJECTION" },
];

const FORECAST_TYPES = [
  { value: "KPI", label: "KPI" },
  { value: "EMISSIONS" },
  { value: "TARGETS" },
  { value: "GREEN_REVENUE", label: "Green Revenue" },
  { value: "TAXONOMY" },
];

function CreateModelModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [form, setForm] = useState({ model_name: "", methodology: "LINEAR_TREND", description: "", model_version: "1.0.0" });
  const [error, setError] = useState<string | null>(null);

  const methodologyLabels: Record<string, string> = {
    LINEAR_TREND: t("strategy.methodLinear"),
    WEIGHTED_MOVING_AVERAGE: t("strategy.methodWeighted"),
    SCENARIO_PROJECTION: t("strategy.methodScenario"),
  };

  const mut = useMutation({
    mutationFn: (p: CreateForecastModelPayload) => createForecastModel(orgId, p),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["strategy", "forecast-models", orgId] }); onClose(); },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : t("strategy.errorModelCreate")),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    if (!form.model_name.trim()) { setError(t("strategy.forecastNameRequired")); return; }
    mut.mutate({
      model_name: form.model_name.trim(),
      methodology: form.methodology,
      description: form.description.trim() || undefined,
      model_version: form.model_version || "1.0.0",
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2">
            <LineChart className="h-5 w-5 text-violet-600" />
            <h2 className="text-lg font-semibold">{t("strategy.newForecastModel")}</h2>
          </div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100">
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>
        <form onSubmit={submit} className="space-y-4 px-6 py-5">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("common.name")} <span className="text-red-500">*</span></label>
            <input value={form.model_name} onChange={(e) => setForm((f) => ({ ...f, model_name: e.target.value }))} placeholder="z. B. Emissions Linear 2030" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("strategy.methodology")}</label>
            <select value={form.methodology} onChange={(e) => setForm((f) => ({ ...f, methodology: e.target.value }))} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500">
              {METHODOLOGIES.map((m) => <option key={m.value} value={m.value}>{methodologyLabels[m.value]}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("common.description")}</label>
            <textarea value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} rows={2} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("common.version")}</label>
            <input value={form.model_version} onChange={(e) => setForm((f) => ({ ...f, model_version: e.target.value }))} placeholder="1.0.0" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        </form>
        <div className="flex justify-end gap-3 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose}>{t("common.cancel")}</Button>
          <Button onClick={submit} disabled={mut.isPending} className="bg-violet-600 hover:bg-violet-700">
            {mut.isPending ? <Spinner className="h-4 w-4" /> : t("strategy.createModel")}
          </Button>
        </div>
      </div>
    </div>
  );
}

function RunForecastModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const { data: models } = useQuery({ queryKey: ["strategy", "forecast-models", orgId], queryFn: () => listForecastModels(orgId) });
  const { data: scenarios } = useQuery({ queryKey: ["strategy", "scenarios", orgId], queryFn: () => listScenarios(orgId) });
  const currentYear = new Date().getFullYear();
  const [form, setForm] = useState({ forecast_model_id: "", forecast_type: "EMISSIONS", target_metric: "", forecast_year: String(currentYear + 5), baseline_value: "", scenario_id: "" });
  const [error, setError] = useState<string | null>(null);

  const forecastTypeLabels: Record<string, string> = {
    KPI: "KPI",
    EMISSIONS: t("strategy.forecastTypeEmissions"),
    TARGETS: t("strategy.forecastTypeTargets"),
    GREEN_REVENUE: t("finEsg.greenRevenueTitle" as Parameters<typeof t>[0]),
    TAXONOMY: t("strategy.forecastTypeTaxonomy"),
  };

  const mut = useMutation({
    mutationFn: (p: RunForecastPayload) => runForecast(orgId, p),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["strategy", "forecast-results", orgId] }); onClose(); },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : t("strategy.errorForecastCreate")),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    if (!form.forecast_model_id) { setError(t("strategy.errorModelRequired")); return; }
    if (!form.target_metric.trim()) { setError(t("strategy.errorMetricRequired")); return; }
    const year = parseInt(form.forecast_year, 10);
    const baseline = parseFloat(form.baseline_value);
    if (isNaN(year) || isNaN(baseline)) { setError(t("strategy.errorNumericFields")); return; }
    mut.mutate({
      forecast_model_id: form.forecast_model_id,
      forecast_type: form.forecast_type,
      target_metric: form.target_metric.trim(),
      forecast_year: year,
      baseline_value: baseline,
      scenario_id: form.scenario_id || undefined,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2">
            <Play className="h-5 w-5 text-violet-600" />
            <h2 className="text-lg font-semibold">{t("strategy.runForecast")}</h2>
          </div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100">
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>
        <form onSubmit={submit} className="space-y-4 px-6 py-5">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("strategy.addModel")} <span className="text-red-500">*</span></label>
            <select value={form.forecast_model_id} onChange={(e) => setForm((f) => ({ ...f, forecast_model_id: e.target.value }))} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500">
              <option value="">{t("strategy.selectModel")}</option>
              {(models ?? []).map((m) => <option key={m.id} value={m.id}>{m.model_name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">{t("common.type")}</label>
              <select value={form.forecast_type} onChange={(e) => setForm((f) => ({ ...f, forecast_type: e.target.value }))} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500">
                {FORECAST_TYPES.map((ft) => <option key={ft.value} value={ft.value}>{forecastTypeLabels[ft.value] ?? ft.value}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">{t("strategy.forecastYear")}</label>
              <input type="number" value={form.forecast_year} onChange={(e) => setForm((f) => ({ ...f, forecast_year: e.target.value }))} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("strategy.targetMetric")} <span className="text-red-500">*</span></label>
            <input value={form.target_metric} onChange={(e) => setForm((f) => ({ ...f, target_metric: e.target.value }))} placeholder="z. B. total_emissions_tco2e" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("strategy.baselineValue")} <span className="text-red-500">*</span></label>
            <input type="number" value={form.baseline_value} onChange={(e) => setForm((f) => ({ ...f, baseline_value: e.target.value }))} placeholder="84500" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("strategy.forecastScenarioOptional")}</label>
            <select value={form.scenario_id} onChange={(e) => setForm((f) => ({ ...f, scenario_id: e.target.value }))} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500">
              <option value="">{t("strategy.noScenarioSelected")}</option>
              {(scenarios ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        </form>
        <div className="flex justify-end gap-3 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose}>{t("common.cancel")}</Button>
          <Button onClick={submit} disabled={mut.isPending} className="bg-violet-600 hover:bg-violet-700">
            {mut.isPending ? <Spinner className="h-4 w-4" /> : t("strategy.startForecast")}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Comparison View ───────────────────────────────────────────────────────────

function ForecastComparePanel({ results }: { results: ForecastResult[] }) {
  const { t } = useLanguage();
  const [idA, setIdA] = useState("");
  const [idB, setIdB] = useState("");

  const a = results.find((r) => r.id === idA);
  const b = results.find((r) => r.id === idB);

  function delta(av: number | null, bv: number | null) {
    if (av == null || bv == null || av === 0) return null;
    return ((bv - av) / Math.abs(av)) * 100;
  }

  const fields: Array<{ label: string; key: keyof ForecastResult }> = [
    { label: t("strategy.compareTargetMetric"), key: "target_metric" },
    { label: t("strategy.compareForecastYear"), key: "forecast_year" },
    { label: t("strategy.compareBaselineValue"), key: "baseline_value" },
    { label: t("strategy.compareForecastValue"), key: "forecast_value" },
    { label: t("strategy.compareLowerBound"), key: "lower_bound" },
    { label: t("strategy.compareUpperBound"), key: "upper_bound" },
    { label: t("strategy.compareConfidence"), key: "confidence_level" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <ArrowRightLeft className="h-4 w-4 text-violet-600" />
          {t("strategy.compareView")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">{t("strategy.forecastA")}</label>
            <select
              value={idA}
              onChange={(e) => setIdA(e.target.value)}
              className="w-full h-8 rounded border border-input bg-background px-2 text-sm"
            >
              <option value="">— —</option>
              {results.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.target_metric} ({r.forecast_year})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">{t("strategy.forecastB")}</label>
            <select
              value={idB}
              onChange={(e) => setIdB(e.target.value)}
              className="w-full h-8 rounded border border-input bg-background px-2 text-sm"
            >
              <option value="">— —</option>
              {results.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.target_metric} ({r.forecast_year})
                </option>
              ))}
            </select>
          </div>
        </div>

        {a && b && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-separate border-spacing-0">
              <thead>
                <tr className="text-xs text-muted-foreground">
                  <th className="py-2 text-left pr-4 font-medium">{t("strategy.compareMetric")}</th>
                  <th className="py-2 text-right font-medium text-violet-700">{t("strategy.forecastA")}</th>
                  <th className="py-2 text-right font-medium text-blue-700">{t("strategy.forecastB")}</th>
                  <th className="py-2 text-right font-medium">Δ</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {fields.map(({ label, key }) => {
                  const av = a[key] as number | string | null;
                  const bv = b[key] as number | string | null;
                  const d = typeof av === "number" && typeof bv === "number" ? delta(av, bv) : null;
                  return (
                    <tr key={label}>
                      <td className="py-2 pr-4 text-xs text-muted-foreground">{label}</td>
                      <td className="py-2 text-right font-mono text-xs">
                        {typeof av === "number" ? av.toLocaleString("de-DE") : (av ?? "—")}
                      </td>
                      <td className="py-2 text-right font-mono text-xs">
                        {typeof bv === "number" ? bv.toLocaleString("de-DE") : (bv ?? "—")}
                      </td>
                      <td className="py-2 text-right text-xs font-medium">
                        {d != null ? (
                          <span className={d > 0 ? "text-red-600" : d < 0 ? "text-emerald-600" : "text-muted-foreground"}>
                            {d > 0 ? "+" : ""}{d.toFixed(1)}%
                          </span>
                        ) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {(!a || !b) && (
          <p className="text-center text-sm text-muted-foreground py-4">
            {t("strategy.compareHint")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default function ForecastsPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";
  const [modal, setModal] = useState<"model" | "run" | null>(null);

  const { data: models, isLoading: l1 } = useQuery({ queryKey: ["strategy", "forecast-models", orgId], queryFn: () => listForecastModels(orgId) });
  const { data: results, isLoading: l2 } = useQuery({ queryKey: ["strategy", "forecast-results", orgId], queryFn: () => listForecastResults(orgId) });

  if (l1 || l2) return <div className="flex h-64 items-center justify-center"><Spinner /></div>;

  const methodologyLabels: Record<string, string> = {
    LINEAR_TREND: t("strategy.methodLinear"),
    WEIGHTED_MOVING_AVERAGE: t("strategy.methodWeighted"),
    SCENARIO_PROJECTION: t("strategy.methodScenario"),
  };

  const forecastTypeLabels: Record<string, string> = {
    KPI: "KPI",
    EMISSIONS: t("strategy.forecastTypeEmissions"),
    TARGETS: t("strategy.forecastTypeTargets"),
    GREEN_REVENUE: t("finEsg.greenRevenueTitle" as Parameters<typeof t>[0]),
    TAXONOMY: t("strategy.forecastTypeTaxonomy"),
  };

  const chartData: ForecastDataPoint[] = [...new Set((results ?? []).map((r) => r.forecast_year))]
    .sort((a, b) => a - b)
    .map((year) => {
      const r = (results ?? []).find((x) => x.forecast_year === year);
      return { period: String(year), baseline: r?.baseline_value ?? null, forecast: r?.forecast_value ?? null };
    });

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("strategy.forecastsTitle")}</h1>
          <p className="text-muted-foreground">{t("strategy.forecastsSubtitle")}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setModal("model")} className="flex items-center gap-2">
            <Plus className="h-4 w-4" />{t("strategy.addModel")}
          </Button>
          <Button onClick={() => setModal("run")} className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700">
            <Play className="h-4 w-4" />{t("strategy.startForecast")}
          </Button>
        </div>
      </div>

      {/* #114 First-forecast wizard */}
      {(models ?? []).length === 0 && (results ?? []).length === 0 && (
        <FirstForecastWizard onCreateModel={() => setModal("model")} />
      )}

      <div className="grid grid-cols-2 gap-4">
        <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">{t("strategy.modelsCount")}</p><p className="mt-1 text-3xl font-bold">{(models ?? []).length}</p></CardContent></Card>
        <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">{t("strategy.forecastsCount")}</p><p className="mt-1 text-3xl font-bold">{(results ?? []).length}</p></CardContent></Card>
      </div>

      {chartData.length > 0 && (
        <Card>
          <CardHeader><CardTitle>{t("strategy.forecastHistory")}</CardTitle></CardHeader>
          <CardContent>
            <ForecastLineChart data={chartData} unit=" tCO₂e" height={280} />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>{t("strategy.forecastModels")}</CardTitle></CardHeader>
        <CardContent>
          {(models ?? []).length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <LineChart className="h-10 w-10 text-slate-300" />
              <p className="text-sm text-slate-600">{t("strategy.noForecasts")}</p>
              <Button onClick={() => setModal("model")} className="bg-violet-600 hover:bg-violet-700">
                <Plus className="mr-2 h-4 w-4" />{t("strategy.createFirstModel")}
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {(models ?? []).map((m) => (
                <div key={m.id} className="flex items-center justify-between rounded-lg border px-4 py-3 hover:bg-slate-50">
                  <div>
                    <p className="font-medium">{m.model_name}</p>
                    {m.description && <p className="text-xs text-muted-foreground">{m.description}</p>}
                    <span className="mt-1 inline-block rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                      {methodologyLabels[m.methodology] ?? m.methodology}
                    </span>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    <p>v{m.model_version}</p>
                    {m.is_approved && <p className="font-medium text-green-600">{t("strategy.forecastApproved")}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {(results ?? []).length > 0 && (
        <Card>
          <CardHeader><CardTitle>{t("strategy.forecastResults")}</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {(results ?? []).map((r) => (
                <div key={r.id} className="flex items-center justify-between rounded-lg border px-4 py-3 hover:bg-slate-50">
                  <div>
                    <p className="font-medium">{r.target_metric}</p>
                    <div className="mt-1 flex gap-2">
                      <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                        {forecastTypeLabels[r.forecast_type] ?? r.forecast_type}
                      </span>
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{r.forecast_year}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">{r.forecast_value !== null ? r.forecast_value.toLocaleString("de-DE") : "—"}</p>
                    <p className="text-xs text-muted-foreground">
                      {t("strategy.forecastBaseLabel").replace("{value}", r.baseline_value?.toLocaleString("de-DE") ?? "—")}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {(results ?? []).length >= 2 && (
        <ForecastComparePanel results={results ?? []} />
      )}

      {modal === "model" && <CreateModelModal orgId={orgId} onClose={() => setModal(null)} />}
      {modal === "run" && <RunForecastModal orgId={orgId} onClose={() => setModal(null)} />}
    </div>
  );
}
