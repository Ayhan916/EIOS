"use client";

import { use, useState, useRef } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Check,
  CheckCircle2,
  Clock,
  Download,
  FileText,
  GitPullRequest,
  Lightbulb,
  Loader2,
  MessageSquare,
  Pencil,
  Send,
  ShieldAlert,
  Trash2,
  UserCheck,
  XCircle,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import {
  getAssessment,
  submitForReview,
  assignReviewer,
  submitReviewAction,
  listReviewActions,
  getActivityTimeline,
} from "@/lib/api/assessments";
import { listUsers } from "@/lib/api/users";
import {
  listComments,
  createComment,
  editComment,
  deleteComment,
} from "@/lib/api/comments";
import { getAssessmentEvidenceInsights, listFindings } from "@/lib/api/findings";
import { listRisks } from "@/lib/api/risks";
import { createRecommendation, listRecommendations, updateRecommendation } from "@/lib/api/recommendations";
import { getComplianceCoverage } from "@/lib/api/compliance";
import { generateReport, listReports, downloadReportPdf } from "@/lib/api/reports";
import { getAssessmentBenchmark } from "@/lib/api/sector_intelligence";
import { useAuth } from "@/lib/auth/context";
import type { ActionStatus, CommentResponse } from "@/types/api";
import {
  extractErrorMessage,
  formatDate,
  formatDateTime,
  severityColor,
  verdictColor,
} from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { Separator } from "@/components/ui/separator";

const STRENGTH_STYLES: Record<string, string> = {
  "Very Strong": "bg-emerald-100 text-emerald-800",
  "Strong":      "bg-green-100 text-green-800",
  "Moderate":    "bg-amber-100 text-amber-800",
  "Weak":        "bg-red-100 text-red-800",
};

function EvidenceStrengthBadge({ strength }: { strength: string }) {
  const cls = STRENGTH_STYLES[strength] ?? "bg-secondary text-secondary-foreground";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}>
      <BookOpen className="h-3 w-3" />
      {strength}
    </span>
  );
}

function SeverityDot({ level }: { level: string }) {
  const c = severityColor(level);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full ${c.bg} ${c.text} px-2.5 py-0.5 text-xs font-semibold capitalize`}>
      <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
      {level}
    </span>
  );
}

function FindingStatusBadge({ status }: { status?: string | null }) {
  if (!status) return null;
  const meta: Record<string, string> = {
    Open:       "bg-slate-100 text-slate-700",
    InProgress: "bg-blue-100 text-blue-700",
    Resolved:   "bg-amber-100 text-amber-700",
    Verified:   "bg-emerald-100 text-emerald-700",
    Dismissed:  "bg-slate-100 text-slate-400",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${meta[status] ?? "bg-slate-100 text-slate-600"}`}>
      {status}
    </span>
  );
}

// ── Role helpers ──────────────────────────────────────────────────────────────

function isAtLeastReviewer(role: string) {
  return ["reviewer", "admin"].includes(role);
}
function isAdmin(role: string) {
  return role === "admin";
}

// ── Review status badge ───────────────────────────────────────────────────────

const REVIEW_STATUS_META: Record<string, { label: string; className: string }> = {
  Draft:             { label: "Draft",             className: "bg-slate-100 text-slate-600" },
  InReview:          { label: "In Review",         className: "bg-blue-100 text-blue-700" },
  ChangesRequested:  { label: "Changes Requested", className: "bg-amber-100 text-amber-700" },
  Approved:          { label: "Approved",          className: "bg-emerald-100 text-emerald-700" },
  Archived:          { label: "Archived",          className: "bg-slate-100 text-slate-500" },
};

function ReviewStatusBadge({ status }: { status: string }) {
  const meta = REVIEW_STATUS_META[status] ?? { label: status, className: "bg-slate-100 text-slate-600" };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${meta.className}`}>
      <GitPullRequest className="h-3 w-3" />
      {meta.label}
    </span>
  );
}

// ── Review action badge ────────────────────────────────────────────────────────

const REVIEW_ACTION_META: Record<string, { label: string; className: string; Icon: React.ElementType }> = {
  approve:         { label: "Approved",          className: "bg-emerald-100 text-emerald-700", Icon: CheckCircle2 },
  reject:          { label: "Rejected",          className: "bg-red-100 text-red-700",         Icon: XCircle },
  request_changes: { label: "Changes Requested", className: "bg-amber-100 text-amber-700",     Icon: MessageSquare },
};

function ReviewActionBadge({ actionType }: { actionType: string }) {
  const meta = REVIEW_ACTION_META[actionType] ?? { label: actionType, className: "bg-slate-100 text-slate-600", Icon: Check };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${meta.className}`}>
      <meta.Icon className="h-3 w-3" />
      {meta.label}
    </span>
  );
}

// ── Comment content renderer (highlights @mentions) ───────────────────────────

function CommentContent({ content }: { content: string }) {
  const parts = content.split(/(@[\w.\-]+)/g);
  return (
    <span>
      {parts.map((part, i) =>
        part.startsWith("@") ? (
          <span key={i} className="text-blue-600 font-medium">{part}</span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </span>
  );
}

// ── Activity event icon + label ───────────────────────────────────────────────

function activityMeta(action: string): { Icon: React.ElementType; iconClass: string; label: string } {
  switch (action) {
    case "assessment.review_started":
      return { Icon: GitPullRequest, iconClass: "text-blue-500",    label: "Submitted for review" };
    case "reviewer.assigned":
      return { Icon: UserCheck,      iconClass: "text-blue-500",    label: "Reviewer assigned" };
    case "assessment.approved":
      return { Icon: CheckCircle2,   iconClass: "text-emerald-500", label: "Approved" };
    case "assessment.rejected":
      return { Icon: XCircle,        iconClass: "text-red-500",     label: "Rejected" };
    case "assessment.changes_requested":
      return { Icon: MessageSquare,  iconClass: "text-amber-500",   label: "Changes requested" };
    case "comment.created":
      return { Icon: MessageSquare,  iconClass: "text-slate-400",   label: "Comment added" };
    case "comment.deleted":
      return { Icon: Trash2,         iconClass: "text-slate-400",   label: "Comment deleted" };
    case "review.approve":
      return { Icon: CheckCircle2,   iconClass: "text-emerald-500", label: "Approved" };
    case "review.reject":
      return { Icon: XCircle,        iconClass: "text-red-500",     label: "Rejected" };
    case "review.request_changes":
      return { Icon: MessageSquare,  iconClass: "text-amber-500",   label: "Changes requested" };
    default:
      return { Icon: Clock,          iconClass: "text-slate-400",   label: action.replace(/[._]/g, " ") };
  }
}

const ACTION_STATUS_META: Record<ActionStatus, { label: string; className: string }> = {
  open:        { label: "Open",        className: "bg-slate-100 text-slate-700" },
  in_progress: { label: "In Progress", className: "bg-blue-100 text-blue-700" },
  resolved:    { label: "Resolved",    className: "bg-amber-100 text-amber-700" },
  verified:    { label: "Verified",    className: "bg-emerald-100 text-emerald-700" },
};

function ActionStatusBadge({ status }: { status: ActionStatus }) {
  const meta = ACTION_STATUS_META[status] ?? ACTION_STATUS_META.open;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${meta.className}`}>
      {meta.label}
    </span>
  );
}

// ── Risk list with inline Create Recommendation ───────────────────────────────

function RiskList({ risks, assessmentId, onRecCreated }: {
  risks: { id: string; title: string; description: string; reasoning?: string | null; risk_level: string; probability?: number | null; impact?: number | null; category?: string | null }[];
  assessmentId: string;
  onRecCreated: () => void;
}) {
  const [openRiskId, setOpenRiskId] = useState<string | null>(null);
  const [recTitle, setRecTitle] = useState("");
  const [recDesc, setRecDesc] = useState("");
  const [recPriority, setRecPriority] = useState("Medium");
  const [recBusy, setRecBusy] = useState(false);
  const [recError, setRecError] = useState<string | null>(null);
  const [recDone, setRecDone] = useState<string | null>(null);

  function openForm(risk: typeof risks[0]) {
    setOpenRiskId(risk.id);
    setRecTitle(`Mitigate: ${risk.title}`);
    setRecDesc(risk.description || "");
    setRecPriority(risk.risk_level === "Critical" || risk.risk_level === "High" ? risk.risk_level : "Medium");
    setRecError(null);
    setRecDone(null);
  }

  async function handleCreate(riskId: string) {
    if (!recTitle.trim() || !recDesc.trim()) { setRecError("Title and description are required."); return; }
    setRecBusy(true);
    setRecError(null);
    try {
      await createRecommendation({ title: recTitle.trim(), description: recDesc.trim(), priority: recPriority, assessment_id: assessmentId });
      setRecDone(riskId);
      onRecCreated();
      setTimeout(() => { setOpenRiskId(null); setRecDone(null); }, 1500);
    } catch {
      setRecError("Failed to create recommendation.");
    } finally {
      setRecBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      {risks.map((r) => (
        <Card key={r.id}>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-foreground">{r.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">{r.description}</p>
                {r.reasoning && (
                  <p className="mt-2 text-xs text-muted-foreground border-l-2 border-border pl-3 italic">{r.reasoning}</p>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  {r.probability != null && (
                    <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">Probability: {Math.round(r.probability * 100)}%</span>
                  )}
                  {r.impact != null && (
                    <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">Impact: {Math.round(r.impact * 100)}%</span>
                  )}
                  {r.category && (
                    <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">{r.category}</span>
                  )}
                </div>
                {/* Inline create recommendation form */}
                {openRiskId === r.id ? (
                  <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50/40 p-3 space-y-2">
                    <p className="text-xs font-semibold text-blue-800">Create Recommendation</p>
                    <input
                      className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                      placeholder="Recommendation title"
                      value={recTitle}
                      onChange={(e) => setRecTitle(e.target.value)}
                    />
                    <textarea
                      rows={2}
                      className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-ring"
                      placeholder="Description / action steps…"
                      value={recDesc}
                      onChange={(e) => setRecDesc(e.target.value)}
                    />
                    <div className="flex items-center gap-2">
                      <select
                        value={recPriority}
                        onChange={(e) => setRecPriority(e.target.value)}
                        className="rounded-md border border-border bg-background px-2 py-1 text-xs"
                      >
                        {["Critical", "High", "Medium", "Low"].map((p) => <option key={p} value={p}>{p}</option>)}
                      </select>
                      {recDone === r.id ? (
                        <span className="flex items-center gap-1 text-xs text-emerald-700 font-medium"><CheckCircle2 className="h-3.5 w-3.5" /> Created</span>
                      ) : (
                        <>
                          <Button size="sm" className="h-7 text-xs" disabled={recBusy} onClick={() => handleCreate(r.id)}>
                            {recBusy ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                            Create
                          </Button>
                          <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setOpenRiskId(null)}>Cancel</Button>
                        </>
                      )}
                    </div>
                    {recError && <p className="text-xs text-red-600">{recError}</p>}
                  </div>
                ) : (
                  <button
                    onClick={() => openForm(r)}
                    className="mt-3 text-xs text-blue-600 hover:underline font-medium flex items-center gap-1"
                  >
                    <Lightbulb className="h-3 w-3" /> Create Recommendation
                  </button>
                )}
              </div>
              <div className="flex-shrink-0">
                <SeverityDot level={r.risk_level} />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function AssessmentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // ── Report state ────────────────────────────────────────────────────────────
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportError, setReportError] = useState("");

  // ── Review workflow state ────────────────────────────────────────────────────
  const [reviewError, setReviewError] = useState("");
  const [reviewLoading, setReviewLoading] = useState(false);
  const [selectedReviewerId, setSelectedReviewerId] = useState("");
  const [reviewComment, setReviewComment] = useState("");
  const [showAssignForm, setShowAssignForm] = useState(false);
  const [showActionPanel, setShowActionPanel] = useState<"" | "approve" | "reject" | "request_changes">("");

  // ── Comment state ────────────────────────────────────────────────────────────
  const [commentDraft, setCommentDraft] = useState("");
  const [commentSubmitting, setCommentSubmitting] = useState(false);
  const [commentError, setCommentError] = useState("");
  const [editingCommentId, setEditingCommentId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState("");
  const commentInputRef = useRef<HTMLTextAreaElement>(null);

  const { mutate: updateAction } = useMutation({
    mutationFn: ({ recId, status }: { recId: string; status: ActionStatus }) =>
      updateRecommendation(recId, { action_status: status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendations", id] });
    },
  });

  const { mutate: updateDueDate } = useMutation({
    mutationFn: ({ recId, due_date }: { recId: string; due_date: string | null }) =>
      updateRecommendation(recId, { due_date }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendations", id] });
    },
  });

  const { data: assessment, isLoading: loadingAssessment } = useQuery({
    queryKey: ["assessment", id],
    queryFn: () => getAssessment(id),
  });

  const { data: findings, isLoading: loadingFindings } = useQuery({
    queryKey: ["findings", id],
    queryFn: () => listFindings(id),
    enabled: !!id,
  });

  const { data: risks, isLoading: loadingRisks } = useQuery({
    queryKey: ["risks", id],
    queryFn: () => listRisks(id),
    enabled: !!id,
  });

  const { data: recs, isLoading: loadingRecs } = useQuery({
    queryKey: ["recommendations", id],
    queryFn: () => listRecommendations(id),
    enabled: !!id,
  });

  const { data: compliance, isLoading: loadingCompliance } = useQuery({
    queryKey: ["compliance", id],
    queryFn: () => getComplianceCoverage(id),
    enabled: !!id,
  });

  const {
    data: reports,
    isLoading: loadingReports,
    refetch: refetchReports,
  } = useQuery({
    queryKey: ["reports", id],
    queryFn: () => listReports(id),
    enabled: !!id,
  });

  const { data: benchmark, isLoading: loadingBenchmark } = useQuery({
    queryKey: ["benchmark", id],
    queryFn: () => getAssessmentBenchmark(id),
    enabled: !!id,
  });

  const { data: evidenceInsights, isLoading: loadingEvidence } = useQuery({
    queryKey: ["evidence-insights", id],
    queryFn: () => getAssessmentEvidenceInsights(id),
    enabled: !!id,
  });

  const { data: reviewActions } = useQuery({
    queryKey: ["review-actions", id],
    queryFn: () => listReviewActions(id),
    enabled: !!id,
  });

  const { data: activity } = useQuery({
    queryKey: ["activity", id],
    queryFn: () => getActivityTimeline(id),
    enabled: !!id,
  });

  const { data: comments, refetch: refetchComments } = useQuery({
    queryKey: ["comments", id],
    queryFn: () => listComments("Assessment", id),
    enabled: !!id,
  });

  const { data: orgUsers } = useQuery({
    queryKey: ["users"],
    queryFn: listUsers,
  });

  // ── Questionnaire state ────────────────────────────────────────────────────────
  const [showQForm, setShowQForm] = useState(false);
  const [qTemplateId, setQTemplateId] = useState("");
  const [qDueDate, setQDueDate] = useState("");

  const { data: qTemplates } = useQuery({
    queryKey: ["questionnaire-templates"],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/supplier-portal/internal/questionnaires/templates");
      return res.data as Array<{ id: string; template_name: string; version: string }>;
    },
    staleTime: 300_000,
  });

  const { data: qAssignments, refetch: refetchQAssignments } = useQuery({
    queryKey: ["questionnaire-assignments", assessment?.supplier_id],
    queryFn: async () => {
      const res = await apiClient.get(
        `/api/v1/supplier-portal/internal/questionnaires/assignments?supplier_id=${assessment!.supplier_id}`
      );
      return res.data as Array<{
        id: string; questionnaire_status: string; due_date: string | null; score: number | null; template_id: string; completion_pct: number | null;
      }>;
    },
    enabled: !!assessment?.supplier_id,
    staleTime: 60_000,
  });

  const sendQMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post("/api/v1/supplier-portal/internal/questionnaires/assign", {
        template_id: qTemplateId,
        supplier_id: assessment!.supplier_id,
        due_date: qDueDate || null,
      });
    },
    onSuccess: () => {
      setShowQForm(false);
      setQTemplateId("");
      setQDueDate("");
      refetchQAssignments();
    },
  });

  // ── Review workflow handlers ──────────────────────────────────────────────────

  async function handleSubmitForReview() {
    setReviewLoading(true);
    setReviewError("");
    try {
      await submitForReview(id, selectedReviewerId ? { reviewer_id: selectedReviewerId } : {});
      queryClient.invalidateQueries({ queryKey: ["assessment", id] });
      queryClient.invalidateQueries({ queryKey: ["activity", id] });
    } catch (err) {
      setReviewError(extractErrorMessage(err));
    } finally {
      setReviewLoading(false);
    }
  }

  async function handleAssignReviewer() {
    if (!selectedReviewerId) return;
    setReviewLoading(true);
    setReviewError("");
    try {
      await assignReviewer(id, { reviewer_id: selectedReviewerId });
      queryClient.invalidateQueries({ queryKey: ["assessment", id] });
      queryClient.invalidateQueries({ queryKey: ["activity", id] });
      setShowAssignForm(false);
      setSelectedReviewerId("");
    } catch (err) {
      setReviewError(extractErrorMessage(err));
    } finally {
      setReviewLoading(false);
    }
  }

  async function handleReviewAction(actionType: "approve" | "reject" | "request_changes") {
    setReviewLoading(true);
    setReviewError("");
    try {
      await submitReviewAction(id, { action_type: actionType, comment: reviewComment || undefined });
      queryClient.invalidateQueries({ queryKey: ["assessment", id] });
      queryClient.invalidateQueries({ queryKey: ["review-actions", id] });
      queryClient.invalidateQueries({ queryKey: ["activity", id] });
      setShowActionPanel("");
      setReviewComment("");
      // #163 Auto-update ESG score when assessment approved/completed
      if (actionType === "approve") {
        try {
          const stored = JSON.parse(localStorage.getItem("eios_automation_rules") ?? "{}");
          if (stored?.esg_score_update?.enabled !== false && assessment?.supplier_id) {
            await apiClient.post(`/api/v1/automations/trigger`, {
              rule_id: "esg_score_update",
              entity_type: "assessment",
              entity_id: id,
              payload: { supplier_id: assessment.supplier_id, recalculate_org_score: stored?.esg_score_update?.config?.recalculate_org_score ?? true },
            });
          }
        } catch { /* silent */ }
      }
    } catch (err) {
      setReviewError(extractErrorMessage(err));
    } finally {
      setReviewLoading(false);
    }
  }

  // ── Comment handlers ──────────────────────────────────────────────────────────

  async function handleSubmitComment() {
    if (!commentDraft.trim()) return;
    setCommentSubmitting(true);
    setCommentError("");
    try {
      await createComment({ entity_type: "Assessment", entity_id: id, content: commentDraft.trim() });
      setCommentDraft("");
      refetchComments();
      queryClient.invalidateQueries({ queryKey: ["activity", id] });
    } catch (err) {
      setCommentError(extractErrorMessage(err));
    } finally {
      setCommentSubmitting(false);
    }
  }

  async function handleEditComment(comment: CommentResponse) {
    if (!editingContent.trim()) return;
    try {
      await editComment(comment.id, { content: editingContent.trim() });
      setEditingCommentId(null);
      setEditingContent("");
      refetchComments();
    } catch {
      // silently fail — the UI stays in edit mode
    }
  }

  async function handleDeleteComment(commentId: string) {
    try {
      await deleteComment(commentId);
      refetchComments();
      queryClient.invalidateQueries({ queryKey: ["activity", id] });
    } catch {
      // silently fail
    }
  }

  async function handleGenerateReport() {
    setGeneratingReport(true);
    setReportError("");
    try {
      await generateReport(id);
      await refetchReports();
    } catch {
      setReportError("Failed to generate report. Please try again.");
    } finally {
      setGeneratingReport(false);
    }
  }

  async function handleDownloadReport(reportId: string, title: string) {
    try {
      await downloadReportPdf(reportId, title);
    } catch {
      setReportError("Failed to download report.");
    }
  }

  if (loadingAssessment) {
    return (
      <div className="flex justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className="py-24 text-center text-muted-foreground">
        Assessment not found.
      </div>
    );
  }

  const qualityPct = assessment.quality_score != null
    ? Math.round(assessment.quality_score * 100)
    : null;

  return (
    <div className="space-y-6">
      {/* Breadcrumb + header */}
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-4 -ml-1 gap-1">
          <Link href="/assessments">
            <ArrowLeft className="h-4 w-4" />
            Back to assessments
          </Link>
        </Button>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold leading-tight">{assessment.title}</h1>
            <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed max-w-3xl">
              {assessment.description}
            </p>
          </div>
          <div className="flex-shrink-0 flex items-start gap-3">
            {qualityPct != null && (
              <div className="text-right">
                <p className="text-xs text-muted-foreground">Quality Score</p>
                <p className={`text-2xl font-bold ${
                  qualityPct >= 70 ? "text-emerald-600" : qualityPct >= 40 ? "text-amber-600" : "text-red-600"
                }`}>
                  {qualityPct}%
                </p>
              </div>
            )}
            <Button variant="outline" size="sm" onClick={() => window.print()} className="gap-1.5 print:hidden">
              <Download className="h-3.5 w-3.5" /> Export PDF
            </Button>
          </div>
        </div>

        {/* Meta strip */}
        <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <span className="capitalize rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground">
            {assessment.status}
          </span>
          <ReviewStatusBadge status={assessment.review_status ?? "Draft"} />
          {assessment.assessment_type && (
            <span className="capitalize">{assessment.assessment_type}</span>
          )}
          <span>{formatDateTime(assessment.created_at)}</span>
          {assessment.methodology && (
            <>
              <Separator orientation="vertical" className="h-3" />
              <span className="italic truncate max-w-xs">{assessment.methodology}</span>
            </>
          )}
        </div>
      </div>

      {/* ── Questionnaire Panel (Item 34 + 35) ─────────────────────────────── */}
      {assessment.supplier_id && (
        <div className="rounded-lg border border-border bg-muted/20 px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <Send className="h-4 w-4 text-blue-500 flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium">Supplier Questionnaire</p>
                {qAssignments && qAssignments.length > 0 ? (
                  <div className="flex flex-col gap-2 mt-1">
                    {qAssignments.map((a) => {
                      const statusCls: Record<string, string> = {
                        pending: "bg-slate-100 text-slate-700",
                        submitted: "bg-blue-100 text-blue-700",
                        approved: "bg-emerald-100 text-emerald-700",
                        rejected: "bg-red-100 text-red-700",
                      };
                      const pct = a.completion_pct ?? (a.questionnaire_status === "submitted" || a.questionnaire_status === "approved" ? 100 : a.questionnaire_status === "pending" ? 0 : null);
                      return (
                        <div key={a.id} className="space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusCls[a.questionnaire_status] ?? "bg-slate-100 text-slate-600"}`}>
                              {a.questionnaire_status}
                            </span>
                            {a.score != null && (
                              <span className="text-[10px] text-muted-foreground">Score: <strong>{a.score.toFixed(0)}</strong></span>
                            )}
                            {a.due_date && (
                              <span className="text-[10px] text-muted-foreground">Due {new Date(a.due_date).toLocaleDateString()}</span>
                            )}
                            {pct != null && (
                              <span className="text-[10px] font-medium text-blue-700">{pct.toFixed(0)}% complete</span>
                            )}
                          </div>
                          {pct != null && (
                            <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${pct >= 100 ? "bg-emerald-500" : pct >= 50 ? "bg-blue-500" : "bg-amber-400"}`}
                                style={{ width: `${Math.min(pct, 100)}%` }}
                              />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground mt-0.5">No questionnaire sent yet</p>
                )}
              </div>
            </div>
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 flex-shrink-0"
              onClick={() => setShowQForm((v) => !v)}
            >
              <Send className="h-3.5 w-3.5" />
              Send Questionnaire
            </Button>
          </div>

          {showQForm && (
            <div className="mt-3 border-t border-border pt-3 space-y-2">
              <div className="flex flex-wrap gap-2 items-end">
                <div className="flex-1 min-w-48">
                  <p className="text-xs text-muted-foreground mb-1">Template</p>
                  <select
                    className="w-full h-8 rounded border border-input bg-background px-2 text-xs"
                    value={qTemplateId}
                    onChange={(e) => setQTemplateId(e.target.value)}
                  >
                    <option value="">Select template…</option>
                    {(qTemplates ?? []).map((t) => (
                      <option key={t.id} value={t.id}>{t.template_name} v{t.version}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Due date (optional)</p>
                  <input
                    type="date"
                    className="h-8 rounded border border-input bg-background px-2 text-xs"
                    value={qDueDate}
                    onChange={(e) => setQDueDate(e.target.value)}
                  />
                </div>
                <Button
                  size="sm"
                  disabled={!qTemplateId || sendQMutation.isPending}
                  onClick={() => sendQMutation.mutate()}
                  className="h-8"
                >
                  {sendQMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Send"}
                </Button>
              </div>
              {sendQMutation.isError && (
                <p className="text-xs text-red-600">Failed to send — check template and supplier.</p>
              )}
              {sendQMutation.isSuccess && (
                <p className="text-xs text-emerald-600">✓ Questionnaire sent successfully.</p>
              )}
            </div>
          )}
        </div>
      )}

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="findings">
            Findings {findings ? `(${findings.length})` : ""}
          </TabsTrigger>
          <TabsTrigger value="risks">
            Risks {risks ? `(${risks.length})` : ""}
          </TabsTrigger>
          <TabsTrigger value="recommendations">
            Actions {recs ? `(${recs.length})` : ""}
          </TabsTrigger>
          <TabsTrigger value="compliance">Compliance</TabsTrigger>
          <TabsTrigger value="benchmark">Benchmark</TabsTrigger>
          <TabsTrigger value="evidence">
            Evidence {evidenceInsights ? `(${evidenceInsights.total_evidence_links})` : ""}
          </TabsTrigger>
          <TabsTrigger value="reports">
            Reports {reports ? `(${reports.length})` : ""}
          </TabsTrigger>
          <TabsTrigger value="review" className="gap-1.5">
            <GitPullRequest className="h-3.5 w-3.5" />
            Review
          </TabsTrigger>
        </TabsList>

        {/* ── OVERVIEW ── */}
        <TabsContent value="overview" className="mt-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card className="flex flex-col">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  <CardTitle className="text-sm font-medium">Findings</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{findings?.length ?? "—"}</p>
                <p className="text-xs text-muted-foreground mt-1">material ESG findings</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <ShieldAlert className="h-4 w-4 text-red-500" />
                  <CardTitle className="text-sm font-medium">Risks</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{risks?.length ?? "—"}</p>
                <p className="text-xs text-muted-foreground mt-1">identified risk factors</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Lightbulb className="h-4 w-4 text-blue-500" />
                  <CardTitle className="text-sm font-medium">Actions</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{recs?.length ?? "—"}</p>
                <p className="text-xs text-muted-foreground mt-1">remediation recommendations</p>
              </CardContent>
            </Card>
          </div>

          {compliance && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="text-base">Compliance Snapshot</CardTitle>
                <CardDescription>
                  Verdict:{" "}
                  <span className={`font-semibold capitalize ${verdictColor(compliance.verdict.status)}`}>
                    {compliance.verdict.status.replace(/_/g, " ")}
                  </span>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="mb-1.5 flex justify-between text-sm">
                    <span className="text-muted-foreground">Overall coverage</span>
                    <span className="font-medium">
                      {Math.round(compliance.overall_coverage_ratio * 100)}%
                    </span>
                  </div>
                  <Progress
                    value={compliance.overall_coverage_ratio * 100}
                    className="h-2"
                  />
                </div>
                <div>
                  <div className="mb-1.5 flex justify-between text-sm">
                    <span className="text-muted-foreground">Mandatory coverage</span>
                    <span className="font-medium">
                      {Math.round(compliance.mandatory_coverage_ratio * 100)}%
                    </span>
                  </div>
                  <Progress
                    value={compliance.mandatory_coverage_ratio * 100}
                    className="h-2"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  {compliance.verdict.explanation}
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ── FINDINGS ── */}
        <TabsContent value="findings" className="mt-6">
          {loadingFindings ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : !findings?.length ? (
            <p className="py-12 text-center text-muted-foreground">No findings extracted.</p>
          ) : (
            <div className="space-y-3">
              {findings.map((f) => (
                <Card key={f.id}>
                  <CardContent className="pt-4 pb-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="font-semibold text-foreground">{f.title}</p>
                        <p className="mt-1 text-sm text-muted-foreground">{f.description}</p>
                        {f.reasoning && (
                          <p className="mt-2 text-xs text-muted-foreground border-l-2 border-border pl-3 italic">
                            {f.reasoning}
                          </p>
                        )}
                        <div className="mt-3 flex flex-wrap gap-2">
                          {f.category && (
                            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                              {f.category}
                            </span>
                          )}
                          <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                            Confidence: {f.confidence}
                          </span>
                          {f.evidence_strength && (
                            <EvidenceStrengthBadge strength={f.evidence_strength} />
                          )}
                          {f.evidence_source_count > 0 && (
                            <span className="rounded-full bg-blue-50 text-blue-700 px-2.5 py-0.5 text-xs">
                              {f.evidence_source_count} source{f.evidence_source_count !== 1 ? "s" : ""}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                        <SeverityDot level={f.severity} />
                        <FindingStatusBadge status={f.status} />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ── RISKS ── */}
        <TabsContent value="risks" className="mt-6">
          {loadingRisks ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : !risks?.length ? (
            <p className="py-12 text-center text-muted-foreground">No risks identified.</p>
          ) : (
            <RiskList risks={risks} assessmentId={id} onRecCreated={() => queryClient.invalidateQueries({ queryKey: ["recommendations", id] })} />
          )}
        </TabsContent>

        {/* ── ACTIONS (Recommendations) ── */}
        <TabsContent value="recommendations" className="mt-6">
          {loadingRecs ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : !recs?.length ? (
            <p className="py-12 text-center text-muted-foreground">No recommendations generated.</p>
          ) : (() => {
            const now = new Date();
            const isOverdue = (due: string | null, actionStatus: ActionStatus) =>
              due != null &&
              new Date(due) < now &&
              actionStatus !== "resolved" &&
              actionStatus !== "verified";

            const overdueCount = recs.filter((r) => isOverdue(r.due_date, r.action_status)).length;

            return (
              <div className="space-y-4">
                {/* Status summary strip */}
                <div className="grid grid-cols-5 gap-3">
                  {(["open", "in_progress", "resolved", "verified"] as ActionStatus[]).map((s) => {
                    const count = recs.filter((r) => r.action_status === s).length;
                    const meta = ACTION_STATUS_META[s];
                    return (
                      <div key={s} className={`rounded-lg p-3 text-center ${meta.className}`}>
                        <p className="text-2xl font-bold">{count}</p>
                        <p className="text-xs font-medium mt-0.5">{meta.label}</p>
                      </div>
                    );
                  })}
                  <div className="rounded-lg p-3 text-center bg-red-100 text-red-700">
                    <p className="text-2xl font-bold">{overdueCount}</p>
                    <p className="text-xs font-medium mt-0.5">Overdue</p>
                  </div>
                </div>

                {/* Action cards */}
                {recs.map((rec) => {
                  const overdue = isOverdue(rec.due_date, rec.action_status);
                  const dueDateValue = rec.due_date
                    ? new Date(rec.due_date).toISOString().split("T")[0]
                    : "";

                  return (
                    <Card
                      key={rec.id}
                      className={overdue ? "border-red-300 bg-red-50/30" : ""}
                    >
                      <CardContent className="pt-4 pb-4">
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <p className="font-semibold text-foreground">{rec.title}</p>
                              {rec.action_required && (
                                <Badge variant="destructive" className="text-[10px] h-4 px-1.5">
                                  Required
                                </Badge>
                              )}
                              <ActionStatusBadge status={rec.action_status} />
                              {overdue && (
                                <span className="inline-flex items-center gap-1 rounded-full bg-red-100 text-red-700 px-2.5 py-0.5 text-xs font-semibold">
                                  <AlertTriangle className="h-3 w-3" />
                                  Overdue
                                </span>
                              )}
                            </div>
                            <p className="mt-1 text-sm text-muted-foreground">{rec.description}</p>
                            {rec.reasoning && (
                              <p className="mt-2 text-xs text-muted-foreground border-l-2 border-border pl-3 italic">
                                {rec.reasoning}
                              </p>
                            )}
                            {/* Due date setter */}
                            <div className="mt-2 flex items-center gap-2">
                              <label className={`text-xs font-medium ${overdue ? "text-red-600" : "text-muted-foreground"}`}>
                                Due date:
                              </label>
                              <input
                                type="date"
                                value={dueDateValue}
                                onChange={(e) =>
                                  updateDueDate({
                                    recId: rec.id,
                                    due_date: e.target.value
                                      ? `${e.target.value}T00:00:00Z`
                                      : null,
                                  })
                                }
                                className={`text-xs rounded border px-2 py-0.5 bg-background cursor-pointer focus:outline-none focus:ring-1 focus:ring-ring ${
                                  overdue
                                    ? "border-red-300 text-red-700"
                                    : "border-border text-foreground"
                                }`}
                              />
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-2 flex-shrink-0">
                            <SeverityDot level={rec.priority} />
                            <select
                              value={rec.action_status}
                              onChange={(e) =>
                                updateAction({ recId: rec.id, status: e.target.value as ActionStatus })
                              }
                              className="text-xs rounded-md border border-border bg-background px-2 py-1 text-foreground cursor-pointer focus:outline-none focus:ring-1 focus:ring-ring"
                            >
                              <option value="open">Open</option>
                              <option value="in_progress">In Progress</option>
                              <option value="resolved">Resolved</option>
                              <option value="verified">Verified</option>
                            </select>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            );
          })()}
        </TabsContent>

        {/* ── COMPLIANCE ── */}
        <TabsContent value="compliance" className="mt-6">
          {loadingCompliance ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : !compliance ? (
            <p className="py-12 text-center text-muted-foreground">
              No compliance data available.
            </p>
          ) : (
            <div className="space-y-6">
              {/* Verdict card */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Compliance Verdict</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-3">
                    <p className={`text-xl font-bold capitalize ${verdictColor(compliance.verdict.status)}`}>
                      {compliance.verdict.status.replace(/_/g, " ")}
                    </p>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {compliance.verdict.explanation}
                  </p>
                  <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-center">
                    {[
                      { label: "Mandatory covered", value: `${compliance.verdict.covered_mandatory_count}/${compliance.verdict.total_mandatory_articles}` },
                      { label: "Mandatory gaps", value: compliance.verdict.mandatory_gap_count },
                      { label: "Critical gaps", value: compliance.verdict.critical_gap_count },
                      { label: "High gaps", value: compliance.verdict.high_gap_count },
                    ].map((stat) => (
                      <div key={stat.label} className="rounded-lg bg-muted/50 p-3">
                        <p className="text-xs text-muted-foreground">{stat.label}</p>
                        <p className="mt-1 text-lg font-bold">{stat.value}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Framework coverage */}
              {compliance.framework_coverage.map((fw) => (
                <Card key={fw.framework}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-semibold">{fw.framework}</CardTitle>
                      <span className="text-sm font-medium text-muted-foreground">
                        {fw.covered_count}/{fw.total_articles} articles covered
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <Progress value={fw.coverage_ratio * 100} className="h-2 mb-4" />
                    <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                      {fw.articles.map((art) => (
                        <div
                          key={art.code}
                          className={`flex items-center gap-2 rounded-md px-2.5 py-1.5 text-xs ${
                            art.covered
                              ? "bg-emerald-50 text-emerald-800"
                              : "bg-red-50 text-red-800"
                          }`}
                        >
                          {art.covered ? (
                            <CheckCircle2 className="h-3 w-3 flex-shrink-0" />
                          ) : (
                            <AlertTriangle className="h-3 w-3 flex-shrink-0" />
                          )}
                          <span className="font-mono font-medium">{art.code}</span>
                          <span className="truncate">{art.title}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}

              {/* Top gaps */}
              {compliance.gaps.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Compliance Gaps</CardTitle>
                    <CardDescription>
                      Regulatory obligations not yet addressed
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {compliance.gaps.map((gap) => (
                      <div
                        key={gap.article_code}
                        className="rounded-lg border border-border p-4"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium text-sm">
                              <span className="font-mono text-muted-foreground mr-2">
                                {gap.article_code}
                              </span>
                              {gap.title}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {gap.explanation}
                            </p>
                            {gap.remediation_hint && (
                              <p className="mt-2 text-xs text-blue-700 bg-blue-50 rounded px-2 py-1">
                                💡 {gap.remediation_hint}
                              </p>
                            )}
                          </div>
                          <SeverityDot level={gap.gap_severity} />
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </TabsContent>
        {/* ── BENCHMARK ── */}
        <TabsContent value="benchmark" className="mt-6">
          {loadingBenchmark ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : !benchmark ? (
            <p className="py-12 text-center text-muted-foreground">
              Benchmark data unavailable. Ensure the assessment has a sector assigned.
            </p>
          ) : (
            <div className="space-y-5">
              {/* Overall rating */}
              <Card>
                <CardHeader>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <CardTitle className="text-base">Sector Benchmark</CardTitle>
                      <CardDescription>
                        {benchmark.sector_name} ({benchmark.sector_nace_code})
                      </CardDescription>
                    </div>
                    <span className={`flex-shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${
                      benchmark.benchmark_rating === "above_sector_baseline"
                        ? "bg-emerald-100 text-emerald-800"
                        : benchmark.benchmark_rating === "meets_sector_baseline"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-red-100 text-red-800"
                    }`}>
                      {benchmark.benchmark_rating.replace(/_/g, " ")}
                    </span>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{benchmark.benchmark_explanation}</p>
                </CardContent>
              </Card>

              {/* Sector inherent risk */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Inherent Sector ESG Risk</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {[
                      { label: "Environmental", level: benchmark.environmental_risk },
                      { label: "Social", level: benchmark.social_risk },
                      { label: "Governance", level: benchmark.governance_risk },
                      { label: "Overall", level: benchmark.overall_sector_risk },
                    ].map(({ label, level }) => {
                      const c = severityColor(level);
                      return (
                        <div key={label} className={`rounded-lg p-3 text-center ${c.bg}`}>
                          <p className={`text-xs font-medium ${c.text}`}>{label}</p>
                          <p className={`text-sm font-bold mt-1 ${c.text}`}>{level}</p>
                        </div>
                      );
                    })}
                  </div>
                  <div className="mt-4 space-y-1">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Applicable Frameworks</p>
                    <div className="flex flex-wrap gap-2">
                      {benchmark.applicable_frameworks.map((fw) => (
                        <span key={fw} className="rounded-full bg-blue-50 text-blue-700 px-2.5 py-0.5 text-xs font-medium">
                          {fw}
                        </span>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Coverage vs baseline */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Compliance Coverage vs Sector Baseline</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="rounded-lg bg-muted/50 p-3 text-center">
                      <p className="text-xs text-muted-foreground">Sector Baseline</p>
                      <p className="text-xl font-bold mt-1">
                        {Math.round(benchmark.baseline_mandatory_coverage * 100)}%
                      </p>
                    </div>
                    <div className="rounded-lg bg-muted/50 p-3 text-center">
                      <p className="text-xs text-muted-foreground">This Assessment</p>
                      <p className={`text-xl font-bold mt-1 ${
                        benchmark.mandatory_coverage == null
                          ? "text-muted-foreground"
                          : benchmark.coverage_vs_baseline != null && benchmark.coverage_vs_baseline >= 0
                          ? "text-emerald-600"
                          : "text-red-600"
                      }`}>
                        {benchmark.mandatory_coverage != null
                          ? `${Math.round(benchmark.mandatory_coverage * 100)}%`
                          : "—"}
                      </p>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">{benchmark.coverage_explanation}</p>
                </CardContent>
              </Card>

              {/* Finding adequacy */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Finding Adequacy</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="rounded-lg bg-muted/50 p-3 text-center">
                      <p className="text-xs text-muted-foreground">Critical</p>
                      <p className="text-xl font-bold text-red-600">{benchmark.finding_distribution.critical}</p>
                    </div>
                    <div className="rounded-lg bg-muted/50 p-3 text-center">
                      <p className="text-xs text-muted-foreground">High</p>
                      <p className="text-xl font-bold text-orange-600">{benchmark.finding_distribution.high}</p>
                    </div>
                    <div className="rounded-lg bg-muted/50 p-3 text-center">
                      <p className="text-xs text-muted-foreground">Medium + Low</p>
                      <p className="text-xl font-bold">{benchmark.finding_distribution.medium + benchmark.finding_distribution.low}</p>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">{benchmark.finding_explanation}</p>
                </CardContent>
              </Card>

              {/* Key sector risk themes */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Key Sector Risk Themes</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {benchmark.key_risk_themes.map((theme) => {
                    const identified = benchmark.key_themes_identified.includes(theme);
                    return (
                      <div
                        key={theme}
                        className={`flex items-center gap-2 rounded-md px-3 py-2 text-xs ${
                          identified
                            ? "bg-emerald-50 text-emerald-800"
                            : "bg-red-50 text-red-700"
                        }`}
                      >
                        {identified ? (
                          <CheckCircle2 className="h-3 w-3 flex-shrink-0" />
                        ) : (
                          <AlertTriangle className="h-3 w-3 flex-shrink-0" />
                        )}
                        <span>{theme}</span>
                      </div>
                    );
                  })}
                </CardContent>
              </Card>

              {/* Regulatory exposure */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Regulatory Exposure</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{benchmark.regulatory_exposure_notes}</p>
                </CardContent>
              </Card>

              {/* Peer comparison */}
              {benchmark.peer_count > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-semibold">
                      Organisational Peer Comparison ({benchmark.peer_count} peer{benchmark.peer_count !== 1 ? "s" : ""})
                    </CardTitle>
                    <CardDescription>
                      Other assessments in the same sector within your organisation
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {benchmark.org_avg_quality_score != null && (
                      <div className="grid grid-cols-2 gap-4">
                        <div className="rounded-lg bg-muted/50 p-3 text-center">
                          <p className="text-xs text-muted-foreground">Org avg quality score</p>
                          <p className="text-xl font-bold">{Math.round(benchmark.org_avg_quality_score * 100)}%</p>
                        </div>
                        <div className="rounded-lg bg-muted/50 p-3 text-center">
                          <p className="text-xs text-muted-foreground">Org avg findings</p>
                          <p className="text-xl font-bold">{benchmark.org_avg_finding_count}</p>
                        </div>
                      </div>
                    )}
                    <div className="space-y-2">
                      {benchmark.peers.map((peer) => (
                        <div key={peer.assessment_id} className="rounded-lg border border-border px-3 py-2 flex items-center justify-between gap-3 text-sm">
                          <span className="truncate text-foreground">{peer.title}</span>
                          <div className="flex-shrink-0 flex gap-2 text-xs text-muted-foreground">
                            <span>{peer.finding_count} findings</span>
                            {peer.quality_score != null && (
                              <span className="font-medium text-foreground">
                                {Math.round(peer.quality_score * 100)}%
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </TabsContent>

        {/* ── EVIDENCE INTELLIGENCE ── */}
        <TabsContent value="evidence" className="mt-6">
          {loadingEvidence ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : !evidenceInsights ? (
            <p className="py-12 text-center text-muted-foreground">
              No evidence data available. Run a workflow to generate findings with evidence traceability.
            </p>
          ) : (
            <div className="space-y-5">
              {/* Summary strip */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  { label: "Total Findings", value: evidenceInsights.total_findings },
                  { label: "With Evidence Links", value: evidenceInsights.linked_findings },
                  { label: "Evidence Links", value: evidenceInsights.total_evidence_links },
                  {
                    label: "Coverage",
                    value: evidenceInsights.total_findings > 0
                      ? `${Math.round((evidenceInsights.linked_findings / evidenceInsights.total_findings) * 100)}%`
                      : "—",
                  },
                ].map((stat) => (
                  <div key={stat.label} className="rounded-lg bg-muted/50 p-3 text-center">
                    <p className="text-xs text-muted-foreground">{stat.label}</p>
                    <p className="text-xl font-bold mt-1">{stat.value}</p>
                  </div>
                ))}
              </div>

              {/* Strength distribution */}
              {Object.keys(evidenceInsights.strength_distribution).length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Evidence Strength Distribution</CardTitle>
                  </CardHeader>
                  <CardContent className="flex flex-wrap gap-2">
                    {(["Very Strong", "Strong", "Moderate", "Weak"] as const).map((s) => {
                      const count = evidenceInsights.strength_distribution[s] ?? 0;
                      if (!count) return null;
                      return (
                        <div key={s} className="flex items-center gap-1.5">
                          <EvidenceStrengthBadge strength={s} />
                          <span className="text-sm font-semibold">{count}</span>
                        </div>
                      );
                    })}
                  </CardContent>
                </Card>
              )}

              {/* Per-finding evidence list */}
              {evidenceInsights.findings.map(({ finding, evidence_links }) => (
                <Card key={finding.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-semibold text-sm">{finding.title}</p>
                        <p className="mt-0.5 text-xs text-muted-foreground">{finding.category}</p>
                      </div>
                      <div className="flex flex-shrink-0 items-center gap-2">
                        {finding.evidence_strength && (
                          <EvidenceStrengthBadge strength={finding.evidence_strength} />
                        )}
                        <SeverityDot level={finding.severity} />
                      </div>
                    </div>
                  </CardHeader>
                  {evidence_links.length > 0 ? (
                    <CardContent className="pt-0 space-y-2">
                      {evidence_links.map((lnk, i) => (
                        <div
                          key={lnk.id}
                          className="rounded-md border border-border bg-muted/30 px-3 py-2"
                        >
                          <div className="flex items-center justify-between gap-3 mb-1.5">
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              <BookOpen className="h-3 w-3" />
                              {lnk.page_number != null && (
                                <span className="font-mono font-medium text-foreground">
                                  p.{lnk.page_number}
                                </span>
                              )}
                              <span>Link {i + 1}</span>
                            </div>
                            {lnk.confidence_score != null && (
                              <span className="text-xs font-semibold text-blue-700 bg-blue-50 rounded px-1.5 py-0.5">
                                {Math.round(lnk.confidence_score * 100)}% match
                              </span>
                            )}
                          </div>
                          {lnk.supporting_excerpt && (
                            <p className="text-xs text-muted-foreground italic leading-relaxed line-clamp-3">
                              &ldquo;{lnk.supporting_excerpt}&rdquo;
                            </p>
                          )}
                        </div>
                      ))}
                    </CardContent>
                  ) : (
                    <CardContent className="pt-0">
                      <p className="text-xs text-muted-foreground italic">No evidence links for this finding.</p>
                    </CardContent>
                  )}
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ── REPORTS ── */}
        <TabsContent value="reports" className="mt-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Executive Reports</h3>
                <p className="text-sm text-muted-foreground">
                  Generate a PDF report capturing all findings, risks, recommendations, and evidence at this point in time.
                </p>
              </div>
              <Button
                onClick={handleGenerateReport}
                disabled={generatingReport}
                className="gap-2 flex-shrink-0"
              >
                {generatingReport ? (
                  <Spinner size="sm" className="text-white" />
                ) : (
                  <FileText className="h-4 w-4" />
                )}
                {generatingReport ? "Generating..." : "Generate Report"}
              </Button>
            </div>

            {reportError && (
              <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200">
                {reportError}
              </div>
            )}

            {loadingReports ? (
              <div className="flex justify-center py-12"><Spinner /></div>
            ) : !reports?.length ? (
              <div className="rounded-lg border-2 border-dashed border-border py-16 text-center">
                <FileText className="mx-auto h-10 w-10 text-muted-foreground/40 mb-3" />
                <p className="text-sm text-muted-foreground">No reports generated yet.</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Click "Generate Report" to create an executive-ready PDF.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {reports.map((report) => (
                  <Card key={report.id}>
                    <CardContent className="pt-4 pb-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <p className="font-semibold text-sm text-foreground truncate">
                            {report.title}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            Generated {formatDateTime(report.created_at)}
                          </p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                              {report.finding_count} findings
                            </span>
                            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                              {report.risk_count} risks
                            </span>
                            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                              {report.recommendation_count} recommendations
                            </span>
                            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                              {report.evidence_count} evidence sources
                            </span>
                          </div>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-shrink-0 gap-1.5"
                          onClick={() => handleDownloadReport(report.id, report.title)}
                        >
                          <Download className="h-3.5 w-3.5" />
                          Download PDF
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
        {/* ── REVIEW ── */}
        <TabsContent value="review" className="mt-6 space-y-6">

          {/* Review status card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-3">
                <CardTitle className="text-base">Review Status</CardTitle>
                <ReviewStatusBadge status={assessment.review_status ?? "Draft"} />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Reviewer</p>
                  <p className="mt-0.5 font-medium">
                    {assessment.assigned_reviewer_id
                      ? (orgUsers?.find((u) => u.id === assessment.assigned_reviewer_id)?.display_name ??
                         assessment.assigned_reviewer_id)
                      : <span className="text-muted-foreground italic">Not assigned</span>}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Due date</p>
                  <p className="mt-0.5 font-medium">
                    {assessment.review_due_date
                      ? formatDate(assessment.review_due_date)
                      : <span className="text-muted-foreground italic">Not set</span>}
                  </p>
                </div>
                {assessment.approval_date && (
                  <div>
                    <p className="text-xs text-muted-foreground">Approved on</p>
                    <p className="mt-0.5 font-medium text-emerald-700">
                      {formatDate(assessment.approval_date)}
                    </p>
                  </div>
                )}
              </div>

              {reviewError && (
                <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
                  {reviewError}
                </div>
              )}

              {/* Submit for review — visible when Draft */}
              {(assessment.review_status ?? "Draft") === "Draft" && (
                <div className="flex items-center gap-3 pt-1">
                  <Button
                    onClick={handleSubmitForReview}
                    disabled={reviewLoading}
                    className="gap-2"
                  >
                    <GitPullRequest className="h-4 w-4" />
                    {reviewLoading ? "Submitting…" : "Submit for Review"}
                  </Button>
                  <p className="text-xs text-muted-foreground">
                    Transitions the assessment to In Review and notifies the assigned reviewer.
                  </p>
                </div>
              )}

              {/* Re-submit after changes requested */}
              {(assessment.review_status ?? "Draft") === "ChangesRequested" && (
                <div className="flex items-center gap-3 pt-1">
                  <Button
                    onClick={handleSubmitForReview}
                    disabled={reviewLoading}
                    variant="outline"
                    className="gap-2"
                  >
                    <GitPullRequest className="h-4 w-4" />
                    {reviewLoading ? "Submitting…" : "Resubmit for Review"}
                  </Button>
                  <p className="text-xs text-muted-foreground">
                    Resubmit after addressing the requested changes.
                  </p>
                </div>
              )}

              {/* Assign reviewer — admin only */}
              {user && isAdmin(user.role) && (
                <div className="border-t border-border pt-4">
                  {!showAssignForm ? (
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2"
                      onClick={() => setShowAssignForm(true)}
                    >
                      <UserCheck className="h-3.5 w-3.5" />
                      {assessment.assigned_reviewer_id ? "Reassign Reviewer" : "Assign Reviewer"}
                    </Button>
                  ) : (
                    <div className="flex items-end gap-3">
                      <div className="flex-1 space-y-1">
                        <label className="text-xs font-medium text-muted-foreground">
                          Select reviewer
                        </label>
                        <select
                          value={selectedReviewerId}
                          onChange={(e) => setSelectedReviewerId(e.target.value)}
                          className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                        >
                          <option value="">— choose a reviewer —</option>
                          {(orgUsers ?? [])
                            .filter((u) => isAtLeastReviewer(u.role) && u.is_active)
                            .map((u) => (
                              <option key={u.id} value={u.id}>
                                {u.display_name} ({u.email})
                              </option>
                            ))}
                        </select>
                      </div>
                      <Button
                        size="sm"
                        onClick={handleAssignReviewer}
                        disabled={!selectedReviewerId || reviewLoading}
                        className="gap-1.5"
                      >
                        <Check className="h-3.5 w-3.5" />
                        Assign
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => { setShowAssignForm(false); setSelectedReviewerId(""); }}
                      >
                        Cancel
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {/* Review action buttons — reviewer+ when InReview */}
              {user && isAtLeastReviewer(user.role) &&
               (assessment.review_status ?? "Draft") === "InReview" && (
                <div className="border-t border-border pt-4 space-y-3">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Governance Decision
                  </p>
                  {showActionPanel === "" ? (
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
                        onClick={() => setShowActionPanel("approve")}
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="gap-1.5 border-amber-300 text-amber-700 hover:bg-amber-50"
                        onClick={() => setShowActionPanel("request_changes")}
                      >
                        <MessageSquare className="h-3.5 w-3.5" />
                        Request Changes
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="gap-1.5 border-red-300 text-red-700 hover:bg-red-50"
                        onClick={() => setShowActionPanel("reject")}
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        Reject
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="flex items-center gap-2">
                        <ReviewActionBadge actionType={showActionPanel} />
                        <span className="text-sm font-medium">
                          {showActionPanel === "approve" && "Approve this assessment"}
                          {showActionPanel === "request_changes" && "Request changes"}
                          {showActionPanel === "reject" && "Reject this assessment"}
                        </span>
                      </div>
                      <textarea
                        rows={3}
                        placeholder="Add a note (optional)…"
                        value={reviewComment}
                        onChange={(e) => setReviewComment(e.target.value)}
                        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none"
                      />
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => handleReviewAction(showActionPanel as "approve" | "reject" | "request_changes")}
                          disabled={reviewLoading}
                          className={
                            showActionPanel === "approve"
                              ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                              : showActionPanel === "reject"
                              ? "bg-red-600 hover:bg-red-700 text-white"
                              : "bg-amber-600 hover:bg-amber-700 text-white"
                          }
                        >
                          {reviewLoading ? "Submitting…" : "Confirm"}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => { setShowActionPanel(""); setReviewComment(""); }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Review decision history */}
          {reviewActions && reviewActions.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Decision History</CardTitle>
                <CardDescription>Formal governance decisions on this assessment</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {reviewActions.map((ra) => (
                  <div key={ra.id} className="flex items-start gap-3 rounded-lg border border-border px-4 py-3">
                    <ReviewActionBadge actionType={ra.action_type} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium">{ra.actor_email}</span>
                        <span className="text-xs text-muted-foreground">
                          {formatDateTime(ra.created_at)}
                        </span>
                      </div>
                      {ra.comment && (
                        <p className="mt-1 text-sm text-muted-foreground italic">
                          &ldquo;{ra.comment}&rdquo;
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Comment thread */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <MessageSquare className="h-4 w-4" />
                Discussion
                {comments && comments.filter((c) => !c.is_deleted).length > 0 && (
                  <span className="text-xs font-normal text-muted-foreground">
                    ({comments.filter((c) => !c.is_deleted).length})
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Comment composer */}
              <div className="space-y-2">
                <textarea
                  ref={commentInputRef}
                  rows={3}
                  placeholder="Write a comment… use @name to mention a colleague"
                  value={commentDraft}
                  onChange={(e) => setCommentDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmitComment();
                  }}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none"
                />
                {commentError && (
                  <p className="text-xs text-red-600">{commentError}</p>
                )}
                <div className="flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">⌘ + Enter to submit</p>
                  <Button
                    size="sm"
                    onClick={handleSubmitComment}
                    disabled={!commentDraft.trim() || commentSubmitting}
                    className="gap-1.5"
                  >
                    <MessageSquare className="h-3.5 w-3.5" />
                    {commentSubmitting ? "Posting…" : "Comment"}
                  </Button>
                </div>
              </div>

              {/* Comment list */}
              {comments && comments.filter((c) => !c.is_deleted).length > 0 ? (
                <div className="space-y-3 border-t border-border pt-4">
                  {comments
                    .filter((c) => !c.is_deleted)
                    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
                    .map((comment) => (
                      <div key={comment.id} className="flex gap-3">
                        {/* Avatar placeholder */}
                        <div className="h-7 w-7 flex-shrink-0 rounded-full bg-primary/10 flex items-center justify-center text-[10px] font-semibold text-primary uppercase">
                          {(comment.author_name ?? "?")[0]}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-medium">
                              {comment.author_name ?? "Unknown"}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {formatDateTime(comment.created_at)}
                            </span>
                            {comment.is_edited && (
                              <span className="text-[10px] text-muted-foreground italic">edited</span>
                            )}
                          </div>

                          {editingCommentId === comment.id ? (
                            <div className="mt-1.5 space-y-2">
                              <textarea
                                rows={3}
                                value={editingContent}
                                onChange={(e) => setEditingContent(e.target.value)}
                                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring resize-none"
                                autoFocus
                              />
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  onClick={() => handleEditComment(comment)}
                                  disabled={!editingContent.trim()}
                                >
                                  Save
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => { setEditingCommentId(null); setEditingContent(""); }}
                                >
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <p className="mt-0.5 text-sm text-foreground leading-relaxed">
                              <CommentContent content={comment.content} />
                            </p>
                          )}

                          {/* Edit / delete actions — only for own comments or admin */}
                          {user && (user.id === comment.author_id || isAdmin(user.role)) &&
                           editingCommentId !== comment.id && (
                            <div className="mt-1 flex items-center gap-1">
                              {user.id === comment.author_id && (
                                <button
                                  onClick={() => {
                                    setEditingCommentId(comment.id);
                                    setEditingContent(comment.content);
                                  }}
                                  className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                                >
                                  <Pencil className="h-2.5 w-2.5" />
                                  Edit
                                </button>
                              )}
                              <button
                                onClick={() => handleDeleteComment(comment.id)}
                                className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-red-600 transition-colors ml-2"
                              >
                                <Trash2 className="h-2.5 w-2.5" />
                                Delete
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                </div>
              ) : (
                <div className="border-t border-border pt-4 text-center py-6">
                  <MessageSquare className="mx-auto h-8 w-8 text-muted-foreground/30 mb-2" />
                  <p className="text-sm text-muted-foreground">No comments yet. Start the discussion.</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Activity timeline */}
          {activity && activity.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Activity Timeline</CardTitle>
                <CardDescription>Chronological audit of all review and collaboration events</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="relative space-y-0">
                  {[...activity]
                    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                    .map((event, i) => {
                      const meta = activityMeta(event.action);
                      return (
                        <div key={i} className="flex gap-3 pb-4 relative">
                          {/* Connector line */}
                          {i < activity.length - 1 && (
                            <div className="absolute left-[13px] top-6 bottom-0 w-px bg-border" />
                          )}
                          <div className={`flex-shrink-0 h-7 w-7 rounded-full bg-muted flex items-center justify-center z-10`}>
                            <meta.Icon className={`h-3.5 w-3.5 ${meta.iconClass}`} />
                          </div>
                          <div className="min-w-0 flex-1 pt-0.5">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-sm font-medium">{meta.label}</span>
                              <span className="text-xs text-muted-foreground">
                                {formatDateTime(event.timestamp)}
                              </span>
                            </div>
                            {event.actor_name && (
                              <p className="text-xs text-muted-foreground">
                                by {event.actor_name}
                              </p>
                            )}
                            {event.detail && (
                              <p className="mt-0.5 text-xs text-muted-foreground italic line-clamp-2">
                                {event.detail}
                              </p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                </div>
              </CardContent>
            </Card>
          )}

        </TabsContent>

      </Tabs>
    </div>
  );
}
