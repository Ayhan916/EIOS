"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  ChevronDown,
  GitBranch,
  Shield,
  TrendingUp,
  Zap,
} from "lucide-react";
import { sectorRiskApi, type RightScore, type SimulationResult } from "@/lib/api/sector-risk";
import { useLanguage } from "@/lib/i18n/context";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

// ── Types ─────────────────────────────────────────────────────────────────────

const SCENARIO_OPTIONS = [
  { value: "geopolitical_conflict", label: "Geopolitischer Konflikt" },
  { value: "sanctions_escalation", label: "Sanktionsverschärfung" },
  { value: "natural_disaster", label: "Naturkatastrophe" },
  { value: "regulatory_change", label: "Regulierungsänderung" },
  { value: "labour_unrest", label: "Arbeitskampf / Streik" },
  { value: "supply_shortage", label: "Versorgungsengpass" },
];

const CONFIDENCE_STYLES: Record<string, string> = {
  High: "text-green-700 bg-green-50 border-green-200",
  Medium: "text-amber-700 bg-amber-50 border-amber-200",
  Low: "text-red-700 bg-red-50 border-red-200",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function scoreBar(score: number, max = 10) {
  const pct = (score / max) * 100;
  let color = "bg-green-500";
  if (score >= 8) color = "bg-red-500";
  else if (score >= 6) color = "bg-orange-400";
  else if (score >= 4) color = "bg-amber-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-bold w-4 text-right">{score}</span>
    </div>
  );
}

function scorePill(score: number) {
  let cls = "bg-green-100 text-green-800 border-green-200";
  if (score >= 8) cls = "bg-red-100 text-red-800 border-red-200";
  else if (score >= 6) cls = "bg-orange-100 text-orange-800 border-orange-200";
  else if (score >= 4) cls = "bg-amber-100 text-amber-800 border-amber-200";
  return (
    <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold border ${cls}`}>
      {score}
    </span>
  );
}

function deltaChip(delta: number) {
  if (delta === 0) return <span className="text-xs text-muted-foreground">±0</span>;
  const cls = delta > 0 ? "text-red-600" : "text-green-600";
  return <span className={`text-xs font-semibold ${cls}`}>{delta > 0 ? `+${delta}` : delta}</span>;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function SectorDetailPage({ params }: { params: Promise<{ nace: string }> }) {
  const { nace } = use(params);
  const { t } = useLanguage();
  const [scenario, setScenario] = useState<string>("");

  const { data: baseline, isLoading: baseLoading } = useQuery({
    queryKey: ["sector-baseline", nace],
    queryFn: () => sectorRiskApi.getSector(nace),
  });

  const { data: simulation, isLoading: simLoading } = useQuery({
    queryKey: ["sector-simulate", nace, scenario],
    queryFn: () => sectorRiskApi.simulate(nace, scenario),
    enabled: !!scenario,
  });

  const displayRights: RightScore[] = scenario && simulation ? simulation.rights : (baseline?.rights ?? []);

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Back */}
      <Link href="/sector-risk" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="h-4 w-4" />
        {t("sectorRisk.allSectors")}
      </Link>

      {baseLoading && (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      )}

      {!baseLoading && !baseline && (
        <div className="text-center py-16 text-muted-foreground">
          {t("sectorRisk.notFound")}
        </div>
      )}

      {baseline && (
        <>
          {/* Header */}
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-mono text-lg font-bold text-foreground">{baseline.nace_code}</span>
                <span className="text-sm text-muted-foreground">{baseline.nace_section}</span>
                {baseline.is_fully_calibrated ? (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">{t("sectorRisk.calibrated")} v{baseline.calibration_version}</span>
                ) : (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border">{t("sectorRisk.fallback")}</span>
                )}
              </div>
              <h1 className="text-2xl font-bold text-foreground mt-1">{baseline.sector_name}</h1>
              <p className="text-xs text-muted-foreground mt-0.5">{t("sectorRisk.calibrationDate")} {baseline.calibration_date}</p>
            </div>

            {/* Scenario selector */}
            <div className="flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-muted-foreground shrink-0" />
              <div className="relative">
                <select
                  value={scenario}
                  onChange={(e) => setScenario(e.target.value)}
                  className="appearance-none pl-3 pr-8 py-2 text-sm rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
                >
                  <option value="">{t("sectorRisk.noScenario")}</option>
                  {SCENARIO_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              </div>
              {scenario && simLoading && <Spinner />}
            </div>
          </div>

          {/* Summary cards (shown when scenario active) */}
          {scenario && simulation && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <Card className="border-amber-200 bg-amber-50">
                <CardContent className="pt-4 pb-4">
                  <p className="text-xs text-amber-700">Szenario</p>
                  <p className="text-sm font-semibold text-amber-900 mt-0.5">{simulation.scenario_name}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4 pb-4">
                  <p className="text-xs text-muted-foreground">{t("sectorRisk.rightsIncreased")}</p>
                  <p className="text-2xl font-bold text-orange-600">{simulation.summary.rights_increased}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4 pb-4">
                  <p className="text-xs text-muted-foreground">{t("sectorRisk.rightsAbove7")}</p>
                  <p className="text-2xl font-bold text-red-600">{simulation.summary.rights_above_7_scenario}</p>
                  <p className="text-xs text-muted-foreground">{t("sectorRisk.baselineLabel")} {simulation.summary.rights_above_7_baseline}</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4 pb-4">
                  <p className="text-xs text-muted-foreground">{t("sectorRisk.highestRisk")}</p>
                  <p className="text-2xl font-bold text-red-600">{simulation.summary.highest_risk_score}</p>
                  <p className="text-xs text-muted-foreground truncate">{simulation.summary.highest_risk_right?.replace(/_/g, " ")}</p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Rights table */}
          <Card>
            <div className="px-4 py-3 border-b border-border flex items-center gap-2">
              <Shield className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium text-sm">
                {t("sectorRisk.rightsTable")} — {scenario && simulation ? `${t("sectorRisk.scenarioLabel")} ${simulation.scenario_name}` : t("sectorRisk.baseline")}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left">
                    <th className="px-4 py-2.5 font-medium text-muted-foreground">{t("sectorRisk.right")}</th>
                    <th className="px-4 py-2.5 font-medium text-muted-foreground text-center w-20">{t("sectorRisk.baseline")}</th>
                    {scenario && simulation && (
                      <>
                        <th className="px-4 py-2.5 font-medium text-muted-foreground text-center w-24">{t("sectorRisk.scenario")}</th>
                        <th className="px-4 py-2.5 font-medium text-muted-foreground text-center w-16">{t("sectorRisk.delta")}</th>
                        <th className="px-4 py-2.5 font-medium text-muted-foreground text-center w-16">{t("sectorRisk.factor")}</th>
                      </>
                    )}
                    <th className="px-4 py-2.5 font-medium text-muted-foreground w-40">{t("sectorRisk.probability")}</th>
                  </tr>
                </thead>
                <tbody>
                  {displayRights.map((r) => (
                    <RightRow
                      key={r.right_id}
                      right={r}
                      showScenario={!!scenario && !!simulation}
                      colSpan={scenario && simulation ? 6 : 3}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Calibrate link */}
          <div className="flex justify-end">
            <Link href="/sector-risk/calibration">
              <Button variant="outline" size="sm">
                <Zap className="h-4 w-4 mr-1.5" />
                {t("sectorRisk.startCalibration")}
              </Button>
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

function RightRow({ right, showScenario, colSpan }: { right: RightScore; showScenario: boolean; colSpan: number }) {
  const { t } = useLanguage();
  const [open, setOpen] = useState(false);
  const scenarioScore = right.scenario?.adjusted_probability;
  const delta = right.scenario?.delta ?? 0;
  const factor = right.scenario?.factor ?? 1.0;
  const explanation = right.scenario?.explanation;
  const displayScore = showScenario && scenarioScore !== undefined ? scenarioScore : right.probability;
  const hasExplanation = showScenario && delta > 0 && !!explanation;

  return (
    <>
      <tr
        className={`border-b border-border last:border-0 transition-colors ${hasExplanation ? "cursor-pointer hover:bg-amber-50/40" : "hover:bg-muted/20"}`}
        onClick={() => hasExplanation && setOpen((v) => !v)}
      >
        <td className="px-4 py-2.5">
          <div className="flex items-center gap-1.5">
            {hasExplanation && (
              <span className={`text-xs text-amber-500 transition-transform ${open ? "rotate-90" : ""}`}>▶</span>
            )}
            <span className="text-foreground">{right.right_name}</span>
            {!right.is_calibrated && (
              <span className="ml-1 text-xs text-muted-foreground">(Fallback)</span>
            )}
          </div>
        </td>
        <td className="px-4 py-2.5 text-center">
          {scorePill(right.probability)}
        </td>
        {showScenario && (
          <>
            <td className="px-4 py-2.5 text-center">
              {scenarioScore !== undefined ? scorePill(scenarioScore) : "—"}
            </td>
            <td className="px-4 py-2.5 text-center">
              {deltaChip(delta)}
            </td>
            <td className="px-4 py-2.5 text-center text-xs text-muted-foreground">
              {factor !== 1.0 ? `×${factor.toFixed(1)}` : "—"}
            </td>
          </>
        )}
        <td className="px-4 py-2.5">{scoreBar(displayScore)}</td>
      </tr>
      {hasExplanation && open && (
        <tr className="bg-amber-50/60 border-b border-amber-100">
          <td colSpan={colSpan} className="px-6 py-2.5">
            <p className="text-xs text-amber-800 leading-relaxed">
              <span className="font-semibold">{t("sectorRisk.explanation")}:</span> {explanation}
            </p>
          </td>
        </tr>
      )}
    </>
  );
}
