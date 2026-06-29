"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listDigitalTwins, createDigitalTwin, type CreateDigitalTwinPayload } from "@/lib/api/strategy";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { Plus, X, Cpu, Users, BarChart3, AlertTriangle, Zap } from "lucide-react";

// ── Create Modal ──────────────────────────────────────────────────────────────

function CreateTwinModal({
  orgId,
  onClose,
}: {
  orgId: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    description: "",
    twin_version: "1.0",
    supplier_count: "",
    kpi_count: "",
    risk_count: "",
    emissions_baseline_tco2e: "",
    business_units: "",
    legal_entities: "",
    regions: "",
    carbon_price_eur: "",
    growth_rate_pct: "",
  });
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (payload: CreateDigitalTwinPayload) =>
      createDigitalTwin(orgId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategy", "digital-twin", orgId] });
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

    const payload: CreateDigitalTwinPayload = {
      name: form.name.trim(),
      description: form.description.trim() || undefined,
      twin_version: form.twin_version.trim() || "1.0",
      supplier_count: form.supplier_count ? Number(form.supplier_count) : undefined,
      kpi_count: form.kpi_count ? Number(form.kpi_count) : undefined,
      risk_count: form.risk_count ? Number(form.risk_count) : undefined,
      emissions_baseline_tco2e: form.emissions_baseline_tco2e
        ? Number(form.emissions_baseline_tco2e)
        : undefined,
    };

    if (form.business_units.trim()) {
      payload.business_units = {
        units: form.business_units.split(",").map((s) => s.trim()).filter(Boolean),
      };
    }
    if (form.legal_entities.trim()) {
      payload.legal_entities = {
        entities: form.legal_entities.split(",").map((s) => s.trim()).filter(Boolean),
      };
    }
    if (form.regions.trim()) {
      payload.regions = {
        regions: form.regions.split(",").map((s) => s.trim()).filter(Boolean),
      };
    }
    if (form.carbon_price_eur || form.growth_rate_pct) {
      payload.assumptions = {
        ...(form.carbon_price_eur ? { carbon_price_eur: Number(form.carbon_price_eur) } : {}),
        ...(form.growth_rate_pct ? { growth_rate_pct: Number(form.growth_rate_pct) } : {}),
      };
    }

    mutation.mutate(payload);
  }

  function field(label: string, key: keyof typeof form, opts?: {
    type?: string;
    placeholder?: string;
    hint?: string;
    required?: boolean;
  }) {
    return (
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">
          {label}
          {opts?.required && <span className="ml-1 text-red-500">*</span>}
        </label>
        {opts?.hint && (
          <p className="mb-1 text-xs text-slate-500">{opts.hint}</p>
        )}
        <input
          type={opts?.type ?? "text"}
          value={form[key]}
          onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
          placeholder={opts?.placeholder}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
        />
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="relative w-full max-w-2xl rounded-xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-violet-600" />
            <h2 className="text-lg font-semibold">Neuer Digital Twin</h2>
          </div>
          <button onClick={onClose} className="rounded-md p-1 hover:bg-slate-100">
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="max-h-[75vh] overflow-y-auto px-6 py-5">
          <div className="space-y-5">
            {/* Basic info */}
            <div className="space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Basisdaten
              </h3>
              {field("Name", "name", { required: true, placeholder: "z. B. EIOS Enterprise Twin 2026" })}
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                  Beschreibung
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="Kurze Beschreibung des Szenarios oder Zustands"
                  rows={2}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
              {field("Version", "twin_version", { placeholder: "1.0" })}
            </div>

            {/* Scale */}
            <div className="space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Unternehmensumfang
              </h3>
              <div className="grid grid-cols-3 gap-4">
                {field("Lieferanten", "supplier_count", { type: "number", placeholder: "142" })}
                {field("KPIs", "kpi_count", { type: "number", placeholder: "38" })}
                {field("Risiken", "risk_count", { type: "number", placeholder: "21" })}
              </div>
            </div>

            {/* Emissions */}
            <div className="space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Klimadaten
              </h3>
              {field("Emissionen Baseline (tCO₂e)", "emissions_baseline_tco2e", {
                type: "number",
                placeholder: "84500",
              })}
            </div>

            {/* Structure */}
            <div className="space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Organisationsstruktur
              </h3>
              {field("Business Units", "business_units", {
                placeholder: "Supply Chain, Operations, Finance",
                hint: "Kommagetrennt",
              })}
              {field("Legal Entities", "legal_entities", {
                placeholder: "EIOS GmbH, EIOS UK Ltd",
                hint: "Kommagetrennt",
              })}
              {field("Regionen", "regions", {
                placeholder: "DACH, UK, APAC",
                hint: "Kommagetrennt",
              })}
            </div>

            {/* Assumptions */}
            <div className="space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Annahmen
              </h3>
              <div className="grid grid-cols-2 gap-4">
                {field("CO₂-Preis (EUR)", "carbon_price_eur", { type: "number", placeholder: "65" })}
                {field("Wachstumsrate (%)", "growth_rate_pct", { type: "number", placeholder: "3.2" })}
              </div>
            </div>
          </div>

          {error && (
            <div className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="flex justify-end gap-3 border-t px-6 py-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Abbrechen
          </Button>
          <Button
            type="submit"
            onClick={handleSubmit}
            disabled={mutation.isPending}
            className="bg-violet-600 hover:bg-violet-700"
          >
            {mutation.isPending ? (
              <span className="flex items-center gap-2">
                <Spinner className="h-4 w-4" /> Erstelle…
              </span>
            ) : (
              "Twin erstellen"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DigitalTwinPage() {
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";
  const [showCreate, setShowCreate] = useState(false);

  const { data: twins, isLoading } = useQuery({
    queryKey: ["strategy", "digital-twin", orgId],
    queryFn: () => listDigitalTwins(orgId),
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Enterprise Digital Twin</h1>
          <p className="text-muted-foreground">
            Strukturierte Abbildung des Enterprise-Zustands für Szenarioplanung
          </p>
        </div>
        <Button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700"
        >
          <Plus className="h-4 w-4" />
          Neuer Twin
        </Button>
      </div>

      {/* Twin Cards */}
      {(twins ?? []).length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <Cpu className="h-10 w-10 text-slate-300" />
            <p className="text-sm font-medium text-slate-600">Noch kein Digital Twin vorhanden</p>
            <p className="text-xs text-slate-400">
              Erstelle einen Twin um Szenarien zu modellieren.
            </p>
            <Button
              onClick={() => setShowCreate(true)}
              className="mt-2 bg-violet-600 hover:bg-violet-700"
            >
              <Plus className="mr-2 h-4 w-4" />
              Ersten Twin erstellen
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(twins ?? []).map((t) => (
            <Card key={t.id} className="transition-shadow hover:shadow-md">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base leading-snug">{t.name}</CardTitle>
                  <div className="flex flex-shrink-0 gap-1">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        t.is_active
                          ? "bg-green-100 text-green-700"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {t.is_active ? "AKTIV" : "INAKTIV"}
                    </span>
                    {t.is_final && (
                      <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                        FINAL
                      </span>
                    )}
                  </div>
                </div>
                {t.description && (
                  <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                    {t.description}
                  </p>
                )}
              </CardHeader>

              <CardContent className="space-y-4">
                {/* KPI Row */}
                <div className="grid grid-cols-3 gap-2 rounded-lg bg-slate-50 p-3 text-center">
                  <div>
                    <div className="flex items-center justify-center gap-1 text-slate-500">
                      <Users className="h-3 w-3" />
                    </div>
                    <p className="text-lg font-bold">{t.supplier_count}</p>
                    <p className="text-xs text-muted-foreground">Lieferanten</p>
                  </div>
                  <div>
                    <div className="flex items-center justify-center gap-1 text-slate-500">
                      <BarChart3 className="h-3 w-3" />
                    </div>
                    <p className="text-lg font-bold">{t.kpi_count}</p>
                    <p className="text-xs text-muted-foreground">KPIs</p>
                  </div>
                  <div>
                    <div className="flex items-center justify-center gap-1 text-slate-500">
                      <AlertTriangle className="h-3 w-3" />
                    </div>
                    <p className="text-lg font-bold">{t.risk_count}</p>
                    <p className="text-xs text-muted-foreground">Risiken</p>
                  </div>
                </div>

                {/* Emissions */}
                {t.emissions_baseline_tco2e !== null && (
                  <div className="flex items-center gap-2 rounded-md border border-emerald-100 bg-emerald-50 px-3 py-2">
                    <Zap className="h-4 w-4 flex-shrink-0 text-emerald-600" />
                    <div>
                      <p className="text-xs text-emerald-700">Emissionen Baseline</p>
                      <p className="text-sm font-semibold text-emerald-900">
                        {t.emissions_baseline_tco2e.toLocaleString("de-DE")} tCO₂e
                      </p>
                    </div>
                  </div>
                )}

                {/* Meta */}
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>v{t.twin_version}</span>
                  <span>
                    Snapshot: {new Date(t.snapshot_date).toLocaleDateString("de-DE")}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showCreate && (
        <CreateTwinModal orgId={orgId} onClose={() => setShowCreate(false)} />
      )}
    </div>
  );
}
