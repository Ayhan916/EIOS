"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Loader2,
  RefreshCw,
  Shield,
  Target,
  Zap,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface OSDashboard {
  objectives_total: number;
  objectives_at_risk: number;
  initiatives_total: number;
  initiatives_active: number;
  actions_open: number;
  actions_overdue: number;
  escalations_triggered: number;
  strategic_risks_critical: number;
  latest_health_score: number | null;
  top_overdue_actions: ESGAction[];
  objectives_by_status: Record<string, number>;
  recent_strategic_risks: StrategicRisk[];
  compliance_operations: number;
  governance_calendar_events: number;
  programs_total: number;
  controls_total: number;
}

interface HealthScore {
  id: string;
  overall_score: number;
  supplier_intelligence_score: number;
  surveillance_score: number;
  compliance_score: number;
  due_diligence_score: number;
  remediation_score: number;
  governance_score: number;
  formula_version: string;
  calculated_at: string;
}

interface ESGAction {
  id: string;
  title: string;
  description: string;
  source_type: string;
  owner_user_id: string | null;
  due_date: string | null;
  action_status: string;
  priority: string;
  linked_objectives: string[];
  created_at: string;
  updated_at: string;
}

interface StrategicRisk {
  id: string;
  title: string;
  description: string;
  category: string;
  risk_level: string;
  probability: string;
  impact: string;
  risk_status: string;
  owner_user_id: string | null;
  linked_suppliers: string[];
  created_at: string;
}

interface TimelineEntry {
  event_type: string;
  entity_type: string;
  entity_id: string;
  title: string;
  timestamp: string;
  status: string | null;
}

// ── Colour maps ───────────────────────────────────────────────────────────────

const RISK_COL: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800",
  HIGH:     "bg-orange-100 text-orange-800",
  MEDIUM:   "bg-amber-100 text-amber-700",
  LOW:      "bg-green-100 text-green-800",
};

const ACTION_PRI_COL: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800",
  HIGH:     "bg-orange-100 text-orange-800",
  MEDIUM:   "bg-amber-100 text-amber-700",
  LOW:      "bg-slate-100 text-slate-600",
};

const STATUS_COL: Record<string, string> = {
  OPEN:        "bg-blue-100 text-blue-700",
  IN_PROGRESS: "bg-indigo-100 text-indigo-700",
  COMPLETED:   "bg-emerald-100 text-emerald-800",
  BLOCKED:     "bg-red-100 text-red-700",
  CANCELLED:   "bg-slate-100 text-slate-500",
  IDENTIFIED:  "bg-slate-100 text-slate-600",
  MITIGATED:   "bg-emerald-100 text-emerald-800",
  ACCEPTED:    "bg-amber-100 text-amber-700",
  CLOSED:      "bg-slate-100 text-slate-500",
};

const ENTITY_ICON: Record<string, React.ElementType> = {
  objective:   Target,
  initiative:  Zap,
  action:      CheckCircle2,
  strategic_risk: AlertTriangle,
  program:     BarChart3,
  control:     Shield,
};

type TabKey = "overview" | "risks" | "actions" | "timeline";

const tab_defs: { key: TabKey; labelKey: string }[] = [
  { key: "overview",  labelKey: "osDash.overviewTab" },
  { key: "risks",     labelKey: "osDash.risksTab" },
  { key: "actions",   labelKey: "osDash.actionsTab" },
  { key: "timeline",  labelKey: "osDash.timelineTab" },
];

// ── Score gauge ───────────────────────────────────────────────────────────────

function ScoreGauge({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  const color = pct >= 75 ? "text-emerald-600" : pct >= 50 ? "text-amber-600" : "text-red-600";
  const ringColor = pct >= 75 ? "stroke-emerald-500" : pct >= 50 ? "stroke-amber-500" : "stroke-red-500";
  const r = 40;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="100" height="100" viewBox="0 0 100 100" className="-rotate-90">
        <circle cx="50" cy="50" r={r} fill="none" strokeWidth="10" className="stroke-muted" />
        <circle
          cx="50" cy="50" r={r} fill="none" strokeWidth="10"
          className={ringColor}
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
        />
      </svg>
      <p className={`text-3xl font-bold -mt-[72px] mb-8 ${color}`}>{pct.toFixed(0)}</p>
    </div>
  );
}

function DimensionBar({ label, score }: { label: string; score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  const barColor = pct >= 75 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{pct.toFixed(0)}</span>
      </div>
      <div className="h-1.5 rounded-full bg-muted">
        <div className={`h-1.5 rounded-full ${barColor} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── KPI card ──────────────────────────────────────────────────────────────────

function KpiCard({
  label, value, sub, accent,
}: {
  label: string; value: number | string; sub?: string; accent?: string;
}) {
  return (
    <Card>
      <CardContent className="py-4 px-5">
        <p className="text-xs text-muted-foreground mb-1">{label}</p>
        <p className={`text-2xl font-bold ${accent ?? ""}`}>{value}</p>
        {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function OSDashboardPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [actionStatusFilter, setActionStatusFilter] = useState("");
  const [riskLevelFilter, setRiskLevelFilter] = useState("");
  const [expandedRisk, setExpandedRisk] = useState<string | null>(null);

  const { data: dash, isLoading: dashLoading } = useQuery<OSDashboard>({
    queryKey: ["os-dashboard"],
    queryFn: () => apiClient.get("/operating-system/dashboard").then((r) => r.data),
  });

  const { data: healthScore, isLoading: scoreLoading } = useQuery<HealthScore>({
    queryKey: ["os-health-score"],
    queryFn: () => apiClient.get("/operating-system/health-score").then((r) => r.data),
  });

  const { data: actions = [], isLoading: actionsLoading } = useQuery<ESGAction[]>({
    queryKey: ["os-actions", actionStatusFilter],
    queryFn: () =>
      apiClient.get("/operating-system/actions", {
        params: { ...(actionStatusFilter ? { action_status: actionStatusFilter } : {}), limit: 100 },
      }).then((r) => r.data),
    enabled: activeTab === "actions",
  });

  const { data: risks = [], isLoading: risksLoading } = useQuery<StrategicRisk[]>({
    queryKey: ["os-strategic-risks", riskLevelFilter],
    queryFn: () =>
      apiClient.get("/operating-system/strategic-risks", {
        params: { ...(riskLevelFilter ? { risk_level: riskLevelFilter } : {}), limit: 200 },
      }).then((r) => r.data),
    enabled: activeTab === "risks",
  });

  const { data: timeline = [], isLoading: timelineLoading } = useQuery<TimelineEntry[]>({
    queryKey: ["os-timeline"],
    queryFn: () => apiClient.get("/operating-system/timeline?limit=50").then((r) => r.data),
    enabled: activeTab === "timeline",
  });

  const refreshScore = useMutation({
    mutationFn: () => apiClient.post("/operating-system/health-score/refresh").then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["os-health-score"] });
      qc.invalidateQueries({ queryKey: ["os-dashboard"] });
    },
  });

  const updateActionStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiClient.patch(`/operating-system/actions/${id}`, { action_status: status }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["os-actions"] }),
  });

  if (dashLoading) return <div className="flex justify-center py-24"><Spinner /></div>;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Activity className="h-7 w-7 text-primary mt-0.5 shrink-0" />
          <div>
            <h1 className="text-2xl font-semibold">{t("osDash.title")}</h1>
            <p className="text-sm text-muted-foreground">{t("osDash.subtitle")}</p>
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          disabled={refreshScore.isPending}
          onClick={() => refreshScore.mutate()}
        >
          {refreshScore.isPending
            ? <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />{t("osDash.refreshing")}</>
            : <><RefreshCw className="h-3.5 w-3.5 mr-1.5" />{t("osDash.refreshScore")}</>}
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {tab_defs.map(({ key, labelKey }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors ${
              activeTab === key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t(labelKey as Parameters<typeof t>[0])}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW TAB ─────────────────────────────────────────────────────── */}
      {activeTab === "overview" && dash && (
        <div className="space-y-6">
          {/* Health Score + Dimensions */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Score gauge card */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{t("osDash.healthScore")}</CardTitle>
              </CardHeader>
              <CardContent>
                {scoreLoading ? (
                  <div className="flex justify-center py-6"><Spinner /></div>
                ) : healthScore ? (
                  <div className="flex flex-col items-center gap-2">
                    <ScoreGauge score={healthScore.overall_score} />
                    <p className="text-[10px] text-muted-foreground font-mono">
                      v{healthScore.formula_version} · {formatDate(healthScore.calculated_at)}
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-4">{t("osDash.noScore")}</p>
                )}
              </CardContent>
            </Card>

            {/* Dimension bars */}
            {healthScore && (
              <Card className="md:col-span-2">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">{t("osDash.dimensions")}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <DimensionBar label={t("osDash.dimSupplier")} score={healthScore.supplier_intelligence_score} />
                  <DimensionBar label={t("osDash.dimSurveillance")} score={healthScore.surveillance_score} />
                  <DimensionBar label={t("osDash.dimCompliance")} score={healthScore.compliance_score} />
                  <DimensionBar label={t("osDash.dimDueDiligence")} score={healthScore.due_diligence_score} />
                  <DimensionBar label={t("osDash.dimRemediation")} score={healthScore.remediation_score} />
                  <DimensionBar label={t("osDash.dimGovernance")} score={healthScore.governance_score} />
                </CardContent>
              </Card>
            )}
          </div>

          {/* KPI grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-4 gap-4">
            <KpiCard
              label={t("osDash.objectivesAtRisk")}
              value={dash.objectives_at_risk}
              sub={`of ${dash.objectives_total} total`}
              accent={dash.objectives_at_risk > 0 ? "text-red-600" : ""}
            />
            <KpiCard
              label={t("osDash.initiativesActive")}
              value={dash.initiatives_active}
              sub={`of ${dash.initiatives_total} total`}
            />
            <KpiCard
              label={t("osDash.actionsOverdue")}
              value={dash.actions_overdue}
              sub={`${dash.actions_open} open total`}
              accent={dash.actions_overdue > 0 ? "text-red-600" : ""}
            />
            <KpiCard
              label={t("osDash.criticalRisks")}
              value={dash.strategic_risks_critical}
              accent={dash.strategic_risks_critical > 0 ? "text-red-600" : ""}
            />
            <KpiCard label={t("osDash.escalations")} value={dash.escalations_triggered} accent={dash.escalations_triggered > 0 ? "text-amber-600" : ""} />
            <KpiCard label={t("osDash.programs")} value={dash.programs_total} />
            <KpiCard label={t("osDash.controls")} value={dash.controls_total} />
            <KpiCard label={t("osDash.calendarEvents")} value={dash.governance_calendar_events} />
          </div>

          {/* Objectives by status */}
          {Object.keys(dash.objectives_by_status).length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Objectives by Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-3">
                  {Object.entries(dash.objectives_by_status).map(([status, count]) => (
                    <div key={status} className="flex items-center gap-1.5">
                      <Badge className={STATUS_COL[status] ?? "bg-slate-100 text-slate-600"}>{status}</Badge>
                      <span className="text-sm font-semibold">{count}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Top overdue actions */}
          {dash.top_overdue_actions.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">{t("osDash.overdueActions")}</h2>
              {dash.top_overdue_actions.map((action) => (
                <Card key={action.id} className="border-red-200">
                  <CardContent className="py-3 px-4 flex items-start justify-between gap-4">
                    <div className="space-y-0.5 flex-1 min-w-0">
                      <p className="font-medium text-sm">{action.title}</p>
                      <div className="flex flex-wrap gap-2">
                        <Badge className={ACTION_PRI_COL[action.priority] ?? "bg-slate-100 text-slate-600"}>{action.priority}</Badge>
                        <Badge className={STATUS_COL[action.action_status] ?? "bg-slate-100 text-slate-600"}>{action.action_status}</Badge>
                      </div>
                    </div>
                    {action.due_date && (
                      <div className="shrink-0 text-right">
                        <div className="flex items-center gap-1 text-xs text-red-600">
                          <Clock className="h-3 w-3" />
                          {formatDate(action.due_date)}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Recent strategic risks from dashboard */}
          {dash.recent_strategic_risks.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Recent Strategic Risks</h2>
              {dash.recent_strategic_risks.map((risk) => (
                <Card key={risk.id} className={risk.risk_level === "CRITICAL" ? "border-red-200" : ""}>
                  <CardContent className="py-3 px-4 flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium text-sm">{risk.title}</p>
                      <p className="text-xs text-muted-foreground">{risk.category}</p>
                    </div>
                    <Badge className={RISK_COL[risk.risk_level] ?? "bg-slate-100 text-slate-600"}>{risk.risk_level}</Badge>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── STRATEGIC RISKS TAB ──────────────────────────────────────────────── */}
      {activeTab === "risks" && (
        <div className="space-y-4">
          {/* Filter */}
          <div className="flex gap-2 flex-wrap">
            <select
              className="h-8 rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              value={riskLevelFilter}
              onChange={(e) => setRiskLevelFilter(e.target.value)}
            >
              <option value="">{t("osDash.allLevels")}</option>
              {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </div>

          {risksLoading ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : risks.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <Shield className="mx-auto mb-3 h-10 w-10 opacity-25" />
              <p className="text-sm">{t("osDash.noRisks")}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {risks.map((risk) => (
                <Card key={risk.id} className={risk.risk_level === "CRITICAL" ? "border-red-200" : ""}>
                  <CardContent className="py-4 space-y-2">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold">{risk.title}</p>
                        <p className="text-xs text-muted-foreground">{risk.category}</p>
                      </div>
                      <div className="flex flex-col items-end gap-1.5 shrink-0">
                        <Badge className={RISK_COL[risk.risk_level] ?? "bg-slate-100 text-slate-600"}>{risk.risk_level}</Badge>
                        <Badge className={STATUS_COL[risk.risk_status] ?? "bg-slate-100 text-slate-600"}>{risk.risk_status}</Badge>
                      </div>
                    </div>

                    <button
                      onClick={() => setExpandedRisk(expandedRisk === risk.id ? null : risk.id)}
                      className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
                    >
                      {expandedRisk === risk.id ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      {expandedRisk === risk.id ? "Hide" : "Details"}
                    </button>

                    {expandedRisk === risk.id && (
                      <div className="border-t pt-2 space-y-1.5">
                        <p className="text-sm text-muted-foreground">{risk.description}</p>
                        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                          <span>{t("osDash.probability")}: <strong>{risk.probability}</strong></span>
                          <span>{t("osDash.impact")}: <strong>{risk.impact}</strong></span>
                        </div>
                        {risk.linked_suppliers.length > 0 && (
                          <p className="text-xs text-muted-foreground">
                            Linked suppliers: {risk.linked_suppliers.length}
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground">{formatDate(risk.created_at)}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── ACTIONS TAB ──────────────────────────────────────────────────────── */}
      {activeTab === "actions" && (
        <div className="space-y-4">
          {/* Filter */}
          <div className="flex gap-2 flex-wrap">
            <select
              className="h-8 rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              value={actionStatusFilter}
              onChange={(e) => setActionStatusFilter(e.target.value)}
            >
              <option value="">{t("osDash.allStatuses")}</option>
              {["OPEN", "IN_PROGRESS", "BLOCKED", "COMPLETED", "CANCELLED"].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {actionsLoading ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : actions.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <CheckCircle2 className="mx-auto mb-3 h-10 w-10 opacity-25" />
              <p className="text-sm">{t("osDash.noActions")}</p>
            </div>
          ) : (
            <div className="rounded-md border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-b">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Action</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t("osDash.priority")}</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t("osDash.dueDate")}</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {actions.map((action) => (
                    <tr key={action.id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3">
                        <p className="font-medium">{action.title}</p>
                        {action.description && (
                          <p className="text-xs text-muted-foreground line-clamp-1">{action.description}</p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge className={ACTION_PRI_COL[action.priority] ?? "bg-slate-100 text-slate-600"}>
                          {action.priority}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {action.due_date ? (
                          <span className={new Date(action.due_date) < new Date() && action.action_status !== "COMPLETED" ? "text-red-600 font-medium" : "text-muted-foreground"}>
                            {formatDate(action.due_date)}
                          </span>
                        ) : (
                          <span className="text-muted-foreground/50 italic">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge className={STATUS_COL[action.action_status] ?? "bg-slate-100 text-slate-600"}>
                          {action.action_status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {action.action_status === "OPEN" && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs"
                            disabled={updateActionStatus.isPending}
                            onClick={() => updateActionStatus.mutate({ id: action.id, status: "IN_PROGRESS" })}
                          >
                            Start
                          </Button>
                        )}
                        {action.action_status === "IN_PROGRESS" && (
                          <Button
                            size="sm"
                            className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700"
                            disabled={updateActionStatus.isPending}
                            onClick={() => updateActionStatus.mutate({ id: action.id, status: "COMPLETED" })}
                          >
                            Complete
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── TIMELINE TAB ─────────────────────────────────────────────────────── */}
      {activeTab === "timeline" && (
        <div className="space-y-2">
          {timelineLoading ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : timeline.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <Activity className="mx-auto mb-3 h-10 w-10 opacity-25" />
              <p className="text-sm">{t("osDash.noTimeline")}</p>
            </div>
          ) : (
            <div className="relative pl-6 space-y-4">
              <div className="absolute left-2.5 top-0 bottom-0 w-px bg-border" />
              {timeline.map((entry, i) => {
                const Icon = ENTITY_ICON[entry.entity_type] ?? Activity;
                return (
                  <div key={`${entry.entity_id}-${i}`} className="relative">
                    <div className="absolute -left-4 mt-0.5 h-4 w-4 rounded-full bg-background border-2 border-primary flex items-center justify-center">
                      <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                    </div>
                    <div className="pl-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Icon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                        <p className="text-sm font-medium">{entry.title}</p>
                        {entry.status && (
                          <Badge className={`text-[10px] py-0 ${STATUS_COL[entry.status] ?? "bg-slate-100 text-slate-600"}`}>
                            {entry.status}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <p className="text-xs text-muted-foreground capitalize">{entry.entity_type.replace(/_/g, " ")}</p>
                        <span className="text-muted-foreground/40">·</span>
                        <p className="text-xs text-muted-foreground">{formatDate(entry.timestamp)}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
