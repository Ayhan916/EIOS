"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listReports, listScenarios, createReport, type CreateReportPayload } from "@/lib/api/strategy";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { Plus, X, FileText, Lock } from "lucide-react";
import { useLanguage } from "@/lib/i18n/context";

function CreateReportModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const { data: scenarios } = useQuery({ queryKey: ["strategy", "scenarios", orgId], queryFn: () => listScenarios(orgId) });
  const currentYear = new Date().getFullYear();
  const [form, setForm] = useState({ report_title: "", report_period: String(currentYear), report_methodology: "", selected_scenario_ids: [] as string[] });
  const [error, setError] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: (p: CreateReportPayload) => createReport(orgId, p),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["strategy", "reports", orgId] }); onClose(); },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Fehler"),
  });

  function toggleScenario(id: string) {
    setForm((f) => ({
      ...f,
      selected_scenario_ids: f.selected_scenario_ids.includes(id)
        ? f.selected_scenario_ids.filter((x) => x !== id)
        : [...f.selected_scenario_ids, id],
    }));
  }

  function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    if (!form.report_title.trim()) { setError("Titel erforderlich"); return; }
    if (!form.report_period.trim()) { setError("Berichtszeitraum erforderlich"); return; }
    mut.mutate({
      report_title: form.report_title.trim(),
      report_period: form.report_period.trim(),
      included_scenario_ids: form.selected_scenario_ids.length > 0 ? form.selected_scenario_ids : undefined,
      report_methodology: form.report_methodology.trim() || undefined,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-violet-600" />
            <h2 className="text-lg font-semibold">Neuer Strategiebericht</h2>
          </div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100"><X className="h-5 w-5 text-slate-500" /></button>
        </div>
        <form onSubmit={submit} className="space-y-5 px-6 py-5">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{t("common.title")} <span className="text-red-500">*</span></label>
            <input value={form.report_title} onChange={(e) => setForm((f) => ({ ...f, report_title: e.target.value }))} placeholder="z. B. Strategie-Review Q4 2026" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Berichtszeitraum <span className="text-red-500">*</span></label>
            <input value={form.report_period} onChange={(e) => setForm((f) => ({ ...f, report_period: e.target.value }))} placeholder="z. B. 2026 oder Q4-2026" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          {(scenarios ?? []).length > 0 && (
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">Szenarien einschließen</label>
              <div className="max-h-36 space-y-1.5 overflow-y-auto rounded-lg border p-2">
                {(scenarios ?? []).map((s) => (
                  <label key={s.id} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 hover:bg-slate-50">
                    <input type="checkbox" checked={form.selected_scenario_ids.includes(s.id)} onChange={() => toggleScenario(s.id)} className="h-4 w-4 rounded border-slate-300 text-violet-600" />
                    <span className="text-sm">{s.name}</span>
                  </label>
                ))}
              </div>
              {form.selected_scenario_ids.length > 0 && (
                <p className="mt-1 text-xs text-violet-600">{form.selected_scenario_ids.length} Szenario(s) ausgewählt</p>
              )}
            </div>
          )}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Methodik (optional)</label>
            <input value={form.report_methodology} onChange={(e) => setForm((f) => ({ ...f, report_methodology: e.target.value }))} placeholder="z. B. SBTi, TCFD, GRI" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500" />
          </div>
          <div className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-700">
            Der Bericht wird als Draft erstellt. Zum Finalisieren muss er separat abgeschlossen werden.
          </div>
          {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        </form>
        <div className="flex justify-end gap-3 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose}>{t("common.cancel")}</Button>
          <Button onClick={submit} disabled={mut.isPending} className="bg-violet-600 hover:bg-violet-700">
            {mut.isPending ? <Spinner className="h-4 w-4" /> : "Bericht erstellen"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function ReportsPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";
  const [showCreate, setShowCreate] = useState(false);

  const { data: reports, isLoading } = useQuery({ queryKey: ["strategy", "reports", orgId], queryFn: () => listReports(orgId) });

  if (isLoading) return <div className="flex h-64 items-center justify-center"><Spinner /></div>;

  const finalized = (reports ?? []).filter((r) => r.is_final);
  const drafts = (reports ?? []).filter((r) => !r.is_final);

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Strategieberichte</h1>
          <p className="text-muted-foreground">Unveränderliche Szenario-Reports für Audit und Board</p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700">
          <Plus className="h-4 w-4" />{t("reports.newReport")}
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">{t("common.total")}</p><p className="mt-1 text-3xl font-bold">{(reports ?? []).length}</p></CardContent></Card>
        <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Finalisiert</p><p className="mt-1 text-3xl font-bold text-blue-600">{finalized.length}</p></CardContent></Card>
        <Card><CardContent className="pt-6"><p className="text-sm text-muted-foreground">Entwurf</p><p className="mt-1 text-3xl font-bold text-slate-500">{drafts.length}</p></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>{t("reports.title")}</CardTitle></CardHeader>
        <CardContent>
          {(reports ?? []).length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <FileText className="h-10 w-10 text-slate-300" />
              <p className="text-sm text-slate-600">Noch kein Strategiebericht erstellt</p>
              <Button onClick={() => setShowCreate(true)} className="mt-1 bg-violet-600 hover:bg-violet-700">
                <Plus className="mr-2 h-4 w-4" />Ersten Bericht erstellen
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {(reports ?? []).map((r) => (
                <div key={r.id} className="flex items-start justify-between rounded-lg border px-4 py-3 transition-colors hover:bg-slate-50">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{r.report_title}</p>
                      {r.is_final ? (
                        <span className="flex items-center gap-1 rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                          <Lock className="h-2.5 w-2.5" />FINAL
                        </span>
                      ) : (
                        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">Entwurf</span>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">Zeitraum: {r.report_period}</p>
                    {r.report_methodology && <p className="mt-0.5 text-xs text-muted-foreground">Methodik: {r.report_methodology}</p>}
                  </div>
                  <div className="ml-4 flex-shrink-0 text-right text-xs text-muted-foreground">
                    <p>{new Date(r.created_at).toLocaleDateString("de-DE")}</p>
                    {r.finalized_at && <p className="text-blue-600">Finalisiert {new Date(r.finalized_at).toLocaleDateString("de-DE")}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {showCreate && <CreateReportModal orgId={orgId} onClose={() => setShowCreate(false)} />}
    </div>
  );
}
