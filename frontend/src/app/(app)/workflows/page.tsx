"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Clock,
  Cpu,
  Loader2,
  PlayCircle,
  RefreshCw,
  XCircle,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { formatDateTime } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface WorkflowTypeInfo {
  workflow_type: string;
  description: string;
  step_count: number;
  agent_sequence: string[];
}

interface WorkflowJob {
  id: string;
  workflow_type: string;
  query: string;
  job_status: string;
  workflow_run_id: string | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

interface WorkflowRunSummary {
  id: string;
  workflow_type: string;
  query: string;
  verdict: string | null;
  overall_risk_level: string | null;
  steps_completed: number;
  total_steps: number;
  total_input_tokens: number;
  total_output_tokens: number;
  finding_count: number;
  risk_count: number;
  recommendation_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}

// ── API ───────────────────────────────────────────────────────────────────────

async function fetchTypes(): Promise<WorkflowTypeInfo[]> {
  return (await apiClient.get("/workflows/types")).data;
}

async function fetchJobs(page = 1): Promise<{ items: WorkflowJob[]; total: number }> {
  return (await apiClient.get(`/workflows/jobs?page=${page}&page_size=20`)).data;
}

async function fetchRuns(page = 1): Promise<{ items: WorkflowRunSummary[]; total: number }> {
  return (await apiClient.get(`/workflows/runs?page=${page}&page_size=20`)).data;
}

async function runWorkflow(payload: { workflow_type: string; query: string }): Promise<WorkflowJob> {
  return (await apiClient.post("/workflows/run", payload)).data;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const WORKFLOW_LABEL_KEYS: Record<string, string> = {
  due_diligence: "workflows.typeDueDiligence",
  quick_scan: "workflows.typeQuickScan",
  evidence_analysis: "workflows.typeEvidenceAnalysis",
  governance_review: "workflows.typeGovernanceReview",
};

const WORKFLOW_ICONS: Record<string, string> = {
  due_diligence: "🔍",
  quick_scan: "⚡",
  evidence_analysis: "📄",
  governance_review: "🏛️",
};

const STATUS_CONFIG: Record<string, { icon: React.ElementType; className: string }> = {
  pending: { icon: Clock, className: "text-amber-600 bg-amber-50 border-amber-200" },
  in_progress: { icon: Loader2, className: "text-blue-600 bg-blue-50 border-blue-200" },
  completed: { icon: CheckCircle2, className: "text-green-600 bg-green-50 border-green-200" },
  failed: { icon: XCircle, className: "text-red-600 bg-red-50 border-red-200" },
  cancelled: { icon: XCircle, className: "text-slate-500 bg-slate-50 border-slate-200" },
};

function JobStatusBadge({ status }: { status: string }) {
  const { t } = useLanguage();
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  const Icon = cfg.icon;
  const labels: Record<string, string> = {
    pending: t("workflows.pending"),
    in_progress: t("workflows.inProgress"),
    completed: t("workflows.completed"),
    failed: t("workflows.failed"),
    cancelled: t("workflows.cancelled"),
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${cfg.className}`}>
      <Icon className={`h-3 w-3 ${status === "in_progress" ? "animate-spin" : ""}`} />
      {labels[status] ?? status}
    </span>
  );
}

const VERDICT_COLOUR: Record<string, string> = {
  COMPLIANT: "text-green-600",
  NON_COMPLIANT: "text-red-600",
  PARTIAL: "text-amber-600",
  INCONCLUSIVE: "text-slate-500",
};

const RISK_COLOUR: Record<string, string> = {
  Critical: "text-red-700 bg-red-50 border-red-200",
  High: "text-orange-700 bg-orange-50 border-orange-200",
  Medium: "text-amber-700 bg-amber-50 border-amber-200",
  Low: "text-green-700 bg-green-50 border-green-200",
};

// ── Main page ─────────────────────────────────────────────────────────────────

const tab_workflow = ["launch", "jobs", "runs"] as const;
type WTab = (typeof tab_workflow)[number];

export default function WorkflowsPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<WTab>("launch");
  const [selectedType, setSelectedType] = useState("");
  const [query, setQuery] = useState("");
  const [submittedJob, setSubmittedJob] = useState<WorkflowJob | null>(null);

  const { data: types = [], isLoading: typesLoading } = useQuery({
    queryKey: ["workflow-types"],
    queryFn: fetchTypes,
    staleTime: 5 * 60_000,
  });

  const { data: jobsPage, isLoading: jobsLoading, refetch: refetchJobs } = useQuery({
    queryKey: ["workflow-jobs"],
    queryFn: () => fetchJobs(),
    refetchInterval: activeTab === "jobs" ? 5_000 : false,
    enabled: activeTab === "jobs",
  });

  const { data: runsPage, isLoading: runsLoading, refetch: refetchRuns } = useQuery({
    queryKey: ["workflow-runs"],
    queryFn: () => fetchRuns(),
    enabled: activeTab === "runs",
    staleTime: 10_000,
  });

  const launch = useMutation({
    mutationFn: runWorkflow,
    onSuccess: (job) => {
      setSubmittedJob(job);
      setQuery("");
      qc.invalidateQueries({ queryKey: ["workflow-jobs"] });
      setActiveTab("jobs");
    },
  });

  const jobs = jobsPage?.items ?? [];
  const runs = runsPage?.items ?? [];

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <PlayCircle className="h-6 w-6 text-primary" />
          {t("workflows.title")}
        </h1>
        <p className="text-muted-foreground text-sm mt-1">{t("workflows.subtitle")}</p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border gap-0">
        {tab_workflow.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab === "launch" ? t("workflows.launch") : tab === "jobs" ? t("workflows.jobsTab") : t("workflows.runsTab")}
          </button>
        ))}
      </div>

      {/* ── Launch tab ── */}
      {activeTab === "launch" && (
        <div className="space-y-6">
          {/* Workflow type cards */}
          {typesLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {types.map((wt) => (
                <button
                  key={wt.workflow_type}
                  onClick={() => setSelectedType(wt.workflow_type)}
                  className={`text-left rounded-xl border p-4 transition-all ${
                    selectedType === wt.workflow_type
                      ? "border-primary bg-primary/5 shadow-sm"
                      : "border-border hover:border-primary/40 hover:bg-muted/30"
                  }`}
                >
                  <div className="text-2xl mb-2">{WORKFLOW_ICONS[wt.workflow_type] ?? "🔄"}</div>
                  <p className="font-semibold text-sm">{WORKFLOW_LABEL_KEYS[wt.workflow_type] ? t(WORKFLOW_LABEL_KEYS[wt.workflow_type] as Parameters<typeof t>[0]) : wt.workflow_type}</p>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{wt.description}</p>
                  <div className="mt-3 flex flex-wrap gap-1">
                    {wt.agent_sequence.map((agent, i) => (
                      <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                        {agent.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Launch form */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{t("workflows.launch")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {!selectedType && (
                <p className="text-sm text-amber-600 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
                  {t("workflows.selectTypePrompt")}
                </p>
              )}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground">{t("workflows.query")} *</label>
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t("workflows.queryPlaceholder")}
                  rows={4}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                />
              </div>
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">{t("workflows.pollNote")}</p>
                <Button
                  onClick={() => launch.mutate({ workflow_type: selectedType, query })}
                  disabled={!selectedType || !query.trim() || launch.isPending}
                  className="gap-1.5"
                >
                  {launch.isPending ? (
                    <><Loader2 className="h-4 w-4 animate-spin" />{t("workflows.running")}</>
                  ) : (
                    <><PlayCircle className="h-4 w-4" />{t("workflows.run")}</>
                  )}
                </Button>
              </div>
              {submittedJob && (
                <div className="rounded-md bg-blue-50 border border-blue-200 px-3 py-2 text-sm text-blue-700">
                  {t("workflows.submitted")}{" "}
                  <span className="font-mono font-semibold">{submittedJob.id.slice(0, 12)}…</span>
                  {" — "}
                  <button
                    className="underline hover:no-underline"
                    onClick={() => { setActiveTab("jobs"); setSubmittedJob(null); }}
                  >
                    {t("workflows.viewJobsLink")}
                  </button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── Jobs tab ── */}
      {activeTab === "jobs" && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button variant="outline" size="sm" onClick={() => refetchJobs()} className="gap-1.5">
              <RefreshCw className="h-4 w-4" /> {t("workflows.refresh")}
            </Button>
          </div>
          {jobsLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : jobs.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground text-sm">{t("workflows.noJobs")}</div>
          ) : (
            <Card>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="px-4 py-3 font-medium text-muted-foreground">{t("workflows.typeLabel")}</th>
                      <th className="px-4 py-3 font-medium text-muted-foreground">{t("workflows.queryLabel")}</th>
                      <th className="px-4 py-3 font-medium text-muted-foreground">{t("workflows.jobStatus")}</th>
                      <th className="px-4 py-3 font-medium text-muted-foreground">{t("workflows.createdAt")}</th>
                      <th className="px-4 py-3 w-10" />
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.map((job) => (
                      <tr key={job.id} className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors">
                        <td className="px-4 py-3">
                          <span className="font-medium">
                            {WORKFLOW_ICONS[job.workflow_type] ?? "🔄"}{" "}
                            {WORKFLOW_LABEL_KEYS[job.workflow_type] ? t(WORKFLOW_LABEL_KEYS[job.workflow_type] as Parameters<typeof t>[0]) : job.workflow_type}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground max-w-xs">
                          <p className="truncate">{job.query}</p>
                        </td>
                        <td className="px-4 py-3">
                          <JobStatusBadge status={job.job_status} />
                          {job.error && (
                            <p className="text-xs text-red-500 mt-1 max-w-[200px] truncate">{job.error}</p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground text-xs">
                          {formatDateTime(job.created_at)}
                        </td>
                        <td className="px-4 py-3">
                          {job.workflow_run_id && (
                            <Link
                              href={`/workflows/${job.workflow_run_id}`}
                              className="inline-flex items-center gap-1 text-primary hover:underline text-xs"
                            >
                              {t("workflows.viewRun")} <ChevronRight className="h-3 w-3" />
                            </Link>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ── Runs tab ── */}
      {activeTab === "runs" && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button variant="outline" size="sm" onClick={() => refetchRuns()} className="gap-1.5">
              <RefreshCw className="h-4 w-4" /> {t("workflows.refresh")}
            </Button>
          </div>
          {runsLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : runs.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground text-sm">{t("workflows.noRuns")}</div>
          ) : (
            <div className="space-y-3">
              {runs.map((run) => (
                <RunCard key={run.id} run={run} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RunCard({ run }: { run: WorkflowRunSummary }) {
  const { t } = useLanguage();
  const verdictCls = VERDICT_COLOUR[run.verdict ?? ""] ?? "text-slate-500";
  const riskCls = RISK_COLOUR[run.overall_risk_level ?? ""] ?? "text-slate-500 bg-slate-50 border-slate-200";

  return (
    <Card className="hover:shadow-sm transition-shadow">
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0 space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-sm">
                {WORKFLOW_ICONS[run.workflow_type] ?? "🔄"}{" "}
                {WORKFLOW_LABEL_KEYS[run.workflow_type] ? t(WORKFLOW_LABEL_KEYS[run.workflow_type] as Parameters<typeof t>[0]) : run.workflow_type}
              </span>
              {run.verdict && (
                <span className={`text-xs font-semibold ${verdictCls}`}>
                  · {run.verdict}
                </span>
              )}
              {run.overall_risk_level && (
                <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${riskCls}`}>
                  {run.overall_risk_level}
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground truncate max-w-xl">{run.query}</p>
            <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
              <span>{t("workflows.stepsCompleted")}: <strong className="text-foreground">{run.steps_completed}/{run.total_steps}</strong></span>
              <span>{t("workflows.findings")}: <strong className="text-foreground">{run.finding_count}</strong></span>
              <span>{t("workflows.risks")}: <strong className="text-foreground">{run.risk_count}</strong></span>
              <span>{t("workflows.recommendations")}: <strong className="text-foreground">{run.recommendation_count}</strong></span>
              <span>{t("workflows.tokens")}: <strong className="text-foreground">{(run.total_input_tokens + run.total_output_tokens).toLocaleString()}</strong></span>
              <span>{formatDateTime(run.created_at)}</span>
            </div>
          </div>
          <Link
            href={`/workflows/${run.id}`}
            className="inline-flex items-center gap-1 text-sm text-primary hover:underline shrink-0"
          >
            <Cpu className="h-4 w-4" />
            {t("workflows.viewRun")}
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
