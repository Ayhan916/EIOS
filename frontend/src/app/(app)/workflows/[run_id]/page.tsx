"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Cpu,
  Loader2,
  XCircle,
  Zap,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { formatDateTime } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentStep {
  agent_run_id: string;
  agent_type: string;
  step_index: number;
  status: string;
  input_tokens: number;
  output_tokens: number;
  error: string | null;
}

interface WorkflowRun {
  id: string;
  workflow_type: string;
  query: string;
  verdict: string | null;
  verdict_reasoning: string | null;
  overall_risk_level: string | null;
  steps_completed: number;
  total_steps: number;
  total_input_tokens: number;
  total_output_tokens: number;
  error: string | null;
  finding_count: number;
  risk_count: number;
  recommendation_count: number;
  status: string;
  created_at: string;
  updated_at: string;
  steps: AgentStep[];
}

interface StepOutput {
  agent_run_id: string;
  agent_type: string;
  step_index: number;
  content: string | null;
  confidence: number | null;
  reasoning: string | null;
  input_tokens: number;
  output_tokens: number;
  llm_provider: string | null;
  llm_model: string | null;
  error: string | null;
}

// ── API ───────────────────────────────────────────────────────────────────────

async function fetchRun(runId: string): Promise<WorkflowRun> {
  return (await apiClient.get(`/workflows/runs/${runId}`)).data;
}

async function fetchStepOutput(runId: string, stepIndex: number): Promise<StepOutput> {
  return (await apiClient.get(`/workflows/runs/${runId}/steps/${stepIndex}/output`)).data;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const WORKFLOW_LABELS: Record<string, string> = {
  due_diligence: "Due Diligence",
  quick_scan: "Quick Scan",
  evidence_analysis: "Evidence Analysis",
  governance_review: "Governance Review",
};

const VERDICT_CONFIG: Record<string, { cls: string }> = {
  COMPLIANT: { cls: "text-green-700 bg-green-50 border-green-300" },
  NON_COMPLIANT: { cls: "text-red-700 bg-red-50 border-red-300" },
  PARTIAL: { cls: "text-amber-700 bg-amber-50 border-amber-300" },
  INCONCLUSIVE: { cls: "text-slate-600 bg-slate-50 border-slate-300" },
};

const RISK_COLOUR: Record<string, string> = {
  Critical: "text-red-700 bg-red-50 border-red-200",
  High: "text-orange-700 bg-orange-50 border-orange-200",
  Medium: "text-amber-700 bg-amber-50 border-amber-200",
  Low: "text-green-700 bg-green-50 border-green-200",
};

const STEP_STATUS: Record<string, { icon: React.ElementType; cls: string }> = {
  pending: { icon: Clock, cls: "text-slate-400" },
  in_progress: { icon: Loader2, cls: "text-blue-500" },
  completed: { icon: CheckCircle2, cls: "text-green-600" },
  failed: { icon: XCircle, cls: "text-red-500" },
};

const AGENT_LABELS: Record<string, string> = {
  research: "Research",
  retrieval: "Knowledge Retrieval",
  reasoning: "Chain-of-Thought Reasoning",
  esg_assessment: "ESG Assessment",
  risk_assessment: "Risk Register",
  recommendation: "Recommendations",
  evaluation: "Quality Evaluation",
  reporting: "Audit Report",
  governance: "Governance Review",
};

// ── Step row with expandable output ──────────────────────────────────────────

function StepRow({ step, runId }: { step: AgentStep; runId: string }) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(false);

  const { data: output, isLoading: outputLoading } = useQuery({
    queryKey: ["step-output", runId, step.step_index],
    queryFn: () => fetchStepOutput(runId, step.step_index),
    enabled: expanded && step.status === "completed",
    staleTime: Infinity,
  });

  const cfg = STEP_STATUS[step.status] ?? STEP_STATUS.pending;
  const Icon = cfg.icon;
  const isCompleted = step.status === "completed";

  return (
    <div className="border-b border-border last:border-0">
      <div className="flex items-center gap-3 px-4 py-3">
        <span className="w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground shrink-0">
          {step.step_index + 1}
        </span>
        <Icon className={`h-4 w-4 shrink-0 ${cfg.cls} ${step.status === "in_progress" ? "animate-spin" : ""}`} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium">{AGENT_LABELS[step.agent_type] ?? step.agent_type.replace(/_/g, " ")}</p>
          <p className="text-xs text-muted-foreground font-mono">{step.agent_type}</p>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground shrink-0">
          <span>{t("workflows.inputTokens")}: {step.input_tokens.toLocaleString()}</span>
          <span>{t("workflows.outputTokens")}: {step.output_tokens.toLocaleString()}</span>
          {step.error && (
            <span className="text-red-500 max-w-[120px] truncate">{step.error}</span>
          )}
        </div>
        {isCompleted && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-0.5 shrink-0"
          >
            {expanded ? <><ChevronUp className="h-3.5 w-3.5" />{t("workflows.hideOutput")}</> : <><ChevronDown className="h-3.5 w-3.5" />{t("workflows.showOutput")}</>}
          </button>
        )}
      </div>

      {expanded && (
        <div className="px-4 pb-4">
          {outputLoading ? (
            <div className="flex items-center gap-2 py-3 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Lade Ausgabe…
            </div>
          ) : output ? (
            <div className="rounded-lg bg-slate-50 border border-slate-200 p-4 space-y-3">
              {output.llm_model && (
                <p className="text-xs text-muted-foreground">
                  {output.llm_provider} · {output.llm_model}
                </p>
              )}
              {output.confidence !== null && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium">{t("workflows.confidence")}:</span>
                  <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden max-w-[120px]">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(output.confidence ?? 0) * 100}%` }} />
                  </div>
                  <span className="font-mono">{((output.confidence ?? 0) * 100).toFixed(0)}%</span>
                </div>
              )}
              {output.reasoning && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-1">{t("workflows.reasoning")}</p>
                  <p className="text-xs text-foreground leading-relaxed">{output.reasoning}</p>
                </div>
              )}
              {output.content && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground mb-1">{t("workflows.stepOutput")}</p>
                  <pre className="text-xs text-foreground leading-relaxed whitespace-pre-wrap font-sans max-h-64 overflow-y-auto">
                    {typeof output.content === "string"
                      ? output.content
                      : JSON.stringify(output.content, null, 2)}
                  </pre>
                </div>
              )}
              {output.error && (
                <p className="text-xs text-red-600 bg-red-50 rounded p-2">{output.error}</p>
              )}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function WorkflowRunPage({ params }: { params: Promise<{ run_id: string }> }) {
  const { run_id } = use(params);
  const { t } = useLanguage();

  const { data: run, isLoading } = useQuery({
    queryKey: ["workflow-run", run_id],
    queryFn: () => fetchRun(run_id),
    refetchInterval: (query) => {
      const data = query.state.data as WorkflowRun | undefined;
      return data?.status === "in_progress" || data?.status === "pending" ? 3_000 : false;
    },
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spinner />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="p-6">
        <Link href="/workflows" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> {t("workflows.backToList")}
        </Link>
        <div className="mt-8 text-center text-muted-foreground">
          <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
          <p>Run not found.</p>
        </div>
      </div>
    );
  }

  const verdictCls = VERDICT_CONFIG[run.verdict ?? ""]?.cls ?? "text-slate-600 bg-slate-50 border-slate-200";
  const riskCls = RISK_COLOUR[run.overall_risk_level ?? ""] ?? "text-slate-500 bg-slate-50 border-slate-200";
  const totalTokens = (run.total_input_tokens + run.total_output_tokens).toLocaleString();

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Back */}
      <Link href="/workflows" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="h-4 w-4" />
        {t("workflows.backToList")}
      </Link>

      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <h1 className="text-xl font-bold">
            {WORKFLOW_LABELS[run.workflow_type] ?? run.workflow_type}
          </h1>
          {run.verdict && (
            <span className={`text-xs px-3 py-1 rounded-full border font-semibold ${verdictCls}`}>
              {run.verdict}
            </span>
          )}
          {run.overall_risk_level && (
            <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${riskCls}`}>
              {run.overall_risk_level}
            </span>
          )}
        </div>
        <p className="text-sm text-muted-foreground max-w-2xl">{run.query}</p>
        <p className="text-xs text-muted-foreground">{formatDateTime(run.created_at)}</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-muted-foreground">{t("workflows.stepsCompleted")}</p>
            <p className="text-2xl font-bold mt-0.5">{run.steps_completed}<span className="text-sm font-normal text-muted-foreground">/{run.total_steps}</span></p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-muted-foreground">{t("workflows.tokens")}</p>
            <p className="text-2xl font-bold mt-0.5">{totalTokens}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-muted-foreground">{t("workflows.findings")} / {t("workflows.risks")}</p>
            <p className="text-2xl font-bold mt-0.5 text-orange-600">{run.finding_count}</p>
            <p className="text-xs text-muted-foreground">{run.risk_count} {t("workflows.risks").toLowerCase()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-xs text-muted-foreground">{t("workflows.recommendations")}</p>
            <p className="text-2xl font-bold mt-0.5 text-blue-600">{run.recommendation_count}</p>
          </CardContent>
        </Card>
      </div>

      {/* Verdict reasoning */}
      {run.verdict_reasoning && (
        <Card className={run.verdict === "NON_COMPLIANT" ? "border-red-200 bg-red-50/30" : run.verdict === "COMPLIANT" ? "border-green-200 bg-green-50/30" : ""}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Zap className="h-4 w-4" />
              {t("workflows.verdict")} Reasoning
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-foreground leading-relaxed">{run.verdict_reasoning}</p>
          </CardContent>
        </Card>
      )}

      {/* Error */}
      {run.error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <p className="font-semibold mb-1">Error</p>
          <p className="font-mono text-xs">{run.error}</p>
        </div>
      )}

      {/* Agent steps */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Cpu className="h-4 w-4 text-muted-foreground" />
            {t("workflows.steps")}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {run.steps.length === 0 ? (
            <p className="text-sm text-muted-foreground px-4 py-6">{t("workflows.noSteps")}</p>
          ) : (
            run.steps.map((step) => (
              <StepRow key={step.step_index} step={step} runId={run.id} />
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
