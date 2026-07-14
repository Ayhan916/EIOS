"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Building2,
  CheckCircle2,
  Globe,
  Loader2,
  Newspaper,
  Search,
  TrendingDown,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  analyzeScenario,
  detectSector,
  SECTOR_OPTIONS,
  type ScenarioResult,
  type SupplierExposure,
} from "@/lib/api/scenario";

// ── Helpers ───────────────────────────────────────────────────────────────────

function ExposureBadge({ level }: { level: string }) {
  const cfg: Record<string, string> = {
    HIGH:    "bg-red-100 text-red-700 border-red-200",
    MEDIUM:  "bg-amber-100 text-amber-700 border-amber-200",
    LOW:     "bg-green-100 text-green-700 border-green-200",
    UNKNOWN: "bg-slate-100 text-slate-600 border-slate-200",
  };
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${cfg[level] ?? cfg.UNKNOWN}`}>
      {level}
    </span>
  );
}

function UrgencyBadge({ urgency }: { urgency: string }) {
  const cfg: Record<string, string> = {
    IMMEDIATE:   "bg-red-600 text-white",
    SHORT_TERM:  "bg-amber-500 text-white",
    MONITOR:     "bg-slate-200 text-slate-700",
  };
  const labels: Record<string, string> = {
    IMMEDIATE: "Sofort",
    SHORT_TERM: "Kurzfristig",
    MONITOR: "Beobachten",
  };
  return (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${cfg[urgency] ?? cfg.MONITOR}`}>
      {labels[urgency] ?? urgency}
    </span>
  );
}

function SupplierCard({ s }: { s: SupplierExposure }) {
  return (
    <div className="border rounded-lg p-4 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="font-medium text-sm">{s.supplier_name}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <UrgencyBadge urgency={s.urgency} />
          <ExposureBadge level={s.exposure_level} />
        </div>
      </div>
      <p className="text-xs text-muted-foreground">{s.exposure_reason}</p>
      <div className="flex items-start gap-1.5 text-xs bg-blue-50 border border-blue-100 rounded px-2 py-1.5">
        <CheckCircle2 className="h-3.5 w-3.5 text-blue-500 shrink-0 mt-0.5" />
        <span>{s.recommended_action}</span>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

function ScenarioContent() {
  const params = useSearchParams();
  const [signalText, setSignalText] = useState(params.get("signal") ?? "");
  const [companyName, setCompanyName] = useState(params.get("company") ?? "");
  const [sector, setSector] = useState(params.get("sector") ?? "");
  const [result, setResult] = useState<ScenarioResult | null>(null);

  // Auto-detect sector from signal text
  useEffect(() => {
    if (signalText.length > 15 && !sector) {
      detectSector(signalText).then((r) => {
        if (r.detected && r.sector) setSector(r.sector);
      });
    }
  }, [signalText, sector]);

  const mutation = useMutation({
    mutationFn: () => analyzeScenario({ signal_text: signalText, company_name: companyName, sector }),
    onSuccess: (data) => setResult(data),
  });

  const canAnalyze = signalText.length >= 10 && companyName.length >= 2 && sector.length >= 2;

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">

      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/intelligence" className="text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-2">
            <Zap className="h-6 w-6 text-amber-500" />
            Szenario-Analyse
          </h1>
          <p className="text-sm text-muted-foreground">
            Projiziert ein Branchen-Ereignis auf Ihr Lieferanten-Portfolio
          </p>
        </div>
      </div>

      {/* Input form */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Ereignis eingeben</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Signal text */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Nachrichtentext / Ereignis</label>
            <textarea
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
              rows={3}
              placeholder="z.B. Volkswagen plant den Abbau von 35.000 Stellen bis 2027 aufgrund sinkender Nachfrage und steigender Kosten..."
              value={signalText}
              onChange={(e) => setSignalText(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Company */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Betroffenes Unternehmen</label>
              <input
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="z.B. Volkswagen"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
              />
            </div>

            {/* Sector */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Branche
                {sector && <span className="ml-1 text-green-600">(auto-erkannt)</span>}
              </label>
              <select
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                value={sector}
                onChange={(e) => setSector(e.target.value)}
              >
                <option value="">Branche wählen...</option>
                {SECTOR_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>

          <Button
            className="w-full"
            disabled={!canAnalyze || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? (
              <><Loader2 className="h-4 w-4 animate-spin mr-2" />Analysiere... (yfinance + News + Lieferanten)</>
            ) : (
              <><Search className="h-4 w-4 mr-2" />Szenario auf Lieferanten projizieren</>
            )}
          </Button>

          {mutation.isError && (
            <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              Analyse fehlgeschlagen. Bitte erneut versuchen.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <div className="space-y-4">

          {/* Overall risk */}
          <div className={`rounded-lg border px-4 py-3 flex items-center justify-between ${
            result.analysis.overall_risk_level === "HIGH"
              ? "bg-red-50 border-red-200"
              : result.analysis.overall_risk_level === "MEDIUM"
              ? "bg-amber-50 border-amber-200"
              : "bg-green-50 border-green-200"
          }`}>
            <div>
              <p className="font-semibold text-sm">{result.company_name} — Gesamtrisiko für Ihr Portfolio</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {result.suppliers_found} Lieferant{result.suppliers_found !== 1 ? "en" : ""} im Sektor {result.sector} gefunden
              </p>
            </div>
            <ExposureBadge level={result.analysis.overall_risk_level} />
          </div>

          {/* 3-column summary */}
          <div className="grid md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs flex items-center gap-1.5 text-muted-foreground">
                  <Newspaper className="h-3.5 w-3.5" /> Ereignis-Zusammenfassung
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{result.analysis.event_summary}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs flex items-center gap-1.5 text-muted-foreground">
                  <BarChart3 className="h-3.5 w-3.5" /> Finanzielle Lage
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{result.analysis.financial_assessment}</p>
                {(result.financial_data.revenue_eur_b as string | null) && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Umsatz: <strong>{String(result.financial_data.revenue_eur_b)} Mrd. €</strong>
                    {(result.financial_data.ebitda_eur_b as string | null) && <> · EBITDA: <strong>{String(result.financial_data.ebitda_eur_b)} Mrd. €</strong></>}
                  </p>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs flex items-center gap-1.5 text-muted-foreground">
                  <Globe className="h-3.5 w-3.5" /> Brancheneffekt
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{result.analysis.sector_impact}</p>
              </CardContent>
            </Card>
          </div>

          {/* News headlines */}
          {result.news_headlines.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs text-muted-foreground">Aktuelle Schlagzeilen (duckduckgo)</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1">
                  {result.news_headlines.map((h, i) => (
                    <li key={i} className="text-xs flex items-start gap-1.5">
                      <TrendingDown className="h-3 w-3 shrink-0 mt-0.5 text-muted-foreground" />
                      {h}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Per-supplier analysis */}
          <div>
            <h2 className="text-sm font-semibold mb-3">
              Lieferanten-Exposition ({result.analysis.suppliers.length})
            </h2>
            {result.analysis.suppliers.length === 0 ? (
              <div className="text-center py-8 text-sm text-muted-foreground border rounded-lg">
                Keine Lieferanten im Sektor <strong>{result.sector}</strong> gefunden.
                <br />
                <span className="text-xs">Prüfen Sie ob Ihre Lieferanten mit der richtigen Branche angelegt sind.</span>
              </div>
            ) : (
              <div className="grid gap-3">
                {result.analysis.suppliers
                  .sort((a, b) => {
                    const order = { HIGH: 0, MEDIUM: 1, LOW: 2, UNKNOWN: 3 };
                    return (order[a.exposure_level] ?? 3) - (order[b.exposure_level] ?? 3);
                  })
                  .map((s) => <SupplierCard key={s.supplier_id} s={s} />)
                }
              </div>
            )}
          </div>

          {/* Data sources */}
          <div className="flex gap-1.5 flex-wrap">
            <span className="text-[10px] text-muted-foreground">Datenquellen:</span>
            {result.analysis.data_sources.map((src) => (
              <Badge key={src} className="text-[10px] bg-slate-100 text-slate-600">{src}</Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ScenarioPage() {
  return (
    <Suspense fallback={<div className="p-6 flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Lade...</div>}>
      <ScenarioContent />
    </Suspense>
  );
}
