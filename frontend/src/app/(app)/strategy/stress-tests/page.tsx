"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listClimateStressTests, listSupplierShocks, listFinancialStressTests, listScenarios,
  createClimateStressTest, createSupplierShock, createFinancialStressTest,
  type CreateClimateStressTestPayload, type CreateSupplierShockPayload, type CreateFinancialStressTestPayload,
} from "@/lib/api/strategy";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { Plus, X, Zap } from "lucide-react";
import { StressTestBarChart } from "@/components/charts/stress-test-bar-chart";
import type { StressTestDataPoint } from "@/components/charts/stress-test-bar-chart";

const CLIMATE_TYPES = [
  { value: "TRANSITION_SHOCK", label: "Transition Shock" },
  { value: "PHYSICAL_RISK", label: "Physisches Risiko" },
  { value: "CARBON_PRICE", label: "CO₂-Preis" },
  { value: "REGULATORY", label: "Regulierung" },
];
const SUPPLIER_SHOCK_TYPES = [
  { value: "SUPPLIER_FAILURE", label: "Lieferantenausfall" },
  { value: "REGIONAL_DISRUPTION", label: "Regionale Störung" },
  { value: "SANCTIONS", label: "Sanktionen" },
  { value: "ESG_INCIDENT", label: "ESG-Vorfall" },
];
const FINANCIAL_TYPES = [
  { value: "FINANCING_COST", label: "Finanzierungskosten" },
  { value: "GREEN_REVENUE_DECLINE", label: "Green-Revenue-Rückgang" },
  { value: "CARBON_TAX", label: "CO₂-Steuer" },
  { value: "TRANSITION_DELAY", label: "Transitionsverzögerung" },
];

type TestTab = "climate" | "supplier" | "financial";

function ClimateModal({ orgId, scenarios, onClose }: { orgId: string; scenarios: { id: string; name: string }[]; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ test_name: "", stress_type: "CARBON_PRICE", scenario_id: "", carbon_price_shock_pct: "", physical_risk_multiplier: "", transition_cost_pct: "" });
  const [error, setError] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: (p: CreateClimateStressTestPayload) => createClimateStressTest(orgId, p),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["strategy", "stress-climate", orgId] }); onClose(); },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Fehler"),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    if (!form.test_name.trim()) { setError("Name erforderlich"); return; }
    mut.mutate({
      test_name: form.test_name.trim(),
      stress_type: form.stress_type,
      scenario_id: form.scenario_id || undefined,
      carbon_price_shock_pct: form.carbon_price_shock_pct ? parseFloat(form.carbon_price_shock_pct) : undefined,
      physical_risk_multiplier: form.physical_risk_multiplier ? parseFloat(form.physical_risk_multiplier) : undefined,
      transition_cost_pct: form.transition_cost_pct ? parseFloat(form.transition_cost_pct) : undefined,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2"><Zap className="h-5 w-5 text-blue-600" /><h2 className="text-lg font-semibold">Neuer Klima-Stresstest</h2></div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100"><X className="h-5 w-5 text-slate-500" /></button>
        </div>
        <form onSubmit={submit} className="space-y-4 px-6 py-5">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Name <span className="text-red-500">*</span></label>
            <input value={form.test_name} onChange={(e) => setForm((f) => ({ ...f, test_name: e.target.value }))} placeholder="z. B. CO₂-Preis €150 Schock" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Typ</label>
            <div className="grid grid-cols-2 gap-2">
              {CLIMATE_TYPES.map((t) => (
                <button key={t.value} type="button" onClick={() => setForm((f) => ({ ...f, stress_type: t.value }))} className={`rounded-lg border-2 px-3 py-2 text-xs font-medium transition-colors ${form.stress_type === t.value ? "border-blue-400 bg-blue-100 text-blue-700" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"}`}>
                  {t.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Szenario</label>
            <select value={form.scenario_id} onChange={(e) => setForm((f) => ({ ...f, scenario_id: e.target.value }))} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
              <option value="">— Keines —</option>
              {scenarios.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">CO₂-Preis Schock (%)</label>
              <input type="number" value={form.carbon_price_shock_pct} onChange={(e) => setForm((f) => ({ ...f, carbon_price_shock_pct: e.target.value }))} placeholder="150" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Transitionskosten (%)</label>
              <input type="number" value={form.transition_cost_pct} onChange={(e) => setForm((f) => ({ ...f, transition_cost_pct: e.target.value }))} placeholder="15" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </div>
          </div>
          {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        </form>
        <div className="flex justify-end gap-3 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose}>Abbrechen</Button>
          <Button onClick={submit} disabled={mut.isPending} className="bg-blue-600 hover:bg-blue-700">
            {mut.isPending ? <Spinner className="h-4 w-4" /> : "Test erstellen"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function SupplierModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ scenario_name: "", shock_type: "SUPPLIER_FAILURE", shock_severity: "0.5", affected_region: "", recovery_timeline_months: "" });
  const [error, setError] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: (p: CreateSupplierShockPayload) => createSupplierShock(orgId, p),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["strategy", "stress-supplier", orgId] }); onClose(); },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Fehler"),
  });

  const severity = parseFloat(form.shock_severity);

  function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    if (!form.scenario_name.trim()) { setError("Name erforderlich"); return; }
    if (isNaN(severity) || severity < 0 || severity > 1) { setError("Schwere muss zwischen 0 und 1 liegen"); return; }
    mut.mutate({
      scenario_name: form.scenario_name.trim(),
      shock_type: form.shock_type,
      shock_severity: severity,
      affected_region: form.affected_region.trim() || undefined,
      recovery_timeline_months: form.recovery_timeline_months ? parseInt(form.recovery_timeline_months, 10) : undefined,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2"><Zap className="h-5 w-5 text-amber-600" /><h2 className="text-lg font-semibold">Neuer Lieferketten-Schock</h2></div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100"><X className="h-5 w-5 text-slate-500" /></button>
        </div>
        <form onSubmit={submit} className="space-y-4 px-6 py-5">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Name <span className="text-red-500">*</span></label>
            <input value={form.scenario_name} onChange={(e) => setForm((f) => ({ ...f, scenario_name: e.target.value }))} placeholder="z. B. APAC Lieferantenausfall" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500" />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Schock-Typ</label>
            <div className="grid grid-cols-2 gap-2">
              {SUPPLIER_SHOCK_TYPES.map((t) => (
                <button key={t.value} type="button" onClick={() => setForm((f) => ({ ...f, shock_type: t.value }))} className={`rounded-lg border-2 px-3 py-2 text-xs font-medium transition-colors ${form.shock_type === t.value ? "border-amber-400 bg-amber-100 text-amber-700" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"}`}>
                  {t.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Schwere: <span className="font-bold text-amber-600">{(severity * 100).toFixed(0)}%</span>
            </label>
            <input type="range" min="0" max="1" step="0.05" value={form.shock_severity} onChange={(e) => setForm((f) => ({ ...f, shock_severity: e.target.value }))} className="w-full accent-amber-500" />
            <div className="flex justify-between text-xs text-slate-400"><span>Gering</span><span>Mittel</span><span>Extrem</span></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Region (optional)</label>
              <input value={form.affected_region} onChange={(e) => setForm((f) => ({ ...f, affected_region: e.target.value }))} placeholder="APAC" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Erholung (Monate)</label>
              <input type="number" value={form.recovery_timeline_months} onChange={(e) => setForm((f) => ({ ...f, recovery_timeline_months: e.target.value }))} placeholder="12" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </div>
          </div>
          {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        </form>
        <div className="flex justify-end gap-3 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose}>Abbrechen</Button>
          <Button onClick={submit} disabled={mut.isPending} className="bg-amber-600 hover:bg-amber-700">
            {mut.isPending ? <Spinner className="h-4 w-4" /> : "Schock erstellen"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function FinancialModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ test_name: "", stress_type: "FINANCING_COST", financing_cost_increase_bps: "", green_revenue_decline_pct: "", carbon_tax_increase_pct: "", transition_delay_months: "" });
  const [error, setError] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: (p: CreateFinancialStressTestPayload) => createFinancialStressTest(orgId, p),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["strategy", "stress-financial", orgId] }); onClose(); },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Fehler"),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault(); setError(null);
    if (!form.test_name.trim()) { setError("Name erforderlich"); return; }
    mut.mutate({
      test_name: form.test_name.trim(),
      stress_type: form.stress_type,
      financing_cost_increase_bps: form.financing_cost_increase_bps ? parseFloat(form.financing_cost_increase_bps) : undefined,
      green_revenue_decline_pct: form.green_revenue_decline_pct ? parseFloat(form.green_revenue_decline_pct) : undefined,
      carbon_tax_increase_pct: form.carbon_tax_increase_pct ? parseFloat(form.carbon_tax_increase_pct) : undefined,
      transition_delay_months: form.transition_delay_months ? parseInt(form.transition_delay_months, 10) : undefined,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2"><Zap className="h-5 w-5 text-green-600" /><h2 className="text-lg font-semibold">Neuer Finanz-Stresstest</h2></div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100"><X className="h-5 w-5 text-slate-500" /></button>
        </div>
        <form onSubmit={submit} className="space-y-4 px-6 py-5">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Name <span className="text-red-500">*</span></label>
            <input value={form.test_name} onChange={(e) => setForm((f) => ({ ...f, test_name: e.target.value }))} placeholder="z. B. Finanzierungskosten +200 bps" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500" />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Typ</label>
            <div className="grid grid-cols-2 gap-2">
              {FINANCIAL_TYPES.map((t) => (
                <button key={t.value} type="button" onClick={() => setForm((f) => ({ ...f, stress_type: t.value }))} className={`rounded-lg border-2 px-3 py-2 text-xs font-medium transition-colors ${form.stress_type === t.value ? "border-green-400 bg-green-100 text-green-700" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"}`}>
                  {t.label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Finanzierungskosten (bps)</label>
              <input type="number" value={form.financing_cost_increase_bps} onChange={(e) => setForm((f) => ({ ...f, financing_cost_increase_bps: e.target.value }))} placeholder="200" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">CO₂-Steuer Erhöhung (%)</label>
              <input type="number" value={form.carbon_tax_increase_pct} onChange={(e) => setForm((f) => ({ ...f, carbon_tax_increase_pct: e.target.value }))} placeholder="50" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Green Revenue Rückgang (%)</label>
              <input type="number" value={form.green_revenue_decline_pct} onChange={(e) => setForm((f) => ({ ...f, green_revenue_decline_pct: e.target.value }))} placeholder="20" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Verzögerung (Monate)</label>
              <input type="number" value={form.transition_delay_months} onChange={(e) => setForm((f) => ({ ...f, transition_delay_months: e.target.value }))} placeholder="18" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            </div>
          </div>
          {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        </form>
        <div className="flex justify-end gap-3 border-t px-6 py-4">
          <Button variant="outline" onClick={onClose}>Abbrechen</Button>
          <Button onClick={submit} disabled={mut.isPending} className="bg-green-600 hover:bg-green-700">
            {mut.isPending ? <Spinner className="h-4 w-4" /> : "Test erstellen"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function StressTestsPage() {
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";
  const [tab, setTab] = useState<TestTab>("climate");
  const [modal, setModal] = useState<TestTab | null>(null);

  const { data: scenarios } = useQuery({ queryKey: ["strategy", "scenarios", orgId], queryFn: () => listScenarios(orgId) });
  const { data: climate, isLoading: l1 } = useQuery({ queryKey: ["strategy", "stress-climate", orgId], queryFn: () => listClimateStressTests(orgId) });
  const { data: supplier, isLoading: l2 } = useQuery({ queryKey: ["strategy", "stress-supplier", orgId], queryFn: () => listSupplierShocks(orgId) });
  const { data: financial, isLoading: l3 } = useQuery({ queryKey: ["strategy", "stress-financial", orgId], queryFn: () => listFinancialStressTests(orgId) });

  if (l1 || l2 || l3) return <div className="flex h-64 items-center justify-center"><Spinner /></div>;

  const allChartData: StressTestDataPoint[] = [
    ...(climate ?? []).map((t) => ({
      test_type: "CLIMATE",
      impact_low: (t.carbon_price_shock_pct ?? t.transition_cost_pct ?? 5) * 0.5,
      expected_impact: t.carbon_price_shock_pct ?? t.transition_cost_pct ?? 10,
      impact_high: (t.carbon_price_shock_pct ?? t.transition_cost_pct ?? 5) * 1.8,
    })),
    ...(supplier ?? []).map((s) => ({
      test_type: "SUPPLIER",
      impact_low: s.shock_severity * 30,
      expected_impact: s.shock_severity * 60,
      impact_high: s.shock_severity * 100,
    })),
    ...(financial ?? []).map((f) => ({
      test_type: "FINANCIAL",
      impact_low: (f.financing_cost_increase_bps ?? f.carbon_tax_increase_pct ?? 5) * 0.4,
      expected_impact: f.financing_cost_increase_bps ?? f.carbon_tax_increase_pct ?? 10,
      impact_high: (f.financing_cost_increase_bps ?? f.carbon_tax_increase_pct ?? 5) * 1.5,
    })),
  ];

  const totalTests = allChartData.length;
  const avgImpact = totalTests > 0 ? allChartData.reduce((s, d) => s + d.expected_impact, 0) / totalTests : 0;
  const maxImpact = totalTests > 0 ? Math.max(...allChartData.map((d) => d.impact_high)) : 0;
  const highImpactCount = allChartData.filter((d) => d.expected_impact > 20).length;

  const TABS: { key: TestTab; label: string; count: number; color: string }[] = [
    { key: "climate", label: "Klima", count: (climate ?? []).length, color: "text-blue-600" },
    { key: "supplier", label: "Lieferkette", count: (supplier ?? []).length, color: "text-amber-600" },
    { key: "financial", label: "Finanziell", count: (financial ?? []).length, color: "text-green-600" },
  ];
  const btnColors: Record<TestTab, string> = {
    climate: "bg-blue-600 hover:bg-blue-700",
    supplier: "bg-amber-600 hover:bg-amber-700",
    financial: "bg-green-600 hover:bg-green-700",
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between">
        <div><h1 className="text-2xl font-bold">Stress Tests</h1><p className="text-muted-foreground">Klima-, Lieferketten- und Finanz-Stresstests</p></div>
        <Button onClick={() => setModal(tab)} className={`flex items-center gap-2 ${btnColors[tab]}`}>
          <Plus className="h-4 w-4" />Neuer Test
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)} className={`rounded-xl border-2 p-4 text-left shadow-sm transition-colors ${tab === t.key ? "border-violet-400 bg-violet-50" : "border-transparent bg-white hover:bg-slate-50"}`}>
            <p className="text-sm text-muted-foreground">{t.label}</p>
            <p className={`text-3xl font-bold ${t.color}`}>{t.count}</p>
          </button>
        ))}
      </div>

      {totalTests > 0 && (
        <Card className="border-violet-100 bg-violet-50/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-violet-900">Portfolio Impact Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: "Total Tests", value: String(totalTests), color: "text-slate-800" },
                { label: "Avg Expected Impact", value: `${avgImpact.toFixed(1)}%`, color: "text-violet-700" },
                { label: "Max Stressed Impact", value: `${maxImpact.toFixed(1)}%`, color: maxImpact > 50 ? "text-red-600" : "text-amber-600" },
                { label: "High-Impact Tests (>20%)", value: String(highImpactCount), color: highImpactCount > 0 ? "text-red-600" : "text-emerald-600" },
              ].map(({ label, value, color }) => (
                <div key={label} className="rounded-lg bg-white/70 p-3 text-center shadow-sm">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
                  <p className={`mt-1 text-2xl font-bold ${color}`}>{value}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {allChartData.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Impact-Vergleich</CardTitle></CardHeader>
          <CardContent>
            <StressTestBarChart data={allChartData} unit="%" height={260} />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>{TABS.find((t) => t.key === tab)?.label}-Stresstests</CardTitle></CardHeader>
        <CardContent>
          {tab === "climate" && (
            (climate ?? []).length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center">
                <Zap className="h-10 w-10 text-slate-300" />
                <p className="text-sm text-slate-600">Noch kein Klima-Stresstest</p>
                <Button onClick={() => setModal("climate")} className="mt-1 bg-blue-600 hover:bg-blue-700"><Plus className="mr-2 h-4 w-4" />Test erstellen</Button>
              </div>
            ) : (
              <div className="space-y-2">
                {(climate ?? []).map((t) => (
                  <div key={t.id} className="flex items-center justify-between rounded-lg border px-4 py-3 hover:bg-slate-50">
                    <div>
                      <p className="font-medium">{t.test_name}</p>
                      <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">{CLIMATE_TYPES.find((x) => x.value === t.stress_type)?.label ?? t.stress_type}</span>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      {t.carbon_price_shock_pct !== null && <p>CO₂ +{t.carbon_price_shock_pct}%</p>}
                      {t.transition_cost_pct !== null && <p>Transition {t.transition_cost_pct}%</p>}
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
          {tab === "supplier" && (
            (supplier ?? []).length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center">
                <Zap className="h-10 w-10 text-slate-300" />
                <p className="text-sm text-slate-600">Noch kein Lieferketten-Schock</p>
                <Button onClick={() => setModal("supplier")} className="mt-1 bg-amber-600 hover:bg-amber-700"><Plus className="mr-2 h-4 w-4" />Schock erstellen</Button>
              </div>
            ) : (
              <div className="space-y-2">
                {(supplier ?? []).map((s) => (
                  <div key={s.id} className="flex items-center justify-between rounded-lg border px-4 py-3 hover:bg-slate-50">
                    <div>
                      <p className="font-medium">{s.scenario_name}</p>
                      <div className="mt-1 flex gap-2">
                        <span className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700">{SUPPLIER_SHOCK_TYPES.find((x) => x.value === s.shock_type)?.label ?? s.shock_type}</span>
                        {s.affected_region && <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{s.affected_region}</span>}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-amber-600">{(s.shock_severity * 100).toFixed(0)}%</p>
                      <p className="text-xs text-muted-foreground">Schwere</p>
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
          {tab === "financial" && (
            (financial ?? []).length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center">
                <Zap className="h-10 w-10 text-slate-300" />
                <p className="text-sm text-slate-600">Noch kein Finanz-Stresstest</p>
                <Button onClick={() => setModal("financial")} className="mt-1 bg-green-600 hover:bg-green-700"><Plus className="mr-2 h-4 w-4" />Test erstellen</Button>
              </div>
            ) : (
              <div className="space-y-2">
                {(financial ?? []).map((f) => (
                  <div key={f.id} className="flex items-center justify-between rounded-lg border px-4 py-3 hover:bg-slate-50">
                    <div>
                      <p className="font-medium">{f.test_name}</p>
                      <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">{FINANCIAL_TYPES.find((x) => x.value === f.stress_type)?.label ?? f.stress_type}</span>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      {f.financing_cost_increase_bps !== null && <p>+{f.financing_cost_increase_bps} bps</p>}
                      {f.carbon_tax_increase_pct !== null && <p>CO₂ +{f.carbon_tax_increase_pct}%</p>}
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </CardContent>
      </Card>

      {modal === "climate" && <ClimateModal orgId={orgId} scenarios={scenarios ?? []} onClose={() => setModal(null)} />}
      {modal === "supplier" && <SupplierModal orgId={orgId} onClose={() => setModal(null)} />}
      {modal === "financial" && <FinancialModal orgId={orgId} onClose={() => setModal(null)} />}
    </div>
  );
}
