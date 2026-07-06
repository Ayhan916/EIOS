"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ClipboardList,
  ExternalLink,
  Shield,
} from "lucide-react";
import {
  listGrievances,
  getGrievanceSummary,
  updateGrievanceStatus,
  type GrievanceReportResponse,
  type GrievanceStatusUpdate,
} from "@/lib/api/grievance";
import { useLanguage } from "@/lib/i18n/context";

const STATUS_COLORS: Record<string, string> = {
  received: "bg-blue-100 text-blue-800 border-blue-300",
  under_review: "bg-amber-100 text-amber-800 border-amber-300",
  investigating: "bg-orange-100 text-orange-800 border-orange-300",
  resolved: "bg-emerald-100 text-emerald-800 border-emerald-300",
  rejected: "bg-slate-100 text-slate-700 border-slate-300",
};

const CATEGORY_LABEL_KEYS: Record<string, string> = {
  labour_rights:  "grievance.catLabourRights",
  child_labour:   "grievance.catChildLabour",
  forced_labour:  "grievance.catForcedLabour",
  health_and_safety: "grievance.catHealthSafety",
  environmental:  "grievance.catEnvironmental",
  discrimination: "grievance.catDiscrimination",
  corruption:     "grievance.catCorruption",
  human_rights:   "grievance.catHumanRights",
  other:          "grievance.catOther",
};

const ALL_STATUSES = [
  "received",
  "under_review",
  "investigating",
  "resolved",
  "rejected",
];

function GrievanceRow({ report }: { report: GrievanceReportResponse }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [statusForm, setStatusForm] = useState<GrievanceStatusUpdate>({
    grievance_status: report.grievance_status,
    reviewer_notes: report.reviewer_notes ?? "",
    resolution_notes: report.resolution_notes ?? "",
  });

  const mutation = useMutation({
    mutationFn: (body: GrievanceStatusUpdate) =>
      updateGrievanceStatus(report.id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["grievances"] });
      qc.invalidateQueries({ queryKey: ["grievance-summary"] });
      setEditing(false);
    },
  });

  return (
    <div className="rounded-xl border border-border bg-card">
      {/* Row header */}
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-semibold ${STATUS_COLORS[report.grievance_status] ?? "bg-slate-100 text-slate-700 border-slate-300"}`}
            >
              {report.grievance_status.replace(/_/g, " ").toUpperCase()}
            </span>
            <span className="text-xs text-muted-foreground">
              {CATEGORY_LABEL_KEYS[report.category] ? t(CATEGORY_LABEL_KEYS[report.category] as Parameters<typeof t>[0]) : report.category}
            </span>
            <span className="text-xs text-muted-foreground font-mono">
              {report.anonymized_reference_code}
            </span>
            <span className="ml-auto text-xs text-muted-foreground">
              {new Date(report.created_at).toLocaleDateString()}
            </span>
          </div>
          <p className="mt-0.5 text-sm font-medium truncate">{report.title}</p>
        </div>
        <button
          onClick={() => setExpanded((v) => !v)}
          className="ml-2 shrink-0 text-muted-foreground hover:text-foreground"
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-border px-4 pb-4 pt-3 space-y-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
              {t("grievance.description")}
            </p>
            <p className="text-sm whitespace-pre-wrap">{report.description}</p>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="font-medium text-muted-foreground">{t("grievance.regulation")}: </span>
              {report.regulation_refs}
            </div>
            <div>
              <span className="font-medium text-muted-foreground">{t("grievance.anonymous")}: </span>
              {report.is_anonymous ? t("grievance.yes") : t("grievance.no")}
            </div>
            {report.linked_finding_id && (
              <div>
                <span className="font-medium text-muted-foreground">{t("grievance.linkedFinding")}: </span>
                <Link
                  href={`/findings/${report.linked_finding_id}`}
                  className="font-mono text-blue-600 hover:underline"
                >
                  {report.linked_finding_id.slice(0, 8)}…
                </Link>
              </div>
            )}
          </div>

          {report.reviewer_notes && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                {t("grievance.reviewerNotes")}
              </p>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {report.reviewer_notes}
              </p>
            </div>
          )}

          {report.resolution_notes && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                {t("grievance.resolutionNotes")}
              </p>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {report.resolution_notes}
              </p>
            </div>
          )}

          {/* Update form */}
          {editing ? (
            <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wide">{t("grievance.updateStatus")}</p>
              <div>
                <label className="mb-1 block text-xs font-medium">{t("grievance.newStatus")}</label>
                <select
                  className="w-full rounded border border-border bg-background px-2 py-1.5 text-sm"
                  value={statusForm.grievance_status}
                  onChange={(e) =>
                    setStatusForm((f) => ({ ...f, grievance_status: e.target.value }))
                  }
                >
                  {ALL_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s.replace(/_/g, " ").toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium">{t("grievance.reviewerNotes")}</label>
                <textarea
                  rows={3}
                  className="w-full rounded border border-border bg-background px-2 py-1.5 text-sm"
                  value={statusForm.reviewer_notes ?? ""}
                  onChange={(e) =>
                    setStatusForm((f) => ({ ...f, reviewer_notes: e.target.value }))
                  }
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium">{t("grievance.resolutionNotes")}</label>
                <textarea
                  rows={2}
                  className="w-full rounded border border-border bg-background px-2 py-1.5 text-sm"
                  value={statusForm.resolution_notes ?? ""}
                  onChange={(e) =>
                    setStatusForm((f) => ({ ...f, resolution_notes: e.target.value }))
                  }
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => mutation.mutate(statusForm)}
                  disabled={mutation.isPending}
                  className="rounded bg-blue-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {mutation.isPending ? t("grievance.saving") : t("grievance.saveUpdate")}
                </button>
                <button
                  onClick={() => setEditing(false)}
                  className="rounded border border-border px-4 py-1.5 text-xs text-muted-foreground hover:text-foreground"
                >
                  {t("common.cancel")}
                </button>
              </div>
              {mutation.isError && (
                <p className="text-xs text-red-600">{t("grievance.updateError")}</p>
              )}
            </div>
          ) : (
            <button
              onClick={() => setEditing(true)}
              className="text-xs text-blue-600 hover:underline"
            >
              {t("grievance.updateLink")}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function GrievancesPage() {
  const { t } = useLanguage();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");

  const { data: summary } = useQuery({
    queryKey: ["grievance-summary"],
    queryFn: getGrievanceSummary,
  });

  const { data: reports, isLoading, error } = useQuery({
    queryKey: ["grievances", statusFilter, categoryFilter],
    queryFn: () =>
      listGrievances({
        status_filter: statusFilter || undefined,
        category_filter: categoryFilter || undefined,
        limit: 100,
      }),
  });

  const backendUrl =
    (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
      .replace(/\/api\/v1$/, "");

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Shield className="h-5 w-5 text-rose-500" />
            {t("grievance.title")}
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {t("grievance.subtitle")}
          </p>
        </div>
        <a
          href={`/grievance?org_id=`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-muted"
        >
          <ExternalLink className="h-4 w-4" />
          {t("grievance.publicForm")}
        </a>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <div className="rounded-xl border border-border bg-card p-3 text-center">
            <p className="text-2xl font-bold">{summary.total}</p>
            <p className="text-xs text-muted-foreground">{t("grievance.total")}</p>
          </div>
          {["received", "under_review", "investigating", "resolved", "rejected"].map((s) => (
            <div key={s} className="rounded-xl border border-border bg-card p-3 text-center">
              <p className="text-2xl font-bold">{summary.by_status[s] ?? 0}</p>
              <p className="text-xs text-muted-foreground">{s.replace(/_/g, " ")}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          className="rounded-lg border border-border bg-background px-3 py-1.5 text-sm"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">{t("grievance.allStatuses")}</option>
          {ALL_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ").toUpperCase()}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-border bg-background px-3 py-1.5 text-sm"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        >
          <option value="">{t("grievance.allCategories")}</option>
          {Object.entries(CATEGORY_LABEL_KEYS).map(([v, key]) => (
            <option key={v} value={v}>{t(key as Parameters<typeof t>[0])}</option>
          ))}
        </select>
      </div>

      {/* List */}
      {isLoading && (
        <p className="text-sm text-muted-foreground">{t("grievance.loadingReports")}</p>
      )}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {t("grievance.loadError")}
        </div>
      )}
      {reports && reports.length === 0 && !isLoading && (
        <div className="rounded-xl border border-dashed border-border p-12 text-center">
          <ClipboardList className="mx-auto mb-3 h-10 w-10 text-muted-foreground/40" />
          <p className="font-medium">{t("grievance.noReports")}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("grievance.noReportsDesc")}
          </p>
        </div>
      )}
      {reports && reports.length > 0 && (
        <div className="space-y-3">
          {reports.map((r) => (
            <GrievanceRow key={r.id} report={r} />
          ))}
        </div>
      )}

      {/* LkSG compliance note */}
      <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800">
        <p className="font-semibold">{t("grievance.lksgNote")}</p>
        <ul className="mt-1 list-disc pl-4 space-y-0.5 text-xs">
          <li>{t("grievance.lksgItem1")}</li>
          <li>{t("grievance.lksgItem2")}</li>
          <li>{t("grievance.lksgItem3")}</li>
          <li>{t("grievance.lksgItem4")}</li>
          <li>{t("grievance.lksgItem5")}</li>
        </ul>
      </div>

      {/* Cross-reference to assessment pipeline */}
      <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
        <div className="text-sm">
          <p className="font-medium text-slate-700">{t("grievance.linkFindingTitle")}</p>
          <p className="text-xs text-slate-500 mt-0.5">
            {t("grievance.linkFindingDesc")}
          </p>
        </div>
        <Link
          href="/findings"
          className="shrink-0 flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
        >
          {t("grievance.searchFindings")}
        </Link>
      </div>
    </div>
  );
}
