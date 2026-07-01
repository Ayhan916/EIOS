"use client";

// ── Tier 7 — Workflow Automation Configuration (#151-165) ─────────────────────
// All 15 automation rules live here. Each rule stores its state in localStorage
// (`eios_automation_rules`) and syncs to /api/v1/automations/rules on save.
// The Activity tab fetches recent automation events from /api/v1/automations/activity.

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  BarChart3,
  Bell,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Leaf,
  Link2,
  Lock,
  Mail,
  MessageSquare,
  RefreshCw,
  Shield,
  ShieldAlert,
  Ticket,
  TrendingDown,
  Zap,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";

// ── Types ─────────────────────────────────────────────────────────────────────

type RuleCategory = "Compliance" | "Risk" | "Scoring" | "Notifications" | "Integrations" | "Sustainability";

interface RuleField {
  key: string;
  label: string;
  type: "number" | "select" | "text" | "email" | "boolean" | "multiselect";
  placeholder?: string;
  options?: string[];
  min?: number;
  max?: number;
  step?: number;
  defaultValue: string | number | boolean | string[];
  hint?: string;
}

interface AutomationRule {
  id: string;
  title: string;
  description: string;
  category: RuleCategory;
  icon: React.ElementType;
  fields: RuleField[];
  requiresIntegration?: string[];
}

interface RuleState {
  enabled: boolean;
  config: Record<string, string | number | boolean | string[]>;
}

interface ActivityEvent {
  id: string;
  rule_id: string;
  triggered_at: string;
  entity_type?: string;
  entity_id?: string;
  summary: string;
  outcome: "success" | "skipped" | "error";
}

// ── Rule definitions (all 15) ─────────────────────────────────────────────────

const RULES: AutomationRule[] = [
  // #151
  {
    id: "ofac_match_finding",
    title: "OFAC match → Create Finding",
    description: "Auto-create a finding when an OFAC sanctions match is detected for any supplier.",
    category: "Compliance",
    icon: ShieldAlert,
    fields: [
      { key: "finding_severity", label: "Finding severity", type: "select", options: ["LOW","MEDIUM","HIGH","CRITICAL"], defaultValue: "HIGH" },
      { key: "finding_category", label: "Finding category", type: "text", defaultValue: "SANCTIONS", placeholder: "SANCTIONS" },
    ],
  },
  // #152
  {
    id: "critical_finding_risk",
    title: "Critical finding → Create Risk",
    description: "Auto-create a risk record whenever a finding is raised with CRITICAL severity.",
    category: "Risk",
    icon: AlertTriangle,
    fields: [
      { key: "risk_level", label: "Risk level", type: "select", options: ["High","Critical"], defaultValue: "Critical" },
      { key: "auto_assign_owner", label: "Auto-assign finding owner as risk owner", type: "boolean", defaultValue: true },
    ],
  },
  // #153
  {
    id: "risk_status_notify",
    title: "Risk status change → Notify assignee",
    description: "Notify the assigned owner whenever a risk's status field changes.",
    category: "Risk",
    icon: Bell,
    fields: [
      { key: "channels", label: "Notification channels", type: "multiselect", options: ["email","teams","slack"], defaultValue: ["email"] },
      { key: "include_comment", label: "Include change comment in notification", type: "boolean", defaultValue: true },
    ],
  },
  // #154
  {
    id: "score_drop_reassessment",
    title: "Score drop below threshold → Schedule reassessment",
    description: "Auto-schedule a supplier reassessment when the ESG score falls below the configured threshold.",
    category: "Scoring",
    icon: TrendingDown,
    fields: [
      { key: "threshold", label: "Score threshold (0–100)", type: "number", defaultValue: 40, min: 0, max: 100 },
      { key: "days_until_assessment", label: "Schedule in (days)", type: "number", defaultValue: 14, min: 1, max: 90 },
    ],
  },
  // #155
  {
    id: "reg_gap_finding",
    title: "Regulatory deadline < threshold → Create Finding",
    description: "Auto-create a finding when a compliance gap has a deadline within the configured number of days.",
    category: "Compliance",
    icon: Clock,
    fields: [
      { key: "days_threshold", label: "Days before deadline", type: "number", defaultValue: 90, min: 7, max: 365 },
      { key: "severity", label: "Finding severity", type: "select", options: ["MEDIUM","HIGH","CRITICAL"], defaultValue: "HIGH" },
    ],
  },
  // #156
  {
    id: "rec_overdue_escalate",
    title: "Overdue recommendation → Escalate",
    description: "Automatically escalate a recommendation to management when it remains overdue beyond the threshold.",
    category: "Notifications",
    icon: Clock,
    fields: [
      { key: "overdue_days", label: "Overdue threshold (days)", type: "number", defaultValue: 14, min: 1, max: 90 },
      { key: "escalate_to", label: "Escalate to", type: "select", options: ["manager","admin","compliance_officer"], defaultValue: "admin" },
    ],
  },
  // #157
  {
    id: "finding_jira_ticket",
    title: "Finding created → JIRA ticket",
    description: "Auto-open a JIRA ticket when a new finding is raised (minimum severity configurable). Requires JIRA integration.",
    category: "Integrations",
    icon: Ticket,
    requiresIntegration: ["jira"],
    fields: [
      { key: "jira_project_key", label: "JIRA project key", type: "text", defaultValue: "", placeholder: "ESG" },
      { key: "min_severity", label: "Minimum severity", type: "select", options: ["LOW","MEDIUM","HIGH","CRITICAL"], defaultValue: "HIGH" },
      { key: "priority_mapping", label: "Map CRITICAL → JIRA priority", type: "select", options: ["Highest","High","Medium","Low"], defaultValue: "Highest" },
    ],
  },
  // #158
  {
    id: "critical_risk_teams",
    title: "Critical risk opened → Teams notification",
    description: "Post a message to the configured Teams channel when a Critical-level risk is created or escalated. Requires Teams integration.",
    category: "Integrations",
    icon: MessageSquare,
    requiresIntegration: ["teams"],
    fields: [
      { key: "include_supplier", label: "Include supplier name in message", type: "boolean", defaultValue: true },
      { key: "include_link", label: "Include direct link to risk", type: "boolean", defaultValue: true },
    ],
  },
  // #159
  {
    id: "supplier_ofac_scan",
    title: "New supplier created → OFAC scan",
    description: "Automatically run an OFAC SDN-list screen whenever a new supplier is added to the system.",
    category: "Compliance",
    icon: Shield,
    fields: [
      { key: "block_on_match", label: "Set supplier status to 'On Hold' if match found", type: "boolean", defaultValue: false },
      { key: "notify_admin", label: "Notify admin on match", type: "boolean", defaultValue: true },
    ],
  },
  // #160
  {
    id: "signal_supplier_link",
    title: "External signal → Link to supplier",
    description: "Automatically match incoming external risk signals to the most likely supplier record by name similarity.",
    category: "Scoring",
    icon: Link2,
    fields: [
      { key: "match_threshold", label: "Match confidence threshold (0.5–1.0)", type: "number", defaultValue: 0.8, min: 0.5, max: 1.0, step: 0.05 },
      { key: "require_confirmation", label: "Require manual confirmation below 0.95 confidence", type: "boolean", defaultValue: true },
    ],
  },
  // #161
  {
    id: "quarterly_sustainability",
    title: "Quarterly report → Email CSO",
    description: "Auto-generate the quarterly sustainability summary report and email it to the configured recipients.",
    category: "Sustainability",
    icon: Leaf,
    fields: [
      { key: "schedule", label: "Frequency", type: "select", options: ["monthly","quarterly","annually"], defaultValue: "quarterly" },
      { key: "recipients", label: "Recipients (comma-separated emails)", type: "text", defaultValue: "", placeholder: "cso@company.com, esg@company.com" },
      { key: "include_charts", label: "Include trend charts", type: "boolean", defaultValue: true },
    ],
  },
  // #162
  {
    id: "kpi_alert",
    title: "KPI measurement below target → Alert",
    description: "Send an alert when a sustainability KPI measurement is recorded below its configured target value.",
    category: "Scoring",
    icon: BarChart3,
    fields: [
      { key: "notify_kpi_owner", label: "Notify KPI owner", type: "boolean", defaultValue: true },
      { key: "channels", label: "Alert channels", type: "multiselect", options: ["email","teams","slack"], defaultValue: ["email"] },
    ],
  },
  // #163
  {
    id: "esg_score_update",
    title: "Assessment completed → Recalculate ESG score",
    description: "Automatically recalculate the supplier's ESG score whenever an assessment is marked complete.",
    category: "Scoring",
    icon: BarChart3,
    fields: [
      { key: "recalculate_org_score", label: "Also recalculate organisation-level score", type: "boolean", defaultValue: true },
      { key: "notify_supplier", label: "Notify supplier contact on score change", type: "boolean", defaultValue: false },
    ],
  },
  // #164
  {
    id: "finding_remediation",
    title: "Finding closed → Assign remediation to risk owner",
    description: "When a finding is closed, auto-create a remediation action item assigned to the corresponding risk owner.",
    category: "Risk",
    icon: CheckCircle2,
    fields: [
      { key: "due_days", label: "Remediation due in (days)", type: "number", defaultValue: 30, min: 1, max: 180 },
      { key: "priority", label: "Remediation priority", type: "select", options: ["Low","Medium","High","Critical"], defaultValue: "High" },
    ],
  },
  // #165
  {
    id: "ghg_carbon_link",
    title: "GHG calculation → Link carbon inventory",
    description: "Auto-link a completed GHG emission calculation to the matching carbon inventory entry by reporting period and scope.",
    category: "Sustainability",
    icon: Leaf,
    fields: [
      { key: "match_period", label: "Match by reporting period", type: "boolean", defaultValue: true },
      { key: "scope_mapping", label: "Scope to link", type: "select", options: ["scope1","scope2","scope3","all"], defaultValue: "all" },
    ],
  },
];

const CATEGORY_ORDER: RuleCategory[] = ["Compliance", "Risk", "Scoring", "Notifications", "Integrations", "Sustainability"];

const CATEGORY_COLORS: Record<RuleCategory, string> = {
  Compliance:    "border-red-200 bg-red-50/40",
  Risk:          "border-orange-200 bg-orange-50/40",
  Scoring:       "border-blue-200 bg-blue-50/40",
  Notifications: "border-violet-200 bg-violet-50/40",
  Integrations:  "border-slate-200 bg-slate-50/40",
  Sustainability:"border-emerald-200 bg-emerald-50/40",
};

const CATEGORY_DOT: Record<RuleCategory, string> = {
  Compliance:    "bg-red-500",
  Risk:          "bg-orange-500",
  Scoring:       "bg-blue-500",
  Notifications: "bg-violet-500",
  Integrations:  "bg-slate-500",
  Sustainability:"bg-emerald-500",
};

const STORAGE_KEY = "eios_automation_rules";

function defaultState(): Record<string, RuleState> {
  const out: Record<string, RuleState> = {};
  for (const rule of RULES) {
    const cfg: Record<string, string | number | boolean | string[]> = {};
    for (const f of rule.fields) cfg[f.key] = f.defaultValue;
    out[rule.id] = { enabled: true, config: cfg };
  }
  return out;
}

// ── Field renderer ────────────────────────────────────────────────────────────

function FieldEditor({
  field,
  value,
  onChange,
}: {
  field: RuleField;
  value: string | number | boolean | string[];
  onChange: (v: string | number | boolean | string[]) => void;
}) {
  if (field.type === "boolean") {
    const checked = value as boolean;
    return (
      <div className="flex items-center gap-3">
        <button
          role="switch"
          aria-checked={checked}
          onClick={() => onChange(!checked)}
          className={`relative inline-flex h-5 w-9 flex-shrink-0 rounded-full border-2 border-transparent transition-colors focus:outline-none ${checked ? "bg-blue-600" : "bg-slate-300 dark:bg-slate-700"}`}
        >
          <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${checked ? "translate-x-4" : "translate-x-0"}`} />
        </button>
        <span className="text-xs text-muted-foreground">{checked ? "Enabled" : "Disabled"}</span>
      </div>
    );
  }

  if (field.type === "select") {
    return (
      <select
        className="h-8 rounded-md border border-input bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
        value={value as string}
        onChange={(e) => onChange(e.target.value)}
      >
        {field.options?.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    );
  }

  if (field.type === "multiselect") {
    const selected = (value as string[]) ?? [];
    return (
      <div className="flex flex-wrap gap-1.5">
        {field.options?.map((o) => {
          const on = selected.includes(o);
          return (
            <button
              key={o}
              type="button"
              onClick={() => onChange(on ? selected.filter((x) => x !== o) : [...selected, o])}
              className={`rounded-full px-2.5 py-0.5 text-[10px] font-medium border transition-colors ${on ? "bg-primary text-primary-foreground border-primary" : "border-border text-muted-foreground hover:border-primary/50"}`}
            >
              {o}
            </button>
          );
        })}
      </div>
    );
  }

  if (field.type === "number") {
    return (
      <Input
        type="number"
        min={field.min}
        max={field.max}
        step={field.step ?? 1}
        value={value as number}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-8 w-28 text-xs"
      />
    );
  }

  return (
    <Input
      type={field.type === "email" ? "email" : "text"}
      value={value as string}
      placeholder={field.placeholder}
      onChange={(e) => onChange(e.target.value)}
      className="h-8 text-xs"
    />
  );
}

// ── Rule card ─────────────────────────────────────────────────────────────────

function RuleCard({
  rule,
  state,
  onChange,
  configuredIntegrations,
}: {
  rule: AutomationRule;
  state: RuleState;
  onChange: (s: RuleState) => void;
  configuredIntegrations: string[];
}) {
  const [expanded, setExpanded] = useState(false);
  const Icon = rule.icon;

  const missingIntegrations = (rule.requiresIntegration ?? []).filter(
    (i) => !configuredIntegrations.includes(i)
  );
  const blocked = missingIntegrations.length > 0;

  function setConfig(key: string, val: string | number | boolean | string[]) {
    onChange({ ...state, config: { ...state.config, [key]: val } });
  }

  return (
    <div className={`rounded-xl border p-4 transition-all ${CATEGORY_COLORS[rule.category]} ${state.enabled && !blocked ? "" : "opacity-70"}`}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-white shadow-sm">
          <Icon className="h-4 w-4 text-foreground" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-sm font-semibold">{rule.title}</p>
              <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{rule.description}</p>
            </div>
            <button
              role="switch"
              aria-checked={state.enabled && !blocked}
              disabled={blocked}
              onClick={() => !blocked && onChange({ ...state, enabled: !state.enabled })}
              className={`relative mt-0.5 inline-flex h-5 w-9 flex-shrink-0 rounded-full border-2 border-transparent transition-colors focus:outline-none disabled:cursor-not-allowed ${state.enabled && !blocked ? "bg-blue-600" : "bg-slate-300 dark:bg-slate-700"}`}
            >
              <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${state.enabled && !blocked ? "translate-x-4" : "translate-x-0"}`} />
            </button>
          </div>

          {blocked && (
            <div className="mt-2 flex items-center gap-1.5 rounded-md bg-amber-50 border border-amber-200 px-2.5 py-1.5 text-xs text-amber-700">
              <Lock className="h-3 w-3 flex-shrink-0" />
              Requires {missingIntegrations.join(", ")} integration to be configured in{" "}
              <a href="/settings/integrations" className="underline hover:text-amber-900">Settings → Integrations</a>
            </div>
          )}

          {rule.fields.length > 0 && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="mt-2 flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
            >
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {expanded ? "Hide" : "Configure"} ({rule.fields.length} option{rule.fields.length !== 1 ? "s" : ""})
            </button>
          )}

          {expanded && (
            <div className="mt-3 space-y-3 rounded-lg bg-white/70 border border-white/50 p-3">
              {rule.fields.map((field) => (
                <div key={field.key}>
                  <label className="text-[11px] font-medium text-foreground block mb-1">{field.label}</label>
                  <FieldEditor
                    field={field}
                    value={state.config[field.key] ?? field.defaultValue}
                    onChange={(v) => setConfig(field.key, v)}
                  />
                  {field.hint && <p className="mt-1 text-[10px] text-muted-foreground">{field.hint}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Activity log tab ──────────────────────────────────────────────────────────

const OUTCOME_STYLES: Record<string, string> = {
  success: "bg-emerald-100 text-emerald-700",
  skipped: "bg-slate-100 text-slate-600",
  error:   "bg-red-100 text-red-700",
};

const RULE_TITLE_MAP = Object.fromEntries(RULES.map((r) => [r.id, r.title]));

function ActivityTab() {
  const { data, isLoading } = useQuery<ActivityEvent[]>({
    queryKey: ["automation-activity"],
    queryFn: async () => {
      try {
        const res = await apiClient.get("/automations/activity?limit=100");
        return res.data?.items ?? res.data ?? [];
      } catch { return []; }
    },
    staleTime: 60_000,
  });

  const events = data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{events.length} event{events.length !== 1 ? "s" : ""} logged</p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : events.length === 0 ? (
        <div className="rounded-xl border border-dashed py-16 text-center">
          <Zap className="mx-auto mb-3 h-8 w-8 text-muted-foreground/30" />
          <p className="text-sm font-medium text-muted-foreground">No automation events yet</p>
          <p className="text-xs text-muted-foreground mt-1">Events will appear here as rules trigger.</p>
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {events.map((ev) => (
                <div key={ev.id} className="flex items-start gap-3 px-4 py-3 hover:bg-muted/20 transition-colors">
                  <span className={`mt-0.5 flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${OUTCOME_STYLES[ev.outcome] ?? "bg-slate-100 text-slate-600"}`}>
                    {ev.outcome}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">
                      {RULE_TITLE_MAP[ev.rule_id] ?? ev.rule_id}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">{ev.summary}</p>
                    {ev.entity_type && ev.entity_id && (
                      <p className="text-[10px] text-muted-foreground/60 mt-0.5 font-mono">
                        {ev.entity_type} · {ev.entity_id.slice(0, 12)}…
                      </p>
                    )}
                  </div>
                  <p className="flex-shrink-0 text-[10px] text-muted-foreground whitespace-nowrap">
                    {new Date(ev.triggered_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Admin guard ───────────────────────────────────────────────────────────────

const ADMIN_ROLES = new Set(["admin", "enterprise_admin", "bu_admin", "compliance_officer"]);

// ── Page ──────────────────────────────────────────────────────────────────────

const TABS = ["Rules", "Activity"] as const;
type Tab = (typeof TABS)[number];

export default function AutomationsPage() {
  const { user } = useAuth();
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<Tab>("Rules");
  const [ruleStates, setRuleStates] = useState<Record<string, RuleState>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<RuleCategory | "All">("All");

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
      if (stored) {
        // Merge: stored state + defaults for any new rules not in storage
        const merged = { ...defaultState(), ...stored };
        setRuleStates(merged);
      } else {
        setRuleStates(defaultState());
      }
    } catch {
      setRuleStates(defaultState());
    }
  }, []);

  // Fetch configured integrations to know which integration-dependent rules can be enabled
  const { data: orgSettings } = useQuery<{ integrations_configured: string[] }>({
    queryKey: ["org-settings-automations"],
    queryFn: async () => {
      try {
        const res = await apiClient.get("/commercial/organizations/me/settings");
        return res.data;
      } catch { return { integrations_configured: [] }; }
    },
    staleTime: 300_000,
  });
  const configuredIntegrations = orgSettings?.integrations_configured ?? [];

  function updateRule(id: string, state: RuleState) {
    setRuleStates((prev) => ({ ...prev, [id]: state }));
    setSaved(false);
  }

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ruleStates));
    try {
      await apiClient.post("/automations/rules/batch", { rules: ruleStates });
    } catch { /* graceful — stored locally regardless */ }
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  const enabledCount = Object.values(ruleStates).filter((s) => s.enabled).length;

  if (user && !ADMIN_ROLES.has(user.role)) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3 text-center">
        <Lock className="h-10 w-10 text-muted-foreground/40" />
        <p className="text-sm font-medium">Admin access required</p>
        <p className="text-xs text-muted-foreground">{t("settings.adminOnly")}</p>
      </div>
    );
  }

  const filteredRules = categoryFilter === "All"
    ? RULES
    : RULES.filter((r) => r.category === categoryFilter);

  const grouped = CATEGORY_ORDER.reduce<Record<string, AutomationRule[]>>((acc, cat) => {
    const items = filteredRules.filter((r) => r.category === cat);
    if (items.length) acc[cat] = items;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">Workflow Automations</h1>
            <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-700">
              {enabledCount}/{RULES.length} active
            </span>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Configure which workflow events trigger automatic actions in EIOS.
            Changes take effect immediately on save.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => {
            setRuleStates(defaultState());
            setSaved(false);
          }} className="gap-2">
            <RefreshCw className="h-3.5 w-3.5" /> Reset to defaults
          </Button>
          <Button size="sm" onClick={handleSave} disabled={saving} className="gap-2">
            {saving ? <><Zap className="h-3.5 w-3.5 animate-pulse" /> {t("settings.saving")}</> : saved ? "✓ Saved" : <><Zap className="h-3.5 w-3.5" /> {t("settings.saveChanges")}</>}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border gap-0">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "Activity" ? (
        <ActivityTab />
      ) : (
        <>
          {/* Category filter */}
          <div className="flex flex-wrap gap-1.5">
            {(["All", ...CATEGORY_ORDER] as const).map((cat) => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat as typeof categoryFilter)}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  categoryFilter === cat
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {cat !== "All" && (
                  <span className={`h-1.5 w-1.5 rounded-full ${CATEGORY_DOT[cat as RuleCategory]}`} />
                )}
                {cat}
                {cat !== "All" && (
                  <span className="opacity-60">
                    ({RULES.filter((r) => r.category === cat).length})
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Rule groups */}
          <div className="space-y-6">
            {Object.entries(grouped).map(([cat, rules]) => (
              <div key={cat}>
                <div className="mb-3 flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${CATEGORY_DOT[cat as RuleCategory]}`} />
                  <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">{cat}</h2>
                  <span className="text-xs text-muted-foreground/60">
                    {rules.filter((r) => ruleStates[r.id]?.enabled).length}/{rules.length} enabled
                  </span>
                </div>
                <div className="space-y-3">
                  {rules.map((rule) => (
                    <RuleCard
                      key={rule.id}
                      rule={rule}
                      state={ruleStates[rule.id] ?? { enabled: true, config: {} }}
                      onChange={(s) => updateRule(rule.id, s)}
                      configuredIntegrations={configuredIntegrations}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Sticky save bar */}
          <div className="sticky bottom-0 border-t border-border bg-background/95 backdrop-blur py-3 px-1 flex items-center justify-between">
            <p className="text-xs text-muted-foreground">{enabledCount} of {RULES.length} rules enabled</p>
            <div className="flex items-center gap-3">
              {saved && <span className="text-xs text-emerald-600 font-medium">Changes saved</span>}
              <Button size="sm" onClick={handleSave} disabled={saving} className="gap-2">
                {saving ? <><Zap className="h-3.5 w-3.5 animate-pulse" /> {t("settings.saving")}</> : <><Zap className="h-3.5 w-3.5" /> {t("settings.saveChanges")}</>}
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
