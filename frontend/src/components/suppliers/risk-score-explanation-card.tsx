"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  TrendingUp,
  Info,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import {
  getSupplierRiskScoreExplanation,
  type FactorExplanation,
} from "@/lib/api/supplier-scores";

// ── Band config ───────────────────────────────────────────────────────────────

const BAND_META: Record<string, { label: string; color: string; bg: string; Icon: React.ElementType }> = {
  Low:      { label: "Niedrig",  color: "text-emerald-700", bg: "bg-emerald-50 border-emerald-200", Icon: ShieldCheck },
  Moderate: { label: "Moderat",  color: "text-amber-700",   bg: "bg-amber-50 border-amber-200",    Icon: ShieldAlert },
  High:     { label: "Hoch",     color: "text-orange-700",  bg: "bg-orange-50 border-orange-200",  Icon: ShieldAlert },
  Critical: { label: "Kritisch", color: "text-red-700",     bg: "bg-red-50 border-red-200",        Icon: ShieldX },
};

const IMPACT_BAR: Record<string, string> = {
  high:   "bg-red-500",
  medium: "bg-amber-400",
  low:    "bg-slate-300",
  none:   "bg-slate-200",
};

const IMPACT_LABEL: Record<string, string> = {
  high:   "Hoch",
  medium: "Mittel",
  low:    "Niedrig",
  none:   "—",
};

// ── Sub-components ────────────────────────────────────────────────────────────

function FactorRow({ factor }: { factor: FactorExplanation }) {
  const barColor = IMPACT_BAR[factor.impact] ?? IMPACT_BAR.none;
  const pct = Math.min(100, factor.pct_of_total);
  return (
    <div className="py-2">
      <div className="mb-1 flex items-center justify-between gap-2 text-sm">
        <span className="font-medium text-foreground truncate" title={factor.label}>
          {factor.label}
        </span>
        <div className="flex items-center gap-3 shrink-0 text-xs text-muted-foreground">
          <span>{factor.count} Einträge</span>
          <span className="font-semibold text-foreground w-12 text-right">
            +{factor.contribution.toFixed(1)} Pkt
          </span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div className="h-2 flex-1 rounded-full bg-muted overflow-hidden">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-xs text-muted-foreground w-8 text-right">
          {pct.toFixed(0)}%
        </span>
      </div>
    </div>
  );
}

function ConfidenceBadge({ level }: { level: string }) {
  const meta: Record<string, string> = {
    High:   "bg-emerald-100 text-emerald-700 border-emerald-200",
    Medium: "bg-amber-100 text-amber-700 border-amber-200",
    Low:    "bg-red-100 text-red-700 border-red-200",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${meta[level] ?? meta.Medium}`}>
      {level === "High" ? "Hoch" : level === "Medium" ? "Mittel" : "Niedrig"}
    </span>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function RiskScoreExplanationCard({ supplierId }: { supplierId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["supplier-risk-explanation", supplierId],
    queryFn: () => getSupplierRiskScoreExplanation(supplierId),
    retry: false,
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex justify-center py-10">
          <Spinner size="lg" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-8 text-center space-y-2">
          <Info className="h-6 w-6 text-muted-foreground mx-auto" />
          <p className="text-sm font-medium">Noch keine Score-Berechnung vorhanden</p>
          <p className="text-xs text-muted-foreground">
            Score neu berechnen um die Faktor-Analyse zu sehen.
          </p>
        </CardContent>
      </Card>
    );
  }

  const band = BAND_META[data.band] ?? BAND_META.Moderate;
  const BandIcon = band.Icon;
  const activeFactors = data.factors.filter((f) => f.contribution > 0);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
            Warum ist dieser Lieferant{" "}
            <span className={`font-bold ${band.color}`}>{band.label}</span> Risk?
          </CardTitle>
          <span className="text-xs text-muted-foreground">
            Formel v{data.formula_version}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-5">
        {/* ── Score hero ── */}
        <div className={`flex items-center gap-4 rounded-lg border p-4 ${band.bg}`}>
          <BandIcon className={`h-10 w-10 shrink-0 ${band.color}`} />
          <div>
            <p className="text-xs text-muted-foreground">Composite Risk Score</p>
            <p className={`text-4xl font-bold tabular-nums ${band.color}`}>
              {data.composite_score.toFixed(1)}
              <span className="text-sm font-normal ml-1 opacity-70">/ 100</span>
            </p>
            <p className={`text-sm font-semibold mt-0.5 ${band.color}`}>
              {band.label} Risk
            </p>
          </div>
          <div className="ml-auto text-right">
            <p className="text-xs text-muted-foreground mb-1">Konfidenz</p>
            <ConfidenceBadge level={data.confidence_level} />
            <p className="text-xs text-muted-foreground mt-1">
              {(data.confidence_score * 100).toFixed(0)}%
            </p>
          </div>
        </div>

        {/* ── Top drivers ── */}
        {data.top_drivers.length > 0 && (
          <div>
            <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <AlertTriangle className="h-3.5 w-3.5" />
              Haupttreiber
            </p>
            <div className="space-y-1">
              {data.top_drivers.map((f) => (
                <div
                  key={f.factor}
                  className="flex items-center justify-between rounded-md bg-red-50 border border-red-100 px-3 py-2 text-sm"
                >
                  <span className="font-medium text-red-800">{f.label}</span>
                  <span className="text-red-700 font-bold">
                    {f.count}× · +{f.contribution.toFixed(1)} Pkt
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── All factors ── */}
        {activeFactors.length > 0 ? (
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Alle Faktoren
            </p>
            <div className="divide-y divide-border">
              {activeFactors.map((f) => (
                <FactorRow key={f.factor} factor={f} />
              ))}
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-dashed p-6 text-center">
            <p className="text-sm text-muted-foreground">
              Score ist 0 — keine Findings, Risks oder offene Actions vorhanden.
            </p>
          </div>
        )}

        {/* ── Limitations ── */}
        {data.limitations.length > 0 && (
          <div className="rounded-lg bg-muted/50 px-3 py-2.5 space-y-1">
            <p className="text-xs font-semibold text-muted-foreground">Einschränkungen</p>
            {data.limitations.map((l, i) => (
              <p key={i} className="text-xs text-muted-foreground">· {l}</p>
            ))}
          </div>
        )}

        {/* ── Methodology note ── */}
        <p className="text-xs text-muted-foreground border-t pt-2">
          {data.confidence_basis}
        </p>
      </CardContent>
    </Card>
  );
}
