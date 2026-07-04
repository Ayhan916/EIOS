"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  ExternalLink,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { capApi, CAP } from "@/lib/api/corrective-action-plans";

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_COLOR: Record<string, string> = {
  DRAFT:              "bg-gray-100 text-gray-700",
  COMMITTED:          "bg-blue-100 text-blue-700",
  IN_PROGRESS:        "bg-amber-100 text-amber-700",
  EVIDENCE_SUBMITTED: "bg-violet-100 text-violet-700",
  VERIFIED:           "bg-emerald-100 text-emerald-700",
  CLOSED:             "bg-slate-100 text-slate-500",
};

const STATUS_TABS = [
  { key: undefined,            label: "All" },
  { key: "DRAFT",              label: "Draft" },
  { key: "COMMITTED",          label: "Committed" },
  { key: "IN_PROGRESS",        label: "In Progress" },
  { key: "EVIDENCE_SUBMITTED", label: "Evidence Submitted" },
  { key: "VERIFIED",           label: "Verified" },
  { key: "CLOSED",             label: "Closed" },
] as const;

// ── KPI cards ─────────────────────────────────────────────────────────────────

function KPICards() {
  const { data: kpis } = useQuery({
    queryKey: ["cap-kpis"],
    queryFn: capApi.getKPIs,
  });
  if (!kpis) return null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {[
        { label: "Total CAPs",       value: kpis.total,                      icon: ClipboardCheck, color: "text-gray-700" },
        { label: "Open",             value: kpis.open,                       icon: Clock,          color: "text-amber-600" },
        { label: "Overdue",          value: kpis.overdue,                    icon: AlertTriangle,  color: kpis.overdue > 0 ? "text-red-600" : "text-gray-400" },
        { label: "Verified",         value: kpis.verified,                   icon: CheckCircle2,   color: "text-emerald-600" },
        {
          label: "Completion Rate",
          value: `${(kpis.completion_rate * 100).toFixed(0)}%`,
          icon: ShieldCheck,
          color: kpis.completion_rate >= 0.8 ? "text-emerald-600" : kpis.completion_rate >= 0.5 ? "text-amber-500" : "text-red-500",
        },
      ].map((k) => (
        <div key={k.label} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <k.icon className={`h-3.5 w-3.5 ${k.color}`} />
            <span className="text-xs text-gray-400">{k.label}</span>
          </div>
          <p className={`text-2xl font-bold tabular-nums ${k.color}`}>{k.value}</p>
        </div>
      ))}
    </div>
  );
}

// ── CAP row ───────────────────────────────────────────────────────────────────

function CAPRow({ cap }: { cap: CAP }) {
  return (
    <div className="flex items-start gap-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
      {/* Status */}
      <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_COLOR[cap.cap_status] ?? "bg-gray-100 text-gray-500"}`}>
        {cap.cap_status.replace("_", " ")}
      </span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">{cap.title}</p>
        <p className="text-xs text-gray-500 mt-0.5 truncate">{cap.description}</p>
        <div className="flex items-center gap-3 mt-1.5 flex-wrap">
          {cap.responsible_party && (
            <span className="text-xs text-gray-400">👤 {cap.responsible_party}</span>
          )}
          {cap.deadline && (
            <span className={`text-xs font-medium ${cap.is_overdue ? "text-red-600" : "text-gray-500"}`}>
              {cap.is_overdue && <AlertTriangle className="inline h-3 w-3 mr-0.5" />}
              Due: {new Date(cap.deadline).toLocaleDateString("en-GB")}
              {cap.is_overdue && ` (+${cap.overdue_days}d overdue)`}
            </span>
          )}
        </div>
      </div>

      {/* Link to finding */}
      <Link
        href={`/findings/${cap.finding_id}`}
        className="shrink-0 flex items-center gap-1 text-xs text-indigo-500 hover:text-indigo-700"
      >
        Finding <ExternalLink className="h-3 w-3" />
      </Link>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CorrectiveActionPlansPage() {
  const [activeStatus, setActiveStatus] = useState<string | undefined>(undefined);

  const { data: caps = [], isLoading } = useQuery({
    queryKey: ["caps-portfolio", activeStatus],
    queryFn: () => capApi.listForOrg(activeStatus),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-emerald-100 dark:bg-emerald-900/30 p-2">
          <ClipboardCheck className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Corrective Action Plans</h1>
          <p className="text-xs text-gray-500">
            Track remediation commitments from finding to evidence verification
          </p>
        </div>
        <Link
          href="/reports"
          className="flex items-center gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 transition-colors"
        >
          <ExternalLink className="h-3.5 w-3.5" /> Berichte generieren →
        </Link>
      </div>

      <KPICards />

      {/* Status tabs */}
      <div className="flex flex-wrap gap-1 border-b border-gray-200 dark:border-gray-700 pb-2">
        {STATUS_TABS.map((tab) => (
          <button
            key={String(tab.key ?? "all")}
            onClick={() => setActiveStatus(tab.key)}
            className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
              activeStatus === tab.key
                ? "bg-emerald-600 text-white"
                : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* List */}
      {isLoading ? (
        <div className="py-10 text-center text-sm text-gray-400">Loading…</div>
      ) : caps.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 py-16 text-center">
          <ShieldCheck className="mx-auto h-8 w-8 text-gray-300 mb-3" />
          <p className="text-sm text-gray-400">
            {activeStatus
              ? `No ${activeStatus.toLowerCase().replace("_", " ")} CAPs.`
              : "No CAPs yet. Create one from a Finding detail page."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {caps.map((cap) => (
            <CAPRow key={cap.id} cap={cap} />
          ))}
        </div>
      )}
    </div>
  );
}
