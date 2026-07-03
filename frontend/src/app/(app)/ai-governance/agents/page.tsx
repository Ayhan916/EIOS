"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronRight,
  Loader2,
  Pause,
  Play,
  RotateCw,
  ShieldAlert,
  ThumbsDown,
  ThumbsUp,
  X,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentHealth {
  agent_id: string;
  agent_type: string;
  name: string;
  status: string;
  enabled: boolean;
  last_successful_run: string | null;
  consecutive_failures: number;
  avg_runtime_ms: number | null;
  success_rate: number | null;
  backlog_count: number;
}

interface AgentDashboard {
  active_agents: number;
  paused_agents: number;
  failed_agents: number;
  total_open_findings: number;
  total_unacknowledged_alerts: number;
  total_critical_alerts: number;
  total_pending_drafts: number;
  recent_findings: AgentFinding[];
  recent_alerts: AgentAlert[];
  per_agent_health: AgentHealth[];
}

interface MonitoringAgent {
  id: string;
  agent_type: string;
  name: string;
  description: string;
  status: string;
  enabled: boolean;
  run_interval_hours: number;
  last_run_at: string | null;
  next_run_at: string | null;
  run_count: number;
  success_count: number;
  failure_count: number;
}

interface AgentRun {
  id: string;
  agent_id: string;
  run_status: string;
  findings_generated: number;
  alerts_generated: number;
  actions_recommended: number;
  started_at: string;
  completed_at: string | null;
  execution_time_ms: number | null;
  error_message: string | null;
}

interface AgentFinding {
  id: string;
  agent_type?: string;
  category: string;
  severity: string;
  title: string;
  description: string;
  confidence_score: number;
  finding_status: string;
  detected_at: string;
  supplier_id: string | null;
  acknowledged_by: string | null;
}

interface AgentAlert {
  id: string;
  agent_id: string;
  severity: string;
  title: string;
  message: string;
  acknowledged_at: string | null;
  created_at: string;
  supplier_id: string | null;
}

interface RecommendationDraft {
  id: string;
  agent_id: string;
  recommendation_text: string;
  rationale: string;
  confidence_score: number;
  draft_status: string;
  approved_by: string | null;
  rejection_reason: string | null;
  created_at: string;
  supplier_id: string | null;
}

// ── Colour helpers ─────────────────────────────────────────────────────────────

const SEV: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800",
  HIGH:     "bg-orange-100 text-orange-800",
  MEDIUM:   "bg-amber-100 text-amber-800",
  LOW:      "bg-green-100 text-green-800",
  INFO:     "bg-blue-100 text-blue-800",
  WARNING:  "bg-amber-100 text-amber-800",
};

const STATUS_COL: Record<string, string> = {
  running:   "bg-blue-100 text-blue-800",
  idle:      "bg-slate-100 text-slate-600",
  paused:    "bg-yellow-100 text-yellow-800",
  error:     "bg-red-100 text-red-800",
  active:    "bg-green-100 text-green-800",
  completed: "bg-emerald-100 text-emerald-800",
  failed:    "bg-red-100 text-red-800",
};

function confBar(score: number) {
  const pct = Math.round(score * 100);
  const col = pct >= 80 ? "bg-emerald-500" : pct >= 60 ? "bg-amber-500" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-muted rounded-full h-1.5 w-20">
        <div className={`h-1.5 rounded-full ${col}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground">{pct}%</span>
    </div>
  );
}

// ── Dashboard Tab ─────────────────────────────────────────────────────────────

function DashboardTab() {
  const { t } = useLanguage();
  const { data: dash, isLoading } = useQuery<AgentDashboard>({
    queryKey: ["agents-dashboard"],
    queryFn: () => apiClient.get("/agents/dashboard").then((r) => r.data),
    refetchInterval: 30_000,
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (!dash) return null;

  const kpis = [
    { label: t("agents.activeAgents"),    value: dash.active_agents,                  colour: "text-green-600" },
    { label: t("agents.pausedAgents"),    value: dash.paused_agents,                  colour: "text-amber-600" },
    { label: t("agents.failedAgents"),    value: dash.failed_agents,                  colour: dash.failed_agents > 0 ? "text-red-600" : "" },
    { label: t("agents.openFindings"),    value: dash.total_open_findings,            colour: dash.total_open_findings > 0 ? "text-orange-600" : "" },
    { label: t("agents.unackedAlerts"),   value: dash.total_unacknowledged_alerts,    colour: dash.total_unacknowledged_alerts > 0 ? "text-red-600" : "" },
    { label: t("agents.criticalAlerts"),  value: dash.total_critical_alerts,          colour: dash.total_critical_alerts > 0 ? "text-red-700 font-bold" : "" },
    { label: t("agents.pendingDrafts"),   value: dash.total_pending_drafts,           colour: "" },
  ];

  return (
    <div className="space-y-6">
      {/* KPI grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {kpis.map(({ label, value, colour }) => (
          <Card key={label}>
            <CardContent className="pt-4 pb-4">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className={`text-3xl font-bold mt-0.5 ${colour}`}>{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Per-agent health table */}
      {dash.per_agent_health.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">{t("agents.perAgentHealth")}</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-xs text-muted-foreground">
                    <th className="px-4 py-2 text-left">Agent</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-right">{t("agents.successRate")}</th>
                    <th className="px-4 py-2 text-right">Backlog</th>
                    <th className="px-4 py-2 text-right">Failures</th>
                    <th className="px-4 py-2 text-left">{t("agents.lastRun")}</th>
                  </tr>
                </thead>
                <tbody>
                  {dash.per_agent_health.map((h) => (
                    <tr key={h.agent_id} className="border-b last:border-0 hover:bg-muted/30">
                      <td className="px-4 py-2.5 font-medium">{h.name}</td>
                      <td className="px-4 py-2.5">
                        <Badge className={STATUS_COL[h.status] ?? "bg-slate-100 text-slate-600"}>
                          {h.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        {h.success_rate != null ? `${(h.success_rate * 100).toFixed(0)}%` : "—"}
                      </td>
                      <td className="px-4 py-2.5 text-right">{h.backlog_count}</td>
                      <td className={`px-4 py-2.5 text-right ${h.consecutive_failures > 0 ? "text-red-600 font-semibold" : ""}`}>
                        {h.consecutive_failures}
                      </td>
                      <td className="px-4 py-2.5 text-muted-foreground text-xs">
                        {h.last_successful_run ? formatDate(h.last_successful_run) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent findings + alerts side by side */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-orange-500" /> {t("agents.recentFindings")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {dash.recent_findings.slice(0, 5).map((f) => (
              <div key={f.id} className="flex items-start gap-2 text-sm">
                <Badge className={`shrink-0 ${SEV[f.severity] ?? "bg-slate-100 text-slate-600"}`}>{f.severity}</Badge>
                <span className="line-clamp-1">{f.title}</span>
              </div>
            ))}
            {dash.recent_findings.length === 0 && (
              <p className="text-xs text-muted-foreground">{t("agents.noFindings")}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-red-500" /> {t("agents.recentAlerts")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {dash.recent_alerts.slice(0, 5).map((a) => (
              <div key={a.id} className="flex items-start gap-2 text-sm">
                <Badge className={`shrink-0 ${SEV[a.severity] ?? "bg-slate-100 text-slate-600"}`}>{a.severity}</Badge>
                <span className="line-clamp-1">{a.title}</span>
              </div>
            ))}
            {dash.recent_alerts.length === 0 && (
              <p className="text-xs text-muted-foreground">{t("agents.noAlerts")}</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Agents Tab ────────────────────────────────────────────────────────────────

function AgentsTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [triggeredId, setTriggeredId] = useState<string | null>(null);

  const { data: agents = [], isLoading } = useQuery<MonitoringAgent[]>({
    queryKey: ["agents-list"],
    queryFn: () => apiClient.get("/agents").then((r) => r.data),
    refetchInterval: 15_000,
  });

  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      apiClient.patch(`/agents/${id}/enable?enabled=${enabled}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents-list"] }),
  });

  const trigger = useMutation({
    mutationFn: (agentType: string) =>
      apiClient.post("/agents/trigger", { agent_type: agentType }).then((r) => r.data),
    onSuccess: (_, agentType) => {
      setTriggeredId(agentType);
      qc.invalidateQueries({ queryKey: ["agents-list"] });
      setTimeout(() => setTriggeredId(null), 3000);
    },
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-3">
      {agents.map((agent) => (
        <Card key={agent.id}>
          <CardContent className="py-4">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1 flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium">{agent.name}</p>
                  <Badge className={STATUS_COL[agent.status] ?? "bg-slate-100 text-slate-600"}>
                    {agent.status}
                  </Badge>
                  {!agent.enabled && (
                    <Badge className="bg-slate-100 text-slate-500">disabled</Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">{agent.description}</p>
                <div className="flex flex-wrap gap-3 text-xs text-muted-foreground mt-1">
                  <span>{t("agents.intervalHours")}: {agent.run_interval_hours}h</span>
                  <span>{t("agents.runCount")}: {agent.run_count}</span>
                  <span>✓ {agent.success_count} / ✗ {agent.failure_count}</span>
                  {agent.last_run_at && <span>{t("agents.lastRun")}: {formatDate(agent.last_run_at)}</span>}
                  {agent.next_run_at && <span>{t("agents.nextRun")}: {formatDate(agent.next_run_at)}</span>}
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 text-xs"
                  disabled={trigger.isPending}
                  onClick={() => trigger.mutate(agent.agent_type)}
                >
                  {triggeredId === agent.agent_type ? (
                    <><CheckCircle2 className="h-3 w-3 mr-1 text-green-600" />{t("agents.triggered")}</>
                  ) : (
                    <><RotateCw className="h-3 w-3 mr-1" />{t("agents.trigger")}</>
                  )}
                </Button>
                <Button
                  size="sm"
                  variant={agent.enabled ? "outline" : "default"}
                  className="h-8 text-xs"
                  disabled={toggle.isPending}
                  onClick={() => toggle.mutate({ id: agent.id, enabled: !agent.enabled })}
                >
                  {agent.enabled
                    ? <><Pause className="h-3 w-3 mr-1" />{t("agents.disable")}</>
                    : <><Play className="h-3 w-3 mr-1" />{t("agents.enable")}</>}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
      {agents.length === 0 && (
        <div className="text-center py-12 text-muted-foreground text-sm">
          <Bot className="mx-auto mb-2 h-8 w-8 opacity-30" />
          {t("agents.noAgents")}
        </div>
      )}
    </div>
  );
}

// ── Findings Tab ──────────────────────────────────────────────────────────────

function FindingsTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [severityFilter, setSeverityFilter] = useState("");

  const { data: findings = [], isLoading } = useQuery<AgentFinding[]>({
    queryKey: ["agents-findings", severityFilter],
    queryFn: () =>
      apiClient.get("/agents/findings", {
        params: { status: "open", severity: severityFilter || undefined, limit: 100 },
      }).then((r) => r.data),
  });

  const acknowledge = useMutation({
    mutationFn: (id: string) => apiClient.post(`/agents/findings/${id}/acknowledge`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents-findings"] }),
  });

  const dismiss = useMutation({
    mutationFn: (id: string) => apiClient.post(`/agents/findings/${id}/dismiss`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents-findings"] }),
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap">
        {["", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
          <button
            key={sev || "all"}
            onClick={() => setSeverityFilter(sev)}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              severityFilter === sev
                ? "bg-slate-800 text-white border-slate-800"
                : "bg-slate-100 text-slate-700 hover:border-slate-400"
            }`}
          >
            {sev || "All"}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {findings.map((f) => (
          <Card key={f.id}>
            <CardContent className="py-4">
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1 flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge className={SEV[f.severity] ?? "bg-slate-100 text-slate-600"}>{f.severity}</Badge>
                    <span className="text-xs text-muted-foreground uppercase tracking-wide">{f.category}</span>
                  </div>
                  <p className="font-medium">{f.title}</p>
                  <p className="text-sm text-muted-foreground line-clamp-2">{f.description}</p>
                  <div className="flex items-center gap-3 mt-1">
                    {confBar(f.confidence_score)}
                    <span className="text-xs text-muted-foreground">{formatDate(f.detected_at)}</span>
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button
                    size="sm" variant="outline" className="h-8 text-xs"
                    disabled={acknowledge.isPending}
                    onClick={() => acknowledge.mutate(f.id)}
                  >
                    <CheckCircle2 className="h-3 w-3 mr-1 text-green-600" /> {t("agents.acknowledge")}
                  </Button>
                  <Button
                    size="sm" variant="ghost" className="h-8 text-xs text-muted-foreground"
                    disabled={dismiss.isPending}
                    onClick={() => dismiss.mutate(f.id)}
                  >
                    <X className="h-3 w-3 mr-1" /> {t("agents.dismiss")}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {findings.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">
            <CheckCircle2 className="mx-auto mb-2 h-8 w-8 text-green-500 opacity-50" />
            {t("agents.noFindings")}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Alerts Tab ────────────────────────────────────────────────────────────────

function AlertsTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const { data: alerts = [], isLoading } = useQuery<AgentAlert[]>({
    queryKey: ["agents-alerts"],
    queryFn: () => apiClient.get("/agents/alerts", { params: { unacknowledged_only: true, limit: 100 } }).then((r) => r.data),
    refetchInterval: 20_000,
  });

  const ack = useMutation({
    mutationFn: (id: string) => apiClient.post(`/agents/alerts/${id}/acknowledge`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents-alerts"] }),
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-3">
      {alerts.map((alert) => (
        <Card key={alert.id} className={alert.severity === "CRITICAL" ? "border-red-300" : ""}>
          <CardContent className="py-4 flex items-start justify-between gap-4">
            <div className="space-y-1 flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <Badge className={SEV[alert.severity] ?? "bg-slate-100 text-slate-600"}>{alert.severity}</Badge>
                <p className="font-medium">{alert.title}</p>
              </div>
              <p className="text-sm text-muted-foreground">{alert.message}</p>
              <p className="text-xs text-muted-foreground">{formatDate(alert.created_at)}</p>
            </div>
            <Button
              size="sm" variant="outline" className="h-8 text-xs shrink-0"
              disabled={ack.isPending}
              onClick={() => ack.mutate(alert.id)}
            >
              <CheckCircle2 className="h-3 w-3 mr-1 text-green-600" /> {t("agents.acknowledge")}
            </Button>
          </CardContent>
        </Card>
      ))}
      {alerts.length === 0 && (
        <div className="text-center py-12 text-muted-foreground text-sm">
          <CheckCircle2 className="mx-auto mb-2 h-8 w-8 text-green-500 opacity-50" />
          {t("agents.noAlerts")}
        </div>
      )}
    </div>
  );
}

// ── Drafts Tab ────────────────────────────────────────────────────────────────

function DraftsTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const { data: drafts = [], isLoading } = useQuery<RecommendationDraft[]>({
    queryKey: ["agents-drafts"],
    queryFn: () => apiClient.get("/agents/drafts", { params: { status: "pending", limit: 50 } }).then((r) => r.data),
  });

  const approve = useMutation({
    mutationFn: (id: string) => apiClient.post(`/agents/drafts/${id}/approve`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents-drafts"] }),
  });

  const reject = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      apiClient.post(`/agents/drafts/${id}/reject`, { reason }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agents-drafts"] });
      setRejectId(null); setRejectReason("");
    },
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-3">
      {drafts.map((draft) => (
        <Card key={draft.id}>
          <CardContent className="py-4 space-y-2">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1 flex-1 min-w-0">
                <p className="font-medium leading-snug">{draft.recommendation_text}</p>
                <p className="text-sm text-muted-foreground line-clamp-2">{draft.rationale}</p>
                <div className="flex items-center gap-3">
                  {confBar(draft.confidence_score)}
                  <span className="text-xs text-muted-foreground">{formatDate(draft.created_at)}</span>
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <Button
                  size="sm" variant="outline" className="h-8 text-xs text-green-700 border-green-300 hover:bg-green-50"
                  disabled={approve.isPending}
                  onClick={() => approve.mutate(draft.id)}
                >
                  {approve.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <ThumbsUp className="h-3 w-3 mr-1" />}
                  {t("agents.approve")}
                </Button>
                <Button
                  size="sm" variant="outline" className="h-8 text-xs text-red-700 border-red-300 hover:bg-red-50"
                  onClick={() => setRejectId(rejectId === draft.id ? null : draft.id)}
                >
                  <ThumbsDown className="h-3 w-3 mr-1" /> {t("agents.reject")}
                </Button>
              </div>
            </div>

            {rejectId === draft.id && (
              <div className="mt-2 space-y-2 border-t pt-2">
                <Label className="text-xs">{t("agents.rejectReason")} *</Label>
                <div className="flex gap-2">
                  <Input
                    className="h-8 text-xs"
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Explain why this recommendation is rejected…"
                  />
                  <Button
                    size="sm" className="h-8 text-xs shrink-0 bg-red-600 hover:bg-red-700"
                    disabled={!rejectReason || reject.isPending}
                    onClick={() => reject.mutate({ id: draft.id, reason: rejectReason })}
                  >
                    {reject.isPending
                      ? <><Loader2 className="h-3 w-3 animate-spin mr-1" />{t("agents.rejecting")}</>
                      : t("agents.reject")}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
      {drafts.length === 0 && (
        <div className="text-center py-12 text-muted-foreground text-sm">
          <CheckCircle2 className="mx-auto mb-2 h-8 w-8 text-green-500 opacity-50" />
          {t("agents.noDrafts")}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = "dashboard" | "agents" | "findings" | "alerts" | "drafts";

const tab_defs: { key: Tab; labelKey: keyof typeof import("@/lib/i18n/en").default; icon: React.ElementType }[] = [
  { key: "dashboard", labelKey: "agents.dashboardTab", icon: Activity },
  { key: "agents",    labelKey: "agents.agentsTab",    icon: Bot },
  { key: "findings",  labelKey: "agents.findingsTab",  icon: AlertTriangle },
  { key: "alerts",    labelKey: "agents.alertsTab",    icon: ShieldAlert },
  { key: "drafts",    labelKey: "agents.draftsTab",    icon: ChevronRight },
];

export default function AgentOpsPage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Bot className="h-7 w-7 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold">{t("agents.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("agents.subtitle")}</p>
        </div>
      </div>

      <div className="flex gap-1 border-b overflow-x-auto">
        {tab_defs.map(({ key, labelKey, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors ${
              activeTab === key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="h-4 w-4" />
            {t(labelKey)}
          </button>
        ))}
      </div>

      <div>
        {activeTab === "dashboard" && <DashboardTab />}
        {activeTab === "agents"    && <AgentsTab />}
        {activeTab === "findings"  && <FindingsTab />}
        {activeTab === "alerts"    && <AlertsTab />}
        {activeTab === "drafts"    && <DraftsTab />}
      </div>
    </div>
  );
}
