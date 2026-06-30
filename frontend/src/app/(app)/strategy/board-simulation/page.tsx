"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listBoardSimulations, listScenarios, createBoardSimulation, type CreateBoardSimulationPayload } from "@/lib/api/strategy";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import { Download, Loader2, Plus, X, Users } from "lucide-react";

function CreateSimulationModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const { data: scenarios } = useQuery({ queryKey: ["strategy", "scenarios", orgId], queryFn: () => listScenarios(orgId) });
  const [form, setForm] = useState({ simulation_name: "", scenario_a_id: "", scenario_b_id: "", scenario_c_id: "", recommendation: "" });
  const [error, setError] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: (p: CreateBoardSimulationPayload) => createBoardSimulation(orgId, p),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["strategy", "board-simulations", orgId] }); onClose(); },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Fehler"),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    if (!form.simulation_name.trim()) { setError("Name erforderlich"); return; }
    if (!form.scenario_a_id && !form.scenario_b_id && !form.scenario_c_id) { setError("Mindestens ein Szenario wählen"); return; }
    mut.mutate({
      simulation_name: form.simulation_name.trim(),
      scenario_a_id: form.scenario_a_id || undefined,
      scenario_b_id: form.scenario_b_id || undefined,
      scenario_c_id: form.scenario_c_id || undefined,
      recommendation: form.recommendation.trim() || undefined,
    });
  }

  const scenarioOptions = (scenarios ?? []).map((s) => ({ id: s.id, name: s.name }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-violet-600" />
            <h2 className="text-lg font-semibold">Neue Board Simulation</h2>
          </div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100"><X className="h-5 w-5 text-slate-500" /></button>
        </div>
        <form onSubmit={submit} className="space-y-5 px-6 py-5">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Name <span className="text-red-500">*</span></label>
            <input value={form.simulation_name} onChange={(e) => setForm((f) => ({ ...f, simulation_name: e.target.value }))} placeholder="z. B. Q4 Board Szenariovergleich" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Szenarien vergleichen</label>
            <p className="mb-3 text-xs text-slate-500">Wähle bis zu 3 Szenarien für den Board-Level-Vergleich</p>
            {(["a", "b", "c"] as const).map((slot, i) => (
              <div key={slot} className="mb-3">
                <label className="mb-1 block text-xs font-medium text-slate-600">Szenario {String.fromCharCode(65 + i)}</label>
                <select
                  value={form[`scenario_${slot}_id` as keyof typeof form]}
                  onChange={(e) => setForm((f) => ({ ...f, [`scenario_${slot}_id`]: e.target.value }))}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="">— Keines —</option>
                  {scenarioOptions.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
            ))}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Empfehlung (optional)</label>
            <textarea value={form.recommendation} onChange={(e) => setForm((f) => ({ ...f, recommendation: e.target.value }))} placeholder="Welches Szenario empfiehlst du dem Board und warum?" rows={3} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        </form>
        <div className="flex justify-end gap-3 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose}>{t("common.cancel")}</Button>
          <Button onClick={submit} disabled={mut.isPending} className="bg-violet-600 hover:bg-violet-700">
            {mut.isPending ? <Spinner className="h-4 w-4" /> : "Simulation erstellen"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function PptxDownloadButton({ simId, simName }: { simId: string; simName: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDownload() {
    setBusy(true);
    setError(null);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("eios_access_token") : null;
      const res = await fetch(`/api/v1/commercial/strategy/board-simulations/${simId}/export?format=pptx`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`Export unavailable (${res.status})`);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${simName.replace(/\s+/g, "_").toLowerCase()}.pptx`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      setError((e as Error).message);
      setTimeout(() => setError(null), 3000);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleDownload}
        disabled={busy}
        className="inline-flex items-center gap-1.5 rounded-md border border-violet-200 bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-700 hover:bg-violet-100 disabled:opacity-50 transition-colors"
      >
        {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />}
        Export PPTX
      </button>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}

export default function BoardSimulationPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";
  const [showCreate, setShowCreate] = useState(false);

  const { data: simulations, isLoading } = useQuery({ queryKey: ["strategy", "board-simulations", orgId], queryFn: () => listBoardSimulations(orgId) });
  const { data: scenarios } = useQuery({ queryKey: ["strategy", "scenarios", orgId], queryFn: () => listScenarios(orgId) });

  if (isLoading) return <div className="flex h-64 items-center justify-center"><Spinner /></div>;

  const scenarioMap = Object.fromEntries((scenarios ?? []).map((s) => [s.id, s.name]));

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("strategy.boardSimTitle")}</h1>
          <p className="text-muted-foreground">{t("strategy.boardSimSubtitle")}</p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700">
          <Plus className="h-4 w-4" />Neue Simulation
        </Button>
      </div>

      <Card>
        <CardHeader><CardTitle>Simulationen</CardTitle></CardHeader>
        <CardContent>
          {(simulations ?? []).length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <Users className="h-10 w-10 text-slate-300" />
              <p className="text-sm text-slate-600">Noch keine Board-Simulation erstellt</p>
              <Button onClick={() => setShowCreate(true)} className="mt-1 bg-violet-600 hover:bg-violet-700">
                <Plus className="mr-2 h-4 w-4" />Erste Simulation erstellen
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {(simulations ?? []).map((sim) => (
                <div key={sim.id} className="rounded-xl border p-4 transition-colors hover:bg-slate-50">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold">{sim.simulation_name}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">{new Date(sim.created_at).toLocaleDateString("de-DE")}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {sim.is_final && <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">FINAL</span>}
                      <PptxDownloadButton simId={sim.id} simName={sim.simulation_name} />
                    </div>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    {(["a", "b", "c"] as const).map((slot, i) => {
                      const id = sim[`scenario_${slot}_id` as "scenario_a_id" | "scenario_b_id" | "scenario_c_id"];
                      return id ? (
                        <div key={slot} className="rounded-lg bg-slate-100 px-3 py-2">
                          <p className="text-xs font-medium text-slate-500">Szenario {String.fromCharCode(65 + i)}</p>
                          <p className="mt-0.5 line-clamp-1 text-sm font-medium">{scenarioMap[id] ?? id.slice(0, 8)}</p>
                        </div>
                      ) : null;
                    })}
                  </div>
                  {sim.recommendation && (
                    <div className="mt-3 rounded-md bg-violet-50 px-3 py-2">
                      <p className="text-xs font-medium text-violet-700">Empfehlung</p>
                      <p className="mt-0.5 line-clamp-2 text-sm text-violet-900">{sim.recommendation}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {showCreate && <CreateSimulationModal orgId={orgId} onClose={() => setShowCreate(false)} />}
    </div>
  );
}
