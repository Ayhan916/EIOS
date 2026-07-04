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

const STATUS_COLORS: Record<string, string> = {
  received: "bg-blue-100 text-blue-800 border-blue-300",
  under_review: "bg-amber-100 text-amber-800 border-amber-300",
  investigating: "bg-orange-100 text-orange-800 border-orange-300",
  resolved: "bg-emerald-100 text-emerald-800 border-emerald-300",
  rejected: "bg-slate-100 text-slate-700 border-slate-300",
};

const CATEGORY_LABELS: Record<string, string> = {
  labour_rights: "Labour Rights",
  child_labour: "Child Labour",
  forced_labour: "Forced Labour",
  health_and_safety: "Health & Safety",
  environmental: "Environmental",
  discrimination: "Discrimination",
  corruption: "Corruption",
  human_rights: "Human Rights",
  other: "Other",
};

const ALL_STATUSES = [
  "received",
  "under_review",
  "investigating",
  "resolved",
  "rejected",
];

function GrievanceRow({ report }: { report: GrievanceReportResponse }) {
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
              {CATEGORY_LABELS[report.category] ?? report.category}
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
              Description
            </p>
            <p className="text-sm whitespace-pre-wrap">{report.description}</p>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="font-medium text-muted-foreground">Regulation: </span>
              {report.regulation_refs}
            </div>
            <div>
              <span className="font-medium text-muted-foreground">Anonymous: </span>
              {report.is_anonymous ? "Yes" : "No"}
            </div>
            {report.linked_finding_id && (
              <div>
                <span className="font-medium text-muted-foreground">Linked Finding: </span>
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
                Reviewer Notes
              </p>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {report.reviewer_notes}
              </p>
            </div>
          )}

          {report.resolution_notes && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                Resolution Notes
              </p>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {report.resolution_notes}
              </p>
            </div>
          )}

          {/* Update form */}
          {editing ? (
            <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wide">Update Status</p>
              <div>
                <label className="mb-1 block text-xs font-medium">New Status</label>
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
                <label className="mb-1 block text-xs font-medium">Reviewer Notes</label>
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
                <label className="mb-1 block text-xs font-medium">Resolution Notes</label>
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
                  {mutation.isPending ? "Saving…" : "Save Update"}
                </button>
                <button
                  onClick={() => setEditing(false)}
                  className="rounded border border-border px-4 py-1.5 text-xs text-muted-foreground hover:text-foreground"
                >
                  Cancel
                </button>
              </div>
              {mutation.isError && (
                <p className="text-xs text-red-600">Failed to update. Please try again.</p>
              )}
            </div>
          ) : (
            <button
              onClick={() => setEditing(true)}
              className="text-xs text-blue-600 hover:underline"
            >
              Update status / add notes
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function GrievancesPage() {
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
            Grievance Mechanism
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            LkSG §8 · CSDDD Art. 14 — Confidential complaint channel
          </p>
        </div>
        <a
          href={`/grievance?org_id=`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm hover:bg-muted"
        >
          <ExternalLink className="h-4 w-4" />
          Public Form
        </a>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <div className="rounded-xl border border-border bg-card p-3 text-center">
            <p className="text-2xl font-bold">{summary.total}</p>
            <p className="text-xs text-muted-foreground">Total</p>
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
          <option value="">All statuses</option>
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
          <option value="">All categories</option>
          {Object.entries(CATEGORY_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
      </div>

      {/* List */}
      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading reports…</p>
      )}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          Failed to load grievance reports.
        </div>
      )}
      {reports && reports.length === 0 && !isLoading && (
        <div className="rounded-xl border border-dashed border-border p-12 text-center">
          <ClipboardList className="mx-auto mb-3 h-10 w-10 text-muted-foreground/40" />
          <p className="font-medium">No reports yet</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Reports submitted via the public form will appear here.
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
        <p className="font-semibold">LkSG §8 / CSDDD Art. 14 Requirements</p>
        <ul className="mt-1 list-disc pl-4 space-y-0.5 text-xs">
          <li>Channel must be accessible to workers, trade unions, local communities, and NGOs</li>
          <li>Reporter identity must not be disclosed to the subject of the report</li>
          <li>All reports must be acknowledged and investigated within a reasonable timeframe</li>
          <li>Annual report must include: number of reports received, investigated, resolved</li>
          <li>Retaliation against reporters is prohibited</li>
        </ul>
      </div>
    </div>
  );
}
