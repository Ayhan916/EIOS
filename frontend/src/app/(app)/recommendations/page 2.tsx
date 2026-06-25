"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Download,
  ExternalLink,
  Filter,
  Loader2,
} from "lucide-react";
import Link from "next/link";
import type { ActionStatus } from "@/types/api";
import apiClient from "@/lib/api/client";
import { updateRecommendation } from "@/lib/api/recommendations";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

function authenticatedDownload(url: string, filename: string) {
  const token = typeof window !== "undefined" ? localStorage.getItem("eios_access_token") : null;
  fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    .then((r) => r.blob())
    .then((blob) => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
    });
}

// ── Types ─────────────────────────────────────────────────────────────────────

interface OrgRecommendation {
  id: string;
  title: string;
  action_status: string;
  priority: string;
  due_date: string | null;
  assessment_id: string;
  created_at: string | null;
  supplier_name: string;
  supplier_id: string;
  is_overdue: boolean;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const PRIORITY_STYLES: Record<string, string> = {
  Critical:  "bg-red-100 text-red-800",
  High:      "bg-orange-100 text-orange-800",
  Medium:    "bg-amber-100 text-amber-800",
  Low:       "bg-slate-100 text-slate-700",
};

const STATUS_STYLES: Record<string, string> = {
  open:        "bg-slate-100 text-slate-700",
  in_progress: "bg-blue-100 text-blue-700",
  resolved:    "bg-amber-100 text-amber-700",
  verified:    "bg-emerald-100 text-emerald-700",
};

// ── Quick status update button ────────────────────────────────────────────────

function StatusChanger({
  rec,
  onDone,
}: {
  rec: OrgRecommendation;
  onDone: () => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);

  async function changeStatus(newStatus: ActionStatus) {
    setBusy(newStatus);
    try {
      await updateRecommendation(rec.id, { action_status: newStatus });
      onDone();
    } finally {
      setBusy(null);
    }
  }

  const status = rec.action_status;

  if (status === "verified") {
    return (
      <span className="text-xs text-emerald-600 font-medium flex items-center gap-1">
        <CheckCircle2 className="h-3.5 w-3.5" /> Verified
      </span>
    );
  }

  return (
    <div className="flex items-center gap-1.5">
      {status === "open" && (
        <Button
          size="sm"
          variant="outline"
          className="h-7 gap-1 px-2 text-xs"
          disabled={!!busy}
          onClick={() => changeStatus("in_progress")}
        >
          {busy === "in_progress" ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
          Start
        </Button>
      )}
      {(status === "open" || status === "in_progress") && (
        <Button
          size="sm"
          variant="outline"
          className="h-7 gap-1 px-2 text-xs"
          disabled={!!busy}
          onClick={() => changeStatus("resolved")}
        >
          {busy === "resolved" ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
          Resolve
        </Button>
      )}
      {status === "resolved" && (
        <Button
          size="sm"
          className="h-7 gap-1 px-2 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
          disabled={!!busy}
          onClick={() => changeStatus("verified")}
        >
          {busy === "verified" ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <CheckCircle2 className="h-3 w-3" />
          )}
          Approve
        </Button>
      )}
    </div>
  );
}

// ── Summary cards ─────────────────────────────────────────────────────────────

function StatusSummary({ recs }: { recs: OrgRecommendation[] }) {
  const open = recs.filter((r) => r.action_status === "open").length;
  const inProgress = recs.filter((r) => r.action_status === "in_progress").length;
  const overdue = recs.filter((r) => r.is_overdue).length;
  const resolved = recs.filter((r) => r.action_status === "resolved").length;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {[
        { label: "Open", value: open, cls: "bg-slate-50 border-slate-200" },
        { label: "In Progress", value: inProgress, cls: "bg-blue-50 border-blue-200" },
        { label: "Overdue", value: overdue, cls: overdue > 0 ? "bg-red-50 border-red-200" : "bg-slate-50 border-slate-200" },
        { label: "Awaiting Approval", value: resolved, cls: resolved > 0 ? "bg-amber-50 border-amber-200" : "bg-slate-50 border-slate-200" },
      ].map(({ label, value, cls }) => (
        <Card key={label} className={`border ${cls}`}>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold tabular-nums">{value}</p>
            <p className="text-xs font-medium mt-0.5 text-muted-foreground">{label}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function RecommendationsPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { data: recs, isLoading } = useQuery<OrgRecommendation[]>({
    queryKey: ["org-recommendations", statusFilter],
    queryFn: async () => {
      const params = statusFilter !== "all" ? `?action_status=${statusFilter}` : "";
      const res = await apiClient.get(`/api/v1/executive/recommendations${params}`);
      return res.data;
    },
    staleTime: 20_000,
  });

  const allRecs = recs ?? [];
  const overdueCount = allRecs.filter((r) => r.is_overdue).length;

  function invalidate() {
    qc.invalidateQueries({ queryKey: ["org-recommendations"] });
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Recommendations</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            All remediation recommendations across your supplier portfolio
          </p>
        </div>
        <div className="flex items-center gap-2">
          {overdueCount > 0 && (
            <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">
              <AlertTriangle className="h-3 w-3" />
              {overdueCount} overdue
            </span>
          )}
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            className="h-8 rounded-md border border-input bg-background px-3 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Awaiting Approval</option>
            <option value="verified">Verified</option>
          </select>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => {
              const params = statusFilter !== "all" ? `?action_status=${statusFilter}` : "";
              authenticatedDownload(
                `/api/v1/executive/recommendations/export${params}`,
                `recommendations-${new Date().toISOString().split("T")[0]}.csv`
              );
            }}
          >
            <Download className="h-3.5 w-3.5" />
            CSV
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : (
        <>
          {statusFilter === "all" && <StatusSummary recs={allRecs} />}

          {allRecs.length === 0 ? (
            <div className="rounded-lg border border-dashed p-10 text-center">
              <CheckCircle2 className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">
                {statusFilter !== "all"
                  ? `No recommendations with status "${statusFilter}".`
                  : "No recommendations yet. Recommendations are generated from ESG assessments."}
              </p>
            </div>
          ) : (
            <Card>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/30 text-xs text-muted-foreground">
                      <th className="px-4 py-3 text-left">Recommendation</th>
                      <th className="px-4 py-3 text-left hidden sm:table-cell">Priority</th>
                      <th className="px-4 py-3 text-left">Supplier</th>
                      <th className="px-4 py-3 text-left hidden md:table-cell">Due</th>
                      <th className="px-4 py-3 text-left">Status</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {allRecs.map((r) => (
                      <tr
                        key={r.id}
                        className={`hover:bg-muted/20 transition-colors ${r.is_overdue ? "bg-red-50/30" : ""}`}
                      >
                        <td className="px-4 py-3">
                          <p className="font-medium line-clamp-1 max-w-xs">{r.title}</p>
                          {r.is_overdue && (
                            <span className="inline-flex items-center gap-0.5 text-[10px] text-red-600 font-medium">
                              <Clock className="h-3 w-3" /> Overdue
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 hidden sm:table-cell">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_STYLES[r.priority] ?? "bg-slate-100 text-slate-700"}`}>
                            {r.priority || "—"}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <Link
                            href={`/suppliers/${r.supplier_id}`}
                            className="text-xs text-blue-600 hover:underline"
                          >
                            {r.supplier_name}
                          </Link>
                        </td>
                        <td className="px-4 py-3 hidden md:table-cell text-xs text-muted-foreground">
                          {r.due_date
                            ? new Date(r.due_date).toLocaleDateString()
                            : "—"}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[r.action_status] ?? "bg-slate-100 text-slate-600"}`}>
                            {r.action_status.replace("_", " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-2">
                            <StatusChanger rec={r} onDone={invalidate} />
                            <Link
                              href={`/assessments/${r.assessment_id}`}
                              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-blue-600"
                            >
                              <ExternalLink className="h-3 w-3" />
                            </Link>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
