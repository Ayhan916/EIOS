"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  CheckSquare,
  ChevronDown,
  ChevronRight,
  Clock,
  FileText,
  Link2,
  Lock,
  Shield,
  ShieldAlert,
  ShieldCheck,
  X,
  Zap,
} from "lucide-react";
import Link from "next/link";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import apiClient from "@/lib/api/client";
import { operatingSystemApi, type ComplianceOperation, type ESGControl } from "@/lib/api/operating-system";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import { formatDate } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ComplianceCenterData {
  soc2_readiness_pct: number;
  soc2_implemented: number;
  soc2_in_progress: number;
  soc2_not_started: number;
  soc2_total: number;
  open_critical_findings: number;
}

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

// ── Shared helpers ────────────────────────────────────────────────────────────

const CONTROL_STATUSES = ["Implemented", "In Progress", "Not Started", "Exempt"] as const;

const CTRL_COLORS: Record<string, string> = {
  Implemented:   "bg-emerald-500",
  "In Progress": "bg-blue-400",
  "Not Started": "bg-slate-200",
  Exempt:        "bg-amber-300",
};
const CTRL_TEXT: Record<string, string> = {
  Implemented:   "text-white",
  "In Progress": "text-white",
  "Not Started": "text-slate-500",
  Exempt:        "text-amber-900",
};

const OPS_STATUS_COLORS: Record<string, string> = {
  ACTIVE:       "bg-emerald-100 text-emerald-700",
  PENDING:      "bg-amber-100 text-amber-700",
  REVIEW:       "bg-blue-100 text-blue-700",
  CLOSED:       "bg-slate-100 text-slate-500",
  IN_PROGRESS:  "bg-blue-100 text-blue-800",
  COMPLIANT:    "bg-green-100 text-green-800",
  NON_COMPLIANT:"bg-red-100 text-red-800",
  UNDER_REVIEW: "bg-yellow-100 text-yellow-800",
};

const SEV_COLORS: Record<string, string> = {
  Critical: "bg-red-100 text-red-700",
  High:     "bg-orange-100 text-orange-700",
  Medium:   "bg-amber-100 text-amber-700",
  Low:      "bg-slate-100 text-slate-600",
};

function coverageColor(pct: number) {
  if (pct >= 80) return "bg-emerald-500";
  if (pct >= 50) return "bg-amber-500";
  return "bg-red-500";
}

// ── TAB 1: Übersicht (Overview) ───────────────────────────────────────────────

function ControlHeatmap({ controls }: { controls: ESGControl[] }) {
  const { t } = useLanguage();
  const types = Array.from(new Set(controls.map((c) => c.control_type))).sort();

  if (!types.length) {
    return <p className="text-sm text-muted-foreground py-4 text-center">{t("common.noData")}</p>;
  }

  const matrix: Record<string, Record<string, number>> = {};
  for (const type of types) {
    matrix[type] = {};
    for (const s of CONTROL_STATUSES) matrix[type][s] = 0;
  }
  for (const c of controls) {
    if (matrix[c.control_type] && CONTROL_STATUSES.includes(c.control_status as typeof CONTROL_STATUSES[number])) {
      matrix[c.control_type][c.control_status]++;
    }
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="text-left py-2 pr-4 font-semibold text-muted-foreground uppercase tracking-wide">{t("compliance.controlType")}</th>
            {CONTROL_STATUSES.map((s) => (
              <th key={s} className="text-center py-2 px-2 font-semibold text-muted-foreground uppercase tracking-wide whitespace-nowrap">{s}</th>
            ))}
            <th className="text-center py-2 px-2 font-semibold text-muted-foreground uppercase tracking-wide">{t("common.total")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {types.map((type) => {
            const row = matrix[type];
            const total = CONTROL_STATUSES.reduce((s, k) => s + (row[k] ?? 0), 0);
            return (
              <tr key={type}>
                <td className="py-2 pr-4 font-medium capitalize text-foreground whitespace-nowrap">
                  {type.replace(/_/g, " ")}
                </td>
                {CONTROL_STATUSES.map((s) => {
                  const count = row[s] ?? 0;
                  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                  return (
                    <td key={s} className="py-2 px-2 text-center">
                      {count > 0 ? (
                        <span className={`inline-flex items-center justify-center rounded px-2 py-0.5 font-semibold ${CTRL_COLORS[s]} ${CTRL_TEXT[s]}`}>
                          {count} <span className="ml-1 opacity-75">({pct}%)</span>
                        </span>
                      ) : (
                        <span className="text-muted-foreground/40">—</span>
                      )}
                    </td>
                  );
                })}
                <td className="py-2 px-2 text-center font-bold text-foreground">{total}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="mt-3 flex flex-wrap gap-3">
        {CONTROL_STATUSES.map((s) => (
          <div key={s} className="flex items-center gap-1.5">
            <span className={`inline-block h-2.5 w-2.5 rounded-sm ${CTRL_COLORS[s]}`} />
            <span className="text-xs text-muted-foreground">{s}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function OverviewTab({ onTabChange }: { onTabChange: (tab: TabKey) => void }) {
  const { t } = useLanguage();

  const { data, isLoading } = useQuery<ComplianceCenterData>({
    queryKey: ["compliance-center"],
    queryFn: async () => {
      const res = await apiClient.get("/executive/command-center");
      return res.data?.cco ?? {};
    },
    staleTime: 300_000,
  });

  const { data: controls } = useQuery<ESGControl[]>({
    queryKey: ["esg-controls-heatmap"],
    queryFn: async () => {
      const res = await operatingSystemApi.listControls({ limit: 500 });
      return res.data ?? [];
    },
    staleTime: 300_000,
  });

  if (isLoading) return <div className="flex justify-center py-16"><Spinner /></div>;

  return (
    <div className="space-y-6">
      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="pt-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">{t("compliance.soc2Readiness")}</p>
                <p className={`mt-1 text-3xl font-bold ${(data?.soc2_readiness_pct ?? 0) >= 80 ? "text-emerald-600" : "text-amber-600"}`}>
                  {data?.soc2_readiness_pct != null ? `${data.soc2_readiness_pct.toFixed(0)}%` : "—"}
                </p>
              </div>
              <ShieldCheck className="h-5 w-5 text-emerald-500 mt-0.5" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">{t("compliance.implemented")}</p>
                <p className="mt-1 text-3xl font-bold text-emerald-600">{data?.soc2_implemented ?? "—"}</p>
                <p className="text-xs text-muted-foreground">{t("compliance.ofControls").replace("{n}", String(data?.soc2_total ?? "—"))}</p>
              </div>
              <CheckCircle2 className="h-5 w-5 text-emerald-500 mt-0.5" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">{t("compliance.inProgress")}</p>
                <p className="mt-1 text-3xl font-bold text-blue-600">{data?.soc2_in_progress ?? "—"}</p>
              </div>
              <Clock className="h-5 w-5 text-blue-500 mt-0.5" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">{t("dashboard.criticalFindings")}</p>
                <p className={`mt-1 text-3xl font-bold ${(data?.open_critical_findings ?? 0) > 0 ? "text-red-600" : "text-foreground"}`}>
                  {data?.open_critical_findings ?? "—"}
                </p>
              </div>
              <AlertTriangle className={`h-5 w-5 mt-0.5 ${(data?.open_critical_findings ?? 0) > 0 ? "text-red-500" : "text-muted-foreground"}`} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Progress bar */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="h-4 w-4 text-blue-500" />
            {t("compliance.controlProgress")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {[
            { labelKey: "compliance.implemented", count: data?.soc2_implemented ?? 0, color: "bg-emerald-500", textColor: "text-emerald-600" },
            { labelKey: "compliance.inProgress",  count: data?.soc2_in_progress  ?? 0, color: "bg-blue-500",   textColor: "text-blue-600" },
            { labelKey: "compliance.notStarted",  count: data?.soc2_not_started  ?? 0, color: "bg-slate-300",  textColor: "text-slate-500" },
          ].map(({ labelKey, count, color, textColor }) => {
            const total = data?.soc2_total ?? 1;
            const pct = Math.round((count / total) * 100);
            return (
              <div key={labelKey}>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-medium">{t(labelKey as Parameters<typeof t>[0])}</span>
                  <span className={`text-xs font-bold ${textColor}`}>{count} ({pct}%)</span>
                </div>
                <div className="h-2 rounded-full bg-muted overflow-hidden">
                  <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Control heatmap */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-blue-500" />
            {t("compliance.coverageHeatmap")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ControlHeatmap controls={controls ?? []} />
        </CardContent>
      </Card>

      {/* Quick navigation within this hub */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          {
            icon: Shield,
            label: t("compliance.viewAllControls"),
            desc: t("compliance.controlLibraryDesc"),
            action: () => window.location.href = "/operating-system/controls",
            isLink: true,
            href: "/operating-system/controls",
          },
          {
            icon: ShieldAlert,
            label: t("esgOs.gapsTitle"),
            desc: t("compliance.gapAnalysisDesc"),
            action: () => onTabChange("gaps"),
            isLink: false,
            href: "",
          },
          {
            icon: CheckSquare,
            label: t("esgOs.complianceOpsTitle"),
            desc: t("compliance.operationsDesc"),
            action: () => onTabChange("operations"),
            isLink: false,
            href: "",
          },
        ].map(({ icon: Icon, label, desc, action, isLink, href }) =>
          isLink ? (
            <Link key={label} href={href} className="flex items-start gap-3 rounded-xl border border-border p-4 hover:bg-muted/50 transition-colors group">
              <div className="rounded-lg bg-muted p-2 flex-shrink-0"><Icon className="h-4 w-4 text-muted-foreground" /></div>
              <div>
                <p className="text-sm font-semibold group-hover:text-primary">{label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
              </div>
            </Link>
          ) : (
            <button key={label} onClick={action} className="flex items-start gap-3 rounded-xl border border-border p-4 hover:bg-muted/50 transition-colors group text-left">
              <div className="rounded-lg bg-muted p-2 flex-shrink-0"><Icon className="h-4 w-4 text-muted-foreground" /></div>
              <div>
                <p className="text-sm font-semibold group-hover:text-primary">{label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
              </div>
            </button>
          )
        )}
      </div>
    </div>
  );
}

// ── TAB 2: Framework-Gaps ─────────────────────────────────────────────────────

function CoverageRadar({ ops }: { ops: ComplianceOperation[] }) {
  const { t } = useLanguage();
  if (ops.length < 3) return null;
  const data = ops.slice(0, 10).map((op) => ({
    framework: op.framework_name.length > 14 ? op.framework_name.slice(0, 12) + "…" : op.framework_name,
    coverage: Math.round(op.coverage_percent),
  }));
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("dashboard.frameworkCoverage")}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <RadarChart data={data}>
            <PolarGrid />
            <PolarAngleAxis dataKey="framework" tick={{ fontSize: 11 }} />
            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} tickCount={5} />
            <Radar name="Coverage %" dataKey="coverage" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} />
            <Tooltip formatter={(v: number) => [`${v}%`, "Coverage"]} />
          </RadarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function AssignControlPanel({ op, controls, onDone }: { op: ComplianceOperation; controls: ESGControl[]; onDone: () => void }) {
  const { t } = useLanguage();
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
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["compliance-operations"] }); onDone(); },
    onError: () => setError("Failed to assign control"),
  });

  const selectedControl = controls.find((c) => c.id === controlId);

  return (
    <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50/60 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-blue-700">{t("esgOs.gap")}</p>
        <button onClick={onDone} className="text-slate-400 hover:text-slate-600"><X className="h-3.5 w-3.5" /></button>
      </div>
      <div>
        <label className="block text-xs text-muted-foreground mb-1">{t("esgOs.controlsTitle")}</label>
        <select className="w-full rounded border border-input bg-background px-2 py-1.5 text-xs" value={controlId} onChange={(e) => setControlId(e.target.value)}>
          <option value="">— Choose a control —</option>
          {controls.map((c) => (
            <option key={c.id} value={c.id}>[{c.control_type}] {c.control_name}</option>
          ))}
        </select>
      </div>
      {selectedControl && (
        <p className="text-xs text-muted-foreground">
          {t("common.status")}: <span className="font-medium">{selectedControl.control_status}</span>
          {" · "}Effectiveness: <span className="font-medium">{selectedControl.effectiveness_status}</span>
        </p>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex gap-2">
        <Button size="sm" className="h-7 text-xs" disabled={!controlId || mut.isPending} onClick={() => mut.mutate()}>
          {mut.isPending ? t("common.loading") : t("esgOs.addControl")}
        </Button>
        <Button size="sm" variant="outline" className="h-7 text-xs" onClick={onDone}>{t("common.cancel")}</Button>
      </div>
    </div>
  );
}

function FrameworkGapRow({ op, controls }: { op: ComplianceOperation; controls: ESGControl[] }) {
  const { t } = useLanguage();
  const [showAssign, setShowAssign] = useState(false);

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            {op.gap_count > 0
              ? <ShieldAlert className="h-4 w-4 text-red-500 flex-shrink-0" />
              : <ShieldCheck className="h-4 w-4 text-emerald-500 flex-shrink-0" />}
            <p className="font-semibold truncate">{op.framework_name}</p>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {op.gap_count} open gap{op.gap_count !== 1 ? "s" : ""}{" · "}
            {op.last_synced_at ? `Last synced ${new Date(op.last_synced_at).toLocaleDateString()}` : "Never synced"}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${OPS_STATUS_COLORS[op.operation_status] ?? "bg-slate-100 text-slate-600"}`}>
            {op.operation_status}
          </span>
          {op.gap_count > 0 && !showAssign && (
            <Button size="sm" variant="outline" className="h-7 gap-1 text-xs border-blue-200 text-blue-700 hover:bg-blue-50" onClick={() => setShowAssign(true)}>
              <Link2 className="h-3 w-3" />{t("esgOs.addControl")}
            </Button>
          )}
        </div>
      </div>
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>{t("dashboard.complianceCoverage")}</span>
          <span className="font-medium">{op.coverage_percent.toFixed(0)}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
          <div className={`h-full rounded-full transition-all ${coverageColor(op.coverage_percent)}`} style={{ width: `${op.coverage_percent}%` }} />
        </div>
      </div>
      {showAssign && <AssignControlPanel op={op} controls={controls} onDone={() => setShowAssign(false)} />}
    </div>
  );
}

function GapsTab() {
  const { t } = useLanguage();

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
  const avgCoverage = ops?.length ? ops.reduce((s, o) => s + o.coverage_percent, 0) / ops.length : 0;

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
      if (!urgentOps.length) return;
      apiClient.post("/automations/trigger", {
        rule_id: "reg_gap_finding",
        entity_type: "compliance_operation",
        payload: { urgent_frameworks: urgentOps.map((o) => o.framework_name), severity, days_threshold: daysThreshold },
      }).catch(() => { /* silent */ });
    } catch { /* silent */ }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ops]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: t("esgOs.gapsTitle"),             value: totalGaps,                    color: totalGaps > 0 ? "text-red-600" : "text-emerald-600" },
          { label: t("esgOs.framework"),             value: criticalFrameworks,            color: criticalFrameworks > 0 ? "text-amber-600" : "text-emerald-600" },
          { label: t("dashboard.complianceCoverage"), value: `${avgCoverage.toFixed(0)}%`, color: avgCoverage >= 70 ? "text-emerald-600" : "text-amber-600" },
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
        <CardHeader><CardTitle className="text-base">{t("esgOs.gapsTitle")}</CardTitle></CardHeader>
        <CardContent>
          {opsLoading && <Spinner />}
          {!opsLoading && (ops ?? []).length === 0 && (
            <div className="flex flex-col items-center gap-2 py-10 text-center">
              <ShieldCheck className="h-10 w-10 text-slate-300" />
              <p className="text-sm text-slate-600">{t("esgOs.noGaps")}</p>
              <p className="text-xs text-muted-foreground">{t("esgOs.noGapsDesc")}</p>
            </div>
          )}
          <div className="space-y-3">
            {(ops ?? [])
              .slice()
              .sort((a, b) => b.gap_count - a.gap_count || a.coverage_percent - b.coverage_percent)
              .map((op) => <FrameworkGapRow key={op.id} op={op} controls={controls ?? []} />)}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── TAB 3: Operationen ────────────────────────────────────────────────────────

function RemediationForm({ gap, onClose }: { gap: ComplianceGap; onClose: () => void }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [title, setTitle] = useState(`Remediate gap: ${gap.description.slice(0, 60)}`);
  const [done, setDone] = useState(false);

  const mut = useMutation({
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
      qc.invalidateQueries({ queryKey: ["compliance-operations"] });
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
        <Button size="sm" className="h-7 text-xs px-3" disabled={!title.trim() || mut.isPending} onClick={() => mut.mutate()}>
          {mut.isPending ? "Creating…" : "Create Action"}
        </Button>
        <Button size="sm" variant="outline" className="h-7 text-xs" onClick={onClose}>{t("common.cancel")}</Button>
      </div>
    </div>
  );
}

function DetailGapRow({ gap }: { gap: ComplianceGap }) {
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
            {gap.calculated_at && <span className="text-[10px] text-muted-foreground">{formatDate(gap.calculated_at)}</span>}
          </div>
          {showForm && <RemediationForm gap={gap} onClose={() => setShowForm(false)} />}
        </div>
        <button onClick={() => setShowForm((v) => !v)} className="flex-shrink-0 inline-flex items-center gap-1 rounded-md bg-violet-50 px-2 py-1 text-xs font-medium text-violet-700 hover:bg-violet-100 transition-colors">
          <Zap className="h-3 w-3" /> Assign Control
        </button>
      </div>
    </div>
  );
}

function ComplianceOpRow({ op, allGaps }: { op: ComplianceOperation; allGaps: ComplianceGap[] }) {
  const [expanded, setExpanded] = useState(false);
  const opGaps = allGaps.slice(0, op.gap_count ?? 0);

  return (
    <Card>
      <CardContent className="py-4 space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1 min-w-0">
            <p className="font-medium">{op.framework_name}</p>
            <p className="text-xs text-muted-foreground">
              {op.gap_count} gap{op.gap_count !== 1 ? "s" : ""}{" · "}
              {op.last_synced_at ? ` Last synced ${formatDate(op.last_synced_at)}` : " Never synced"}
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Badge className={OPS_STATUS_COLORS[op.operation_status] ?? "bg-gray-100 text-gray-800"}>
              {op.operation_status}
            </Badge>
            {(op.gap_count ?? 0) > 0 && (
              <button onClick={() => setExpanded((v) => !v)} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
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
              opGaps.map((g) => <DetailGapRow key={g.id} gap={g} />)
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function OperationsTab() {
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

  if (isLoading) return <div className="flex items-center justify-center h-64"><Spinner /></div>;
  if (error) return <div className="text-red-600 py-4">Failed to load compliance operations.</div>;

  const avgCoverage = ops && ops.length > 0
    ? ops.reduce((sum, o) => sum + (o.coverage_percent ?? 0), 0) / ops.length : 0;
  const openGaps = (allGaps ?? []).filter((g) => !g.is_resolved);
  const criticalGaps = openGaps.filter((g) => g.severity === "Critical").length;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs font-medium text-muted-foreground">Frameworks</CardTitle></CardHeader>
          <CardContent><p className="text-3xl font-bold">{ops?.length ?? 0}</p></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs font-medium text-muted-foreground">Avg Coverage</CardTitle></CardHeader>
          <CardContent>
            <p className={`text-3xl font-bold ${avgCoverage >= 80 ? "text-emerald-600" : avgCoverage >= 50 ? "text-amber-600" : "text-red-600"}`}>
              {avgCoverage.toFixed(1)}%
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs font-medium text-muted-foreground">Open Gaps</CardTitle></CardHeader>
          <CardContent><p className="text-3xl font-bold text-red-600">{openGaps.length}</p></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5 text-red-500" /> {t("findings.critical")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-3xl font-bold ${criticalGaps > 0 ? "text-red-600" : "text-emerald-600"}`}>{criticalGaps}</p>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-3">
        {ops?.map((op) => <ComplianceOpRow key={op.id} op={op} allGaps={openGaps} />)}
        {(ops?.length ?? 0) === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            No compliance operations yet. Gaps are synced automatically from M31.
          </div>
        )}
      </div>
    </div>
  );
}

// ── Tab nav ───────────────────────────────────────────────────────────────────

const tab_defs = [
  { key: "overview",    label: "Übersicht" },
  { key: "gaps",        label: "Framework-Gaps" },
  { key: "operations",  label: "Operationen" },
] as const;

type TabKey = (typeof tab_defs)[number]["key"];

// ── Page ──────────────────────────────────────────────────────────────────────

const ADMIN_ROLES = new Set(["admin", "enterprise_admin", "bu_admin"]);

export default function ComplianceCenterPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<TabKey>("overview");

  if (!user || !ADMIN_ROLES.has(user.role)) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3 text-center">
        <Lock className="h-10 w-10 text-muted-foreground/40" />
        <p className="text-sm font-medium">{t("settings.adminOnly")}</p>
        <p className="text-xs text-muted-foreground">{t("compliance.adminRestricted")}</p>
        <Link href="/dashboard" className="text-xs text-blue-600 hover:underline">{t("compliance.backToDashboard")}</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("nav.complianceCenter")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("compliance.centerSubtitle")}</p>
        </div>
        <div className="flex gap-2">
          <Link href="/enterprise/audit" className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium hover:bg-muted transition-colors">
            <FileText className="h-4 w-4" /> {t("compliance.auditTrail")}
          </Link>
          <Link href="/reports" className="flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
            <BarChart3 className="h-4 w-4" /> {t("compliance.complianceReports")}
          </Link>
        </div>
      </div>

      {/* Tab bar */}
      <div className="border-b border-border">
        <nav className="-mb-px flex gap-0">
          {tab_defs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "overview"   && <OverviewTab onTabChange={setActiveTab} />}
        {activeTab === "gaps"       && <GapsTab />}
        {activeTab === "operations" && <OperationsTab />}
      </div>
    </div>
  );
}
