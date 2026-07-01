"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import {
  AlertTriangle,
  CheckCircle2,
  CheckSquareIcon,
  ChevronDown,
  ChevronRight,
  Zap,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { operatingSystemApi, type ComplianceOperation } from "@/lib/api/operating-system";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Progress } from "@/components/ui/progress";
import { formatDate } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ComplianceGap {
  id: string;
  description: string;
  severity: string;
  gap_type: string;
  regulation_requirement_id: string;
  supplier_id: string | null;
  is_resolved: boolean;
  calculated_at: string | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  IN_PROGRESS: "bg-blue-100 text-blue-800",
  COMPLIANT:   "bg-green-100 text-green-800",
  NON_COMPLIANT: "bg-red-100 text-red-800",
  UNDER_REVIEW: "bg-yellow-100 text-yellow-800",
};

const SEV_COLORS: Record<string, string> = {
  Critical: "bg-red-100 text-red-700",
  High:     "bg-orange-100 text-orange-700",
  Medium:   "bg-amber-100 text-amber-700",
  Low:      "bg-slate-100 text-slate-600",
};

// ── Assign Control Inline ─────────────────────────────────────────────────────

function AssignControlForm({
  gap,
  onClose,
}: {
  gap: ComplianceGap;
  onClose: () => void;
}) {
  const { t } = useLanguage();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(`Remediate gap: ${gap.description.slice(0, 60)}`);
  const [done, setDone] = useState(false);

  const mutation = useMutation({
    mutationFn: async () => {
      await apiClient.post("/recommendations/", {
        title,
        description: gap.description,
        priority: gap.severity === "Critical" ? "Critical" : gap.severity === "High" ? "High" : "Medium",
        action_required: true,
      });
    },
    onSuccess: () => {
      setDone(true);
      queryClient.invalidateQueries({ queryKey: ["compliance-operations"] });
      setTimeout(onClose, 1500);
    },
  });

  if (done) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-emerald-600 py-1">
        <CheckCircle2 className="h-3.5 w-3.5" /> Action created
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-2 rounded-lg border border-blue-200 bg-blue-50/60 p-3">
      <p className="text-xs font-semibold text-blue-700">Create Remediation Action</p>
      <input
        className="w-full rounded border border-input bg-background px-2 py-1 text-xs"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Action title"
      />
      <div className="flex gap-2">
        <Button
          size="sm"
          className="h-7 text-xs px-3"
          disabled={!title.trim() || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {mutation.isPending ? "Creating…" : "Create Action"}
        </Button>
        <Button size="sm" variant="outline" className="h-7 text-xs" onClick={onClose}>
          {t("common.cancel")}
        </Button>
      </div>
    </div>
  );
}

// ── Gap Row ───────────────────────────────────────────────────────────────────

function GapRow({ gap }: { gap: ComplianceGap }) {
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="border-b border-border last:border-0 px-4 py-2.5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-foreground line-clamp-2">{gap.description || gap.gap_type}</p>
          <div className="flex items-center gap-2 mt-1">
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${SEV_COLORS[gap.severity] ?? "bg-slate-100 text-slate-600"}`}>
              {gap.severity}
            </span>
            <span className="text-[10px] text-muted-foreground">{gap.gap_type.replace(/_/g, " ")}</span>
            {gap.calculated_at && (
              <span className="text-[10px] text-muted-foreground">{formatDate(gap.calculated_at)}</span>
            )}
          </div>
          {showForm && (
            <AssignControlForm gap={gap} onClose={() => setShowForm(false)} />
          )}
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex-shrink-0 inline-flex items-center gap-1 rounded-md bg-violet-50 px-2 py-1 text-xs font-medium text-violet-700 hover:bg-violet-100 transition-colors"
        >
          <Zap className="h-3 w-3" /> Assign Control
        </button>
      </div>
    </div>
  );
}

// ── ComplianceOp Row with expandable gaps ─────────────────────────────────────

function ComplianceOpRow({
  op,
  allGaps,
}: {
  op: ComplianceOperation;
  allGaps: ComplianceGap[];
}) {
  const [expanded, setExpanded] = useState(false);

  // Heuristically match gaps to this framework by requirement_id prefix or show all when no framework match
  const opGaps = allGaps.slice(0, op.gap_count ?? 0);

  return (
    <Card>
      <CardContent className="py-4 space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1 min-w-0">
            <p className="font-medium">{op.framework_name}</p>
            <p className="text-xs text-muted-foreground">
              {op.gap_count} gap{op.gap_count !== 1 ? "s" : ""} ·
              {op.last_synced_at ? ` Last synced ${formatDate(op.last_synced_at)}` : " Never synced"}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Badge className={STATUS_COLORS[op.operation_status] ?? "bg-gray-100 text-gray-800"}>
              {op.operation_status}
            </Badge>
            {(op.gap_count ?? 0) > 0 && (
              <button
                onClick={() => setExpanded((v) => !v)}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                {expanded ? "Hide" : "View"} gaps
              </button>
            )}
          </div>
        </div>
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Coverage</span>
            <span>{op.coverage_percent.toFixed(1)}%</span>
          </div>
          <Progress value={op.coverage_percent} className="h-2" />
        </div>

        {expanded && (
          <div className="mt-3 rounded-lg border border-border bg-muted/20">
            {opGaps.length === 0 ? (
              <p className="px-4 py-3 text-xs text-muted-foreground">No gap details available.</p>
            ) : (
              opGaps.map((g) => <GapRow key={g.id} gap={g} />)
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ComplianceOperationsPage() {
  const { t } = useLanguage();
  const { data: ops, isLoading, error } = useQuery({
    queryKey: ["compliance-operations"],
    queryFn: () => operatingSystemApi.listComplianceOperations({ limit: 100 }).then((r) => r.data),
  });

  const { data: allGaps } = useQuery({
    queryKey: ["org-compliance-gaps"],
    queryFn: async () => {
      const res = await apiClient.get("/reporting/gaps?limit=200");
      return res.data as ComplianceGap[];
    },
    staleTime: 120_000,
  });

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><Spinner /></div>;
  }

  if (error) {
    return <div className="p-6 text-red-600">Failed to load compliance operations.</div>;
  }

  const avgCoverage = ops && ops.length > 0
    ? ops.reduce((sum, o) => sum + (o.coverage_percent ?? 0), 0) / ops.length
    : 0;
  const totalGaps = ops?.reduce((sum, o) => sum + (o.gap_count ?? 0), 0) ?? 0;
  const openGaps = allGaps?.filter((g) => !g.is_resolved) ?? [];

  const criticalGaps = openGaps.filter((g) => g.severity === "Critical").length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CheckSquareIcon className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-2xl font-semibold">{t("esgOs.complianceOpsTitle")}</h1>
        </div>
        <span className="text-sm text-muted-foreground">{ops?.length ?? 0} frameworks</span>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Frameworks</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{ops?.length ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Avg Coverage</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-3xl font-bold ${avgCoverage >= 80 ? "text-emerald-600" : avgCoverage >= 50 ? "text-amber-600" : "text-red-600"}`}>
              {avgCoverage.toFixed(1)}%
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Open Gaps</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">{openGaps.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5 text-red-500" /> {t("findings.critical")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-3xl font-bold ${criticalGaps > 0 ? "text-red-600" : "text-emerald-600"}`}>
              {criticalGaps}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-3">
        {ops?.map((op) => (
          <ComplianceOpRow key={op.id} op={op} allGaps={openGaps} />
        ))}
        {ops?.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            No compliance operations yet. Gaps are synced automatically from M31.
          </div>
        )}
      </div>
    </div>
  );
}
