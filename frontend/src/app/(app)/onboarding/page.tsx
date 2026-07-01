"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import {
  Building2,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  FileText,
  Leaf,
  Plus,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import apiClient from "@/lib/api/client";

// ── Types ─────────────────────────────────────────────────────────────────────

interface OrgFormData {
  name: string;
  industry: string;
  country: string;
  employee_count: string;
  reporting_year: string;
}

interface SupplierEntry {
  name: string;
  country: string;
  tier: string;
}

type Framework = "CSRD" | "GRI" | "TCFD" | "SFDR" | "EU_TAXONOMY";

// ── API calls ─────────────────────────────────────────────────────────────────

async function createSupplier(s: SupplierEntry) {
  const res = await apiClient.post("/suppliers/", {
    name: s.name.trim(),
    country: s.country.trim() || undefined,
    tier: parseInt(s.tier) || 1,
  });
  return res.data;
}

async function createAssessmentTemplate(frameworks: Framework[]) {
  const results = [];
  for (const fw of frameworks) {
    try {
      const res = await apiClient.post("/assessments/", {
        name: `${fw} Initial Assessment`,
        assessment_type: fw,
        status: "PENDING",
      });
      results.push(res.data);
    } catch {
      // non-blocking — framework may not be configured yet
    }
  }
  return results;
}

// ── Step components ───────────────────────────────────────────────────────────

function Step1Org({
  form,
  onChange,
}: {
  form: OrgFormData;
  onChange: (f: OrgFormData) => void;
}) {
  function set(key: keyof OrgFormData, value: string) {
    onChange({ ...form, [key]: value });
  }

  return (
    <div className="space-y-5">
      <div>
        <Label htmlFor="org-name">Organisation Name *</Label>
        <Input
          id="org-name"
          value={form.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="Acme GmbH"
          className="mt-1"
          required
          aria-required="true"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="org-industry">Branche</Label>
          <Input
            id="org-industry"
            value={form.industry}
            onChange={(e) => set("industry", e.target.value)}
            placeholder="Manufacturing"
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="org-country">Land (ISO)</Label>
          <Input
            id="org-country"
            value={form.country}
            onChange={(e) => set("country", e.target.value)}
            placeholder="DE"
            maxLength={2}
            className="mt-1"
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="org-employees">Mitarbeiterzahl</Label>
          <Input
            id="org-employees"
            type="number"
            min={1}
            value={form.employee_count}
            onChange={(e) => set("employee_count", e.target.value)}
            placeholder="500"
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="org-year">Berichtsjahr</Label>
          <Input
            id="org-year"
            type="number"
            min={2020}
            max={2030}
            value={form.reporting_year}
            onChange={(e) => set("reporting_year", e.target.value)}
            placeholder="2024"
            className="mt-1"
          />
        </div>
      </div>
    </div>
  );
}

function Step2Suppliers({
  suppliers,
  onChange,
}: {
  suppliers: SupplierEntry[];
  onChange: (s: SupplierEntry[]) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);

  function addBlank() {
    if (suppliers.length >= 10) return;
    onChange([...suppliers, { name: "", country: "", tier: "1" }]);
  }

  function update(i: number, key: keyof SupplierEntry, value: string) {
    const next = suppliers.map((s, idx) => (idx === i ? { ...s, [key]: value } : s));
    onChange(next);
  }

  function remove(i: number) {
    onChange(suppliers.filter((_, idx) => idx !== i));
  }

  function handleCsv(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      const lines = text.split("\n").slice(1); // skip header
      const parsed: SupplierEntry[] = lines
        .map((l) => l.split(","))
        .filter((cols) => cols[0]?.trim())
        .slice(0, 10)
        .map((cols) => ({
          name: cols[0]?.trim() ?? "",
          country: cols[1]?.trim() ?? "",
          tier: cols[2]?.trim() ?? "1",
        }));
      onChange(parsed);
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => fileRef.current?.click()}
          className="gap-1.5"
          aria-label="Upload CSV file with suppliers"
        >
          <Upload className="h-4 w-4" aria-hidden="true" />
          CSV Upload
        </Button>
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          onChange={handleCsv}
          className="hidden"
          aria-label="Select CSV file"
        />
        <span className="text-xs text-muted-foreground">
          Oder manuell bis zu 10 Lieferanten eingeben (CSV: name,country,tier)
        </span>
      </div>

      {suppliers.length === 0 && (
        <p className="rounded-md border border-dashed p-4 text-center text-sm text-muted-foreground">
          Noch keine Lieferanten. Füge 1–3 Lieferanten hinzu oder überspringe diesen Schritt.
        </p>
      )}

      <div className="space-y-3">
        {suppliers.map((s, i) => (
          <div key={i} className="flex items-center gap-2">
            <Input
              value={s.name}
              onChange={(e) => update(i, "name", e.target.value)}
              placeholder="Lieferant Name"
              aria-label={`Supplier ${i + 1} name`}
              className="flex-1"
            />
            <Input
              value={s.country}
              onChange={(e) => update(i, "country", e.target.value)}
              placeholder="DE"
              maxLength={2}
              aria-label={`Supplier ${i + 1} country`}
              className="w-16"
            />
            <Input
              type="number"
              value={s.tier}
              onChange={(e) => update(i, "tier", e.target.value)}
              min={1}
              max={4}
              aria-label={`Supplier ${i + 1} tier`}
              className="w-16"
            />
            <button
              type="button"
              onClick={() => remove(i)}
              aria-label={`Remove supplier ${i + 1}`}
              className="rounded p-1 text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>

      {suppliers.length < 10 && (
        <Button type="button" variant="outline" size="sm" onClick={addBlank} className="gap-1">
          <Plus className="h-4 w-4" aria-hidden="true" /> Lieferant hinzufügen
        </Button>
      )}
    </div>
  );
}

const FRAMEWORKS: { id: Framework; label: string; desc: string; icon: React.ElementType }[] = [
  { id: "CSRD", label: "CSRD / ESRS", desc: "EU Corporate Sustainability Reporting Directive", icon: FileText },
  { id: "GRI", label: "GRI Standards", desc: "Global Reporting Initiative 2021", icon: Leaf },
  { id: "TCFD", label: "TCFD", desc: "Task Force on Climate-related Financial Disclosures", icon: Building2 },
  { id: "SFDR", label: "SFDR / PAI", desc: "Sustainable Finance Disclosure Regulation", icon: FileText },
  { id: "EU_TAXONOMY", label: "EU Taxonomy", desc: "EU Taxonomy for Sustainable Finance", icon: Leaf },
];

function Step3Frameworks({
  selected,
  onChange,
}: {
  selected: Framework[];
  onChange: (f: Framework[]) => void;
}) {
  function toggle(id: Framework) {
    onChange(
      selected.includes(id) ? selected.filter((f) => f !== id) : [...selected, id]
    );
  }

  return (
    <div className="space-y-3" role="group" aria-label="Select reporting frameworks">
      {FRAMEWORKS.map(({ id, label, desc, icon: Icon }) => {
        const active = selected.includes(id);
        return (
          <button
            key={id}
            type="button"
            onClick={() => toggle(id)}
            aria-pressed={active}
            className={cn(
              "w-full flex items-start gap-4 rounded-lg border p-4 text-left transition-colors",
              active
                ? "border-primary bg-primary/5 ring-1 ring-primary"
                : "border-border hover:border-primary/40 hover:bg-muted/50"
            )}
          >
            <div className={cn("mt-0.5 rounded-md p-1.5", active ? "bg-primary/10" : "bg-muted")}>
              <Icon className={cn("h-5 w-5", active ? "text-primary" : "text-muted-foreground")} aria-hidden="true" />
            </div>
            <div>
              <p className={cn("font-medium text-sm", active ? "text-primary" : "text-foreground")}>{label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
            </div>
            {active && <CheckCircle className="ml-auto h-4 w-4 text-primary flex-shrink-0 mt-0.5" aria-hidden="true" />}
          </button>
        );
      })}
    </div>
  );
}

// ── Step 4: First KPI ────────────────────────────────────────────────────────

interface KpiFormData {
  name: string;
  unit: string;
  target_value: string;
  kpi_type: string;
}

const KPI_TYPES = [
  { value: "EMISSIONS_INTENSITY", label: "Emissionsintensität" },
  { value: "RENEWABLE_ENERGY_PCT", label: "Erneuerbare Energie %" },
  { value: "WASTE_REDUCTION_PCT", label: "Abfallreduktion %" },
  { value: "WATER_USAGE", label: "Wasserverbrauch" },
  { value: "SUPPLIER_ESG_SCORE", label: "Lieferanten-ESG-Score" },
  { value: "CUSTOM", label: "Benutzerdefiniert" },
];

function Step4KPI({
  form,
  onChange,
}: {
  form: KpiFormData;
  onChange: (f: KpiFormData) => void;
}) {
  return (
    <div className="space-y-5">
      <div className="rounded-md bg-blue-50 border border-blue-100 px-4 py-3 text-sm text-blue-800">
        Lege deinen ersten KPI fest. Du kannst beliebig viele KPIs später unter <strong>Sustainability → KPIs</strong> hinzufügen.
      </div>
      <div>
        <Label htmlFor="kpi-type">KPI-Typ</Label>
        <select
          id="kpi-type"
          value={form.kpi_type}
          onChange={(e) => onChange({ ...form, kpi_type: e.target.value })}
          className="mt-1 w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
        >
          {KPI_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </div>
      <div>
        <Label htmlFor="kpi-name">KPI Name *</Label>
        <Input
          id="kpi-name"
          value={form.name}
          onChange={(e) => onChange({ ...form, name: e.target.value })}
          placeholder="z. B. CO₂-Intensität pro EUR Umsatz"
          className="mt-1"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="kpi-unit">Einheit</Label>
          <Input
            id="kpi-unit"
            value={form.unit}
            onChange={(e) => onChange({ ...form, unit: e.target.value })}
            placeholder="z. B. tCO₂e/MEUR"
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="kpi-target">Zielwert</Label>
          <Input
            id="kpi-target"
            type="number"
            value={form.target_value}
            onChange={(e) => onChange({ ...form, target_value: e.target.value })}
            placeholder="z. B. 50"
            className="mt-1"
          />
        </div>
      </div>
    </div>
  );
}

// ── Step 5: First Emission Data ──────────────────────────────────────────────

interface EmissionFormData {
  scope1: string;
  scope2: string;
  scope3: string;
  year: string;
}

function Step5Emissions({
  form,
  onChange,
}: {
  form: EmissionFormData;
  onChange: (f: EmissionFormData) => void;
}) {
  return (
    <div className="space-y-5">
      <div className="rounded-md bg-emerald-50 border border-emerald-100 px-4 py-3 text-sm text-emerald-800">
        Gib deine Scope-1/2/3-Emissionen für das Basisjahr ein. Diese Daten werden als Ausgangspunkt für Prognosen und Ziele verwendet.
      </div>
      <div>
        <Label htmlFor="em-year">Berichtsjahr</Label>
        <Input
          id="em-year"
          type="number"
          min={2020}
          max={2030}
          value={form.year}
          onChange={(e) => onChange({ ...form, year: e.target.value })}
          className="mt-1 w-32"
        />
      </div>
      {[
        { key: "scope1" as const, label: "Scope 1 — Direkte Emissionen (tCO₂e)", placeholder: "z. B. 1200" },
        { key: "scope2" as const, label: "Scope 2 — Strom / Wärme (tCO₂e)", placeholder: "z. B. 850" },
        { key: "scope3" as const, label: "Scope 3 — Wertschöpfungskette (tCO₂e)", placeholder: "z. B. 5400" },
      ].map(({ key, label, placeholder }) => (
        <div key={key}>
          <Label htmlFor={`em-${key}`}>{label}</Label>
          <Input
            id={`em-${key}`}
            type="number"
            min={0}
            value={form[key]}
            onChange={(e) => onChange({ ...form, [key]: e.target.value })}
            placeholder={placeholder}
            className="mt-1"
          />
        </div>
      ))}
    </div>
  );
}

// ── Step 6: Summary ──────────────────────────────────────────────────────────

function Step6Summary({
  orgName,
  supplierCount,
  frameworkCount,
  kpiName,
  scope1,
  scope2,
  scope3,
}: {
  orgName: string;
  supplierCount: number;
  frameworkCount: number;
  kpiName: string;
  scope1: string;
  scope2: string;
  scope3: string;
}) {
  const totalEmissions = (parseFloat(scope1) || 0) + (parseFloat(scope2) || 0) + (parseFloat(scope3) || 0);

  const items = [
    { label: "Organisation", value: orgName || "—", ok: !!orgName },
    { label: "Lieferanten", value: `${supplierCount} hinzugefügt`, ok: supplierCount > 0 },
    { label: "Frameworks", value: `${frameworkCount} ausgewählt`, ok: frameworkCount > 0 },
    { label: "Erster KPI", value: kpiName || "—", ok: !!kpiName },
    { label: "Emissionsdaten", value: totalEmissions > 0 ? `${totalEmissions.toLocaleString()} tCO₂e gesamt` : "Nicht angegeben", ok: totalEmissions > 0 },
  ];

  return (
    <div className="space-y-4">
      <div className="rounded-md bg-violet-50 border border-violet-100 px-4 py-3 text-sm text-violet-800">
        Fast fertig! Überprüfe deine Einstellungen und klicke auf <strong>Abschließen</strong>.
      </div>
      <div className="space-y-2">
        {items.map(({ label, value, ok }) => (
          <div key={label} className="flex items-center justify-between rounded-md border px-4 py-3">
            <div>
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-sm font-medium">{value}</p>
            </div>
            <span className={`text-xs font-medium ${ok ? "text-emerald-600" : "text-amber-600"}`}>
              {ok ? "✓" : "—"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Wizard ────────────────────────────────────────────────────────────────────

const STEPS = ["Organisation", "Lieferanten", "Framework", "Erster KPI", "Emissionen", "Zusammenfassung"];

async function createFirstKpi(orgId: string | null, kpi: KpiFormData) {
  if (!kpi.name.trim()) return;
  try {
    await apiClient.post(`/sustainability/${orgId ?? "default"}/kpis`, {
      name: kpi.name.trim(),
      unit: kpi.unit.trim() || "—",
      target_value: parseFloat(kpi.target_value) || undefined,
      kpi_type: kpi.kpi_type,
      frequency: "ANNUAL",
    });
  } catch {
    // non-blocking
  }
}

async function createEmissionInventory(orgId: string | null, em: EmissionFormData) {
  const yr = parseInt(em.year) || new Date().getFullYear();
  if (!em.scope1 && !em.scope2 && !em.scope3) return;
  try {
    await apiClient.post(`/sustainability/${orgId ?? "default"}/inventory`, {
      reporting_year: yr,
      period_start: `${yr}-01-01T00:00:00Z`,
      period_end: `${yr}-12-31T23:59:59Z`,
      scope1_emissions: parseFloat(em.scope1) || 0,
      scope2_emissions: parseFloat(em.scope2) || 0,
      scope3_emissions: parseFloat(em.scope3) || 0,
      unit: "tCO2e",
    });
  } catch {
    // non-blocking
  }
}

export default function OnboardingPage() {
  const router = useRouter();
  const { t } = useLanguage();
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [orgForm, setOrgForm] = useState<OrgFormData>({
    name: "", industry: "", country: "", employee_count: "", reporting_year: "2024",
  });
  const [suppliers, setSuppliers] = useState<SupplierEntry[]>([]);
  const [frameworks, setFrameworks] = useState<Framework[]>(["CSRD"]);
  const [kpiForm, setKpiForm] = useState<KpiFormData>({
    name: "", unit: "", target_value: "", kpi_type: "EMISSIONS_INTENSITY",
  });
  const [emForm, setEmForm] = useState<EmissionFormData>({
    scope1: "", scope2: "", scope3: "", year: String(new Date().getFullYear()),
  });

  const mut = useMutation({
    mutationFn: async () => {
      const orgRes = await apiClient.patch("/organizations/me", {
        name: orgForm.name.trim(),
        industry: orgForm.industry.trim() || undefined,
        country: orgForm.country.trim() || undefined,
      });
      const orgId = orgRes.data?.id ?? null;
      const validSuppliers = suppliers.filter((s) => s.name.trim());
      await Promise.all(validSuppliers.map(createSupplier));
      if (frameworks.length > 0) await createAssessmentTemplate(frameworks);
      await createFirstKpi(orgId, kpiForm);
      await createEmissionInventory(orgId, emForm);
    },
    onSuccess: () => router.push("/dashboard"),
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Fehler beim Speichern"),
  });

  function next() {
    if (step === 0 && !orgForm.name.trim()) {
      setError("Organisationsname ist erforderlich.");
      return;
    }
    setError(null);
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  }

  function back() {
    setError(null);
    setStep((s) => Math.max(s - 1, 0));
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-background p-6" aria-label="Onboarding wizard">
      <div className="w-full max-w-xl">
        {/* Progress */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground mb-6 text-center">
            {t("onboard.title")}
          </h1>
          <nav aria-label="Onboarding steps">
            <ol className="flex items-center gap-0">
              {STEPS.map((label, i) => (
                <li key={label} className="flex items-center flex-1">
                  <div className="flex flex-col items-center flex-1">
                    <div
                      className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold border-2 transition-colors",
                        i < step
                          ? "bg-primary border-primary text-primary-foreground"
                          : i === step
                          ? "border-primary text-primary"
                          : "border-border text-muted-foreground"
                      )}
                      aria-current={i === step ? "step" : undefined}
                    >
                      {i < step ? <CheckCircle className="h-4 w-4" aria-hidden="true" /> : i + 1}
                    </div>
                    <span
                      className={cn(
                        "mt-1 text-[11px] font-medium",
                        i === step ? "text-primary" : "text-muted-foreground"
                      )}
                    >
                      {label}
                    </span>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div
                      className={cn(
                        "h-0.5 flex-1 -mt-5",
                        i < step ? "bg-primary" : "bg-border"
                      )}
                    />
                  )}
                </li>
              ))}
            </ol>
          </nav>
        </div>

        <Card>
          <CardContent className="pt-6 pb-6">
            {step === 0 && <Step1Org form={orgForm} onChange={setOrgForm} />}
            {step === 1 && <Step2Suppliers suppliers={suppliers} onChange={setSuppliers} />}
            {step === 2 && <Step3Frameworks selected={frameworks} onChange={setFrameworks} />}
            {step === 3 && <Step4KPI form={kpiForm} onChange={setKpiForm} />}
            {step === 4 && <Step5Emissions form={emForm} onChange={setEmForm} />}
            {step === 5 && (
              <Step6Summary
                orgName={orgForm.name}
                supplierCount={suppliers.filter((s) => s.name.trim()).length}
                frameworkCount={frameworks.length}
                kpiName={kpiForm.name}
                scope1={emForm.scope1}
                scope2={emForm.scope2}
                scope3={emForm.scope3}
              />
            )}

            {error && (
              <p role="alert" className="mt-4 text-sm text-destructive">
                {error}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Navigation */}
        <div className="mt-5 flex items-center justify-between">
          <Button
            variant="outline"
            onClick={back}
            disabled={step === 0}
            className="gap-1"
            aria-label="Go to previous step"
          >
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            {t("onboard.back")}
          </Button>

          {step < STEPS.length - 1 ? (
            <Button onClick={next} className="gap-1" aria-label="Go to next step">
              {t("onboard.next")}
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          ) : (
            <Button
              onClick={() => mut.mutate()}
              disabled={mut.isPending}
              className="gap-1"
              aria-label="Complete onboarding"
            >
              {mut.isPending ? t("settings.saving") : t("onboard.finish")}
              <CheckCircle className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}
        </div>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          <button
            type="button"
            onClick={() => router.push("/dashboard")}
            className="underline hover:text-foreground"
          >
            {t("onboard.skip")} — später einrichten
          </button>
        </p>
      </div>
    </main>
  );
}
