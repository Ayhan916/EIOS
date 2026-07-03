"use client";

import { useQueries } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardList,
  FileCheck,
  FileText,
  Lightbulb,
  Radio,
  Search,
  Shield,
  Upload,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import apiClient from "@/lib/api/client";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useLanguage } from "@/lib/i18n/context";
import { useReadiness } from "@/hooks/use-readiness";
import type { StepReadiness } from "@/lib/api/pipeline";

// ── Helper ────────────────────────────────────────────────────────────────────

function extractCount(data: unknown): number {
  if (Array.isArray(data)) return data.length;
  if (data && typeof data === "object") {
    const d = data as Record<string, unknown>;
    if (typeof d.total === "number") return d.total;
    if (typeof d.count === "number") return d.count;
    if (Array.isArray(d.items)) return (d.items as unknown[]).length;
    if (Array.isArray(d.data)) return (d.data as unknown[]).length;
    if (Array.isArray(d.suppliers)) return (d.suppliers as unknown[]).length;
    if (Array.isArray(d.assessments)) return (d.assessments as unknown[]).length;
    if (Array.isArray(d.findings)) return (d.findings as unknown[]).length;
    if (Array.isArray(d.risks)) return (d.risks as unknown[]).length;
    if (Array.isArray(d.recommendations)) return (d.recommendations as unknown[]).length;
  }
  return 0;
}

// ── Step definitions ──────────────────────────────────────────────────────────

interface StepDef {
  key: string;
  icon: React.ElementType;
  hue: string;       // Tailwind color token (e.g. "blue")
  href: string;
  endpoint: string;
  labelKey: "process.step1" | "process.step2" | "process.step3" | "process.step4" | "process.step5" | "process.step6" | "process.step7" | "process.step8" | "process.step9";
  descKey:  "process.step1Desc" | "process.step2Desc" | "process.step3Desc" | "process.step4Desc" | "process.step5Desc" | "process.step6Desc" | "process.step7Desc" | "process.step8Desc" | "process.step9Desc";
}

const STEPS: StepDef[] = [
  { key: "onboard",        icon: Building2,    hue: "blue",    href: "/suppliers",                     endpoint: "/suppliers?limit=1",                  labelKey: "process.step1", descKey: "process.step1Desc" },
  { key: "plan",           icon: Radio,        hue: "indigo",  href: "/assessments/schedules",          endpoint: "/assessments/schedules?limit=1",       labelKey: "process.step2", descKey: "process.step2Desc" },
  { key: "assess",         icon: ClipboardList, hue: "violet", href: "/assessments",                   endpoint: "/assessments?limit=1",                 labelKey: "process.step3", descKey: "process.step3Desc" },
  { key: "findings",       icon: Search,       hue: "amber",   href: "/risk/findings",                 endpoint: "/findings?limit=1",                    labelKey: "process.step4", descKey: "process.step4Desc" },
  { key: "risks",          icon: AlertTriangle, hue: "orange", href: "/risk/risks",                    endpoint: "/risks?limit=1",                       labelKey: "process.step5", descKey: "process.step5Desc" },
  { key: "recommendations",icon: Lightbulb,    hue: "yellow",  href: "/risk/recommendations",          endpoint: "/recommendations?limit=1",             labelKey: "process.step6", descKey: "process.step6Desc" },
  { key: "remediation",    icon: Wrench,       hue: "/lime",   href: "/sustainability/initiatives",    endpoint: "/operating-system/initiatives?limit=1", labelKey: "process.step7", descKey: "process.step7Desc" },
  { key: "verification",   icon: FileCheck,    hue: "teal",    href: "/risk/evidence",                 endpoint: "/evidence?limit=1",                    labelKey: "process.step8", descKey: "process.step8Desc" },
  { key: "reporting",      icon: BarChart3,    hue: "emerald", href: "/reports",                       endpoint: "/reporting/packages?limit=1",          labelKey: "process.step9", descKey: "process.step9Desc" },
];

// Tailwind hue → class maps (must be full strings for purge safety)
const HUE_CLASSES: Record<string, { badge: string; icon: string; border: string; dot: string; ring: string }> = {
  "blue":    { badge: "bg-blue-500 text-white",    icon: "text-blue-500",    border: "border-blue-200",    dot: "bg-blue-500",    ring: "ring-blue-200" },
  "indigo":  { badge: "bg-indigo-500 text-white",  icon: "text-indigo-500",  border: "border-indigo-200",  dot: "bg-indigo-500",  ring: "ring-indigo-200" },
  "violet":  { badge: "bg-violet-500 text-white",  icon: "text-violet-500",  border: "border-violet-200",  dot: "bg-violet-500",  ring: "ring-violet-200" },
  "amber":   { badge: "bg-amber-500 text-white",   icon: "text-amber-500",   border: "border-amber-200",   dot: "bg-amber-500",   ring: "ring-amber-200" },
  "orange":  { badge: "bg-orange-500 text-white",  icon: "text-orange-500",  border: "border-orange-200",  dot: "bg-orange-500",  ring: "ring-orange-200" },
  "yellow":  { badge: "bg-yellow-500 text-slate-900", icon: "text-yellow-600", border: "border-yellow-200", dot: "bg-yellow-500", ring: "ring-yellow-200" },
  "/lime":   { badge: "bg-lime-500 text-slate-900",   icon: "text-lime-600",   border: "border-lime-200",   dot: "bg-lime-500",   ring: "ring-lime-200" },
  "teal":    { badge: "bg-teal-500 text-white",    icon: "text-teal-500",    border: "border-teal-200",    dot: "bg-teal-500",    ring: "ring-teal-200" },
  "emerald": { badge: "bg-emerald-500 text-white", icon: "text-emerald-500", border: "border-emerald-200", dot: "bg-emerald-500", ring: "ring-emerald-200" },
};

// ── Step card ─────────────────────────────────────────────────────────────────

function StepCard({ step, index, count, isLoading, readiness }: {
  step: StepDef;
  index: number;
  count: number;
  isLoading: boolean;
  readiness: StepReadiness | undefined;
}) {
  const { t } = useLanguage();
  const [showMissing, setShowMissing] = useState(false);
  const Icon = step.icon;
  const hue = HUE_CLASSES[step.hue] ?? HUE_CLASSES["blue"];
  const isActive = count > 0;
  const hasMissing = readiness && readiness.status !== "ok" && readiness.missing.length > 0;
  const isError = readiness?.status === "error";

  const cardBorder = hasMissing
    ? (isError ? "border-red-300 dark:border-red-700" : "border-amber-300 dark:border-amber-700")
    : isActive ? `border ${hue.border}` : "border-border";

  return (
    <Card className={`group relative transition-all duration-200 hover:shadow-md ${cardBorder}`}>
      <CardContent className="py-5 space-y-3">
        {/* Step number + icon row */}
        <div className="flex items-start justify-between gap-2">
          <div className={`flex h-7 w-7 items-center justify-center rounded-full text-[11px] font-bold shrink-0 ${isActive ? hue.badge : "bg-slate-100 text-slate-500"}`}>
            {index + 1}
          </div>
          <div className="flex items-center gap-1.5">
            {hasMissing && (
              <AlertTriangle className={`h-3.5 w-3.5 ${isError ? "text-red-500" : "text-amber-500"}`} />
            )}
            {readiness && readiness.status === "ok" && (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            )}
            <div className={`rounded-lg p-2 ${isActive ? `ring-2 ${hue.ring}` : "bg-slate-50"}`}>
              <Icon className={`h-4 w-4 ${isActive ? hue.icon : "text-slate-400"}`} />
            </div>
          </div>
        </div>

        {/* Title + description */}
        <div>
          <p className="font-semibold text-sm leading-tight">{t(step.labelKey)}</p>
          <p className="text-xs text-muted-foreground mt-0.5 leading-snug">{t(step.descKey)}</p>
        </div>

        {/* Readiness score bar */}
        {readiness && (
          <div>
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-[10px] text-muted-foreground">{t("readiness.score")}</span>
              <span className={`text-[10px] font-bold ${
                readiness.score >= 80 ? "text-emerald-600" :
                readiness.score >= 50 ? "text-amber-600" : "text-red-600"
              }`}>{readiness.score}%</span>
            </div>
            <div className="h-1 w-full rounded-full bg-muted overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  readiness.score >= 80 ? "bg-emerald-500" :
                  readiness.score >= 50 ? "bg-amber-400" : "bg-red-500"
                }`}
                style={{ width: `${readiness.score}%` }}
              />
            </div>
          </div>
        )}

        {/* Count + status */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <span className={`inline-block h-2 w-2 rounded-full ${isActive ? hue.dot : "bg-slate-200"}`} />
            {isLoading
              ? <Spinner className="h-3.5 w-3.5" />
              : <span className={`text-sm font-bold tabular-nums ${isActive ? "text-foreground" : "text-slate-400"}`}>{count}</span>}
            <span className="text-xs text-muted-foreground">{t("process.openItems")}</span>
          </div>
          {isActive && !hasMissing && (
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 flex items-center gap-0.5">
              <CheckCircle2 className="h-2.5 w-2.5" /> Aktiv
            </span>
          )}
        </div>

        {/* Missing items toggle */}
        {hasMissing && (
          <div className={`rounded-md border px-2.5 py-2 text-xs ${
            isError
              ? "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/30"
              : "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30"
          }`}>
            <button
              onClick={() => setShowMissing(!showMissing)}
              className={`flex w-full items-center gap-1.5 font-medium ${isError ? "text-red-700 dark:text-red-300" : "text-amber-700 dark:text-amber-300"}`}
            >
              {isError
                ? <AlertTriangle className="h-3 w-3 shrink-0" />
                : <AlertTriangle className="h-3 w-3 shrink-0" />
              }
              <span className="flex-1 text-left">{t("readiness.whatsMissing")} ({readiness.missing.length})</span>
              {showMissing ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
            {showMissing && (
              <ul className={`mt-1.5 space-y-1 ${isError ? "text-red-600 dark:text-red-400" : "text-amber-700 dark:text-amber-300"}`}>
                {readiness.missing.map((item, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    {item.type === "upload" ? <Upload className="h-3 w-3 shrink-0 mt-0.5" /> : <ArrowRight className="h-3 w-3 shrink-0 mt-0.5" />}
                    <Link href={item.href} className="underline underline-offset-2 hover:opacity-80 leading-snug">
                      {item.label}{item.count > 0 ? ` (${item.count})` : ""}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Link */}
        <Link href={step.href}
          className={`flex w-full items-center justify-center gap-1.5 rounded-lg py-1.5 text-xs font-medium transition-colors ${
            isActive
              ? `${hue.badge} hover:opacity-90`
              : "bg-slate-100 text-slate-500 hover:bg-slate-200"
          }`}>
          {t("process.viewPage")} <ArrowRight className="h-3 w-3" />
        </Link>
      </CardContent>
    </Card>
  );
}

// ── Row connector (between grid rows) ─────────────────────────────────────────

function RowConnector({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 py-1 col-span-3">
      <div className="h-px flex-1 bg-border" />
      <span className="flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1 text-[11px] font-medium text-muted-foreground whitespace-nowrap">
        <ChevronDown className="h-3 w-3" /> {label}
      </span>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

const PHASE_LABELS = ["Eingang & Analyse", "Bewertung & Steuerung", "Aktion & Abschluss"];

export default function ProcessPage() {
  const { t } = useLanguage();
  const { data: readinessData } = useReadiness();

  function getReadiness(key: string): StepReadiness | undefined {
    return readinessData?.steps.find((s) => s.key === key);
  }

  const results = useQueries({
    queries: STEPS.map((step) => ({
      queryKey: ["process-count", step.key],
      queryFn: async () => {
        try {
          const res = await apiClient.get(step.endpoint);
          return extractCount(res.data);
        } catch {
          return 0;
        }
      },
      staleTime: 120_000,
      retry: false,
    })),
  });

  const counts = results.map((r) => (r.data ?? 0));
  const isAnyLoading = results.some((r) => r.isLoading);
  const activeCount = counts.filter((c) => c > 0).length;
  const totalOpen = counts.reduce((s, c) => s + c, 0);
  const completionPct = Math.round((activeCount / STEPS.length) * 100);

  // Steps are arranged 3 per row
  const row1 = STEPS.slice(0, 3);
  const row2 = STEPS.slice(3, 6);
  const row3 = STEPS.slice(6, 9);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("process.title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("process.subtitle")}</p>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-muted-foreground">Aktive Phasen</p>
            <p className="text-2xl font-bold text-primary mt-0.5">{activeCount}<span className="text-base font-normal text-muted-foreground ml-1">/ {STEPS.length}</span></p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-3">
            <p className="text-xs text-muted-foreground">Offene Items gesamt</p>
            <p className={`text-2xl font-bold mt-0.5 ${totalOpen > 0 ? "text-foreground" : "text-slate-400"}`}>
              {isAnyLoading ? <Spinner className="h-5 w-5" /> : totalOpen}
            </p>
          </CardContent>
        </Card>
        <Card className="sm:col-span-2">
          <CardContent className="pt-4 pb-3">
            <div className="flex justify-between items-center mb-1.5">
              <p className="text-xs text-muted-foreground">Pipeline-Auslastung</p>
              <div className="flex items-center gap-3">
                {readinessData && (
                  <span className={`text-[10px] font-semibold ${
                    readinessData.overall_score >= 80 ? "text-emerald-600" :
                    readinessData.overall_score >= 50 ? "text-amber-600" : "text-red-600"
                  }`}>
                    {t("readiness.overallScore")}: {readinessData.overall_score}%
                  </span>
                )}
                <p className="text-xs font-semibold">{completionPct}%</p>
              </div>
            </div>
            <div className="h-2.5 w-full rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-500 via-violet-500 to-emerald-500 transition-all duration-500"
                style={{ width: `${completionPct}%` }}
              />
            </div>
            <div className="mt-1.5 flex gap-1 flex-wrap">
              {STEPS.map((step, i) => {
                const hue = HUE_CLASSES[step.hue] ?? HUE_CLASSES["blue"];
                return (
                  <span key={step.key}
                    className={`inline-block h-1.5 w-1.5 rounded-full ${counts[i] > 0 ? hue.dot : "bg-slate-200"}`}
                    title={t(step.labelKey)}
                  />
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Phase label 1 */}
        <div className="sm:col-span-3">
          <PhaseDivider label={PHASE_LABELS[0]} icon={<FileText className="h-3.5 w-3.5" />} />
        </div>

        {/* Row 1 */}
        {row1.map((step, i) => (
          <div key={step.key} className="relative">
            <StepCard step={step} index={i} count={counts[i]} isLoading={results[i].isLoading} readiness={getReadiness(step.key)} />
            {i < 2 && (
              <div className="hidden sm:flex absolute -right-2 top-1/2 -translate-y-1/2 z-10 items-center justify-center h-4 w-4 rounded-full bg-border">
                <ArrowRight className="h-2.5 w-2.5 text-muted-foreground" />
              </div>
            )}
          </div>
        ))}

        {/* Phase label 2 */}
        <RowConnector label="→ Weiter zur Bewertung" />
        <div className="sm:col-span-3">
          <PhaseDivider label={PHASE_LABELS[1]} icon={<Shield className="h-3.5 w-3.5" />} />
        </div>

        {/* Row 2 */}
        {row2.map((step, i) => {
          const globalIdx = i + 3;
          return (
            <div key={step.key} className="relative">
              <StepCard step={step} index={globalIdx} count={counts[globalIdx]} isLoading={results[globalIdx].isLoading} readiness={getReadiness(step.key)} />
              {i < 2 && (
                <div className="hidden sm:flex absolute -right-2 top-1/2 -translate-y-1/2 z-10 items-center justify-center h-4 w-4 rounded-full bg-border">
                  <ArrowRight className="h-2.5 w-2.5 text-muted-foreground" />
                </div>
              )}
            </div>
          );
        })}

        {/* Phase label 3 */}
        <RowConnector label="→ Weiter zur Umsetzung" />
        <div className="sm:col-span-3">
          <PhaseDivider label={PHASE_LABELS[2]} icon={<CheckCircle2 className="h-3.5 w-3.5" />} />
        </div>

        {/* Row 3 */}
        {row3.map((step, i) => {
          const globalIdx = i + 6;
          return (
            <div key={step.key} className="relative">
              <StepCard step={step} index={globalIdx} count={counts[globalIdx]} isLoading={results[globalIdx].isLoading} readiness={getReadiness(step.key)} />
              {i < 2 && (
                <div className="hidden sm:flex absolute -right-2 top-1/2 -translate-y-1/2 z-10 items-center justify-center h-4 w-4 rounded-full bg-border">
                  <ArrowRight className="h-2.5 w-2.5 text-muted-foreground" />
                </div>
              )}
            </div>
          );
        })}

        {/* Final step — disclosure output */}
        <div className="sm:col-span-3 mt-2">
          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-emerald-300" />
            <Link href="/disclosure"
              className="flex items-center gap-2 rounded-xl border-2 border-emerald-400 bg-emerald-50 px-5 py-3 text-sm font-semibold text-emerald-800 hover:bg-emerald-100 transition-colors">
              <FileText className="h-4 w-4" />
              Disclosure & Regulatorische Meldungen
              <ArrowRight className="h-4 w-4 ml-1" />
            </Link>
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-emerald-300" />
          </div>
        </div>
      </div>

      {/* Process legend */}
      <div className="rounded-xl border border-border bg-muted/30 px-5 py-4">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">Legende</p>
        <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-blue-500" /> Phase aktiv (Items vorhanden)
          </div>
          <div className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full bg-slate-200" /> Phase leer / noch nicht begonnen
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3 w-3 text-emerald-600" /> Aktiv-Badge
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Phase divider ─────────────────────────────────────────────────────────────

function PhaseDivider({ label, icon }: { label: string; icon: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-1">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}
