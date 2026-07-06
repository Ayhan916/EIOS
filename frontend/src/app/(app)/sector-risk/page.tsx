"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, BarChart3, ChevronRight, FlaskConical, Shield, SlidersHorizontal } from "lucide-react";
import { sectorRiskApi, type SectorListItem } from "@/lib/api/sector-risk";
import { useLanguage } from "@/lib/i18n/context";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";

// ── Helpers ───────────────────────────────────────────────────────────────────

function scoreColor(score: number): string {
  if (score >= 8) return "text-red-600 bg-red-50 border-red-200";
  if (score >= 6) return "text-orange-600 bg-orange-50 border-orange-200";
  if (score >= 4) return "text-amber-600 bg-amber-50 border-amber-200";
  return "text-green-700 bg-green-50 border-green-200";
}

function avgBarColor(avg: number): string {
  if (avg >= 7) return "bg-red-500";
  if (avg >= 5) return "bg-orange-400";
  if (avg >= 3.5) return "bg-amber-400";
  return "bg-green-500";
}

function rightLabel(rightId: string | null): string {
  if (!rightId) return "—";
  return rightId.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function SectorRiskPage() {
  const { t } = useLanguage();
  const [calibratedOnly, setCalibratedOnly] = useState(false);
  const [search, setSearch] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["sector-risk-list", calibratedOnly],
    queryFn: () => sectorRiskApi.listSectors(calibratedOnly),
  });

  const sectors = (data ?? []).filter((s) =>
    !search ||
    s.sector_name.toLowerCase().includes(search.toLowerCase()) ||
    s.nace_code.includes(search)
  );

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Shield className="h-6 w-6 text-amber-500" />
            {t("sectorRisk.title")}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">{t("sectorRisk.subtitle")}</p>
        </div>
        <div className="flex gap-2 shrink-0">
          <Link href="/sector-risk/calibration">
            <Button variant="outline" size="sm">
              <FlaskConical className="h-4 w-4 mr-1.5" />
              {t("sectorRisk.calibrate")}
            </Button>
          </Link>
          <Link href="/sector-risk/scenarios">
            <Button variant="outline" size="sm">
              <AlertTriangle className="h-4 w-4 mr-1.5" />
              {t("sectorRisk.scenarios")}
            </Button>
          </Link>
        </div>
      </div>

      {/* Summary cards */}
      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4 pb-4">
              <p className="text-xs text-muted-foreground">{t("sectorRisk.totalSectors")}</p>
              <p className="text-2xl font-bold">{data.length}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-4">
              <p className="text-xs text-muted-foreground">{t("sectorRisk.calibratedSectors")}</p>
              <p className="text-2xl font-bold text-blue-600">{data.filter((s) => s.is_calibrated).length}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-4">
              <p className="text-xs text-muted-foreground">{t("sectorRisk.highRiskRights")}</p>
              <p className="text-2xl font-bold text-red-600">{data.filter((s) => s.highest_probability >= 7).length}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-4">
              <p className="text-xs text-muted-foreground">{t("sectorRisk.highestScore")}</p>
              <p className="text-2xl font-bold">
                {data.length ? (data.reduce((a, s) => a + s.average_probability, 0) / data.length).toFixed(1) : "—"}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 items-center flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <input
            type="text"
            placeholder={t("sectorRisk.searchPlaceholder")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <Button
          variant={calibratedOnly ? "default" : "outline"}
          size="sm"
          onClick={() => setCalibratedOnly((v) => !v)}
        >
          <SlidersHorizontal className="h-4 w-4 mr-1.5" />
          {t("sectorRisk.onlyCalibratedFilter")}
        </Button>
      </div>

      {/* Table */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}
      {error && (
        <EmptyState icon={AlertTriangle} title={t("sectorRisk.loadError")} description={t("sectorRisk.loadErrorDesc")} />
      )}
      {!isLoading && !error && sectors.length === 0 && (
        <EmptyState icon={BarChart3} title={t("sectorRisk.noSectorsFound")} description={t("sectorRisk.adjustFilter")} />
      )}
      {!isLoading && sectors.length > 0 && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="px-4 py-3 font-medium text-muted-foreground w-20">NACE</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground">{t("sectorRisk.colSector")}</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground text-center w-24">{t("sectorRisk.colHighestRisk")}</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground text-center w-24">{t("sectorRisk.colRightsAbove7")}</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground w-40">{t("sectorRisk.colAvgProbability")}</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground w-28">{t("common.status")}</th>
                  <th className="px-4 py-3 w-10" />
                </tr>
              </thead>
              <tbody>
                {sectors.map((sector) => (
                  <SectorRow key={sector.nace_code} sector={sector} />
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

function SectorRow({ sector }: { sector: SectorListItem }) {
  const { t } = useLanguage();
  return (
    <tr className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors">
      <td className="px-4 py-3">
        <span className="font-mono font-semibold text-foreground">{sector.nace_code}</span>
        <span className="ml-1 text-xs text-muted-foreground">{sector.nace_section}</span>
      </td>
      <td className="px-4 py-3 font-medium text-foreground">{sector.sector_name}</td>
      <td className="px-4 py-3 text-center">
        <span className={`inline-flex items-center justify-center w-9 h-9 rounded-full text-sm font-bold border ${scoreColor(sector.highest_probability)}`}>
          {sector.highest_probability}
        </span>
      </td>
      <td className="px-4 py-3 text-center">
        <span className={`text-sm font-semibold ${sector.rights_above_7 >= 5 ? "text-red-600" : sector.rights_above_7 >= 2 ? "text-orange-500" : "text-muted-foreground"}`}>
          {sector.rights_above_7}
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${avgBarColor(sector.average_probability)}`}
              style={{ width: `${(sector.average_probability / 10) * 100}%` }}
            />
          </div>
          <span className="text-xs font-medium w-8 text-right">{sector.average_probability.toFixed(1)}</span>
        </div>
      </td>
      <td className="px-4 py-3">
        {sector.is_calibrated ? (
          <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
            {t("sectorRisk.calibrated")}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border">
            {t("sectorRisk.fallback")}
          </span>
        )}
      </td>
      <td className="px-4 py-3">
        <Link href={`/sector-risk/${sector.nace_code}`} className="text-muted-foreground hover:text-foreground transition-colors">
          <ChevronRight className="h-4 w-4" />
        </Link>
      </td>
    </tr>
  );
}
