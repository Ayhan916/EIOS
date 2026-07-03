"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpRight,
  ChevronDown,
  ChevronRight,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Minus,
  Users,
} from "lucide-react";
import {
  segmentationApi,
  RiskSegment,
  SegmentedSupplierEntry,
} from "@/lib/api/supplier-segmentation";

// ── Band config ───────────────────────────────────────────────────────────────

const BAND_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; border: string; icon: React.ElementType }
> = {
  Critical: {
    label: "Critical",
    color: "text-red-700",
    bg: "bg-red-50 dark:bg-red-950/20",
    border: "border-red-300 dark:border-red-800",
    icon: AlertTriangle,
  },
  High: {
    label: "High",
    color: "text-orange-700",
    bg: "bg-orange-50 dark:bg-orange-950/20",
    border: "border-orange-300 dark:border-orange-800",
    icon: ShieldAlert,
  },
  Moderate: {
    label: "Moderate",
    color: "text-amber-700",
    bg: "bg-amber-50 dark:bg-amber-950/20",
    border: "border-amber-200 dark:border-amber-800",
    icon: AlertTriangle,
  },
  Low: {
    label: "Low",
    color: "text-emerald-700",
    bg: "bg-emerald-50 dark:bg-emerald-950/20",
    border: "border-emerald-200 dark:border-emerald-800",
    icon: ShieldCheck,
  },
};

// ── Trend icon ────────────────────────────────────────────────────────────────

function TrendIcon({ trend, delta }: { trend: string; delta: number }) {
  if (trend === "Improving")
    return (
      <span className="flex items-center gap-0.5 text-xs text-emerald-600">
        <TrendingUp className="h-3 w-3" />
        +{delta.toFixed(1)}
      </span>
    );
  if (trend === "Deteriorating")
    return (
      <span className="flex items-center gap-0.5 text-xs text-red-500">
        <TrendingDown className="h-3 w-3" />
        {delta.toFixed(1)}
      </span>
    );
  return (
    <span className="flex items-center gap-0.5 text-xs text-gray-400">
      <Minus className="h-3 w-3" /> Stable
    </span>
  );
}

// ── Supplier row ──────────────────────────────────────────────────────────────

function SupplierRow({ s }: { s: SegmentedSupplierEntry }) {
  return (
    <div className="flex items-center gap-3 py-1.5 border-b border-gray-100 dark:border-gray-800 last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <Link
            href={`/suppliers/${s.supplier_id}`}
            className="text-sm font-medium text-gray-900 dark:text-white hover:text-indigo-600 truncate"
          >
            {s.name}
          </Link>
          <ArrowUpRight className="h-3 w-3 text-gray-300 shrink-0" />
        </div>
        <p className="text-xs text-gray-400 truncate">
          {s.country}{s.industry ? ` · ${s.industry}` : ""}
          {s.supplier_tier ? ` · ${s.supplier_tier}` : ""}
        </p>
      </div>
      <div className="text-right shrink-0 space-y-0.5">
        <p className="text-xs font-bold tabular-nums text-gray-700 dark:text-gray-300">
          Risk {s.risk_score.toFixed(0)}
        </p>
        <TrendIcon trend={s.trend} delta={s.trend_delta} />
      </div>
    </div>
  );
}

// ── Segment card ──────────────────────────────────────────────────────────────

function SegmentCard({ segment }: { segment: RiskSegment }) {
  const [expanded, setExpanded] = useState(segment.risk_band === "Critical" || segment.risk_band === "High");
  const cfg = BAND_CONFIG[segment.risk_band] ?? BAND_CONFIG.Low;
  const Icon = cfg.icon;

  return (
    <div className={`rounded-xl border ${cfg.border} ${cfg.bg} overflow-hidden`}>
      {/* Header */}
      <div
        className="flex items-center gap-3 p-4 cursor-pointer select-none"
        onClick={() => setExpanded((v) => !v)}
      >
        <Icon className={`h-5 w-5 ${cfg.color} shrink-0`} />
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={`font-bold text-base ${cfg.color}`}>
              {cfg.label}
            </span>
            <span className={`text-2xl font-black tabular-nums ${cfg.color}`}>
              {segment.count}
            </span>
          </div>
          {segment.count > 0 && (
            <div className="flex gap-3 mt-0.5 text-xs text-gray-500">
              <span>Avg Risk: <b className="text-gray-700 dark:text-gray-300">{segment.avg_risk_score}</b></span>
              <span>Avg ESG: <b className="text-gray-700 dark:text-gray-300">{segment.avg_esg_score}</b></span>
            </div>
          )}
        </div>

        {/* Trend mini-summary */}
        {segment.count > 0 && (
          <div className="text-right text-xs space-y-0.5 shrink-0">
            {segment.improving > 0 && (
              <p className="text-emerald-600 flex items-center justify-end gap-0.5">
                <TrendingUp className="h-3 w-3" /> {segment.improving}
              </p>
            )}
            {segment.deteriorating > 0 && (
              <p className="text-red-500 flex items-center justify-end gap-0.5">
                <TrendingDown className="h-3 w-3" /> {segment.deteriorating}
              </p>
            )}
          </div>
        )}

        <span className="text-gray-400 ml-1">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </span>
      </div>

      {/* Supplier list */}
      {expanded && (
        <div className="bg-white dark:bg-gray-900/60 border-t border-gray-200 dark:border-gray-700 px-4 py-2">
          {segment.suppliers.length === 0 ? (
            <p className="text-xs text-gray-400 py-2">No suppliers in this tier.</p>
          ) : (
            segment.suppliers.map((s) => <SupplierRow key={s.supplier_id} s={s} />)
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SupplierSegmentationPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["supplier-segmentation"],
    queryFn: segmentationApi.getSegmentation,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-orange-100 dark:bg-orange-900/30 p-2">
          <Users className="h-6 w-6 text-orange-600 dark:text-orange-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            Supplier Segmentation
          </h1>
          <p className="text-xs text-gray-500">
            Risk tiering based on latest deterministic ESG/Risk scores
          </p>
        </div>
      </div>

      {/* KPI strip */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Total Suppliers", value: data.total_suppliers, color: "text-gray-700" },
            { label: "Scored",          value: data.total_scored,    color: "text-indigo-600" },
            {
              label: "Critical + High",
              value: (data.segments.find((s) => s.risk_band === "Critical")?.count ?? 0) +
                     (data.segments.find((s) => s.risk_band === "High")?.count ?? 0),
              color: "text-red-600",
            },
            { label: "Unscored",        value: data.unscored_count,  color: "text-gray-400" },
          ].map((k) => (
            <div
              key={k.label}
              className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3"
            >
              <p className="text-xs text-gray-400 mb-1">{k.label}</p>
              <p className={`text-2xl font-bold tabular-nums ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Segment cards */}
      {isLoading ? (
        <div className="py-12 text-center text-sm text-gray-400">Loading segmentation…</div>
      ) : !data ? null : (
        <div className="space-y-3">
          {data.segments.map((seg) => (
            <SegmentCard key={seg.risk_band} segment={seg} />
          ))}
          {data.unscored_count > 0 && (
            <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 p-4 text-center">
              <p className="text-sm text-gray-400">
                {data.unscored_count} supplier{data.unscored_count !== 1 ? "s" : ""} not yet scored.{" "}
                <Link href="/suppliers" className="text-indigo-500 hover:underline">
                  Trigger scoring →
                </Link>
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
