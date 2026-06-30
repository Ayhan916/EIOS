"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, FlaskConical, Loader2, XCircle } from "lucide-react";
import { listScienceBasedTargets, type ScienceBasedTarget } from "@/lib/api/sustainability";
import apiClient from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useLanguage } from "@/lib/i18n/context";

const ORG_ID = "default";

function statusColor(s: string) {
  switch (s) {
    case "COMMITTED":  return "bg-emerald-100 text-emerald-800";
    case "VALIDATED":  return "bg-blue-100 text-blue-800";
    case "ACHIEVED":   return "bg-purple-100 text-purple-800";
    case "DRAFT":      return "bg-slate-100 text-slate-600";
    default:           return "bg-amber-100 text-amber-800";
  }
}

interface ValidationResult {
  compliant: boolean;
  required_reduction_percent: number;
  achieved_reduction_percent: number;
  gap_percent: number;
  message: string;
}

function SBTCard({ sbt }: { sbt: ScienceBasedTarget }) {
  const { t } = useLanguage();
  const [showValidate, setShowValidate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [s1Base, setS1Base] = useState("");
  const [s2Base, setS2Base] = useState("");
  const [s1Target, setS1Target] = useState("");
  const [s2Target, setS2Target] = useState("");

  async function runValidation() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await apiClient.post("/api/v1/integrations/sbti/validate", {
        target_id: sbt.id,
        base_year: sbt.baseline_year,
        target_year: sbt.target_year,
        base_year_scope1_tco2e: parseFloat(s1Base),
        base_year_scope2_tco2e: parseFloat(s2Base),
        target_scope1_tco2e: parseFloat(s1Target),
        target_scope2_tco2e: parseFloat(s2Target),
      });
      setResult(r.data);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Validation failed");
    } finally {
      setBusy(false);
    }
  }

  const canSubmit = s1Base && s2Base && s1Target && s2Target;

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold truncate">{sbt.name}</p>
          <p className="text-xs text-muted-foreground">
            {sbt.sbt_type} · {sbt.sbt_framework} · {sbt.scope}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`rounded px-2 py-0.5 text-xs font-medium ${statusColor(sbt.sbt_status)}`}>
            {sbt.sbt_status}
          </span>
          <Button
            size="sm"
            variant="outline"
            className="h-7 px-2 text-xs"
            onClick={() => { setShowValidate((v) => !v); setResult(null); setError(null); }}
          >
            <FlaskConical className="h-3.5 w-3.5 mr-1" />
            {t("sustain.validateTarget")}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <div className="rounded bg-muted p-2">
          <p className="text-muted-foreground">{t("sustain.baselineYear")}</p>
          <p className="font-bold">{sbt.baseline_year}</p>
        </div>
        <div className="rounded bg-muted p-2">
          <p className="text-muted-foreground">{t("sustain.targetYear")}</p>
          <p className="font-bold">{sbt.target_year}</p>
        </div>
        <div className="rounded bg-emerald-50 p-2">
          <p className="text-muted-foreground">Reduction Goal</p>
          <p className="font-bold text-emerald-700">{sbt.target_reduction_percent}%</p>
        </div>
      </div>

      {/* Milestone progress bars */}
      {(() => {
        const now = 2026;
        const base = sbt.baseline_year ?? 2020;
        const milestones = [
          { year: 2030, color: "bg-amber-500" },
          { year: 2050, color: "bg-emerald-500" },
        ];
        return (
          <div className="space-y-2 pt-1">
            {milestones.map(({ year, color }) => {
              const pct = base >= year ? 100 : Math.min(Math.max(Math.round(((now - base) / (year - base)) * 100), 0), 100);
              return (
                <div key={year} className="space-y-0.5">
                  <div className="flex justify-between text-[10px] text-muted-foreground">
                    <span>Progress toward {year}</span>
                    <span className="font-medium">{pct}%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                    <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        );
      })()}

      {sbt.description && (
        <p className="text-xs text-muted-foreground line-clamp-2">{sbt.description}</p>
      )}

      <div className="flex gap-4 text-xs text-muted-foreground">
        {sbt.commitment_date && (
          <span>Committed {new Date(sbt.commitment_date).toLocaleDateString()}</span>
        )}
        {sbt.approval_date && (
          <span>Approved {new Date(sbt.approval_date).toLocaleDateString()}</span>
        )}
      </div>

      {showValidate && (
        <div className="rounded-lg border bg-muted/30 p-3 space-y-3">
          <p className="text-xs font-medium">SBTi 1.5°C Validation — Emission Inputs (tCO₂e)</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <label className="block text-muted-foreground mb-1">Scope 1 — Baseline</label>
              <input
                type="number" min="0" step="0.01"
                className="w-full rounded border px-2 py-1 text-sm bg-background"
                placeholder="e.g. 5000"
                value={s1Base}
                onChange={(e) => setS1Base(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-muted-foreground mb-1">Scope 2 — Baseline</label>
              <input
                type="number" min="0" step="0.01"
                className="w-full rounded border px-2 py-1 text-sm bg-background"
                placeholder="e.g. 2000"
                value={s2Base}
                onChange={(e) => setS2Base(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-muted-foreground mb-1">Scope 1 — Target</label>
              <input
                type="number" min="0" step="0.01"
                className="w-full rounded border px-2 py-1 text-sm bg-background"
                placeholder="e.g. 2500"
                value={s1Target}
                onChange={(e) => setS1Target(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-muted-foreground mb-1">Scope 2 — Target</label>
              <input
                type="number" min="0" step="0.01"
                className="w-full rounded border px-2 py-1 text-sm bg-background"
                placeholder="e.g. 1000"
                value={s2Target}
                onChange={(e) => setS2Target(e.target.value)}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              className="h-7 text-xs"
              disabled={!canSubmit || busy}
              onClick={runValidation}
            >
              {busy ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
              Run Validation
            </Button>
            <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setShowValidate(false)}>
              {t("common.cancel")}
            </Button>
          </div>

          {result && (
            <div className={`rounded-md p-3 text-sm flex items-start gap-2 ${result.compliant ? "bg-emerald-50 border border-emerald-200" : "bg-red-50 border border-red-200"}`}>
              {result.compliant
                ? <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                : <XCircle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
              }
              <div className="space-y-1">
                <p className={`font-medium ${result.compliant ? "text-emerald-800" : "text-red-800"}`}>
                  {result.compliant ? "Compliant with SBTi 1.5°C" : "Not compliant with SBTi 1.5°C"}
                </p>
                <p className="text-xs text-muted-foreground">{result.message}</p>
                <div className="flex gap-4 text-xs">
                  <span>Required: <strong>{result.required_reduction_percent?.toFixed(1)}%</strong></span>
                  <span>Achieved: <strong>{result.achieved_reduction_percent?.toFixed(1)}%</strong></span>
                  {!result.compliant && (
                    <span className="text-red-600">Gap: <strong>{result.gap_percent?.toFixed(1)}%</strong></span>
                  )}
                </div>
              </div>
            </div>
          )}
          {error && (
            <p className="text-xs text-red-600">{error}</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function ScienceBasedTargetsPage() {
  const { t } = useLanguage();
  const { data: sbts, isLoading } = useQuery({
    queryKey: ["sbts", ORG_ID],
    queryFn: () => listScienceBasedTargets(ORG_ID),
  });

  const committed = sbts?.filter((s) => s.sbt_status === "COMMITTED").length ?? 0;
  const validated = sbts?.filter((s) => s.sbt_status === "VALIDATED").length ?? 0;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("sustain.sbtTitle")}</h1>
        <p className="text-muted-foreground text-sm mt-1">
          {t("sustain.sbtSubtitle")}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Total SBTs</p>
            <p className="text-2xl font-bold">{sbts?.length ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Committed</p>
            <p className="text-2xl font-bold text-emerald-600">{committed}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Validated</p>
            <p className="text-2xl font-bold text-blue-600">{validated}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FlaskConical className="h-4 w-4 text-emerald-600" />
            {t("sustain.sbtTitle")}{sbts ? ` (${sbts.length})` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <Spinner />}
          {sbts?.length === 0 && (
            <p className="text-sm text-muted-foreground">
              {t("sustain.noSbtDesc")}
            </p>
          )}
          <div className="space-y-4">
            {sbts?.map((s) => <SBTCard key={s.id} sbt={s} />)}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
