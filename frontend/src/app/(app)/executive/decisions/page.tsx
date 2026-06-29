"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock, XCircle, Filter } from "lucide-react";
import { useState } from "react";
import Link from "next/link";
import apiClient from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";

// ── #139 Decision Log ─────────────────────────────────────────────────────────

interface DecisionRecord {
  id: string;
  title: string;
  decision: "Approved" | "Rejected" | "ChangesRequested" | string;
  decided_by: string;
  decided_at: string;
  comment?: string;
  priority: string;
  entity_type: string;
}

const DECISION_STYLES: Record<string, { cls: string; icon: React.ElementType; label: string }> = {
  Approved:         { cls: "bg-emerald-100 text-emerald-700", icon: CheckCircle2, label: "Approved" },
  Rejected:         { cls: "bg-red-100 text-red-700",         icon: XCircle,      label: "Rejected" },
  ChangesRequested: { cls: "bg-amber-100 text-amber-700",     icon: Clock,        label: "Changes Requested" },
};

const PRIORITY_COLORS: Record<string, string> = {
  Critical: "text-red-600",
  High:     "text-orange-600",
  Medium:   "text-amber-600",
  Low:      "text-slate-500",
};

export default function DecisionLogPage() {
  const [filter, setFilter] = useState<"all" | "Approved" | "Rejected" | "ChangesRequested">("all");

  const { data, isLoading } = useQuery<DecisionRecord[]>({
    queryKey: ["decision-log"],
    queryFn: async () => {
      const r = await apiClient.get("/api/v1/recommendations/decisions?limit=100");
      return r.data?.items ?? r.data ?? [];
    },
    staleTime: 60_000,
  });

  const decisions = (data ?? []).filter((d) => filter === "all" || d.decision === filter);

  const counts = {
    Approved:         (data ?? []).filter((d) => d.decision === "Approved").length,
    Rejected:         (data ?? []).filter((d) => d.decision === "Rejected").length,
    ChangesRequested: (data ?? []).filter((d) => d.decision === "ChangesRequested").length,
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Decision Log</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Complete history of approved and rejected recommendations
          </p>
        </div>
        <Link href="/recommendations" className="rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition-colors">
          Open Recommendations →
        </Link>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        {(["Approved", "Rejected", "ChangesRequested"] as const).map((k) => {
          const { cls, icon: Icon, label } = DECISION_STYLES[k];
          return (
            <button
              key={k}
              onClick={() => setFilter(filter === k ? "all" : k)}
              className={`rounded-xl border p-4 text-left transition-all ${filter === k ? "ring-2 ring-primary" : "hover:border-primary/30"}`}
            >
              <div className="flex items-center gap-2 mb-1">
                <Icon className="h-4 w-4" />
                <span className="text-sm font-medium">{label}</span>
              </div>
              <p className="text-3xl font-bold">{counts[k]}</p>
            </button>
          );
        })}
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-muted-foreground" />
        {(["all", "Approved", "Rejected", "ChangesRequested"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filter === f ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            {f === "all" ? "All" : DECISION_STYLES[f]?.label ?? f}
          </button>
        ))}
      </div>

      {/* Decision list */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            {decisions.length} decision{decisions.length !== 1 ? "s" : ""}
            {filter !== "all" && ` · ${DECISION_STYLES[filter]?.label ?? filter}`}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : decisions.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No decisions recorded yet.</p>
          ) : (
            <div className="divide-y divide-border">
              {decisions.map((d) => {
                const style = DECISION_STYLES[d.decision] ?? { cls: "bg-slate-100 text-slate-600", icon: Clock, label: d.decision };
                const Icon = style.icon;
                return (
                  <div key={d.id} className="flex items-start gap-4 px-6 py-4">
                    <div className={`flex-shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold flex items-center gap-1 ${style.cls}`}>
                      <Icon className="h-3 w-3" />
                      {style.label}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{d.title}</p>
                      <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <span className={`font-medium ${PRIORITY_COLORS[d.priority] ?? ""}`}>{d.priority}</span>
                        <span>·</span>
                        <span>{d.entity_type?.replace(/_/g, " ")}</span>
                        {d.decided_by && <><span>·</span><span>by {d.decided_by}</span></>}
                        {d.decided_at && <><span>·</span><span>{formatDate(d.decided_at)}</span></>}
                      </div>
                      {d.comment && (
                        <p className="mt-1 text-xs text-muted-foreground italic line-clamp-2">{d.comment}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
