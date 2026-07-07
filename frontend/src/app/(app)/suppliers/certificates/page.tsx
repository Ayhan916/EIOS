"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import {
  AlertTriangle,
  ArrowUpRight,
  Award,
  CheckCircle2,
  Clock,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import {
  certLifecycleApi,
  CertificateAlertEntry,
  CertTypeCount,
} from "@/lib/api/certificate-lifecycle";

// ── Lifecycle config ──────────────────────────────────────────────────────────

const LIFECYCLE_CONFIG = {
  EXPIRED: {
    label: "Expired",
    color: "text-red-700",
    bg: "bg-red-100 dark:bg-red-950/30",
    border: "border-red-300 dark:border-red-800",
    icon: XCircle,
  },
  EXPIRING_SOON: {
    label: "Expiring ≤30d",
    color: "text-orange-700",
    bg: "bg-orange-100 dark:bg-orange-950/30",
    border: "border-orange-300 dark:border-orange-800",
    icon: AlertTriangle,
  },
  EXPIRING_60D: {
    label: "Expiring ≤60d",
    color: "text-amber-700",
    bg: "bg-amber-100 dark:bg-amber-950/30",
    border: "border-amber-200 dark:border-amber-800",
    icon: Clock,
  },
  EXPIRING_90D: {
    label: "Expiring ≤90d",
    color: "text-yellow-700",
    bg: "bg-yellow-50 dark:bg-yellow-950/20",
    border: "border-yellow-200 dark:border-yellow-700",
    icon: Clock,
  },
  ACTIVE: {
    label: "Active",
    color: "text-emerald-700",
    bg: "bg-emerald-50 dark:bg-emerald-950/20",
    border: "border-emerald-200 dark:border-emerald-700",
    icon: CheckCircle2,
  },
} as const;

type LifecycleStatus = keyof typeof LIFECYCLE_CONFIG;


// ── Countdown badge ───────────────────────────────────────────────────────────

function CountdownBadge({ days, status }: { days: number | null; status: LifecycleStatus }) {
  const cfg = LIFECYCLE_CONFIG[status];
  if (days === null) return null;
  if (days < 0)
    return (
      <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${cfg.bg} ${cfg.color}`}>
        {Math.abs(days)}d overdue
      </span>
    );
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${cfg.bg} ${cfg.color}`}>
      {days}d left
    </span>
  );
}

// ── Alert row ─────────────────────────────────────────────────────────────────

function AlertRow({ entry }: { entry: CertificateAlertEntry }) {
  const cfg = LIFECYCLE_CONFIG[entry.lifecycle_status as LifecycleStatus] ?? LIFECYCLE_CONFIG.ACTIVE;
  const Icon = cfg.icon;

  return (
    <div className={`flex items-start gap-3 rounded-xl border ${cfg.border} ${cfg.bg} p-3`}>
      <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${cfg.color}`} />

      <div className="flex-1 min-w-0">
        <div className="flex items-start gap-2 flex-wrap">
          <span className="text-sm font-semibold text-gray-900 dark:text-white">
            {entry.cert_type.replace(/_/g, " ")}
            {entry.custom_cert_name && ` — ${entry.custom_cert_name}`}
          </span>
          {entry.is_verified && (
            <span className="rounded-full bg-emerald-100 text-emerald-700 text-xs px-1.5 py-0.5 flex items-center gap-0.5">
              <ShieldCheck className="h-3 w-3" /> Verified
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-0.5 flex-wrap text-xs text-gray-500">
          <Link
            href={`/suppliers/${entry.supplier_id}`}
            className="text-indigo-500 hover:text-indigo-700 flex items-center gap-0.5"
          >
            {entry.supplier_name} <ArrowUpRight className="h-3 w-3" />
          </Link>
          {entry.issuing_body && <span>· {entry.issuing_body}</span>}
          {entry.valid_until && (
            <span>
              · Expires:{" "}
              {new Date(entry.valid_until).toLocaleDateString("en-GB", {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            </span>
          )}
        </div>
      </div>

      <div className="shrink-0">
        <CountdownBadge days={entry.days_until_expiry} status={entry.lifecycle_status as LifecycleStatus} />
      </div>
    </div>
  );
}

// ── Cert type breakdown ───────────────────────────────────────────────────────

function CertTypeTable({ items }: { items: CertTypeCount[] }) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden">
      <div className="px-4 py-2 border-b border-gray-100 dark:border-gray-800">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">By Certificate Type</p>
      </div>
      <div className="divide-y divide-gray-100 dark:divide-gray-800">
        {items.slice(0, 12).map((c) => (
          <div key={c.cert_type} className="flex items-center gap-3 px-4 py-2">
            <span className="flex-1 text-sm text-gray-700 dark:text-gray-300 font-mono text-xs">
              {c.cert_type.replace(/_/g, " ")}
            </span>
            <span className="text-sm tabular-nums text-gray-500">{c.total} total</span>
            {c.expired > 0 && (
              <span className="text-xs text-red-600 font-medium">{c.expired} expired</span>
            )}
            {c.expiring_soon > 0 && (
              <span className="text-xs text-orange-500 font-medium">{c.expiring_soon} ≤30d</span>
            )}
          </div>
        ))}
        {items.length === 0 && (
          <p className="px-4 py-3 text-sm text-gray-400">No certificates recorded.</p>
        )}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CertificatesPage() {
  const { t } = useLanguage();
  const FILTER_TABS: { key: LifecycleStatus | "ALL"; label: string }[] = [
    { key: "ALL",           label: t("certLifecycle.allAlerts") },
    { key: "EXPIRED",       label: t("certLifecycle.expired") },
    { key: "EXPIRING_SOON", label: t("certLifecycle.expiringSoon") },
    { key: "EXPIRING_60D",  label: t("certLifecycle.expiring60d") },
    { key: "EXPIRING_90D",  label: t("certLifecycle.expiring90d") },
  ];
  const [activeFilter, setActiveFilter] = useState<LifecycleStatus | "ALL">("ALL");
  const [daysWindow, setDaysWindow] = useState(90);

  const { data, isLoading } = useQuery({
    queryKey: ["cert-lifecycle", daysWindow],
    queryFn: () => certLifecycleApi.getLifecycle(daysWindow),
  });

  const filteredAlerts =
    !data
      ? []
      : activeFilter === "ALL"
      ? data.alerts
      : data.alerts.filter((a) => a.lifecycle_status === activeFilter);

  return (
    <div className="space-y-6">
      <Link href="/suppliers" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        ← Suppliers
      </Link>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-violet-100 dark:bg-violet-900/30 p-2">
            <Award className="h-6 w-6 text-violet-600 dark:text-violet-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              {t("certLifecycle.title")}
            </h1>
            <p className="text-xs text-gray-500">
              {t("certLifecycle.subtitle")}
            </p>
          </div>
        </div>

        {/* Window selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">Alert window:</span>
          {[30, 60, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDaysWindow(d)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                daysWindow === d
                  ? "bg-violet-600 text-white"
                  : "bg-gray-100 text-gray-500 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700"
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* KPI cards */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          {[
            { id: "total",    label: t("certLifecycle.total"),        value: data.total,          color: "text-gray-700" },
            { id: "active",   label: t("certLifecycle.active"),       value: data.active,         color: "text-emerald-600" },
            { id: "verified", label: t("certLifecycle.verified"),     value: data.verified,       color: "text-blue-600" },
            { id: "exp30",    label: t("certLifecycle.expiringSoon"), value: data.expiring_soon,  color: data.expiring_soon  > 0 ? "text-orange-600" : "text-gray-400" },
            { id: "exp60",    label: t("certLifecycle.expiring60d"),  value: data.expiring_60d,   color: data.expiring_60d   > 0 ? "text-amber-600"  : "text-gray-400" },
            { id: "expired",  label: t("certLifecycle.expired"),      value: data.expired,        color: data.expired        > 0 ? "text-red-600"    : "text-gray-400" },
          ].map((k) => (
            <div key={k.id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3">
              <p className="text-xs text-gray-400 mb-1">{k.label}</p>
              <p className={`text-2xl font-bold tabular-nums ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Alert list */}
        <div className="lg:col-span-2 space-y-3">
          {/* Filter tabs */}
          <div className="flex flex-wrap gap-1">
            {FILTER_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveFilter(tab.key)}
                className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
                  activeFilter === tab.key
                    ? "bg-violet-600 text-white"
                    : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
                }`}
              >
                {tab.label}
                {tab.key !== "ALL" && data && (
                  <span className="ml-1.5 opacity-70">
                    ({tab.key === "EXPIRED"
                      ? data.expired
                      : tab.key === "EXPIRING_SOON"
                      ? data.expiring_soon
                      : tab.key === "EXPIRING_60D"
                      ? data.expiring_60d
                      : data.expiring_90d})
                  </span>
                )}
              </button>
            ))}
          </div>

          {isLoading ? (
            <div className="py-10 text-center text-sm text-gray-400">Loading…</div>
          ) : filteredAlerts.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 py-12 text-center">
              <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-400 mb-3" />
              <p className="text-sm text-gray-400">No alerts for this filter.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredAlerts.map((a) => (
                <AlertRow key={a.cert_id} entry={a} />
              ))}
            </div>
          )}
        </div>

        {/* Type breakdown sidebar */}
        <div>
          {data && <CertTypeTable items={data.by_cert_type} />}
        </div>
      </div>
    </div>
  );
}
