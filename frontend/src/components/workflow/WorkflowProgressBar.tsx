"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, Circle, AlertCircle, ChevronRight } from "lucide-react";
import { getWorkflowContext, type WorkflowStepResponse } from "@/lib/api/workflow";
import { Spinner } from "@/components/ui/spinner";

interface Props {
  entityType: string;
  entityId: string;
}

const STEP_ICONS: Record<string, string> = {
  supplier: "🏭",
  assessment: "📋",
  finding: "🔍",
  risk: "⚠️",
  recommendation: "💡",
  cap: "✅",
};

function StepNode({ step, isLast }: { step: WorkflowStepResponse; isLast: boolean }) {
  const isDone = step.status === "done";
  const isPartial = step.status === "partial";
  const isMissing = step.status === "missing";
  const isCurrent = step.current;

  const dotCls = isCurrent
    ? "bg-blue-600 ring-2 ring-blue-200 text-white"
    : isDone
    ? "bg-emerald-500 text-white"
    : isPartial
    ? "bg-amber-400 text-white"
    : "bg-muted-foreground/20 text-muted-foreground";

  const labelCls = isCurrent
    ? "text-blue-700 font-semibold"
    : isDone
    ? "text-foreground font-medium"
    : "text-muted-foreground";

  const countCls = isDone
    ? "bg-emerald-100 text-emerald-700"
    : isPartial
    ? "bg-amber-100 text-amber-700"
    : isCurrent
    ? "bg-blue-100 text-blue-700"
    : "bg-muted text-muted-foreground";

  const nodeContent = (
    <div className="flex flex-col items-center gap-1 min-w-0">
      <div className={`h-7 w-7 rounded-full flex items-center justify-center text-xs flex-shrink-0 transition-all ${dotCls}`}>
        {isDone && !isCurrent ? (
          <CheckCircle2 className="h-4 w-4" />
        ) : isMissing && !isCurrent ? (
          <Circle className="h-3.5 w-3.5" />
        ) : (
          <span>{STEP_ICONS[step.key] ?? "•"}</span>
        )}
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <span className={`text-[11px] whitespace-nowrap ${labelCls}`}>{step.label}</span>
        {step.count > 0 && (
          <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${countCls}`}>
            {step.count}
          </span>
        )}
      </div>
    </div>
  );

  return (
    <div className="flex items-start gap-0">
      <div className="flex flex-col items-center">
        {step.route && !isCurrent ? (
          <Link href={step.route} className="hover:opacity-80 transition-opacity">
            {nodeContent}
          </Link>
        ) : (
          nodeContent
        )}
      </div>
      {!isLast && (
        <div className={`mt-3.5 h-px flex-1 min-w-[20px] mx-1 ${isDone ? "bg-emerald-300" : "bg-border"}`} />
      )}
    </div>
  );
}

export function WorkflowProgressBar({ entityType, entityId }: Props) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["workflow-context", entityType, entityId],
    queryFn: () => getWorkflowContext(entityType, entityId),
    staleTime: 30_000,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/20 px-4 py-2.5 text-xs text-muted-foreground">
        <Spinner size="sm" />
        <span>Lade Workflow-Kontext…</span>
      </div>
    );
  }

  if (isError || !data) return null;

  return (
    <div className="rounded-lg border border-border bg-card shadow-sm">
      {/* Header row */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            {data.workflow_name}
          </span>
          {data.supplier_name && (
            <>
              <ChevronRight className="h-3 w-3 text-muted-foreground/50" />
              <span className="text-xs text-muted-foreground">{data.supplier_name}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-24 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                data.completion_pct === 100 ? "bg-emerald-500" : "bg-blue-500"
              }`}
              style={{ width: `${data.completion_pct}%` }}
            />
          </div>
          <span className="text-[11px] font-semibold text-muted-foreground">
            {data.completion_pct}%
          </span>
        </div>
      </div>

      {/* Steps */}
      <div className="flex items-start px-4 py-3 overflow-x-auto">
        {data.steps.map((step, idx) => (
          <StepNode key={step.key} step={step} isLast={idx === data.steps.length - 1} />
        ))}
      </div>

      {/* Next action CTA */}
      {data.next_step?.next_action_route && (
        <div className="border-t border-border px-4 py-2.5 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <AlertCircle className="h-3.5 w-3.5 text-amber-500" />
            <span>Nächster Schritt:</span>
            <span className="font-medium text-foreground">{data.next_step.next_action_label}</span>
          </div>
          <Link
            href={data.next_step.next_action_route}
            className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-blue-700 transition-colors"
          >
            {data.next_step.next_action_label}
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      )}
    </div>
  );
}
