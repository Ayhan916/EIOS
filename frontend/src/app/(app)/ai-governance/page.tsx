"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronRight,
  FileCode,
  FileText,
  Layers,
  Loader2,
  Plus,
  Shield,
} from "lucide-react";
import {
  getDashboard,
  listModels,
  reportIncidentFlat,
  createControl,
} from "@/lib/api/ai-governance";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";

const ORG_ID = "default";

// ── Sub-sections config ────────────────────────────────────────────────────────

const SECTIONS = [
  { href: "/ai-governance/models",     icon: Bot,        labelKey: "aiGov.modelsTitle",    descKey: "aiGov.modelsSubtitle"    },
  { href: "/ai-governance/use-cases",  icon: Layers,     labelKey: "aiGov.useCasesTitle",  descKey: "aiGov.useCasesSubtitle"  },
  { href: "/ai-governance/controls",   icon: Shield,     labelKey: "aiGov.controlsTitle",  descKey: "aiGov.controlsSubtitle"  },
  { href: "/ai-governance/monitoring", icon: Activity,   labelKey: "aiGov.monitoringTitle", descKey: "aiGov.monitoringSubtitle" },
  { href: "/ai-governance/incidents",  icon: AlertTriangle, labelKey: "aiGov.incidentsTitle", descKey: "aiGov.incidentsSubtitle" },
  { href: "/ai-governance/prompts",    icon: FileCode,   labelKey: "aiGov.promptsTitle",   descKey: "aiGov.promptsSubtitle"   },
  { href: "/ai-governance/reports",    icon: FileText,   labelKey: "aiGov.reportsTitle",   descKey: "aiGov.reportsSubtitle"   },
  { href: "/workflows",                icon: Activity,   labelKey: "nav.workflowMonitor",  descKey: "workflows.subtitle"      },
] as const;

// ── KPI card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, colour }: { label: string; value: number | string; colour?: string }) {
  return (
    <Card>
      <CardContent className="pt-5 pb-5">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className={`text-3xl font-bold mt-1 ${colour ?? "text-foreground"}`}>{value}</p>
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AIGovernancePage() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  // Quick-action form state
  const [showControl, setShowControl] = useState(false);
  const [ctrlName, setCtrlName] = useState("");
  const [ctrlType, setCtrlType] = useState("PREVENTIVE");
  const [ctrlDesc, setCtrlDesc] = useState("");

  const [showIncident, setShowIncident] = useState(false);
  const [incType, setIncType] = useState("HALLUCINATION");
  const [incSev, setIncSev] = useState("MEDIUM");
  const [incDesc, setIncDesc] = useState("");
  const [incModelId, setIncModelId] = useState("");

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["ai-governance-dashboard", ORG_ID],
    queryFn: () => getDashboard(ORG_ID),
    staleTime: 60_000,
    retry: false,
  });

  const { data: models = [] } = useQuery({
    queryKey: ["ai-models", ORG_ID],
    queryFn: () => listModels(ORG_ID),
    staleTime: 5 * 60_000,
    retry: false,
  });

  const addControl = useMutation({
    mutationFn: () => createControl(ORG_ID, {
      name: ctrlName,
      control_type: ctrlType,
      description: ctrlDesc || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-controls", ORG_ID] });
      qc.invalidateQueries({ queryKey: ["ai-governance-dashboard", ORG_ID] });
      setShowControl(false);
      setCtrlName(""); setCtrlType("PREVENTIVE"); setCtrlDesc("");
    },
  });

  const addIncident = useMutation({
    mutationFn: () => reportIncidentFlat(ORG_ID, {
      incident_type: incType,
      severity: incSev,
      description: incDesc,
      model_id: incModelId || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-incidents", ORG_ID] });
      qc.invalidateQueries({ queryKey: ["ai-governance-dashboard", ORG_ID] });
      setShowIncident(false);
      setIncType("HALLUCINATION"); setIncSev("MEDIUM"); setIncDesc(""); setIncModelId("");
    },
  });

  const d = dashboard;

  return (
    <div className="p-6 space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Bot className="h-6 w-6 text-primary" />
            {t("aiGov.title")}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">{t("aiGov.subtitle")}</p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => { setShowControl(!showControl); setShowIncident(false); }}>
            <Plus className="h-4 w-4 mr-1.5" /> {t("aiGov.addControl")}
          </Button>
          <Button size="sm" variant="outline" onClick={() => { setShowIncident(!showIncident); setShowControl(false); }}>
            <AlertTriangle className="h-4 w-4 mr-1.5" /> {t("aiGov.reportIncident")}
          </Button>
        </div>
      </div>

      {/* Create Control inline form */}
      {showControl && (
        <Card className="border-blue-200 bg-blue-50/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">{t("aiGov.addControl")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">{t("aiGov.controlsTitle")} Name *</Label>
                <Input className="mt-1" value={ctrlName} onChange={(e) => setCtrlName(e.target.value)} placeholder="e.g. Output Filtering" />
              </div>
              <div>
                <Label className="text-xs">Type</Label>
                <select className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={ctrlType} onChange={(e) => setCtrlType(e.target.value)}>
                  {["PREVENTIVE", "DETECTIVE", "CORRECTIVE"].map((v) => <option key={v}>{v}</option>)}
                </select>
              </div>
            </div>
            <div>
              <Label className="text-xs">Description</Label>
              <Input className="mt-1" value={ctrlDesc} onChange={(e) => setCtrlDesc(e.target.value)} placeholder="Describe what this control does…" />
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={() => setShowControl(false)}>{t("common.cancel")}</Button>
              <Button size="sm" disabled={!ctrlName || addControl.isPending} onClick={() => addControl.mutate()}>
                {addControl.isPending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                {t("common.save")}
              </Button>
            </div>
            {addControl.isSuccess && (
              <p className="text-xs text-green-700 flex items-center gap-1"><CheckCircle2 className="h-3 w-3" /> Control created.</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Report Incident inline form */}
      {showIncident && (
        <Card className="border-orange-200 bg-orange-50/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">{t("aiGov.reportIncident")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid sm:grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">{t("aiGov.incidentType")}</Label>
                <select className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={incType} onChange={(e) => setIncType(e.target.value)}>
                  {["HALLUCINATION","POLICY_VIOLATION","PRIVACY_CONCERN","BIAS_CONCERN","UNSAFE_OUTPUT","OTHER"].map((v) => (
                    <option key={v} value={v}>{v.replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-xs">{t("aiGov.severity")}</Label>
                <select className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={incSev} onChange={(e) => setIncSev(e.target.value)}>
                  {["LOW","MEDIUM","HIGH","CRITICAL"].map((v) => <option key={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <Label className="text-xs">AI Model (optional)</Label>
                <select className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={incModelId} onChange={(e) => setIncModelId(e.target.value)}>
                  <option value="">— none —</option>
                  {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </div>
            </div>
            <div>
              <Label className="text-xs">Description *</Label>
              <textarea className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                rows={2} value={incDesc} onChange={(e) => setIncDesc(e.target.value)}
                placeholder="Describe the incident…" />
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={() => setShowIncident(false)}>{t("common.cancel")}</Button>
              <Button size="sm" variant="destructive" disabled={!incDesc || addIncident.isPending} onClick={() => addIncident.mutate()}>
                {addIncident.isPending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                {t("aiGov.reportIncident")}
              </Button>
            </div>
            {addIncident.isSuccess && (
              <p className="text-xs text-green-700 flex items-center gap-1"><CheckCircle2 className="h-3 w-3" /> Incident reported.</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* KPI Dashboard */}
      {dashLoading ? (
        <div className="flex justify-center py-8"><Spinner /></div>
      ) : d ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <KpiCard label="Total Models" value={d.total_models} />
          <KpiCard label="Active Models" value={d.active_models} colour="text-green-600" />
          <KpiCard label="Total Use Cases" value={d.total_use_cases} />
          <KpiCard label="Pending Approvals" value={d.pending_approvals}
            colour={d.pending_approvals > 0 ? "text-amber-600" : undefined} />
          <KpiCard label="Open Incidents" value={d.open_incidents}
            colour={d.open_incidents > 0 ? "text-red-600" : undefined} />
          <KpiCard label="Unresolved Drift Alerts" value={d.unresolved_drift_alerts}
            colour={d.unresolved_drift_alerts > 0 ? "text-orange-600" : undefined} />
          <KpiCard label="Active Policies" value={d.active_policies} />
          <Card>
            <CardContent className="pt-5 pb-5">
              <p className="text-xs text-muted-foreground">Last Report Status</p>
              <p className={`text-lg font-semibold mt-1 ${
                d.last_report_status === "COMPLIANT" ? "text-green-600"
                : d.last_report_status ? "text-amber-600"
                : "text-muted-foreground"}`}>
                {d.last_report_status ?? "—"}
              </p>
            </CardContent>
          </Card>
        </div>
      ) : (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Dashboard-Daten nicht verfügbar. Stellen Sie sicher, dass der Backend-Server läuft.
        </div>
      )}

      {/* Section navigation grid */}
      <div>
        <h2 className="text-base font-semibold mb-4">Bereiche</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {SECTIONS.map((s) => {
            const Icon = s.icon;
            return (
              <Link key={s.href} href={s.href}
                className="group rounded-xl border border-border bg-card p-4 hover:border-primary/40 hover:shadow-sm transition-all">
                <div className="flex items-start justify-between mb-3">
                  <div className="rounded-lg bg-muted p-2">
                    <Icon className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors mt-0.5" />
                </div>
                <p className="text-sm font-semibold leading-tight">{t(s.labelKey as any)}</p>
                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{t(s.descKey as any)}</p>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
