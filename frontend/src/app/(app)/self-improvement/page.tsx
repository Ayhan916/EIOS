"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
  TrendingUp,
  XCircle,
  Zap,
} from "lucide-react";
import { selfImprovementApi, ImprovementProposal } from "@/lib/api/self-improvement";
import { useLanguage } from "@/lib/i18n/context";
import { formatDate } from "@/lib/utils";

// ── Status config (no labels — computed inside components) ────────────────────

const STATUS_CONFIG: Record<
  string,
  { color: string; icon: React.ElementType }
> = {
  DRAFT:       { color: "bg-gray-100 text-gray-700 border border-gray-200",       icon: AlertTriangle },
  APPROVED:    { color: "bg-blue-100 text-blue-700 border border-blue-200",       icon: ThumbsUp },
  IN_PROGRESS: { color: "bg-amber-100 text-amber-700 border border-amber-200",    icon: RefreshCw },
  VERIFIED:    { color: "bg-emerald-100 text-emerald-700 border border-emerald-200", icon: CheckCircle2 },
  REJECTED:    { color: "bg-red-100 text-red-700 border border-red-200",          icon: XCircle },
};

const STATUS_TABS = [
  { key: undefined,      labelKey: "selfImprovement.tabAll" },
  { key: "DRAFT",        labelKey: "selfImprovement.statusDraft" },
  { key: "APPROVED",     labelKey: "selfImprovement.statusApproved" },
  { key: "IN_PROGRESS",  labelKey: "selfImprovement.statusInProgress" },
  { key: "VERIFIED",     labelKey: "selfImprovement.statusVerified" },
  { key: "REJECTED",     labelKey: "selfImprovement.statusRejected" },
] as const;

// ── Reject modal ──────────────────────────────────────────────────────────────

function RejectModal({ onConfirm, onCancel }: { onConfirm: (reason: string) => void; onCancel: () => void }) {
  const { t } = useLanguage();
  const [reason, setReason] = useState("");
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="rounded-xl bg-white dark:bg-gray-900 shadow-xl border border-gray-200 dark:border-gray-700 w-full max-w-md p-6 space-y-4">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t("selfImprovement.rejectTitle")}</h3>
        <p className="text-xs text-gray-500">{t("selfImprovement.rejectHint")}</p>
        <textarea
          rows={4}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder={t("selfImprovement.rejectPlaceholder")}
          className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-red-400"
        />
        <div className="flex gap-2 justify-end">
          <button onClick={onCancel} className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
            {t("common.cancel")}
          </button>
          <button
            onClick={() => reason.length >= 10 && onConfirm(reason)}
            disabled={reason.length < 10}
            className="px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
          >
            {t("selfImprovement.rejectBtn")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Proposal card ─────────────────────────────────────────────────────────────

function ProposalCard({
  proposal,
  onApprove,
  onReject,
}: {
  proposal: ImprovementProposal;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const cfg = STATUS_CONFIG[proposal.approval_status] ?? STATUS_CONFIG.DRAFT;
  const StatusIcon = cfg.icon;

  const weaknessLabels: Record<string, string> = {
    LOW_BENCHMARK_ACCURACY:   t("selfImprovement.wkBenchmarkAcc"),
    DECLINING_ACCURACY_TREND: t("selfImprovement.wkAccuracyTrend"),
    HIGH_HALLUCINATION_RATE:  t("selfImprovement.wkHallucinationRate"),
    HIGH_ERROR_RATE:          t("selfImprovement.wkErrorRate"),
    LOW_CONFIDENCE:           t("selfImprovement.wkConfidence"),
    LOW_PLATFORM_HEALTH:      t("selfImprovement.wkPlatformHealth"),
    COST_ANOMALY:             t("selfImprovement.wkCostAnomaly"),
  };

  const statusLabels: Record<string, string> = {
    DRAFT:       t("selfImprovement.statusDraft"),
    APPROVED:    t("selfImprovement.statusApproved"),
    IN_PROGRESS: t("selfImprovement.statusInProgress"),
    VERIFIED:    t("selfImprovement.statusVerified"),
    REJECTED:    t("selfImprovement.statusRejected"),
  };

  const weaknessLabel = weaknessLabels[proposal.weakness_type] ?? proposal.weakness_type;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden">
      {/* Header */}
      <div className="flex items-start gap-3 p-4">
        {/* Priority badge */}
        <div
          className={`shrink-0 rounded-lg px-2 py-1 text-xs font-black tabular-nums ${
            proposal.priority_score >= 7
              ? "bg-red-100 text-red-700"
              : proposal.priority_score >= 4
              ? "bg-amber-100 text-amber-700"
              : "bg-gray-100 text-gray-600"
          }`}
        >
          {proposal.priority_score.toFixed(1)}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-gray-400 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded">
              {weaknessLabel}
            </span>
            <span className="text-xs font-mono text-gray-400">
              {proposal.affected_module}
            </span>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cfg.color}`}>
              <StatusIcon className="inline h-3 w-3 mr-0.5" />
              {statusLabels[proposal.approval_status] ?? proposal.approval_status}
            </span>
          </div>
          <p className="mt-1.5 text-sm font-semibold text-gray-900 dark:text-white leading-snug">
            {proposal.title}
          </p>
          <p className="mt-0.5 text-xs text-gray-500">
            {t("selfImprovement.impact")
              .replace("{n}", (proposal.expected_impact * 100).toFixed(1))
              .replace("{cur}", (proposal.current_value * 100).toFixed(1))
              .replace("{tgt}", (proposal.target_value * 100).toFixed(1))}
            {proposal.weakness_type === "COST_ANOMALY" && (
              <> {t("selfImprovement.impactUsd")}</>
            )}
          </p>
        </div>

        <button
          onClick={() => setExpanded((e) => !e)}
          className="shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-gray-100 dark:border-gray-800 px-4 pb-4 pt-3 space-y-3">
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{t("selfImprovement.descLabel")}</p>
            <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{proposal.description}</p>
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{t("selfImprovement.actionLabel")}</p>
            <pre className="text-xs text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded-lg p-3 whitespace-pre-wrap font-mono leading-relaxed">
              {proposal.suggested_action}
            </pre>
          </div>

          {proposal.verified_improvement !== null && (
            <div className="rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 px-3 py-2">
              <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                {t("selfImprovement.verifiedImprovement").replace("{delta}", `${proposal.verified_improvement > 0 ? "+" : ""}${proposal.verified_improvement.toFixed(1)}`)}
              </p>
              {proposal.verified_at && (
                <p className="text-xs text-emerald-600 dark:text-emerald-500 mt-0.5">
                  {t("selfImprovement.verifiedAt").replace("{date}", formatDate(proposal.verified_at))}
                </p>
              )}
            </div>
          )}

          {proposal.reject_reason && (
            <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 px-3 py-2">
              <p className="text-xs font-semibold text-red-700">{t("selfImprovement.rejectionReason")}</p>
              <p className="text-xs text-red-600 mt-0.5">{proposal.reject_reason}</p>
            </div>
          )}

          {/* Action buttons */}
          {proposal.approval_status === "DRAFT" && (
            <div className="flex gap-2 pt-1">
              <button
                onClick={() => onApprove(proposal.id)}
                className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700"
              >
                <ThumbsUp className="h-3 w-3" />
                {t("selfImprovement.approveBtn")}
              </button>
              <button
                onClick={() => onReject(proposal.id)}
                className="flex items-center gap-1.5 rounded-lg border border-red-300 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
              >
                <ThumbsDown className="h-3 w-3" />
                {t("selfImprovement.rejectBtn")}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SelfImprovementPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<string | undefined>(undefined);
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);

  const { data: summary } = useQuery({
    queryKey: ["self-improvement-summary"],
    queryFn: selfImprovementApi.getSummary,
  });

  const { data: proposals = [], isLoading } = useQuery({
    queryKey: ["self-improvement-proposals", activeTab],
    queryFn: () => selfImprovementApi.listProposals(activeTab),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["self-improvement-proposals"] });
    qc.invalidateQueries({ queryKey: ["self-improvement-summary"] });
  };

  const detectMutation = useMutation({
    mutationFn: selfImprovementApi.detect,
    onSuccess: invalidate,
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => selfImprovementApi.approve(id),
    onSuccess: invalidate,
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      selfImprovementApi.reject(id, reason),
    onSuccess: () => { invalidate(); setRejectTarget(null); },
  });

  const summaryCards = summary ? [
    { labelKey: "selfImprovement.statusDraft", value: summary.open_draft,  color: "text-gray-600" },
    { labelKey: "selfImprovement.statusApproved", value: summary.approved, color: "text-blue-600" },
    { labelKey: "selfImprovement.statusVerified", value: summary.verified, color: "text-emerald-600" },
    { labelKey: "selfImprovement.statusRejected", value: summary.rejected, color: "text-red-500" },
    {
      labelKey: "selfImprovement.healthScore",
      value: summary.latest_health_score !== null ? `${summary.latest_health_score.toFixed(0)}/100` : "—",
      color: summary.latest_health_score !== null && summary.latest_health_score >= 80
        ? "text-emerald-600"
        : summary.latest_health_score !== null && summary.latest_health_score >= 60
        ? "text-amber-600"
        : "text-red-600",
    },
  ] : [];

  return (
    <div className="space-y-6 p-6">
      {rejectTarget && (
        <RejectModal
          onConfirm={(reason) => rejectMutation.mutate({ id: rejectTarget, reason })}
          onCancel={() => setRejectTarget(null)}
        />
      )}

      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-violet-100 dark:bg-violet-900/30 p-2">
            <TrendingUp className="h-6 w-6 text-violet-600 dark:text-violet-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">{t("selfImprovement.title")}</h1>
            <p className="text-xs text-gray-500">{t("selfImprovement.subtitle")}</p>
          </div>
        </div>
        <button
          onClick={() => detectMutation.mutate()}
          disabled={detectMutation.isPending}
          className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-60"
        >
          <Zap className={`h-4 w-4 ${detectMutation.isPending ? "animate-pulse" : ""}`} />
          {detectMutation.isPending ? t("selfImprovement.detecting") : t("selfImprovement.detectBtn")}
        </button>
      </div>

      {/* Detect result banner */}
      {detectMutation.data && (
        <div className={`rounded-xl border px-4 py-3 text-sm ${
          detectMutation.data.proposals_created > 0
            ? "bg-violet-50 dark:bg-violet-900/20 border-violet-200 dark:border-violet-800 text-violet-800 dark:text-violet-300"
            : "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600"
        }`}>
          {detectMutation.data.message}
        </div>
      )}

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {summaryCards.map((s) => (
            <div
              key={s.labelKey}
              className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3 text-center"
            >
              <p className={`text-2xl font-bold tabular-nums ${s.color}`}>{s.value}</p>
              <p className="text-xs text-gray-400 mt-0.5">{t(s.labelKey as Parameters<typeof t>[0])}</p>
            </div>
          ))}
        </div>
      )}

      {/* Status tabs */}
      <div className="flex flex-wrap gap-1 border-b border-gray-200 dark:border-gray-700 pb-2">
        {STATUS_TABS.map((tab) => (
          <button
            key={String(tab.key ?? "all")}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded px-3 py-1.5 text-xs font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-violet-600 text-white"
                : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
            }`}
          >
            {t(tab.labelKey as Parameters<typeof t>[0])}
            {tab.key === "DRAFT" && summary && summary.open_draft > 0 && (
              <span className="ml-1 rounded-full bg-amber-500 text-white text-xs px-1">
                {summary.open_draft}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Proposals list */}
      {isLoading ? (
        <div className="py-10 text-center text-sm text-gray-400">{t("selfImprovement.loading")}</div>
      ) : proposals.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 py-16 text-center">
          <ShieldCheck className="mx-auto h-8 w-8 text-gray-300 mb-3" />
          <p className="text-sm text-gray-400">
            {activeTab
              ? t("selfImprovement.noProposals").replace("{status}", activeTab.toLowerCase())
              : t("selfImprovement.noProposalsAll")}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {proposals.map((p) => (
            <ProposalCard
              key={p.id}
              proposal={p}
              onApprove={(id) => approveMutation.mutate(id)}
              onReject={(id) => setRejectTarget(id)}
            />
          ))}
        </div>
      )}

      <p className="text-xs text-gray-400">
        {t("selfImprovement.humanNote")}
      </p>
    </div>
  );
}
