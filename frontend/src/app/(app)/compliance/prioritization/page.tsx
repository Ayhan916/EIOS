"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ListOrdered,
  RefreshCw,
  AlertTriangle,
  ChevronUp,
  ChevronDown,
  Info,
} from "lucide-react";
import { prioritizationApi, PrioritizationDecision } from "@/lib/api/prioritization";
import { useLanguage } from "@/lib/i18n/context";

// ── Score badge ───────────────────────────────────────────────────────────────

const SCORE_STYLES: Record<string, string> = {
  high: "bg-red-100 text-red-800 border border-red-300 dark:bg-red-900/30 dark:text-red-300",
  medium:
    "bg-amber-100 text-amber-800 border border-amber-300 dark:bg-amber-900/30 dark:text-amber-300",
  low: "bg-emerald-100 text-emerald-800 border border-emerald-300 dark:bg-emerald-900/30 dark:text-emerald-300",
};

function scoreLevel(score: number) {
  if (score >= 2.5) return "high";
  if (score >= 1.5) return "medium";
  return "low";
}

function ScoreBadge({ score }: { score: number }) {
  const level = scoreLevel(score);
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${SCORE_STYLES[level]}`}>
      {score.toFixed(2)}
    </span>
  );
}

// ── Override modal ────────────────────────────────────────────────────────────

interface OverrideModalProps {
  decision: PrioritizationDecision;
  totalSuppliers: number;
  onClose: () => void;
  onSave: (newRank: number, comment: string) => void;
  isPending: boolean;
}

function OverrideModal({
  decision,
  totalSuppliers,
  onClose,
  onSave,
  isPending,
}: OverrideModalProps) {
  const { t } = useLanguage();
  const [newRank, setNewRank] = useState(decision.priority_rank);
  const [comment, setComment] = useState(decision.override_comment ?? "");
  const commentTooShort = comment.trim().length < 10;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-xl bg-white dark:bg-gray-900 shadow-2xl p-6 space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t("prio.overrideTitle").replace("{name}", decision.supplier_name)}
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {t("prio.autoRank").replace("{rank}", String(decision.priority_rank)).replace("{score}", decision.priority_score.toFixed(2))}
        </p>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t("prio.newRankLabel")}
          </label>
          <input
            type="number"
            min={1}
            max={totalSuppliers}
            value={newRank}
            onChange={(e) => setNewRank(Number(e.target.value))}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t("prio.justificationLabel")}{" "}
            <span className="text-rose-500">*</span>{" "}
            <span className="text-gray-400">{t("prio.justificationRequired")}</span>
          </label>
          <textarea
            rows={4}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="e.g. Supplier A is a strategic partner with mitigating contractual controls already in place; risk is lower than the automated score suggests."
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white resize-none"
          />
          {commentTooShort && comment.length > 0 && (
            <p className="mt-1 text-xs text-rose-500">{t("prio.minChars")}</p>
          )}
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            {t("common.cancel")}
          </button>
          <button
            onClick={() => onSave(newRank, comment.trim())}
            disabled={commentTooShort || isPending}
            className="rounded-lg px-4 py-2 text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isPending ? t("prio.saving") : t("prio.saveOverride")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Reasoning popover ─────────────────────────────────────────────────────────

function ReasoningCell({ reasoning }: { reasoning: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-blue-500 hover:text-blue-700"
        title="Show reasoning"
      >
        <Info className="h-4 w-4" />
      </button>
      {open && (
        <div
          className="absolute z-30 left-6 top-0 w-80 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-xl p-3 text-xs text-gray-600 dark:text-gray-300"
          onClick={() => setOpen(false)}
        >
          {reasoning}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PrioritizationPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [capacity, setCapacity] = useState(4);
  const [overrideTarget, setOverrideTarget] = useState<PrioritizationDecision | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["prioritization"],
    queryFn: () => prioritizationApi.getRanking(),
  });

  const computeMutation = useMutation({
    mutationFn: () => prioritizationApi.computeRanking({ resource_capacity_per_quarter: capacity }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prioritization"] }),
  });

  const overrideMutation = useMutation({
    mutationFn: ({ id, rank, comment }: { id: string; rank: number; comment: string }) =>
      prioritizationApi.overrideRank(id, { new_rank: rank, override_comment: comment }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["prioritization"] });
      setOverrideTarget(null);
    },
  });

  const decisions = data?.decisions ?? [];
  const computedAt = data?.computed_at
    ? new Date(data.computed_at).toLocaleString()
    : null;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-orange-100 dark:bg-orange-900/30 p-2">
            <ListOrdered className="h-6 w-6 text-orange-600 dark:text-orange-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              {t("prio.title")}
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {t("prio.subtitle")}
            </p>
          </div>
        </div>

        {/* Compute controls */}
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
            {t("prio.capacityLabel")}
            <input
              type="number"
              min={1}
              max={100}
              value={capacity}
              onChange={(e) => setCapacity(Number(e.target.value))}
              className="w-16 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-sm text-center"
            />
          </label>
          <button
            onClick={() => computeMutation.mutate()}
            disabled={computeMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${computeMutation.isPending ? "animate-spin" : ""}`} />
            {computeMutation.isPending ? t("prio.computing") : t("prio.computeRanking")}
          </button>
        </div>
      </div>

      {/* Last computed */}
      {computedAt && (
        <p className="text-xs text-gray-400">
          {t("prio.lastComputed")
            .replace("{date}", computedAt ?? "")
            .replace("{n}", String(data?.total_suppliers ?? 0))
            .replace("{q}", String(data?.resource_capacity_per_quarter ?? 0))}
        </p>
      )}

      {/* Capacity notice */}
      {decisions.length > 0 && (
        <div className="rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 px-4 py-3 text-sm text-blue-700 dark:text-blue-300 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>
            {t("prio.scheduledNotice")
              .replace("{q}", String(data?.resource_capacity_per_quarter ?? 0))
              .replace("{n}", String(decisions.slice(0, data?.resource_capacity_per_quarter ?? 4).length))}
          </span>
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 dark:bg-rose-900/20 px-4 py-3 text-sm text-rose-700">
          {t("prio.loadError")}
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <div className="text-sm text-gray-400 py-8 text-center">{t("prio.loading")}</div>
      ) : decisions.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 py-16 text-center text-gray-400">
          {t("prio.noRanking")}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800 text-xs uppercase text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-4 py-3 text-left">{t("prio.colRank")}</th>
                <th className="px-4 py-3 text-left">{t("prio.colSupplier")}</th>
                <th className="px-4 py-3 text-center">{t("prio.colScore")}</th>
                <th className="px-4 py-3 text-center">{t("prio.colSeverity")}</th>
                <th className="px-4 py-3 text-center">{t("prio.colProbability")}</th>
                <th className="px-4 py-3 text-center">{t("prio.colScale")}</th>
                <th className="px-4 py-3 text-center">{t("prio.colReasoning")}</th>
                <th className="px-4 py-3 text-center">{t("prio.colOverride")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {decisions.map((d, idx) => {
                const inScope = idx < (data?.resource_capacity_per_quarter ?? 4);
                return (
                  <tr
                    key={d.id}
                    className={
                      inScope
                        ? "bg-blue-50/50 dark:bg-blue-900/10 hover:bg-blue-50 dark:hover:bg-blue-900/20"
                        : "bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                    }
                  >
                    <td className="px-4 py-3 font-bold text-gray-700 dark:text-gray-200 w-12">
                      #{d.priority_rank}
                      {d.overridden_manually && (
                        <span className="ml-1 text-orange-400 text-xs" title="Manually overridden">
                          ★
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                      {d.supplier_name}
                      {inScope && (
                        <span className="ml-2 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 text-xs px-2 py-0.5">
                          {t("prio.qNext")}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <ScoreBadge score={d.priority_score} />
                    </td>
                    <td className="px-4 py-3 text-center text-gray-600 dark:text-gray-400">
                      {d.severity_weight.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-600 dark:text-gray-400">
                      {d.probability_weight.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-600 dark:text-gray-400">
                      {d.people_affected_weight.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <ReasoningCell reasoning={d.reasoning} />
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => setOverrideTarget(d)}
                        className="rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 border border-gray-200 dark:border-gray-700"
                        title="Override rank"
                      >
                        <span className="flex items-center gap-1">
                          <ChevronUp className="h-3 w-3" />
                          <ChevronDown className="h-3 w-3" />
                        </span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Regulation notice */}
      <p className="text-xs text-gray-400 dark:text-gray-500">
        {t("prio.regulationNote")}
      </p>

      {/* Override modal */}
      {overrideTarget && (
        <OverrideModal
          decision={overrideTarget}
          totalSuppliers={decisions.length}
          onClose={() => setOverrideTarget(null)}
          onSave={(rank, comment) =>
            overrideMutation.mutate({ id: overrideTarget.id, rank, comment })
          }
          isPending={overrideMutation.isPending}
        />
      )}
    </div>
  );
}
