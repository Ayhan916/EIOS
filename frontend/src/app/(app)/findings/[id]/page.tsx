"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useRef, useCallback } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
  Link2,
  Loader2,
  ShieldAlert,
  Upload,
  Zap,
} from "lucide-react";
import { getFinding, getFindingEvidenceLinks, getFindingLinkedRisks } from "@/lib/api/findings";
import { listRisks } from "@/lib/api/risks";
import apiClient from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";
import { CopilotDrawer } from "@/components/copilot-drawer";
import { AskKBButton } from "@/components/layout/knowledge-search";
import { useLanguage } from "@/lib/i18n/context";

// ── #145 Finding Audit: complete change history ───────────────────────────────

interface ActivityEntry {
  id: string;
  action: string;
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  actor_name: string | null;
  created_at: string;
}

const ACTION_COLORS: Record<string, string> = {
  created:   "bg-blue-500",
  updated:   "bg-amber-500",
  closed:    "bg-slate-400",
  reopened:  "bg-violet-500",
  escalated: "bg-red-500",
  commented: "bg-emerald-500",
};

function AuditTrailPanel({ entityId }: { entityId: string }) {
  const { t } = useLanguage();
  const [open, setOpen] = useState(false);

  const { data: entries, isLoading } = useQuery({
    queryKey: ["audit-trail", "finding", entityId],
    queryFn: async () => {
      const r = await apiClient.get(`/findings/${entityId}/activity`);
      return r.data as ActivityEntry[];
    },
    enabled: open,
    staleTime: 60_000,
  });

  function exportCsv() {
    if (!entries?.length) return;
    const rows = [["Action","Field","Old Value","New Value","Actor","Timestamp"]];
    for (const e of entries) {
      rows.push([e.action, e.field_name ?? "", e.old_value ?? "", e.new_value ?? "", e.actor_name ?? "System", e.created_at]);
    }
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `finding-audit-${entityId.slice(0, 8)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="rounded-lg border">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-muted-foreground" />
          Change History
          {entries && entries.length > 0 && (
            <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium">{entries.length}</span>
          )}
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>

      {open && (
        <div className="border-t">
          <div className="flex items-center justify-between px-4 pt-2 pb-1">
            <p className="text-xs text-muted-foreground">{entries?.length ?? 0} events</p>
            {entries && entries.length > 0 && (
              <button onClick={exportCsv} className="text-[10px] text-blue-600 hover:underline flex items-center gap-0.5">
                <FileText className="h-3 w-3" /> {t("findings.exportCsv")}
              </button>
            )}
          </div>
          <div className="px-4 pb-4 space-y-3 max-h-80 overflow-y-auto">
            {isLoading && <div className="py-2"><Spinner /></div>}
            {!isLoading && (!entries || entries.length === 0) && (
              <p className="text-xs text-muted-foreground text-center py-4">No history recorded yet.</p>
            )}
            {(entries ?? []).map((e, idx) => {
              const dotColor = ACTION_COLORS[e.action?.toLowerCase()] ?? "bg-slate-300";
              const isFirst = idx === 0;
              const isLast = idx === (entries?.length ?? 0) - 1;
              return (
                <div key={e.id} className="flex items-start gap-3 text-xs">
                  <div className="flex flex-col items-center flex-shrink-0 pt-0.5">
                    <div className={`h-2 w-2 rounded-full ${dotColor}`} />
                    {!isLast && <div className="mt-1 w-px flex-1 bg-border" style={{ minHeight: 16 }} />}
                  </div>
                  <div className="min-w-0 flex-1 pb-1">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="font-semibold capitalize">{e.action}</span>
                      {e.field_name && (
                        <span className="rounded bg-muted px-1 py-0.5 font-mono text-[10px]">{e.field_name}</span>
                      )}
                      <span className="text-muted-foreground text-[10px] ml-auto whitespace-nowrap">
                        {new Date(e.created_at).toLocaleString()}
                      </span>
                    </div>
                    {e.old_value != null && e.new_value != null && (
                      <div className="mt-1 flex items-center gap-1.5 flex-wrap">
                        <span className="rounded bg-red-50 px-1.5 py-0.5 text-red-700 line-through font-mono text-[10px] max-w-[120px] truncate" title={e.old_value}>
                          {e.old_value}
                        </span>
                        <span className="text-muted-foreground">→</span>
                        <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-emerald-700 font-mono text-[10px] max-w-[120px] truncate" title={e.new_value}>
                          {e.new_value}
                        </span>
                      </div>
                    )}
                    <p className="text-muted-foreground/70 mt-0.5">
                      {e.actor_name ?? "System"}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Evidence Drag-Drop ────────────────────────────────────────────────────────

function EvidenceDropZone({ findingId }: { findingId: string }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadedName, setUploadedName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const upload = useCallback(async (file: File) => {
    setUploading(true);
    setUploadedName(null);
    const form = new FormData();
    form.append("file", file);
    form.append("finding_id", findingId);
    try {
      await apiClient.post("/evidence/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadedName(file.name);
      qc.invalidateQueries({ queryKey: ["finding-evidence-links", findingId] });
      setTimeout(() => setUploadedName(null), 3000);
    } catch {
      // silently ignore — backend may not have this endpoint
    } finally {
      setUploading(false);
    }
  }, [findingId, qc]);

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) upload(file);
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-4 text-center transition-colors ${
        isDragging ? "border-blue-400 bg-blue-50" : "border-muted-foreground/20 hover:border-blue-300 hover:bg-muted/30"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); }}
      />
      {uploading ? (
        <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
      ) : uploadedName ? (
        <>
          <CheckCircle2 className="h-5 w-5 text-emerald-500" />
          <p className="text-xs text-emerald-600 font-medium">{uploadedName} uploaded</p>
        </>
      ) : (
        <>
          <Upload className="h-5 w-5 text-muted-foreground/60" />
          <p className="text-xs text-muted-foreground">Drop file here or click to upload evidence</p>
        </>
      )}
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function severityColors(s: string) {
  if (s === "Critical") return { bg: "bg-red-100", text: "text-red-800", dot: "bg-red-500" };
  if (s === "High") return { bg: "bg-orange-100", text: "text-orange-800", dot: "bg-orange-500" };
  if (s === "Medium") return { bg: "bg-amber-100", text: "text-amber-800", dot: "bg-amber-400" };
  return { bg: "bg-slate-100", text: "text-slate-700", dot: "bg-slate-400" };
}

function SeverityBadge({ severity }: { severity: string }) {
  const c = severityColors(severity);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full ${c.bg} ${c.text} px-2.5 py-0.5 text-xs font-semibold`}>
      <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
      {severity}
    </span>
  );
}

function StatusBadge({ status }: { status?: string | null }) {
  if (!status) return null;
  const meta: Record<string, string> = {
    Open: "bg-slate-100 text-slate-700",
    InProgress: "bg-blue-100 text-blue-700",
    Resolved: "bg-amber-100 text-amber-700",
    Verified: "bg-emerald-100 text-emerald-700",
    Dismissed: "bg-slate-100 text-slate-400",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${meta[status] ?? "bg-slate-100 text-slate-600"}`}>
      {status}
    </span>
  );
}

function RiskLevelBadge({ level }: { level: string }) {
  const m: Record<string, string> = {
    Critical: "bg-red-100 text-red-800",
    High: "bg-orange-100 text-orange-800",
    Medium: "bg-amber-100 text-amber-800",
    Low: "bg-emerald-100 text-emerald-800",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${m[level] ?? "bg-slate-100 text-slate-600"}`}>
      {level}
    </span>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function FindingDetailPage() {
  const { t } = useLanguage();
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: finding, isLoading } = useQuery({
    queryKey: ["finding", id],
    queryFn: () => getFinding(id),
    enabled: !!id,
  });

  const { data: evidenceLinks } = useQuery({
    queryKey: ["finding-evidence-links", id],
    queryFn: () => getFindingEvidenceLinks(id),
    enabled: !!id,
  });

  const { data: linkedRisks } = useQuery({
    queryKey: ["finding-risks", id],
    queryFn: () => getFindingLinkedRisks(id),
    enabled: !!id,
  });

  const { data: recommendations } = useQuery({
    queryKey: ["recommendations", finding?.assessment_id],
    queryFn: async () => {
      const res = await apiClient.get(`/recommendations/`, {
        params: { assessment_id: finding!.assessment_id },
      });
      return res.data as Array<{
        id: string; title: string; priority: string; action_status: string; due_date: string | null;
      }>;
    },
    enabled: !!finding?.assessment_id,
  });

  const { data: remediationPlan } = useQuery<{
    id: string; assessment_id: string; status: string;
    actions: { id: string; description: string; status: string; due_date: string | null; assigned_to: string | null }[];
    created_at: string;
  } | null>({
    queryKey: ["remediation-plan", finding?.assessment_id],
    queryFn: async () => {
      try {
        const r = await apiClient.get(`/assessments/${finding!.assessment_id}/remediation`);
        return r.data;
      } catch { return null; }
    },
    enabled: !!finding?.assessment_id,
    retry: false,
  });

  const createRecMutation = useMutation({
    mutationFn: async () => {
      if (!finding) return;
      await apiClient.post("/recommendations/", {
        title: `Remediate: ${finding.title}`,
        description: `Address finding: ${finding.description}`,
        priority: finding.severity === "Critical" ? "Critical" : finding.severity === "High" ? "High" : "Medium",
        assessment_id: finding.assessment_id,
        action_required: true,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendations", finding?.assessment_id] });
    },
  });

  if (isLoading || !finding) {
    return <div className="flex justify-center py-24"><Spinner size="lg" /></div>;
  }

  const c = severityColors(finding.severity);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* ── Back + Header ─────────────────────────────────────────────────── */}
      <div>
        <Link
          href="/findings"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> {t("common.back")} — {t("findings.title")}
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-foreground leading-tight">{finding.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <SeverityBadge severity={finding.severity} />
              <StatusBadge status={(finding as any).status} />
              {finding.category && (
                <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium">
                  {finding.category}
                </span>
              )}
              <span className="text-xs text-muted-foreground">
                Confidence: <span className="font-medium capitalize">{finding.confidence}</span>
              </span>
            </div>
          </div>
          <div className="flex-shrink-0 flex items-center gap-2">
            <CopilotDrawer
              contextType="finding"
              contextId={finding.id}
              contextSummary={`${finding.severity} finding: ${finding.title}`}
            />
            <Button
              size="sm"
              variant="outline"
              onClick={() => createRecMutation.mutate()}
              disabled={createRecMutation.isPending}
              className="gap-1.5"
            >
              <Zap className="h-3.5 w-3.5" />
              {t("findings.createRecommendation")}
            </Button>
            {finding.assessment_id && (
              <Button size="sm" variant="ghost" asChild>
                <Link href={`/assessments/${finding.assessment_id}`} className="gap-1.5">
                  <FileText className="h-3.5 w-3.5" /> {t("findings.assessment")}
                </Link>
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* ── Main Column ─────────────────────────────────────────────────── */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-blue-500" />
                {t("common.description")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-foreground leading-relaxed">{finding.description}</p>
              {finding.reasoning && (
                <div className="border-l-2 border-blue-300 pl-4">
                  <p className="text-xs font-semibold text-muted-foreground mb-1">Reasoning</p>
                  <p className="text-sm text-muted-foreground italic">{finding.reasoning}</p>
                </div>
              )}
              {finding.uncertainty && (
                <div className="border-l-2 border-amber-300 pl-4">
                  <p className="text-xs font-semibold text-muted-foreground mb-1">Uncertainty</p>
                  <p className="text-sm text-muted-foreground italic">{finding.uncertainty}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Linked Risks */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-orange-500" />
                {t("nav.risks")}
                {linkedRisks && linkedRisks.length > 0 && (
                  <span className="rounded-full bg-orange-100 text-orange-700 px-2 py-0.5 text-xs font-semibold">
                    {linkedRisks.length}
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!linkedRisks || linkedRisks.length === 0 ? (
                <div className="py-6 text-center">
                  <ShieldAlert className="mx-auto h-8 w-8 text-muted-foreground/30 mb-2" />
                  <p className="text-sm text-muted-foreground">{t("risks.noRisks")}</p>
                  {finding.assessment_id && (
                    <Link
                      href={`/assessments/${finding.assessment_id}?tab=risks`}
                      className="mt-2 inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                    >
                      View assessment risks <ArrowLeft className="h-3 w-3 rotate-180" />
                    </Link>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  {linkedRisks.map((risk) => (
                    <Link
                      key={risk.id}
                      href={`/risks/${risk.id}`}
                      className="flex items-start justify-between gap-3 rounded-lg border border-border px-3 py-2.5 hover:bg-muted/40 transition-colors"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">{risk.title}</p>
                        {risk.description && (
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{risk.description}</p>
                        )}
                        {risk.category && (
                          <span className="mt-1 inline-block rounded bg-secondary px-1.5 py-0.5 text-[10px]">{risk.category}</span>
                        )}
                      </div>
                      <RiskLevelBadge level={risk.risk_level} />
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recommendations (Remediation) */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                {t("findings.createRecommendation")}
              </CardTitle>
              <Button
                size="sm"
                variant="outline"
                onClick={() => createRecMutation.mutate()}
                disabled={createRecMutation.isPending}
                className="gap-1.5 text-xs"
              >
                <Zap className="h-3 w-3" /> {t("common.new")}
              </Button>
            </CardHeader>
            <CardContent>
              {!recommendations || recommendations.length === 0 ? (
                <div className="py-6 text-center">
                  <CheckCircle2 className="mx-auto h-8 w-8 text-muted-foreground/30 mb-2" />
                  <p className="text-sm text-muted-foreground">{t("recommendations.noRecommendations")}</p>
                  <button
                    onClick={() => createRecMutation.mutate()}
                    className="mt-2 text-xs text-blue-600 hover:underline"
                  >
                    {t("findings.createRecommendation")} →
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {recommendations.map((rec) => {
                    const statusCls: Record<string, string> = {
                      open: "bg-slate-100 text-slate-700",
                      in_progress: "bg-blue-100 text-blue-700",
                      resolved: "bg-amber-100 text-amber-700",
                      verified: "bg-emerald-100 text-emerald-700",
                    };
                    const priorityCls: Record<string, string> = {
                      Critical: "text-red-600",
                      High: "text-orange-600",
                      Medium: "text-amber-600",
                      Low: "text-slate-600",
                    };
                    return (
                      <Link
                        key={rec.id}
                        href="/recommendations"
                        className="flex items-start justify-between gap-3 rounded-lg border border-border px-3 py-2.5 hover:bg-muted/40 transition-colors"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium truncate">{rec.title}</p>
                          {rec.due_date && (
                            <p className="text-xs text-muted-foreground mt-0.5">{t("findings.dueDate")}: {formatDate(rec.due_date)}</p>
                          )}
                        </div>
                        <div className="flex flex-col items-end gap-1 flex-shrink-0">
                          <span className={`text-xs font-semibold ${priorityCls[rec.priority] ?? "text-slate-600"}`}>
                            {rec.priority}
                          </span>
                          <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${statusCls[rec.action_status] ?? "bg-slate-100 text-slate-600"}`}>
                            {rec.action_status}
                          </span>
                        </div>
                      </Link>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ── Sidebar ─────────────────────────────────────────────────────── */}
        <div className="space-y-6">
          {/* Evidence links */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Link2 className="h-4 w-4 text-violet-500" />
                {t("evidence.title")}
                {evidenceLinks && evidenceLinks.length > 0 && (
                  <span className="rounded-full bg-violet-100 text-violet-700 px-2 py-0.5 text-xs font-semibold">
                    {evidenceLinks.length}
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {finding.evidence_strength && (
                <div className="mb-3 rounded-lg bg-muted/50 px-3 py-2 flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Strength</span>
                  <span className={`text-xs font-semibold ${
                    finding.evidence_strength === "Very Strong" ? "text-emerald-600"
                    : finding.evidence_strength === "Strong" ? "text-blue-600"
                    : finding.evidence_strength === "Moderate" ? "text-amber-600"
                    : "text-slate-500"
                  }`}>
                    {finding.evidence_strength}
                  </span>
                </div>
              )}
              <EvidenceDropZone findingId={id} />
              {!evidenceLinks || evidenceLinks.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4">{t("evidence.noEvidence")}</p>
              ) : (
                <div className="space-y-2">
                  {evidenceLinks.map((link) => (
                    <div
                      key={link.id}
                      className="rounded-lg border border-border p-2.5 space-y-1"
                    >
                      {link.supporting_excerpt && (
                        <p className="text-xs text-muted-foreground italic line-clamp-3">
                          &ldquo;{link.supporting_excerpt}&rdquo;
                        </p>
                      )}
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                          {link.link_method}
                        </span>
                        {link.confidence_score != null && (
                          <span className="text-[10px] text-muted-foreground">
                            {Math.round(link.confidence_score * 100)}% conf.
                          </span>
                        )}
                      </div>
                      {link.page_number != null && (
                        <p className="text-[10px] text-muted-foreground">Page {link.page_number}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Metadata */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-muted-foreground">{t("common.details")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("common.severity")}</span>
                <SeverityBadge severity={finding.severity} />
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Confidence</span>
                <span className="font-medium capitalize">{finding.confidence}</span>
              </div>
              {finding.category && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t("common.category")}</span>
                  <span className="font-medium">{finding.category}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("evidence.title")}</span>
                <span className="font-medium">{finding.evidence_source_count}</span>
              </div>
              {finding.assessment_id && (
                <div className="pt-2 border-t border-border">
                  <Link
                    href={`/assessments/${finding.assessment_id}`}
                    className="flex items-center gap-1.5 text-xs text-blue-600 hover:underline"
                  >
                    <FileText className="h-3.5 w-3.5" />
                    {t("common.view")} {t("findings.assessment")}
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>

          {/* #91 Remediation Plan card */}
          {remediationPlan && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  {t("esgOs.remediationPlan")}
                  <span className={`ml-auto rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                    remediationPlan.status === "completed" ? "bg-emerald-100 text-emerald-700" :
                    remediationPlan.status === "in_progress" ? "bg-blue-100 text-blue-700" :
                    "bg-slate-100 text-slate-600"
                  }`}>{remediationPlan.status}</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 pt-0">
                {remediationPlan.actions.length === 0 ? (
                  <p className="text-xs text-muted-foreground">{t("common.noData")}</p>
                ) : (
                  <>
                    {/* #92 Progress tracker */}
                    {(() => {
                      const done = remediationPlan.actions.filter((a) => a.status === "completed").length;
                      const pct = Math.round((done / remediationPlan.actions.length) * 100);
                      return (
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs text-muted-foreground">
                            <span>{done}/{remediationPlan.actions.length} actions complete</span>
                            <span className="font-semibold">{pct}%</span>
                          </div>
                          <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                            <div className={`h-full rounded-full ${pct === 100 ? "bg-emerald-500" : "bg-blue-500"}`} style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })()}
                    {remediationPlan.actions.slice(0, 4).map((a) => (
                      <div key={a.id} className="flex items-start gap-2 text-xs">
                        <span className={`mt-0.5 h-2 w-2 flex-shrink-0 rounded-full ${a.status === "completed" ? "bg-emerald-500" : "bg-muted-foreground/30"}`} />
                        <span className={`flex-1 ${a.status === "completed" ? "line-through text-muted-foreground" : ""}`}>{a.description}</span>
                      </div>
                    ))}
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {/* Audit Trail */}
          <AuditTrailPanel entityId={id} />

          {/* #84 Ask Knowledge Base */}
          <AskKBButton contextQuery={finding.title} />

          {/* Quick actions */}
          <div className="space-y-2">
            <Button variant="outline" size="sm" className="w-full gap-1.5" asChild>
              <Link href="/findings">
                <AlertTriangle className="h-3.5 w-3.5" /> {t("findings.title")}
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
