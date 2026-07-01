"use client";

import { useState, useRef, useCallback } from "react";
import { useLanguage } from "@/lib/i18n/context";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  Printer,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
  Loader2,
  Shield,
  Upload,
  User,
  Zap,
} from "lucide-react";
import { getRisk, getRiskLinkedFindings, patchRisk } from "@/lib/api/risks";
import apiClient from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";
import { CopilotDrawer } from "@/components/copilot-drawer";
import { AskKBButton } from "@/components/layout/knowledge-search";

// ── #56 Audit Trail ──────────────────────────────────────────────────────────

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
    queryKey: ["audit-trail", "risk", entityId],
    queryFn: async () => {
      const r = await apiClient.get(`/risks/${entityId}/activity`);
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

// ── #57 Evidence Drag-Drop ────────────────────────────────────────────────────

function EvidenceDropZone({ riskId }: { riskId: string }) {
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
    form.append("risk_id", riskId);
    try {
      await apiClient.post("/evidence/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadedName(file.name);
      qc.invalidateQueries({ queryKey: ["risk-evidence", riskId] });
      setTimeout(() => setUploadedName(null), 3000);
    } catch { /* silently ignore */ }
    finally { setUploading(false); }
  }, [riskId, qc]);

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

const RISK_LEVEL_COLORS: Record<string, string> = {
  Critical: "bg-red-100 text-red-800",
  High:     "bg-orange-100 text-orange-800",
  Medium:   "bg-amber-100 text-amber-800",
  Low:      "bg-emerald-100 text-emerald-800",
};

const STATUS_COLORS: Record<string, string> = {
  Active:   "bg-blue-100 text-blue-700",
  Reviewed: "bg-violet-100 text-violet-700",
  Archived: "bg-slate-100 text-slate-500",
};

function RiskLevelBadge({ level }: { level: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${RISK_LEVEL_COLORS[level] ?? "bg-slate-100 text-slate-600"}`}>
      {level}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_COLORS[status] ?? "bg-slate-100 text-slate-600"}`}>
      {status}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const m: Record<string, string> = {
    Critical: "bg-red-100 text-red-700",
    High:     "bg-orange-100 text-orange-700",
    Medium:   "bg-amber-100 text-amber-700",
    Low:      "bg-slate-100 text-slate-600",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${m[severity] ?? "bg-slate-100 text-slate-600"}`}>
      {severity}
    </span>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function RiskDetailPage() {
  const { t } = useLanguage();
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [ownerInput, setOwnerInput] = useState("");
  const [editingOwner, setEditingOwner] = useState(false);

  const { data: risk, isLoading } = useQuery({
    queryKey: ["risk", id],
    queryFn: () => getRisk(id),
    enabled: !!id,
  });

  const { data: linkedFindings } = useQuery({
    queryKey: ["risk-findings", id],
    queryFn: () => getRiskLinkedFindings(id),
    enabled: !!id,
  });

  const { data: recommendations } = useQuery({
    queryKey: ["recommendations", risk?.assessment_id],
    queryFn: async () => {
      const res = await apiClient.get("/recommendations/", {
        params: { assessment_id: risk!.assessment_id },
      });
      return res.data as Array<{
        id: string; title: string; priority: string; action_status: string; due_date: string | null;
      }>;
    },
    enabled: !!risk?.assessment_id,
  });

  const patchMutation = useMutation({
    mutationFn: (patch: { status?: string; risk_level?: string; owner?: string }) =>
      patchRisk(id, patch),
    onSuccess: async (_, patch) => {
      queryClient.invalidateQueries({ queryKey: ["risk", id] });
      setEditingOwner(false);
      // #153 Auto-notify assignee when risk status changes
      if (patch.status) {
        try {
          const stored = JSON.parse(localStorage.getItem("eios_automation_rules") ?? "{}");
          if (stored?.risk_status_notify?.enabled !== false) {
            await apiClient.post(`/automations/trigger`, {
              rule_id: "risk_status_notify",
              entity_type: "risk",
              entity_id: id,
              payload: { new_status: patch.status },
            });
          }
        } catch { /* silent */ }
      }
      // #158 Teams notification when risk escalated to Critical
      if (patch.risk_level === "Critical") {
        try {
          const stored = JSON.parse(localStorage.getItem("eios_automation_rules") ?? "{}");
          if (stored?.critical_risk_teams?.enabled !== false) {
            await apiClient.post(`/automations/trigger`, {
              rule_id: "critical_risk_teams",
              entity_type: "risk",
              entity_id: id,
              payload: {
                include_supplier: stored?.critical_risk_teams?.config?.include_supplier ?? true,
                include_link: stored?.critical_risk_teams?.config?.include_link ?? true,
              },
            });
          }
        } catch { /* silent */ }
      }
    },
  });

  const createRecMutation = useMutation({
    mutationFn: async () => {
      if (!risk) return;
      await apiClient.post("/recommendations/", {
        title: `Mitigate: ${risk.title}`,
        description: `Address risk: ${risk.description}`,
        priority: risk.risk_level === "Critical" ? "Critical" : risk.risk_level === "High" ? "High" : "Medium",
        assessment_id: risk.assessment_id,
        action_required: true,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recommendations", risk?.assessment_id] });
    },
  });

  if (isLoading || !risk) {
    return <div className="flex justify-center py-24"><Spinner size="lg" /></div>;
  }

  const probabilityPct = risk.probability != null ? Math.round(risk.probability * 100) : null;
  const impactPct = risk.impact != null ? Math.round(risk.impact * 100) : null;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* ── Back + Header ─────────────────────────────────────────────────── */}
      <div>
        <Link
          href="/risks"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> {t("common.back")}
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-foreground leading-tight">{risk.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <RiskLevelBadge level={risk.risk_level} />
              <StatusBadge status={risk.status} />
              {risk.category && (
                <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium">{risk.category}</span>
              )}
              {risk.owner && (
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <User className="h-3 w-3" /> {risk.owner}
                </span>
              )}
            </div>
          </div>
          <div className="flex-shrink-0 flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => window.print()} className="gap-1.5 print:hidden">
              <Printer className="h-3.5 w-3.5" /> Export PDF
            </Button>
            <CopilotDrawer
              contextType="risk"
              contextId={risk.id}
              contextSummary={`${risk.risk_level} risk: ${risk.title}`}
            />
            {risk.risk_level !== "Critical" && (
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 border-orange-300 text-orange-700 hover:bg-orange-50"
                onClick={() => patchMutation.mutate({ risk_level: "Critical" })}
                disabled={patchMutation.isPending}
              >
                <ChevronUp className="h-3.5 w-3.5" /> Escalate
              </Button>
            )}
            {risk.status !== "Reviewed" && risk.status !== "Verified" && (
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5"
                onClick={() => patchMutation.mutate({ status: "Reviewed" })}
                disabled={patchMutation.isPending}
              >
                <CheckCircle2 className="h-3.5 w-3.5" /> Mark Reviewed
              </Button>
            )}
            {risk.status === "Reviewed" && (
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                onClick={() => patchMutation.mutate({ status: "Verified" })}
                disabled={patchMutation.isPending}
              >
                <CheckCircle2 className="h-3.5 w-3.5" /> Verify Mitigation
              </Button>
            )}
            {risk.assessment_id && (
              <Button size="sm" variant="ghost" asChild>
                <Link href={`/assessments/${risk.assessment_id}`} className="gap-1.5">
                  <FileText className="h-3.5 w-3.5" /> {t("risks.assessment")}
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
              <p className="text-sm text-foreground leading-relaxed">{risk.description}</p>
              {risk.reasoning && (
                <div className="border-l-2 border-blue-300 pl-4">
                  <p className="text-xs font-semibold text-muted-foreground mb-1">Reasoning</p>
                  <p className="text-sm text-muted-foreground italic">{risk.reasoning}</p>
                </div>
              )}
              {risk.uncertainty && (
                <div className="border-l-2 border-amber-300 pl-4">
                  <p className="text-xs font-semibold text-muted-foreground mb-1">Uncertainty</p>
                  <p className="text-sm text-muted-foreground italic">{risk.uncertainty}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Linked Findings */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
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
                  <AlertTriangle className="mx-auto h-8 w-8 text-muted-foreground/30 mb-2" />
                  <p className="text-sm text-muted-foreground">No findings linked to this risk.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {linkedFindings.map((finding) => (
                    <Link
                      key={finding.id}
                      href={`/findings/${finding.id}`}
                      className="flex items-start justify-between gap-3 rounded-lg border border-border px-3 py-2.5 hover:bg-muted/40 transition-colors"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">{finding.title}</p>
                        {finding.description && (
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{finding.description}</p>
                        )}
                      </div>
                      <SeverityBadge severity={finding.severity} />
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* #57 Evidence upload drop zone */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Upload className="h-4 w-4 text-blue-500" />
                {t("nav.evidence")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <EvidenceDropZone riskId={id} />
            </CardContent>
          </Card>

          {/* Mitigation Actions (Recommendations) */}
          <Card>
            <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base flex items-center gap-2">
                <Zap className="h-4 w-4 text-emerald-500" />
                Mitigation Actions
              </CardTitle>
              <Button
                size="sm"
                variant="outline"
                onClick={() => createRecMutation.mutate()}
                disabled={createRecMutation.isPending}
                className="gap-1.5 text-xs"
              >
                <Zap className="h-3 w-3" /> New Action
              </Button>
            </CardHeader>
            <CardContent>
              {!recommendations || recommendations.length === 0 ? (
                <div className="py-6 text-center">
                  <Zap className="mx-auto h-8 w-8 text-muted-foreground/30 mb-2" />
                  <p className="text-sm text-muted-foreground">No mitigation actions yet.</p>
                  <button
                    onClick={() => createRecMutation.mutate()}
                    className="mt-2 text-xs text-blue-600 hover:underline"
                  >
                    Create the first action →
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
                            <p className="text-xs text-muted-foreground mt-0.5">Due {formatDate(rec.due_date)}</p>
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
          {/* Status controls */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
                <Shield className="h-4 w-4" /> Risk Controls
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Status */}
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5">{t("common.status")}</p>
                <div className="flex gap-1.5 flex-wrap">
                  {(["Active", "Reviewed", "Verified", "Archived"] as const).map((s) => (
                    <button
                      key={s}
                      onClick={() => patchMutation.mutate({ status: s })}
                      disabled={patchMutation.isPending || risk.status === s}
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors ${
                        risk.status === s
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-border text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              {/* Risk Level */}
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5">{t("risks.riskLevel")}</p>
                <div className="flex gap-1.5 flex-wrap">
                  {(["Critical", "High", "Medium", "Low"] as const).map((l) => (
                    <button
                      key={l}
                      onClick={() => patchMutation.mutate({ risk_level: l })}
                      disabled={patchMutation.isPending || risk.risk_level === l}
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors ${
                        risk.risk_level === l
                          ? `${RISK_LEVEL_COLORS[l]} border-current`
                          : "border-border text-muted-foreground hover:bg-muted"
                      }`}
                    >
                      {l}
                    </button>
                  ))}
                </div>
              </div>

              {/* Owner */}
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5">Owner</p>
                {editingOwner ? (
                  <div className="flex gap-2">
                    <Input
                      value={ownerInput}
                      onChange={(e) => setOwnerInput(e.target.value)}
                      placeholder="Name or email"
                      className="h-7 text-xs"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") patchMutation.mutate({ owner: ownerInput });
                        if (e.key === "Escape") setEditingOwner(false);
                      }}
                    />
                    <Button
                      size="sm"
                      className="h-7 px-2 text-xs"
                      onClick={() => patchMutation.mutate({ owner: ownerInput })}
                      disabled={patchMutation.isPending}
                    >
                      {t("common.save")}
                    </Button>
                  </div>
                ) : (
                  <button
                    onClick={() => { setOwnerInput(risk.owner ?? ""); setEditingOwner(true); }}
                    className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <User className="h-3.5 w-3.5" />
                    {risk.owner ?? "Assign owner…"}
                  </button>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Risk metrics */}
          {(probabilityPct != null || impactPct != null) && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-muted-foreground">Risk Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {probabilityPct != null && (
                  <div>
                    <div className="flex justify-between text-xs text-muted-foreground mb-1">
                      <span>Probability</span>
                      <span className="font-semibold text-foreground">{probabilityPct}%</span>
                    </div>
                    <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${probabilityPct >= 70 ? "bg-red-500" : probabilityPct >= 40 ? "bg-amber-400" : "bg-emerald-500"}`}
                        style={{ width: `${probabilityPct}%` }}
                      />
                    </div>
                  </div>
                )}
                {impactPct != null && (
                  <div>
                    <div className="flex justify-between text-xs text-muted-foreground mb-1">
                      <span>Impact</span>
                      <span className="font-semibold text-foreground">{impactPct}%</span>
                    </div>
                    <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${impactPct >= 70 ? "bg-red-500" : impactPct >= 40 ? "bg-amber-400" : "bg-emerald-500"}`}
                        style={{ width: `${impactPct}%` }}
                      />
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Metadata */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-muted-foreground">{t("common.details")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("risks.riskLevel")}</span>
                <RiskLevelBadge level={risk.risk_level} />
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("common.status")}</span>
                <StatusBadge status={risk.status} />
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Confidence</span>
                <span className="font-medium capitalize">{risk.confidence}</span>
              </div>
              {risk.category && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t("common.category")}</span>
                  <span className="font-medium">{risk.category}</span>
                </div>
              )}
              {risk.assessment_id && (
                <div className="pt-2 border-t border-border">
                  <Link
                    href={`/assessments/${risk.assessment_id}`}
                    className="flex items-center gap-1.5 text-xs text-blue-600 hover:underline"
                  >
                    <FileText className="h-3.5 w-3.5" />
                    View parent assessment
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>
          {/* #84 Ask Knowledge Base */}
          <AskKBButton contextQuery={risk?.title} />

          {/* #56 Audit trail */}
          <AuditTrailPanel entityId={id} />
        </div>
      </div>
    </div>
  );
}
