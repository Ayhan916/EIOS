"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Download, ExternalLink, Filter, GitBranch, Layers, Loader2, Plus, ShieldAlert, UserCheck, X } from "lucide-react";
import { useLanguage } from "@/lib/i18n/context";
import { EmptyState } from "@/components/ui/empty-state";
import { ReadinessBanner } from "@/components/layout/readiness-banner";
import Link from "next/link";
import apiClient from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

function authenticatedDownload(url: string, filename: string) {
  const token = typeof window !== "undefined" ? localStorage.getItem("eios_access_token") : null;
  fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    .then((r) => r.blob())
    .then((blob) => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
    });
}

function exportToCsv(rows: OrgFinding[], filename: string) {
  const headers = ["id", "title", "severity", "category", "status", "supplier_name", "assessment_id", "created_at"];
  const lines = [headers.join(",")];
  for (const r of rows) {
    lines.push(
      [r.id, `"${r.title.replace(/"/g, '""')}"`, r.severity, r.category || "", r.status, `"${r.supplier_name}"`, r.assessment_id, r.created_at ?? ""].join(",")
    );
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ── Types ─────────────────────────────────────────────────────────────────────

interface OrgFinding {
  id: string;
  title: string;
  severity: string;
  category: string;
  status: string;
  assessment_id: string;
  created_at: string | null;
  supplier_name: string;
  supplier_id: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const SEVERITY_STYLES: Record<string, string> = {
  Critical: "bg-red-100 text-red-800 border-red-200",
  High:     "bg-orange-100 text-orange-800 border-orange-200",
  Medium:   "bg-amber-100 text-amber-800 border-amber-200",
  Low:      "bg-slate-100 text-slate-700 border-slate-200",
};

const STATUS_STYLES: Record<string, string> = {
  Open:        "bg-slate-100 text-slate-700",
  InProgress:  "bg-blue-100 text-blue-700",
  Resolved:    "bg-amber-100 text-amber-700",
  Verified:    "bg-emerald-100 text-emerald-700",
};

function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${SEVERITY_STYLES[severity] ?? "bg-slate-100 text-slate-700"}`}>
      {severity === "Critical" && <AlertTriangle className="h-3 w-3" />}
      {severity}
    </span>
  );
}

// ── Severity counts ───────────────────────────────────────────────────────────

function SeveritySummary({ findings, onFilter }: { findings: OrgFinding[]; onFilter: (sev: string) => void }) {
  const counts: Record<string, number> = {};
  for (const f of findings) {
    counts[f.severity] = (counts[f.severity] ?? 0) + 1;
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {(["Critical", "High", "Medium", "Low"] as const).map((sev) => (
        <Card key={sev} className={`border cursor-pointer transition-colors hover:opacity-80 ${SEVERITY_STYLES[sev] ?? ""}`} onClick={() => onFilter(sev)}>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold tabular-nums">{counts[sev] ?? 0}</p>
            <p className="text-xs font-medium mt-0.5">{sev}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Inline Recommendation Form ────────────────────────────────────────────────

function CreateRecommendationInline({
  finding,
  onClose,
}: {
  finding: OrgFinding;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(`Remediate: ${finding.title}`);
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState(
    finding.severity === "Critical" ? "Critical"
    : finding.severity === "High" ? "High"
    : finding.severity === "Medium" ? "Medium"
    : "Low"
  );
  const [done, setDone] = useState(false);

  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/recommendations/", {
        title,
        description: description || `Remediate finding: ${finding.title}`,
        priority,
        assessment_id: finding.assessment_id,
      });
      return res.data;
    },
    onSuccess: () => {
      setDone(true);
      queryClient.invalidateQueries({ queryKey: ["org-findings"] });
      setTimeout(onClose, 1500);
    },
  });

  if (done) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-emerald-600 py-1">
        <CheckCircle2 className="h-3.5 w-3.5" />
        Recommendation created
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-2 rounded-lg border border-blue-200 bg-blue-50/60 p-3 dark:border-blue-800 dark:bg-blue-950/30">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-blue-700 dark:text-blue-400">Create Recommendation</p>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <input
        className="w-full rounded border border-input bg-background px-2 py-1 text-xs"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Title"
      />
      <textarea
        className="w-full rounded border border-input bg-background px-2 py-1 text-xs"
        rows={2}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Description (optional — defaults to finding title)"
      />
      <div className="flex items-center gap-2">
        <select
          className="h-7 rounded border border-input bg-background px-2 text-xs"
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
        >
          <option value="Critical">Critical</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        <Button
          size="sm"
          className="h-7 text-xs px-3"
          disabled={!title.trim() || createMutation.isPending}
          onClick={() => createMutation.mutate()}
        >
          {createMutation.isPending ? "Creating…" : "Create"}
        </Button>
      </div>
      {createMutation.isError && (
        <p className="text-xs text-red-600">Failed — please try again.</p>
      )}
    </div>
  );
}

// ── Link to Risk Form ─────────────────────────────────────────────────────────

function LinkToRiskInline({
  findingId,
  assessmentId,
  onClose,
}: {
  findingId: string;
  assessmentId: string;
  onClose: () => void;
}) {
  const [selectedRiskId, setSelectedRiskId] = useState("");
  const [done, setDone] = useState(false);

  const { data: risks } = useQuery({
    queryKey: ["org-risks-for-link"],
    queryFn: async () => {
      const res = await apiClient.get("/executive/risks?limit=100");
      return res.data as Array<{ id: string; title: string; risk_level: string }>;
    },
    staleTime: 60_000,
  });

  const linkMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/findings/${findingId}/risks/${selectedRiskId}`);
    },
    onSuccess: () => {
      setDone(true);
      setTimeout(onClose, 1200);
    },
  });

  if (done) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-emerald-600 py-1">
        <CheckCircle2 className="h-3.5 w-3.5" /> Risk linked
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-2 rounded-lg border border-violet-200 bg-violet-50/60 p-3 dark:border-violet-800 dark:bg-violet-950/30">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-violet-700 dark:text-violet-400">Link to Risk</p>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <select
        className="w-full h-7 rounded border border-input bg-background px-2 text-xs"
        value={selectedRiskId}
        onChange={(e) => setSelectedRiskId(e.target.value)}
      >
        <option value="">Select a risk…</option>
        {(risks ?? []).map((r) => (
          <option key={r.id} value={r.id}>[{r.risk_level}] {r.title}</option>
        ))}
      </select>
      <Button
        size="sm"
        className="h-7 text-xs px-3"
        disabled={!selectedRiskId || linkMutation.isPending}
        onClick={() => linkMutation.mutate()}
      >
        {linkMutation.isPending ? "Linking…" : "Link"}
      </Button>
      {linkMutation.isError && <p className="text-xs text-red-600">Failed — please try again.</p>}
    </div>
  );
}

// ── Finding Row ───────────────────────────────────────────────────────────────

function FindingRow({
  f,
  selected,
  onToggle,
}: {
  f: OrgFinding;
  selected: boolean;
  onToggle: () => void;
}) {
  const [showRecForm, setShowRecForm] = useState(false);
  const [showLinkForm, setShowLinkForm] = useState(false);

  return (
    <>
      <tr
        className={`hover:bg-muted/20 transition-colors ${selected ? "bg-blue-50/40 dark:bg-blue-950/20" : ""}`}
      >
        <td className="px-4 py-3">
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggle}
            className="rounded"
            aria-label={`Select ${f.title}`}
          />
        </td>
        <td className="px-4 py-3">
          <Link href={`/findings/${f.id}`} className="font-medium text-foreground hover:text-blue-600 hover:underline line-clamp-1 max-w-xs block">
            {f.title}
          </Link>
          {showRecForm && (
            <CreateRecommendationInline finding={f} onClose={() => setShowRecForm(false)} />
          )}
          {showLinkForm && (
            <LinkToRiskInline
              findingId={f.id}
              assessmentId={f.assessment_id}
              onClose={() => setShowLinkForm(false)}
            />
          )}
        </td>
        <td className="px-4 py-3">
          <SeverityBadge severity={f.severity} />
        </td>
        <td className="px-4 py-3 hidden sm:table-cell">
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
            {f.category || "—"}
          </span>
        </td>
        <td className="px-4 py-3">
          <Link
            href={`/suppliers/${f.supplier_id}`}
            className="text-blue-600 hover:underline text-xs"
          >
            {f.supplier_name}
          </Link>
        </td>
        <td className="px-4 py-3 hidden md:table-cell">
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[f.status] ?? "bg-slate-100 text-slate-600"}`}>
            {f.status}
          </span>
        </td>
        <td className="px-4 py-3 hidden lg:table-cell text-xs text-muted-foreground">
          {f.created_at ? new Date(f.created_at).toLocaleDateString() : "—"}
        </td>
        <td className="px-4 py-3 text-right">
          <div className="flex items-center justify-end gap-1.5">
            <button
              onClick={() => { setShowRecForm((s) => !s); setShowLinkForm(false); }}
              className="inline-flex items-center gap-1 rounded-md bg-violet-50 px-2 py-1 text-xs font-medium text-violet-700 hover:bg-violet-100 transition-colors"
              title="Create recommendation from this finding"
            >
              <Plus className="h-3 w-3" />
              Recommend
            </button>
            <button
              onClick={() => { setShowLinkForm((s) => !s); setShowRecForm(false); }}
              className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 transition-colors"
              title="Link this finding to a risk"
            >
              <GitBranch className="h-3 w-3" />
              Link Risk
            </button>
            <Link
              href={`/assessments/${f.assessment_id}`}
              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
            >
              <ExternalLink className="h-3 w-3" />
            </Link>
          </div>
        </td>
      </tr>
    </>
  );
}

// ── Bulk Status Panel ─────────────────────────────────────────────────────────

function BulkStatusPanel({
  ids,
  findings,
  onDone,
  onCancel,
}: {
  ids: string[];
  findings: OrgFinding[];
  onDone: () => void;
  onCancel: () => void;
}) {
  const qc = useQueryClient();
  const [status, setStatus] = useState("Resolved");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function apply() {
    setBusy(true);
    await Promise.all(ids.map((id) => apiClient.patch(`/findings/${id}`, { status })));
    qc.invalidateQueries({ queryKey: ["org-findings"] });

    try {
      const stored = JSON.parse(localStorage.getItem("eios_automation_rules") ?? "{}");
      const criticalIds = findings.filter((f) => ids.includes(f.id) && f.severity === "Critical").map((f) => f.id);

      // #152 Critical finding → trigger risk creation
      if (criticalIds.length > 0 && stored?.critical_finding_risk?.enabled !== false) {
        await apiClient.post("/automations/trigger", {
          rule_id: "critical_finding_risk",
          entity_type: "finding",
          payload: { finding_ids: criticalIds },
        }).catch(() => { /* silent */ });
      }

      // #157 JIRA ticket for any status-changed findings
      if (stored?.finding_jira_ticket?.enabled !== false) {
        const minSev = stored?.finding_jira_ticket?.config?.min_severity ?? "High";
        const sevOrder = ["Critical", "High", "Medium", "Low"];
        const minIdx = sevOrder.indexOf(minSev);
        const jiraIds = findings.filter((f) => ids.includes(f.id) && sevOrder.indexOf(f.severity) <= minIdx).map((f) => f.id);
        if (jiraIds.length > 0) {
          await apiClient.post("/automations/trigger", {
            rule_id: "finding_jira_ticket",
            entity_type: "finding",
            payload: {
              finding_ids: jiraIds,
              jira_project_key: stored?.finding_jira_ticket?.config?.jira_project_key ?? "",
              priority_mapping: stored?.finding_jira_ticket?.config?.priority_mapping ?? "severity",
            },
          }).catch(() => { /* silent */ });
        }
      }

      // #164 Remediation assignment when finding resolved/verified
      if ((status === "Resolved" || status === "Verified") && stored?.finding_remediation?.enabled !== false) {
        await apiClient.post("/automations/trigger", {
          rule_id: "finding_remediation",
          entity_type: "finding",
          payload: {
            finding_ids: ids,
            new_status: status,
            due_days: stored?.finding_remediation?.config?.due_days ?? 30,
            priority: stored?.finding_remediation?.config?.priority ?? "High",
          },
        }).catch(() => { /* silent */ });
      }
    } catch { /* silent */ }

    setDone(true);
    setBusy(false);
    setTimeout(onDone, 800);
  }

  if (done) return (
    <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50/60 px-4 py-3 text-xs text-emerald-700">
      <CheckCircle2 className="h-4 w-4" /> {ids.length} finding{ids.length !== 1 ? "s" : ""} updated to <strong>{status}</strong>
    </div>
  );

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50/60 px-4 py-3 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-slate-700">Bulk Status Change — {ids.length} finding{ids.length !== 1 ? "s" : ""}</p>
        <button onClick={onCancel}><X className="h-3.5 w-3.5 text-muted-foreground" /></button>
      </div>
      <div className="flex items-center gap-3">
        <select
          className="h-8 rounded border border-input bg-background px-2 text-xs"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="Open">Open</option>
          <option value="InProgress">In Progress</option>
          <option value="Resolved">Resolved</option>
          <option value="Verified">Verified</option>
        </select>
        <Button size="sm" className="h-8 text-xs" disabled={busy} onClick={apply}>
          {busy ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
          Apply to {ids.length}
        </Button>
        <button onClick={onCancel} className="text-xs text-muted-foreground hover:underline">Cancel</button>
      </div>
    </div>
  );
}

// ── Bulk Link to Risk Panel ───────────────────────────────────────────────────

function BulkLinkToRiskPanel({
  findings,
  onDone,
  onCancel,
}: {
  findings: OrgFinding[];
  onDone: () => void;
  onCancel: () => void;
}) {
  const qc = useQueryClient();
  const [riskId, setRiskId] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const { data: risks } = useQuery({
    queryKey: ["org-risks-for-bulk-link"],
    queryFn: async () => {
      const res = await apiClient.get("/executive/risks?limit=100");
      return res.data as Array<{ id: string; title: string; risk_level: string }>;
    },
    staleTime: 60_000,
  });

  async function link() {
    if (!riskId) return;
    setBusy(true);
    await Promise.all(findings.map((f) =>
      apiClient.post(`/findings/${f.id}/risks/${riskId}`)
        .catch(() => {})
    ));
    qc.invalidateQueries({ queryKey: ["org-findings"] });
    setDone(true);
    setBusy(false);
    setTimeout(onDone, 800);
  }

  if (done) return (
    <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50/60 px-4 py-3 text-xs text-emerald-700">
      <CheckCircle2 className="h-4 w-4" /> {findings.length} finding{findings.length !== 1 ? "s" : ""} linked to risk
    </div>
  );

  return (
    <div className="rounded-lg border border-violet-200 bg-violet-50/60 px-4 py-3 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-violet-700">Bulk Link to Risk — {findings.length} finding{findings.length !== 1 ? "s" : ""}</p>
        <button onClick={onCancel}><X className="h-3.5 w-3.5 text-muted-foreground" /></button>
      </div>
      <div className="flex items-center gap-3">
        <select
          className="flex-1 h-8 rounded border border-input bg-background px-2 text-xs"
          value={riskId}
          onChange={(e) => setRiskId(e.target.value)}
        >
          <option value="">Select a risk…</option>
          {(risks ?? []).map((r) => (
            <option key={r.id} value={r.id}>[{r.risk_level}] {r.title}</option>
          ))}
        </select>
        <Button size="sm" className="h-8 text-xs bg-violet-600 hover:bg-violet-700" disabled={!riskId || busy} onClick={link}>
          {busy ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
          Link {findings.length}
        </Button>
        <button onClick={onCancel} className="text-xs text-muted-foreground hover:underline">Cancel</button>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

// ── Bulk Escalate Panel ───────────────────────────────────────────────────────

function BulkEscalatePanel({
  findings,
  onDone,
  onCancel,
}: {
  findings: OrgFinding[];
  onDone: () => void;
  onCancel: () => void;
}) {
  const qc = useQueryClient();
  const highestSev = findings.some((f) => f.severity === "Critical")
    ? "Critical"
    : findings.some((f) => f.severity === "High")
    ? "High"
    : findings.some((f) => f.severity === "Medium")
    ? "Medium"
    : "Low";

  const [title, setTitle] = useState(
    `Bulk Remediation — ${findings.length} finding${findings.length !== 1 ? "s" : ""}`
  );
  const [description, setDescription] = useState(
    findings.map((f) => `• [${f.severity}] ${f.title} (${f.supplier_name})`).join("\n")
  );
  const [priority, setPriority] = useState(highestSev);
  const [done, setDone] = useState(false);

  const mutation = useMutation({
    mutationFn: async () => {
      await apiClient.post("/recommendations/", {
        title,
        description,
        priority,
        assessment_id: findings[0]?.assessment_id ?? null,
      });
    },
    onSuccess: () => {
      setDone(true);
      qc.invalidateQueries({ queryKey: ["org-findings"] });
      setTimeout(onDone, 1200);
    },
  });

  if (done) {
    return (
      <div className="flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
        <CheckCircle2 className="h-4 w-4" /> Recommendation created for {findings.length} findings
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-amber-800 flex items-center gap-1.5">
          <ShieldAlert className="h-4 w-4" />
          Escalate {findings.length} selected finding{findings.length !== 1 ? "s" : ""}
        </p>
        <button onClick={onCancel} className="text-muted-foreground hover:text-foreground">
          <X className="h-4 w-4" />
        </button>
      </div>
      <input
        className="w-full rounded border border-input bg-white px-3 py-1.5 text-sm"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Recommendation title"
      />
      <textarea
        className="w-full rounded border border-input bg-white px-3 py-1.5 text-sm font-mono text-xs"
        rows={Math.min(6, findings.length + 2)}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <div className="flex items-center gap-2">
        <select
          className="h-8 rounded border border-input bg-white px-2 text-sm"
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
        >
          <option value="Critical">Critical</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        <Button
          size="sm"
          className="bg-amber-600 hover:bg-amber-700 text-white"
          disabled={!title.trim() || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {mutation.isPending && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
          Create Recommendation
        </Button>
        <button onClick={onCancel} className="text-sm text-muted-foreground hover:underline">
          Cancel
        </button>
      </div>
      {mutation.isError && (
        <p className="text-xs text-red-600">{(mutation.error as Error).message}</p>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function FindingsPage() {
  const { t } = useLanguage();
  const searchParams = useSearchParams();
  const initSeverity = searchParams.get("severity") || "all";
  const initSupplier = searchParams.get("supplier_id") || "";
  const [severityFilter, setSeverityFilter] = useState<string>(initSeverity);
  const [supplierFilter] = useState<string>(initSupplier);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showBulkEscalate, setShowBulkEscalate] = useState(false);
  const [showBulkStatus, setShowBulkStatus] = useState(false);
  const [showBulkLink, setShowBulkLink] = useState(false);

  const { data: findings, isLoading } = useQuery<OrgFinding[]>({
    queryKey: ["org-findings", severityFilter, supplierFilter],
    queryFn: async () => {
      const p = new URLSearchParams();
      if (severityFilter !== "all") p.set("severity", severityFilter);
      if (supplierFilter) p.set("supplier_id", supplierFilter);
      const qs = p.toString() ? `?${p.toString()}` : "";
      const res = await apiClient.get(`/executive/findings${qs}`);
      return res.data;
    },
    staleTime: 30_000,
  });

  const allFindings = findings ?? [];

  function toggleAll() {
    if (selected.size === allFindings.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(allFindings.map((f) => f.id)));
    }
  }

  function toggleOne(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const selectedFindings = allFindings.filter((f) => selected.has(f.id));
  const allSelected = allFindings.length > 0 && selected.size === allFindings.length;

  return (
    <div className="space-y-6">
      <ReadinessBanner stepKey="findings" />
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("findings.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("findings.noFindingsDesc")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            className="h-8 rounded-md border border-input bg-background px-3 text-sm"
            value={severityFilter}
            onChange={(e) => { setSeverityFilter(e.target.value); setSelected(new Set()); }}
          >
            <option value="all">{t("findings.allSeverity")}</option>
            <option value="Critical">{t("findings.critical")}</option>
            <option value="High">{t("findings.high")}</option>
            <option value="Medium">{t("findings.medium")}</option>
            <option value="Low">Low</option>
          </select>

          {selected.size > 0 && (
            <>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 border-slate-300 text-slate-700"
                onClick={() => { setShowBulkStatus((v) => !v); setShowBulkEscalate(false); setShowBulkLink(false); }}
              >
                <UserCheck className="h-3.5 w-3.5" />
                Assign {selected.size}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 border-violet-300 text-violet-700"
                onClick={() => { setShowBulkLink((v) => !v); setShowBulkEscalate(false); setShowBulkStatus(false); }}
              >
                <GitBranch className="h-3.5 w-3.5" />
                Link Risk {selected.size}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 border-blue-300 text-blue-700"
                onClick={() => exportToCsv(selectedFindings, `findings-selected-${new Date().toISOString().split("T")[0]}.csv`)}
              >
                <Layers className="h-3.5 w-3.5" />
                Export {selected.size}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 border-amber-300 text-amber-700"
                onClick={() => { setShowBulkEscalate((v) => !v); setShowBulkStatus(false); setShowBulkLink(false); }}
              >
                <ShieldAlert className="h-3.5 w-3.5" />
                Escalate {selected.size}
              </Button>
            </>
          )}

          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => {
              const params = severityFilter !== "all" ? `?severity=${severityFilter}` : "";
              authenticatedDownload(
                `/executive/findings/export${params}`,
                `findings-${new Date().toISOString().split("T")[0]}.csv`
              );
            }}
          >
            <Download className="h-3.5 w-3.5" />
            CSV
          </Button>
        </div>
      </div>

      {showBulkStatus && selected.size > 0 && (
        <BulkStatusPanel
          ids={[...selected]}
          findings={selectedFindings}
          onDone={() => { setShowBulkStatus(false); setSelected(new Set()); }}
          onCancel={() => setShowBulkStatus(false)}
        />
      )}
      {showBulkLink && selected.size > 0 && (
        <BulkLinkToRiskPanel
          findings={selectedFindings}
          onDone={() => { setShowBulkLink(false); setSelected(new Set()); }}
          onCancel={() => setShowBulkLink(false)}
        />
      )}
      {showBulkEscalate && selected.size > 0 && (
        <BulkEscalatePanel
          findings={selectedFindings}
          onDone={() => { setShowBulkEscalate(false); setSelected(new Set()); }}
          onCancel={() => setShowBulkEscalate(false)}
        />
      )}

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : (
        <>
          {/* Severity summary */}
          {severityFilter === "all" && <SeveritySummary findings={allFindings} onFilter={(sev) => { setSeverityFilter(sev); setSelected(new Set()); }} />}

          {/* Findings table */}
          {allFindings.length === 0 ? (
            <div className="rounded-lg border border-dashed">
              <EmptyState
                icon={AlertTriangle}
                title={t("findings.noFindings")}
                description={severityFilter !== "all"
                  ? t("findings.noFindingsDesc")
                  : t("findings.noFindingsDesc")}
                actions={severityFilter === "all" ? [
                  { label: t("assessments.newAssessment"), href: "/assessments/new", variant: "primary" },
                  { label: t("suppliers.title"), href: "/suppliers", variant: "outline" },
                ] : undefined}
              />
            </div>
          ) : (
            <Card>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/30 text-xs text-muted-foreground">
                      <th className="px-4 py-3 text-left w-8">
                        <input
                          type="checkbox"
                          checked={allSelected}
                          onChange={toggleAll}
                          className="rounded"
                          aria-label="Select all"
                        />
                      </th>
                      <th className="px-4 py-3 text-left">Finding</th>
                      <th className="px-4 py-3 text-left">Severity</th>
                      <th className="px-4 py-3 text-left hidden sm:table-cell">Category</th>
                      <th className="px-4 py-3 text-left">Supplier</th>
                      <th className="px-4 py-3 text-left hidden md:table-cell">Status</th>
                      <th className="px-4 py-3 text-left hidden lg:table-cell">Date</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {allFindings.map((f) => (
                      <FindingRow
                        key={f.id}
                        f={f}
                        selected={selected.has(f.id)}
                        onToggle={() => toggleOne(f.id)}
                      />
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
