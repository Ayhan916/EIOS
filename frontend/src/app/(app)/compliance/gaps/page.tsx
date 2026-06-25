"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api/client";
import { ShieldCheck, ShieldAlert, X, Link2 } from "lucide-react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { operatingSystemApi, type ComplianceOperation, type ESGControl } from "@/lib/api/operating-system";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

const STATUS_STYLES: Record<string, string> = {
  ACTIVE:    "bg-emerald-100 text-emerald-700",
  PENDING:   "bg-amber-100 text-amber-700",
  REVIEW:    "bg-blue-100 text-blue-700",
  CLOSED:    "bg-slate-100 text-slate-500",
};

function coverageColor(pct: number) {
  if (pct >= 80) return "bg-emerald-500";
  if (pct >= 50) return "bg-amber-500";
  return "bg-red-500";
}

function CoverageRadar({ ops }: { ops: ComplianceOperation[] }) {
  if (ops.length < 3) return null;
  const data = ops.slice(0, 10).map((op) => ({
    framework: op.framework_name.length > 14
      ? op.framework_name.slice(0, 12) + "…"
      : op.framework_name,
    coverage: Math.round(op.coverage_percent),
  }));
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Framework Coverage Radar</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <RadarChart data={data}>
            <PolarGrid />
            <PolarAngleAxis dataKey="framework" tick={{ fontSize: 11 }} />
            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} tickCount={5} />
            <Radar
              name="Coverage %"
              dataKey="coverage"
              stroke="#3b82f6"
              fill="#3b82f6"
              fillOpacity={0.25}
            />
            <Tooltip formatter={(v: number) => [`${v}%`, "Coverage"]} />
          </RadarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function AssignControlPanel({
  op,
  controls,
  onDone,
}: {
  op: ComplianceOperation;
  controls: ESGControl[];
  onDone: () => void;
}) {
  const qc = useQueryClient();
  const [controlId, setControlId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mut = useMutation({
    mutationFn: () =>
      operatingSystemApi.assignAccountability({
        entity_type: "compliance_operation",
        entity_id: op.id,
        role: "CONTROL_OWNER",
        assigned_to_user_id: controlId,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compliance-operations"] });
      onDone();
    },
    onError: () => setError("Failed to assign control"),
  });

  const selectedControl = controls.find((c) => c.id === controlId);

  return (
    <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50/60 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-blue-700">Assign Control to Gap</p>
        <button onClick={onDone} className="text-slate-400 hover:text-slate-600"><X className="h-3.5 w-3.5" /></button>
      </div>
      <div>
        <label className="block text-xs text-muted-foreground mb-1">Select Control</label>
        <select
          className="w-full rounded border border-input bg-background px-2 py-1.5 text-xs"
          value={controlId}
          onChange={(e) => setControlId(e.target.value)}
        >
          <option value="">— Choose a control —</option>
          {controls.map((c) => (
            <option key={c.id} value={c.id}>
              [{c.control_type}] {c.control_name}
            </option>
          ))}
        </select>
      </div>
      {selectedControl && (
        <p className="text-xs text-muted-foreground">
          Status: <span className="font-medium">{selectedControl.control_status}</span>
          {" · "}Effectiveness: <span className="font-medium">{selectedControl.effectiveness_status}</span>
        </p>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex gap-2">
        <Button
          size="sm"
          className="h-7 text-xs"
          disabled={!controlId || mut.isPending}
          onClick={() => mut.mutate()}
        >
          {mut.isPending ? "Assigning…" : "Assign Control"}
        </Button>
        <Button size="sm" variant="outline" className="h-7 text-xs" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

function GapRow({ op, controls }: { op: ComplianceOperation; controls: ESGControl[] }) {
  const [showAssign, setShowAssign] = useState(false);

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            {op.gap_count > 0 ? (
              <ShieldAlert className="h-4 w-4 text-red-500 flex-shrink-0" />
            ) : (
              <ShieldCheck className="h-4 w-4 text-emerald-500 flex-shrink-0" />
            )}
            <p className="font-semibold truncate">{op.framework_name}</p>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {op.gap_count} open gap{op.gap_count !== 1 ? "s" : ""}{" · "}
            {op.last_synced_at
              ? `Last synced ${new Date(op.last_synced_at).toLocaleDateString()}`
              : "Never synced"}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${STATUS_STYLES[op.operation_status] ?? "bg-slate-100 text-slate-600"}`}>
            {op.operation_status}
          </span>
          {op.gap_count > 0 && !showAssign && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 gap-1 text-xs border-blue-200 text-blue-700 hover:bg-blue-50"
              onClick={() => setShowAssign(true)}
            >
              <Link2 className="h-3 w-3" />
              Assign Control
            </Button>
          )}
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>Coverage</span>
          <span className="font-medium">{op.coverage_percent.toFixed(0)}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${coverageColor(op.coverage_percent)}`}
            style={{ width: `${op.coverage_percent}%` }}
          />
        </div>
      </div>

      {showAssign && (
        <AssignControlPanel op={op} controls={controls} onDone={() => setShowAssign(false)} />
      )}
    </div>
  );
}

export default function ComplianceGapsPage() {
  const { data: ops, isLoading: opsLoading } = useQuery({
    queryKey: ["compliance-operations"],
    queryFn: () => operatingSystemApi.listComplianceOperations({ limit: 100 }).then((r) => r.data),
  });

  const { data: controls } = useQuery({
    queryKey: ["esg-controls"],
    queryFn: () => operatingSystemApi.listControls({ limit: 100 }).then((r) => r.data),
    staleTime: 300_000,
  });

  const totalGaps = (ops ?? []).reduce((s, o) => s + o.gap_count, 0);
  const criticalFrameworks = (ops ?? []).filter((o) => o.coverage_percent < 50).length;
  const avgCoverage = ops?.length
    ? ops.reduce((s, o) => s + o.coverage_percent, 0) / ops.length
    : 0;

  // #155 Auto-create regulatory gap finding when deadline < threshold
  useEffect(() => {
    if (!ops?.length) return;
    try {
      const stored = JSON.parse(localStorage.getItem("eios_automation_rules") ?? "{}");
      if (stored?.reg_gap_finding?.enabled === false) return;
      const daysThreshold = Number(stored?.reg_gap_finding?.config?.days_threshold ?? 90);
      const severity = stored?.reg_gap_finding?.config?.severity ?? "HIGH";
      const now = Date.now();
      const urgentOps = ops.filter((op) => {
        if (!op.last_synced_at || op.gap_count === 0) return false;
        const deadline = new Date(op.last_synced_at).getTime() + 365 * 24 * 3_600_000;
        const daysUntil = (deadline - now) / (24 * 3_600_000);
        return daysUntil > 0 && daysUntil < daysThreshold;
      });
      if (urgentOps.length === 0) return;
      apiClient.post("/api/v1/automations/trigger", {
        rule_id: "reg_gap_finding",
        entity_type: "compliance_operation",
        payload: { urgent_frameworks: urgentOps.map((o) => o.framework_name), severity, days_threshold: daysThreshold },
      }).catch(() => { /* silent */ });
    } catch { /* silent */ }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ops]);

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Compliance Gap Analysis</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Framework gaps across all compliance operations — assign controls to close gaps
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Open Gaps", value: totalGaps, color: totalGaps > 0 ? "text-red-600" : "text-emerald-600" },
          { label: "Frameworks < 50% Coverage", value: criticalFrameworks, color: criticalFrameworks > 0 ? "text-amber-600" : "text-emerald-600" },
          { label: "Avg Coverage", value: `${avgCoverage.toFixed(0)}%`, color: avgCoverage >= 70 ? "text-emerald-600" : "text-amber-600" },
        ].map(({ label, value, color }) => (
          <Card key={label}>
            <CardContent className="pt-4 pb-3">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {(ops ?? []).length >= 3 && <CoverageRadar ops={ops ?? []} />}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Framework Gaps</CardTitle>
        </CardHeader>
        <CardContent>
          {opsLoading && <Spinner />}
          {!opsLoading && (ops ?? []).length === 0 && (
            <div className="flex flex-col items-center gap-2 py-10 text-center">
              <ShieldCheck className="h-10 w-10 text-slate-300" />
              <p className="text-sm text-slate-600">No compliance operations found.</p>
              <p className="text-xs text-muted-foreground">Add frameworks via Operating System → Compliance Operations.</p>
            </div>
          )}
          <div className="space-y-3">
            {(ops ?? [])
              .slice()
              .sort((a, b) => b.gap_count - a.gap_count || a.coverage_percent - b.coverage_percent)
              .map((op) => (
                <GapRow key={op.id} op={op} controls={controls ?? []} />
              ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
