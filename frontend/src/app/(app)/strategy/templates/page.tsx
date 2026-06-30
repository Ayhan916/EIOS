"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listScenarioTemplates, listStressTestTemplates,
  createScenarioTemplate, createStressTestTemplate,
  type CreateScenarioTemplatePayload, type CreateStressTestTemplatePayload,
} from "@/lib/api/strategy";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import { Plus, X, Puzzle } from "lucide-react";

const SCENARIO_TEMPLATE_TYPES = [
  { value: "NET_ZERO", label: "Net Zero" },
  { value: "CARBON_PRICE_SHOCK", label: "CO₂-Preis-Schock" },
  { value: "SUPPLIER_FAILURE", label: "Lieferantenausfall" },
  { value: "REGULATORY_TIGHTENING", label: "Regulierungsverschärfung" },
  { value: "TAXONOMY_EXPANSION", label: "Taxonomie-Erweiterung" },
  { value: "CLIMATE_DISASTER", label: "Klimakatastrophe" },
];
const SCENARIO_TYPES = [
  { value: "CLIMATE", label: "Klima" },
  { value: "REGULATORY", label: "Regulierung" },
  { value: "FINANCIAL", label: "Finanziell" },
  { value: "SUPPLY_CHAIN", label: "Lieferkette" },
  { value: "COMBINED", label: "Kombiniert" },
];
const STRESS_TEMPLATE_TYPES = [
  { value: "CLIMATE", label: "Klima" },
  { value: "FINANCIAL", label: "Finanziell" },
  { value: "REGULATORY", label: "Regulierung" },
  { value: "SUPPLY_CHAIN", label: "Lieferkette" },
];
const SEVERITY_LEVELS = [
  { value: "LOW", label: "Gering", color: "bg-green-100 text-green-700" },
  { value: "MEDIUM", label: "Mittel", color: "bg-amber-100 text-amber-700" },
  { value: "HIGH", label: "Hoch", color: "bg-orange-100 text-orange-700" },
  { value: "EXTREME", label: "Extrem", color: "bg-red-100 text-red-700" },
];

function CreateScenarioTemplateModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const { t } = useLanguage();
  const [form, setForm] = useState({ template_name: "", template_type: "NET_ZERO", scenario_type: "CLIMATE", description: "", default_time_horizon_years: "5" });
  const [error, setError] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: (p: CreateScenarioTemplatePayload) => createScenarioTemplate(orgId, p),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["strategy", "scenario-templates", orgId] }); onClose(); },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Fehler"),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    if (!form.template_name.trim()) { setError("Name erforderlich"); return; }
    mut.mutate({
      template_name: form.template_name.trim(),
      template_type: form.template_type,
      scenario_type: form.scenario_type,
      description: form.description.trim() || undefined,
      default_time_horizon_years: parseInt(form.default_time_horizon_years, 10) || 5,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2"><Puzzle className="h-5 w-5 text-violet-600" /><h2 className="text-lg font-semibold">Neue Szenario-Vorlage</h2></div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100"><X className="h-5 w-5 text-slate-500" /></button>
        </div>
        <form onSubmit={submit} className="space-y-4 px-6 py-5">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("common.name")} <span className="text-red-500">*</span></label>
            <input value={form.template_name} onChange={(e) => setForm((f) => ({ ...f, template_name: e.target.value }))} placeholder="z. B. SBTi 1.5°C Standard" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Vorlagentyp</label>
              <select value={form.template_type} onChange={(e) => setForm((f) => ({ ...f, template_type: e.target.value }))} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
                {SCENARIO_TEMPLATE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Szenario-Typ</label>
              <select value={form.scenario_type} onChange={(e) => setForm((f) => ({ ...f, scenario_type: e.target.value }))} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
                {SCENARIO_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("common.description")}</label>
            <textarea value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} rows={2} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Standard-Zeithorizont (Jahre)</label>
            <input type="number" min={1} value={form.default_time_horizon_years} onChange={(e) => setForm((f) => ({ ...f, default_time_horizon_years: e.target.value }))} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        </form>
        <div className="flex justify-end gap-3 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose}>{t("common.cancel")}</Button>
          <Button onClick={submit} disabled={mut.isPending} className="bg-violet-600 hover:bg-violet-700">
            {mut.isPending ? <Spinner className="h-4 w-4" /> : t("strategy.addTemplate")}
          </Button>
        </div>
      </div>
    </div>
  );
}

function CreateStressTemplateModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const { t } = useLanguage();
  const [form, setForm] = useState({ template_name: "", template_type: "CLIMATE", severity_level: "MEDIUM", methodology: "" });
  const [error, setError] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: (p: CreateStressTestTemplatePayload) => createStressTestTemplate(orgId, p),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["strategy", "stress-templates", orgId] }); onClose(); },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Fehler"),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    if (!form.template_name.trim()) { setError("Name erforderlich"); return; }
    mut.mutate({
      template_name: form.template_name.trim(),
      template_type: form.template_type,
      severity_level: form.severity_level,
      methodology: form.methodology.trim() || undefined,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2"><Puzzle className="h-5 w-5 text-orange-600" /><h2 className="text-lg font-semibold">Neue Stresstest-Vorlage</h2></div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100"><X className="h-5 w-5 text-slate-500" /></button>
        </div>
        <form onSubmit={submit} className="space-y-4 px-6 py-5">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("common.name")} <span className="text-red-500">*</span></label>
            <input value={form.template_name} onChange={(e) => setForm((f) => ({ ...f, template_name: e.target.value }))} placeholder="z. B. Extremes Wetterereignis" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("common.type")}</label>
            <select value={form.template_type} onChange={(e) => setForm((f) => ({ ...f, template_type: e.target.value }))} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              {STRESS_TEMPLATE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">{t("common.severity")}</label>
            <div className="grid grid-cols-2 gap-2">
              {SEVERITY_LEVELS.map((s) => (
                <button key={s.value} type="button" onClick={() => setForm((f) => ({ ...f, severity_level: s.value }))} className={`rounded-lg border-2 px-3 py-2 text-sm font-medium transition-colors ${form.severity_level === s.value ? `${s.color} border-orange-400` : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"}`}>
                  {s.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Methodik (optional)</label>
            <input value={form.methodology} onChange={(e) => setForm((f) => ({ ...f, methodology: e.target.value }))} placeholder="z. B. TCFD, NGFS" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        </form>
        <div className="flex justify-end gap-3 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose}>{t("common.cancel")}</Button>
          <Button onClick={submit} disabled={mut.isPending} className="bg-orange-600 hover:bg-orange-700">
            {mut.isPending ? <Spinner className="h-4 w-4" /> : t("strategy.addTemplate")}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function TemplatesPage() {
  const { user } = useAuth();
  const { t } = useLanguage();
  const orgId = user?.organization_id ?? "default";
  const [modal, setModal] = useState<"scenario" | "stress" | null>(null);

  const { data: scenarioTemplates, isLoading: l1 } = useQuery({ queryKey: ["strategy", "scenario-templates", orgId], queryFn: () => listScenarioTemplates(orgId) });
  const { data: stressTemplates, isLoading: l2 } = useQuery({ queryKey: ["strategy", "stress-templates", orgId], queryFn: () => listStressTestTemplates(orgId) });

  if (l1 || l2) return <div className="flex h-64 items-center justify-center"><Spinner /></div>;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("strategy.templatesTitle")}</h1>
          <p className="text-muted-foreground">{t("strategy.templatesSubtitle")}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setModal("stress")} className="flex items-center gap-2">
            <Plus className="h-4 w-4" />Stresstest-Vorlage
          </Button>
          <Button onClick={() => setModal("scenario")} className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700">
            <Plus className="h-4 w-4" />Szenario-Vorlage
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-base">Szenario-Vorlagen</CardTitle>
            <span className="rounded-full bg-violet-100 px-2 py-0.5 text-xs font-semibold text-violet-700">{(scenarioTemplates ?? []).length}</span>
          </CardHeader>
          <CardContent>
            {(scenarioTemplates ?? []).length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-6 text-center">
                <Puzzle className="h-8 w-8 text-slate-300" />
                <p className="text-sm text-slate-500">Noch keine Szenario-Vorlagen</p>
                <Button onClick={() => setModal("scenario")} size="sm" className="mt-1 bg-violet-600 hover:bg-violet-700">
                  <Plus className="mr-1.5 h-3 w-3" />{t("common.create")}
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {(scenarioTemplates ?? []).map((t) => (
                  <div key={t.id} className="flex items-start justify-between rounded-lg border px-3 py-2.5 hover:bg-slate-50">
                    <div>
                      <p className="text-sm font-medium">{t.template_name}</p>
                      {t.description && <p className="line-clamp-1 text-xs text-muted-foreground">{t.description}</p>}
                      <div className="mt-1 flex gap-1">
                        <span className="rounded bg-violet-100 px-1.5 py-0.5 text-xs text-violet-700">{SCENARIO_TEMPLATE_TYPES.find((x) => x.value === t.template_type)?.label ?? t.template_type}</span>
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{t.default_time_horizon_years}J</span>
                      </div>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      <p>{t.usage_count}× genutzt</p>
                      {t.is_approved && <p className="font-medium text-green-600">Genehmigt</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-base">Stresstest-Vorlagen</CardTitle>
            <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-700">{(stressTemplates ?? []).length}</span>
          </CardHeader>
          <CardContent>
            {(stressTemplates ?? []).length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-6 text-center">
                <Puzzle className="h-8 w-8 text-slate-300" />
                <p className="text-sm text-slate-500">Noch keine Stresstest-Vorlagen</p>
                <Button onClick={() => setModal("stress")} size="sm" className="mt-1 bg-orange-600 hover:bg-orange-700">
                  <Plus className="mr-1.5 h-3 w-3" />{t("common.create")}
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {(stressTemplates ?? []).map((t) => {
                  const sev = SEVERITY_LEVELS.find((s) => s.value === t.severity_level);
                  return (
                    <div key={t.id} className="flex items-start justify-between rounded-lg border px-3 py-2.5 hover:bg-slate-50">
                      <div>
                        <p className="text-sm font-medium">{t.template_name}</p>
                        <div className="mt-1 flex gap-1">
                          <span className="rounded bg-orange-100 px-1.5 py-0.5 text-xs text-orange-700">{STRESS_TEMPLATE_TYPES.find((x) => x.value === t.template_type)?.label ?? t.template_type}</span>
                          {sev && <span className={`rounded px-1.5 py-0.5 text-xs ${sev.color}`}>{sev.label}</span>}
                        </div>
                      </div>
                      <div className="text-right text-xs text-muted-foreground">
                        <p>{t.usage_count}× genutzt</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {modal === "scenario" && <CreateScenarioTemplateModal orgId={orgId} onClose={() => setModal(null)} />}
      {modal === "stress" && <CreateStressTemplateModal orgId={orgId} onClose={() => setModal(null)} />}
    </div>
  );
}
