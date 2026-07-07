"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import {
  AlertTriangle,
  ArrowUpRight,
  ChevronDown,
  ChevronRight,
  Globe,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Minus,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { geoHeatmapApi, GeoCountryEntry } from "@/lib/api/geo-heatmap";

// ── Band config ───────────────────────────────────────────────────────────────

const BAND_COLOR: Record<string, string> = {
  Critical: "text-red-700",
  High:     "text-orange-600",
  Moderate: "text-amber-600",
  Low:      "text-emerald-600",
};

const BAND_BG: Record<string, string> = {
  Critical: "bg-red-100 dark:bg-red-950/30",
  High:     "bg-orange-100 dark:bg-orange-950/30",
  Moderate: "bg-amber-100 dark:bg-amber-950/30",
  Low:      "bg-emerald-100 dark:bg-emerald-950/30",
};

const BAND_BAR_COLOR: Record<string, string> = {
  Critical: "#dc2626",
  High:     "#ea580c",
  Moderate: "#d97706",
  Low:      "#059669",
};

// ── Country row ───────────────────────────────────────────────────────────────

function CountryRow({ entry }: { entry: GeoCountryEntry }) {
  const [expanded, setExpanded] = useState(
    entry.worst_band === "Critical" || entry.worst_band === "High"
  );
  const color = BAND_COLOR[entry.worst_band] ?? "text-gray-500";
  const bg    = BAND_BG[entry.worst_band]    ?? "bg-gray-50";

  return (
    <div className={`rounded-xl border ${expanded ? "border-gray-300 dark:border-gray-600" : "border-gray-200 dark:border-gray-700"} overflow-hidden`}>
      {/* Header row */}
      <div
        className="flex items-center gap-3 p-3 cursor-pointer select-none hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="text-gray-400 shrink-0">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </span>

        {/* Country + band */}
        <div className="w-36 shrink-0">
          <p className="text-sm font-semibold text-gray-900 dark:text-white">{entry.country}</p>
          <span className={`text-xs font-medium ${color}`}>{entry.worst_band}</span>
        </div>

        {/* Supplier count */}
        <div className="w-14 text-center shrink-0">
          <p className="text-lg font-bold tabular-nums text-gray-700 dark:text-gray-200">
            {entry.supplier_count}
          </p>
          <p className="text-xs text-gray-400">suppliers</p>
        </div>

        {/* Avg risk bar */}
        <div className="flex-1 min-w-0 flex items-center gap-2">
          <div className="flex-1 h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.min(entry.avg_risk_score, 100)}%`,
                backgroundColor: BAND_BAR_COLOR[entry.worst_band] ?? "#6b7280",
              }}
            />
          </div>
          <span className={`text-sm font-bold tabular-nums w-10 text-right shrink-0 ${color}`}>
            {entry.avg_risk_score}
          </span>
        </div>

        {/* Avg ESG */}
        <div className="w-16 text-right shrink-0">
          <p className="text-xs text-gray-400">ESG</p>
          <p className="text-sm font-semibold text-emerald-600">{entry.avg_esg_score}</p>
        </div>

        {/* Trend indicators */}
        <div className="w-20 shrink-0 space-y-0.5 text-right">
          {entry.deteriorating > 0 && (
            <p className="text-xs text-red-500 flex items-center justify-end gap-0.5">
              <TrendingDown className="h-3 w-3" />{entry.deteriorating}
            </p>
          )}
          {entry.improving > 0 && (
            <p className="text-xs text-emerald-600 flex items-center justify-end gap-0.5">
              <TrendingUp className="h-3 w-3" />{entry.improving}
            </p>
          )}
        </div>

        {/* External country risk (enrichment) */}
        {entry.country_risk_score !== null ? (
          <div className="w-20 text-right shrink-0">
            <p className="text-xs text-gray-400">Ext. risk</p>
            <p className="text-xs font-medium text-gray-600 dark:text-gray-300">
              {entry.country_risk_score} · {entry.country_risk_level}
            </p>
            {entry.sanctions_status && entry.sanctions_status !== "none" && (
              <p className="text-xs text-red-500">⚠ sanctions</p>
            )}
          </div>
        ) : (
          <div className="w-20 shrink-0" />
        )}
      </div>

      {/* Expanded supplier list */}
      {expanded && (
        <div className="border-t border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900/60 px-4 py-2">
          {entry.suppliers.map((s) => (
            <div
              key={s.supplier_id}
              className="flex items-center gap-3 py-1.5 border-b border-gray-100 dark:border-gray-800 last:border-0"
            >
              <span
                className={`shrink-0 rounded-full px-1.5 py-0.5 text-xs font-semibold ${BAND_BG[s.risk_band] ?? "bg-gray-100"} ${BAND_COLOR[s.risk_band] ?? "text-gray-500"}`}
              >
                {s.risk_band}
              </span>
              <div className="flex-1 min-w-0">
                <Link
                  href={`/suppliers/${s.supplier_id}`}
                  className="text-sm font-medium text-gray-800 dark:text-white hover:text-indigo-600 flex items-center gap-1"
                >
                  {s.name}
                  <ArrowUpRight className="h-3 w-3 text-gray-300" />
                </Link>
                <p className="text-xs text-gray-400 truncate">
                  {s.industry}{s.supplier_tier ? ` · ${s.supplier_tier}` : ""}
                </p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-xs font-bold tabular-nums text-gray-700 dark:text-gray-300">
                  Risk {s.risk_score}
                </p>
                <p className="text-xs text-gray-400">ESG {s.esg_score}</p>
              </div>
              <div className="w-16 text-right shrink-0">
                {s.trend === "Improving" && (
                  <span className="text-xs text-emerald-600 flex items-center justify-end gap-0.5">
                    <TrendingUp className="h-3 w-3" /> ↑
                  </span>
                )}
                {s.trend === "Deteriorating" && (
                  <span className="text-xs text-red-500 flex items-center justify-end gap-0.5">
                    <TrendingDown className="h-3 w-3" /> ↓
                  </span>
                )}
                {s.trend === "Stable" && (
                  <span className="text-xs text-gray-400 flex items-center justify-end gap-0.5">
                    <Minus className="h-3 w-3" /> –
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Bar chart view ────────────────────────────────────────────────────────────

function RiskBarChart({ countries }: { countries: GeoCountryEntry[] }) {
  const top = countries.slice(0, 15);
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
        Avg Risk Score by Country (top {top.length})
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={top} layout="vertical" margin={{ left: 70, right: 20 }}>
          <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10 }} />
          <YAxis
            type="category"
            dataKey="country"
            tick={{ fontSize: 11 }}
            width={65}
          />
          <Tooltip
            formatter={(v: number) => [`${v}`, "Avg Risk"]}
            contentStyle={{ fontSize: 11 }}
          />
          <Bar dataKey="avg_risk_score" radius={[0, 4, 4, 0]}>
            {top.map((entry) => (
              <Cell
                key={entry.country}
                fill={BAND_BAR_COLOR[entry.worst_band] ?? "#6b7280"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function GeoHeatmapPage() {
  const { t } = useLanguage();
  const { data, isLoading } = useQuery({
    queryKey: ["supplier-geo-heatmap"],
    queryFn: geoHeatmapApi.getHeatmap,
  });

  return (
    <div className="space-y-6">
      <Link href="/suppliers" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        ← Suppliers
      </Link>
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-blue-100 dark:bg-blue-900/30 p-2">
          <Globe className="h-6 w-6 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            {t("geoHeatmap.title")}
          </h1>
          <p className="text-xs text-gray-500">
            {t("geoHeatmap.subtitle")}
          </p>
        </div>
      </div>

      {/* KPI strip */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { id: "countries", label: t("geoHeatmap.countries"), value: data.countries_count, color: "text-blue-600" },
            { id: "mapped", label: t("geoHeatmap.suppliersMapped"), value: data.total_suppliers, color: "text-gray-700" },
            { id: "critical", label: t("geoHeatmap.criticalCountries"), value: data.countries.filter((c) => c.worst_band === "Critical").length, color: "text-red-600" },
            { id: "high", label: t("geoHeatmap.highCountries"), value: data.countries.filter((c) => c.worst_band === "High" || c.worst_band === "Critical").length, color: "text-orange-600" },
          ].map((k) => (
            <div key={k.id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3">
              <p className="text-xs text-gray-400 mb-1">{k.label}</p>
              <p className={`text-2xl font-bold tabular-nums ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Bar chart */}
      {data && data.countries.length > 0 && (
        <RiskBarChart countries={data.countries} />
      )}

      {/* Country list */}
      {isLoading ? (
        <div className="py-12 text-center text-sm text-gray-400">Loading geographic data…</div>
      ) : !data || data.countries.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 py-16 text-center">
          <Globe className="mx-auto h-8 w-8 text-gray-300 mb-3" />
          <p className="text-sm text-gray-400">
            No scored suppliers with country data yet.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {data.countries.map((entry) => (
            <CountryRow key={entry.country} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
