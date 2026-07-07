"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
  Loader2,
  ShieldCheck,
  Upload,
  User,
  XCircle,
} from "lucide-react";
import { capApi } from "@/lib/api/corrective-action-plans";
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

const STATUS_COLORS: Record<string, string> = {
  DRAFT:              "bg-gray-100 text-gray-700",
  COMMITTED:          "bg-blue-100 text-blue-700",
  IN_PROGRESS:        "bg-amber-100 text-amber-700",
  EVIDENCE_SUBMITTED: "bg-violet-100 text-violet-700",
  VERIFIED:           "bg-emerald-100 text-emerald-700",
  CLOSED:             "bg-slate-100 text-slate-500",
};

const STATUS_LABELS: Record<string, string> = {
  DRAFT:              "Draft",
  COMMITTED:          "Committed",
  IN_PROGRESS:        "In Progress",
  EVIDENCE_SUBMITTED: "Evidence Submitted",
  VERIFIED:           "Verified",
  CLOSED:             "Closed",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_COLORS[status] ?? "bg-slate-100 text-slate-600"}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

// ── Evidence Submit Modal ─────────────────────────────────────────────────────

function EvidenceSubmitPanel({ capId, onSuccess }: { capId: string; onSuccess: () => void }) {
  const [note, setNote] = useState("");
  const [fileUrl, setFileUrl] = useState("");

  const mutation = useMutation({
    mutationFn: () => capApi.submitEvidence(capId, { evidence_note: note, evidence_file_url: fileUrl || null }),
    onSuccess,
  });

  return (
    <div className="space-y-3 pt-2">
      <textarea
        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-ring"
        rows={3}
        placeholder="Describe the evidence submitted…"
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <input
        className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        placeholder="Evidence file URL (optional)"
        value={fileUrl}
        onChange={(e) => setFileUrl(e.target.value)}
      />
      <Button
        size="sm"
        className="gap-1.5 w-full"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending || note.trim().length < 5}
      >
        {mutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
        Submit Evidence
      </Button>
    </div>
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
    queryKey: ["audit-trail", "cap", entityId],
    queryFn: async () => {
      const r = await apiClient.get(`/corrective-action-plans/${entityId}/activity`);
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

export default function CAPDetailPage() {
  const { t } = useLanguage();
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [showEvidencePanel, setShowEvidencePanel] = useState(false);

  const { data: cap, isLoading } = useQuery({
    queryKey: ["cap", id],
    queryFn: () => capApi.getById(id),
    enabled: !!id,
  });

  const { data: finding } = useQuery({
    queryKey: ["finding", cap?.finding_id],
    queryFn: async () => {
      const r = await apiClient.get(`/findings/${cap!.finding_id}`);
      return r.data as { id: string; title: string; severity: string; assessment_id: string };
    },
    enabled: !!cap?.finding_id,
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["cap", id] });

  const commitMutation   = useMutation({ mutationFn: () => capApi.commit(id),   onSuccess: refresh });
  const startMutation    = useMutation({ mutationFn: () => capApi.start(id),    onSuccess: refresh });

  if (isLoading || !cap) {
    return <div className="flex justify-center py-24"><Spinner size="lg" /></div>;
  }

  const isOverdue = cap.is_overdue && cap.cap_status !== "CLOSED" && cap.cap_status !== "VERIFIED";

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Workflow pipeline */}
      <WorkflowProgressBar entityType="cap" entityId={id} />

      {/* Back + Header */}
      <div>
        <Link
          href="/corrective-action-plans"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> {t("common.back")}
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-foreground leading-tight">{cap.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <StatusBadge status={cap.cap_status} />
              {isOverdue && (
                <span className="inline-flex items-center gap-1 rounded-full bg-red-100 text-red-700 px-2.5 py-0.5 text-xs font-semibold">
                  <AlertTriangle className="h-3 w-3" /> Overdue {cap.overdue_days}d
                </span>
              )}
              {cap.deadline && (
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Calendar className="h-3 w-3" /> Deadline {formatDate(cap.deadline)}
                </span>
              )}
              {cap.responsible_party && (
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <User className="h-3 w-3" /> {cap.responsible_party}
                </span>
              )}
            </div>
          </div>
          <div className="flex-shrink-0 flex items-center gap-2">
            {cap.cap_status === "DRAFT" && (
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5"
                onClick={() => commitMutation.mutate()}
                disabled={commitMutation.isPending}
              >
                {commitMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                Commit
              </Button>
            )}
            {cap.cap_status === "COMMITTED" && (
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5"
                onClick={() => startMutation.mutate()}
                disabled={startMutation.isPending}
              >
                {startMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                Start
              </Button>
            )}
            {cap.cap_status === "IN_PROGRESS" && (
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 border-violet-300 text-violet-700 hover:bg-violet-50"
                onClick={() => setShowEvidencePanel((v) => !v)}
              >
                <Upload className="h-3.5 w-3.5" /> Submit Evidence
              </Button>
            )}
            <CopilotDrawer
              contextType="cap"
              contextId={cap.id}
              contextSummary={`CAP: ${cap.title} (${cap.cap_status})`}
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-blue-500" />
                {t("common.description")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-foreground leading-relaxed">{cap.description}</p>
            </CardContent>
          </Card>

          {/* Evidence Submit Panel (inline, collapsible) */}
          {showEvidencePanel && (
            <Card className="border-violet-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Upload className="h-4 w-4 text-violet-500" />
                  Submit Evidence
                </CardTitle>
              </CardHeader>
              <CardContent>
                <EvidenceSubmitPanel
                  capId={id}
                  onSuccess={() => { refresh(); setShowEvidencePanel(false); }}
                />
              </CardContent>
            </Card>
          )}

          {/* Evidence record (if submitted) */}
          {cap.evidence_note && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <FileText className="h-4 w-4 text-emerald-500" />
                  Evidence
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm">{cap.evidence_note}</p>
                {cap.evidence_file_url && (
                  <a
                    href={cap.evidence_file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                  >
                    <FileText className="h-3 w-3" /> View attached file
                  </a>
                )}
                {cap.evidence_submitted_at && (
                  <p className="text-xs text-muted-foreground">Submitted {formatDate(cap.evidence_submitted_at)}</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Verification record */}
          {cap.verification_note && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-500" />
                  Verification
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm">{cap.verification_note}</p>
                {cap.verified_at && (
                  <p className="text-xs text-muted-foreground">Verified {formatDate(cap.verified_at)}</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Insufficient reason */}
          {cap.insufficient_reason && (
            <Card className="border-red-200">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2 text-red-600">
                  <XCircle className="h-4 w-4" />
                  Evidence Insufficient
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{cap.insufficient_reason}</p>
              </CardContent>
            </Card>
          )}

          {/* Linked Finding */}
          {finding && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  Source Finding
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Link
                  href={`/findings/${finding.id}`}
                  className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2.5 hover:bg-muted/40 transition-colors"
                >
                  <p className="text-sm font-medium truncate">{finding.title}</p>
                  <span className="text-xs text-muted-foreground shrink-0">{finding.severity}</span>
                </Link>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Lifecycle status */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                <ShieldCheck className="h-4 w-4" /> Lifecycle
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                {(["DRAFT", "COMMITTED", "IN_PROGRESS", "EVIDENCE_SUBMITTED", "VERIFIED", "CLOSED"] as const).map((s) => {
                  const statuses = ["DRAFT", "COMMITTED", "IN_PROGRESS", "EVIDENCE_SUBMITTED", "VERIFIED", "CLOSED"];
                  const currentIdx = statuses.indexOf(cap.cap_status);
                  const sIdx = statuses.indexOf(s);
                  const isDone = sIdx < currentIdx;
                  const isCurrent = s === cap.cap_status;
                  return (
                    <div key={s} className={`flex items-center gap-2 rounded px-2 py-1 text-xs ${isCurrent ? "bg-primary/10 text-primary font-semibold" : isDone ? "text-emerald-600" : "text-muted-foreground"}`}>
                      <div className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${isCurrent ? "bg-primary" : isDone ? "bg-emerald-500" : "bg-muted-foreground/30"}`} />
                      {STATUS_LABELS[s]}
                    </div>
                  );
                })}
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
                <span className="text-muted-foreground">{t("common.status")}</span>
                <StatusBadge status={cap.cap_status} />
              </div>
              {cap.responsible_party && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Responsible</span>
                  <span className="font-medium">{cap.responsible_party}</span>
                </div>
              )}
              {cap.deadline && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Deadline</span>
                  <span className={`font-medium ${isOverdue ? "text-red-600" : ""}`}>{formatDate(cap.deadline)}</span>
                </div>
              )}
              {cap.closed_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Closed</span>
                  <span className="font-medium">{formatDate(cap.closed_at)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created</span>
                <span className="text-muted-foreground">{formatDate(cap.created_at)}</span>
              </div>
              {cap.finding_id && (
                <div className="pt-2 border-t border-border">
                  <Link
                    href={`/findings/${cap.finding_id}`}
                    className="flex items-center gap-1.5 text-xs text-blue-600 hover:underline"
                  >
                    <AlertTriangle className="h-3.5 w-3.5" />
                    View source finding
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>

          <AskKBButton contextQuery={cap.title} />
          <AuditTrailPanel entityId={id} />
        </div>
      </div>
    </div>
  );
}
