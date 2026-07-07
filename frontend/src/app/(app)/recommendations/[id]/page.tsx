"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BookOpen,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
  Loader2,
  TrendingUp,
  UserCheck,
  Zap,
} from "lucide-react";
import { getRecommendation, updateRecommendation } from "@/lib/api/recommendations";
import apiClient from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";
import { CopilotDrawer } from "@/components/copilot-drawer";
import { AskKBButton } from "@/components/layout/knowledge-search";
import { useLanguage } from "@/lib/i18n/context";
import { WorkflowProgressBar } from "@/components/workflow/WorkflowProgressBar";

// ── Helpers ───────────────────────────────────────────────────────────────────

const PRIORITY_COLORS: Record<string, string> = {
  Critical: "bg-red-100 text-red-800 border border-red-300",
  High:     "bg-orange-100 text-orange-800 border border-orange-300",
  Medium:   "bg-amber-100 text-amber-800 border border-amber-300",
  Low:      "bg-slate-100 text-slate-700 border border-slate-200",
};

const STATUS_COLORS: Record<string, string> = {
  open:        "bg-slate-100 text-slate-700",
  in_progress: "bg-blue-100 text-blue-700",
  resolved:    "bg-amber-100 text-amber-700",
  verified:    "bg-emerald-100 text-emerald-700",
};

const COMPLEXITY_COLORS: Record<string, string> = {
  low:    "text-emerald-600",
  medium: "text-amber-600",
  high:   "text-red-600",
};

function PriorityBadge({ priority }: { priority: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${PRIORITY_COLORS[priority] ?? "bg-slate-100 text-slate-600"}`}>
      {priority}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_COLORS[status] ?? "bg-slate-100 text-slate-600"}`}>
      {status.replace("_", " ")}
    </span>
  );
}

// ── Audit Trail ───────────────────────────────────────────────────────────────

interface ActivityEntry {
  id: string;
  action: string;
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  actor_name: string | null;
  created_at: string;
}

function AuditTrailPanel({ entityId }: { entityId: string }) {
  const [open, setOpen] = useState(false);

  const { data: entries, isLoading } = useQuery({
    queryKey: ["audit-trail", "recommendation", entityId],
    queryFn: async () => {
      const r = await apiClient.get(`/recommendations/${entityId}/activity`);
      return r.data as ActivityEntry[];
    },
    enabled: open,
    staleTime: 60_000,
  });

  return (
    <div className="rounded-lg border">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-muted-foreground" />
          Audit Trail
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>
      {open && (
        <div className="border-t px-4 py-3 space-y-2 max-h-64 overflow-y-auto">
          {isLoading && <Spinner />}
          {!isLoading && (!entries || entries.length === 0) && (
            <p className="text-xs text-muted-foreground text-center py-2">No history recorded.</p>
          )}
          {(entries ?? []).map((e) => (
            <div key={e.id} className="flex items-start gap-2 text-xs">
              <div className="mt-0.5 h-1.5 w-1.5 rounded-full bg-slate-300 flex-shrink-0" />
              <div className="min-w-0">
                <span className="font-medium">{e.action}</span>
                {e.field_name && <span className="text-muted-foreground"> · {e.field_name}</span>}
                {e.old_value && e.new_value && (
                  <span className="text-muted-foreground"> {e.old_value} → {e.new_value}</span>
                )}
                <div className="text-muted-foreground/70">
                  {e.actor_name ?? "System"} · {new Date(e.created_at).toLocaleString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function RecommendationDetailPage() {
  const { t } = useLanguage();
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: rec, isLoading } = useQuery({
    queryKey: ["recommendation", id],
    queryFn: () => getRecommendation(id),
    enabled: !!id,
  });

  const { data: linkedFindings } = useQuery({
    queryKey: ["recommendation-findings", id],
    queryFn: async () => {
      const r = await apiClient.get(`/recommendations/${id}/findings`);
      return r.data as Array<{ id: string; title: string; severity: string }>;
    },
    enabled: !!id,
  });

  const patchMutation = useMutation({
    mutationFn: (patch: Parameters<typeof updateRecommendation>[1]) =>
      updateRecommendation(id, patch),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendation", id] });
    },
  });

  if (isLoading || !rec) {
    return <div className="flex justify-center py-24"><Spinner size="lg" /></div>;
  }

  const STATUS_NEXT: Record<string, string | null> = {
    open:        "in_progress",
    in_progress: "resolved",
    resolved:    "verified",
    verified:    null,
  };
  const nextStatus = STATUS_NEXT[rec.action_status];

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Workflow pipeline */}
      <WorkflowProgressBar entityType="recommendation" entityId={id} />

      {/* Back + Header */}
      <div>
        <Link
          href="/recommendations"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> {t("common.back")}
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-foreground leading-tight">{rec.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <PriorityBadge priority={rec.priority} />
              <StatusBadge status={rec.action_status} />
              {rec.implementation_complexity && (
                <span className={`text-xs font-medium capitalize ${COMPLEXITY_COLORS[rec.implementation_complexity] ?? "text-slate-600"}`}>
                  {rec.implementation_complexity} complexity
                </span>
              )}
              {rec.due_date && (
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Calendar className="h-3 w-3" /> Due {formatDate(rec.due_date)}
                </span>
              )}
            </div>
          </div>
          <div className="flex-shrink-0 flex items-center gap-2">
            {nextStatus && (
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5"
                onClick={() => patchMutation.mutate({ action_status: nextStatus as any })}
                disabled={patchMutation.isPending}
              >
                {patchMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                )}
                Mark {nextStatus.replace("_", " ")}
              </Button>
            )}
            <CopilotDrawer
              contextType="recommendation"
              contextId={rec.id}
              contextSummary={`${rec.priority} recommendation: ${rec.title}`}
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description + Reasoning */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-blue-500" />
                {t("common.description")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-foreground leading-relaxed">{rec.description}</p>
              {rec.reasoning && (
                <div className="border-l-2 border-blue-300 pl-4">
                  <p className="text-xs font-semibold text-muted-foreground mb-1">Reasoning</p>
                  <p className="text-sm text-muted-foreground italic">{rec.reasoning}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Business case */}
          {(rec.expected_benefit || rec.expected_risk || rec.expected_roi) && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-emerald-500" />
                  Business Case
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {rec.expected_benefit && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground mb-1">Expected Benefit</p>
                    <p className="text-sm">{rec.expected_benefit}</p>
                  </div>
                )}
                {rec.expected_risk && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground mb-1">Implementation Risk</p>
                    <p className="text-sm">{rec.expected_risk}</p>
                  </div>
                )}
                {rec.expected_roi && (
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground mb-1">Expected ROI</p>
                    <p className="text-sm">{rec.expected_roi}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Linked Findings */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-500" />
                Linked Findings
                {linkedFindings && linkedFindings.length > 0 && (
                  <span className="rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 text-xs font-semibold">
                    {linkedFindings.length}
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!linkedFindings || linkedFindings.length === 0 ? (
                <div className="py-6 text-center">
                  <Zap className="mx-auto h-8 w-8 text-muted-foreground/30 mb-2" />
                  <p className="text-sm text-muted-foreground">No findings linked.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {linkedFindings.map((f) => (
                    <Link
                      key={f.id}
                      href={`/findings/${f.id}`}
                      className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2.5 hover:bg-muted/40 transition-colors"
                    >
                      <p className="text-sm font-medium truncate">{f.title}</p>
                      <span className="text-xs text-muted-foreground shrink-0">{f.severity}</span>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Status controls */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                <UserCheck className="h-4 w-4" /> Action Status
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-1.5 flex-wrap">
                {(["open", "in_progress", "resolved", "verified"] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => patchMutation.mutate({ action_status: s })}
                    disabled={patchMutation.isPending || rec.action_status === s}
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors ${
                      rec.action_status === s
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border text-muted-foreground hover:bg-muted"
                    }`}
                  >
                    {s.replace("_", " ")}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Metadata */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-muted-foreground">{t("common.details")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Priority</span>
                <PriorityBadge priority={rec.priority} />
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("common.status")}</span>
                <StatusBadge status={rec.action_status} />
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Confidence</span>
                <span className="font-medium capitalize">{rec.confidence}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Action Required</span>
                <span className={`font-medium ${rec.action_required ? "text-red-600" : "text-slate-500"}`}>
                  {rec.action_required ? "Yes" : "No"}
                </span>
              </div>
              {rec.due_date && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Due Date</span>
                  <span className="font-medium">{formatDate(rec.due_date)}</span>
                </div>
              )}
              {rec.approved_by && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Approved By</span>
                  <span className="font-medium">{rec.approved_by}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created</span>
                <span className="text-muted-foreground">{formatDate(rec.created_at)}</span>
              </div>
            </CardContent>
          </Card>

          {/* Parent links */}
          {rec.assessment_id && (
            <Card>
              <CardContent className="pt-4 space-y-2">
                <Link
                  href={`/assessments/${rec.assessment_id}`}
                  className="flex items-center gap-1.5 text-xs text-blue-600 hover:underline"
                >
                  <FileText className="h-3.5 w-3.5" />
                  View parent assessment
                </Link>
              </CardContent>
            </Card>
          )}

          <AskKBButton contextQuery={rec.title} />
          <AuditTrailPanel entityId={id} />
        </div>
      </div>
    </div>
  );
}
