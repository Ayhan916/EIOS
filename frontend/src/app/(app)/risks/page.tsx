"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { EmptyState } from "@/components/ui/empty-state";
import { ReadinessBanner } from "@/components/layout/readiness-banner";
import {
  AlertTriangle,
  ArrowUpCircle,
  CheckCircle2,
  Download,
  Filter,
  Layers,
  Loader2,
  ShieldAlert,
  UserCheck,
  X,
} from "lucide-react";
import { useLanguage } from "@/lib/i18n/context";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import Link from "next/link";
import apiClient from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

// ── Types ─────────────────────────────────────────────────────────────────────

interface OrgRisk {
  id: string;
  title: string;
  risk_level: string;
  status: string;
  owner: string | null;
  category: string;
  probability: number | null;
  impact: number | null;
  severity_score: number | null;
  probability_score: number | null;
  assessment_id: string;
  created_at: string | null;
  supplier_name: string;
  supplier_id: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const LEVEL_STYLES: Record<string, string> = {
  Critical: "bg-red-100 text-red-800 border-red-200",
  High:     "bg-orange-100 text-orange-800 border-orange-200",
  Medium:   "bg-amber-100 text-amber-800 border-amber-200",
  Low:      "bg-slate-100 text-slate-700 border-slate-200",
};

const STATUS_STYLES: Record<string, string> = {
  Draft:    "bg-slate-100 text-slate-600",
  Active:   "bg-blue-100 text-blue-700",
  Reviewed: "bg-violet-100 text-violet-700",
  Archived: "bg-emerald-100 text-emerald-700",
};

const STATUS_LABELS: Record<string, string> = {
  Draft:    "Open",
  Active:   "Active",
  Reviewed: "In Review",
  Archived: "Closed",
};

function RiskLevelBadge({ level }: { level: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
        LEVEL_STYLES[level] ?? "bg-slate-100 text-slate-700"
      }`}
    >
      {level === "Critical" && <AlertTriangle className="h-3 w-3" />}
      {level}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        STATUS_STYLES[status] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

function exportToCsv(rows: OrgRisk[], filename: string) {
  const headers = ["id", "title", "risk_level", "status", "owner", "category", "supplier_name", "assessment_id", "created_at"];
  const lines = [headers.join(",")];
  for (const r of rows) {
    lines.push(
      [
        r.id,
        `"${r.title.replace(/"/g, '""')}"`,
        r.risk_level,
        r.status,
        r.owner ?? "",
        r.category || "",
        `"${r.supplier_name}"`,
        r.assessment_id,
        r.created_at ?? "",
      ].join(",")
    );
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ── Inline Row Actions ────────────────────────────────────────────────────────

function RiskRow({
  risk,
  selected,
  onToggle,
}: {
  risk: OrgRisk;
  selected: boolean;
  onToggle: () => void;
}) {
  const queryClient = useQueryClient();
  const [showEscalateForm, setShowEscalateForm] = useState(false);
  const [assigneeName, setAssigneeName] = useState(risk.owner ?? "");
  const [escalated, setEscalated] = useState(false);

  const patchMutation = useMutation({
    mutationFn: async (patch: { status?: string; risk_level?: string; owner?: string }) => {
      const res = await apiClient.patch(`/risks/${risk.id}`, patch);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org-risks"] });
    },
  });

  function handleStatusChange(newStatus: string) {
    patchMutation.mutate({ status: newStatus });
  }

  function handleEscalate() {
    patchMutation.mutate({ risk_level: "Critical", owner: assigneeName || undefined });
    setEscalated(true);
    setShowEscalateForm(false);
    setTimeout(() => setEscalated(false), 2000);
  }

  const isLoading = patchMutation.isPending;

  return (
    <tr
      className={`hover:bg-muted/20 transition-colors ${
        selected ? "bg-blue-50/40 dark:bg-blue-950/20" : ""
      }`}
    >
      {/* Checkbox */}
      <td className="px-4 py-3 w-8">
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          className="rounded"
          aria-label={`Select ${risk.title}`}
        />
      </td>

      {/* Title */}
      <td className="px-4 py-3 max-w-xs">
        <Link href={`/risks/${risk.id}`} className="font-medium text-foreground hover:text-blue-600 hover:underline line-clamp-1 block">
          {risk.title}
        </Link>
        {risk.category && (
          <p className="text-xs text-muted-foreground mt-0.5">{risk.category}</p>
        )}
      </td>

      {/* Risk Level */}
      <td className="px-4 py-3">
        <RiskLevelBadge level={risk.risk_level} />
      </td>

      {/* Status dropdown */}
      <td className="px-4 py-3">
        <select
          className="h-7 rounded border border-input bg-background px-2 text-xs disabled:opacity-50"
          value={risk.status}
          disabled={isLoading}
          onChange={(e) => handleStatusChange(e.target.value)}
        >
          <option value="Draft">Open</option>
          <option value="Active">Active</option>
          <option value="Reviewed">In Review</option>
          <option value="Archived">Closed</option>
        </select>
      </td>

      {/* Supplier */}
      <td className="px-4 py-3 hidden sm:table-cell">
        <Link
          href={`/suppliers/${risk.supplier_id}`}
          className="text-blue-600 hover:underline text-xs"
        >
          {risk.supplier_name}
        </Link>
      </td>

      {/* Date */}
      <td className="px-4 py-3 hidden lg:table-cell text-xs text-muted-foreground">
        {risk.created_at ? new Date(risk.created_at).toLocaleDateString() : "—"}
      </td>

      {/* Actions */}
      <td className="px-4 py-3 text-right">
        <div className="flex items-center justify-end gap-1.5">
          {/* #93 Promote Draft to Active */}
          {risk.status === "Draft" && !showEscalateForm && (
            <button
              onClick={() => patchMutation.mutate({ status: "Active" })}
              disabled={isLoading}
              title="Promote to Active Risk"
              className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50 transition-colors"
            >
              <Layers className="h-3 w-3" /> Promote
            </button>
          )}
          {risk.risk_level !== "Critical" && !showEscalateForm && (
            <button
              onClick={() => setShowEscalateForm(true)}
              disabled={isLoading}
              title="Escalate to Critical"
              className="inline-flex items-center gap-1 rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-50 transition-colors"
            >
              {escalated ? (
                <CheckCircle2 className="h-3 w-3 text-emerald-600" />
              ) : (
                <ArrowUpCircle className="h-3 w-3" />
              )}
              {escalated ? "Escalated" : "Escalate"}
            </button>
          )}
          {showEscalateForm && (
            <div className="flex items-center gap-1">
              <input
                type="text"
                placeholder="Assignee name"
                value={assigneeName}
                onChange={(e) => setAssigneeName(e.target.value)}
                className="h-7 w-28 rounded border border-input bg-background px-2 text-xs"
                autoFocus
              />
              <button
                onClick={handleEscalate}
                disabled={isLoading}
                className="inline-flex items-center gap-1 rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                <ArrowUpCircle className="h-3 w-3" /> Confirm
              </button>
              <button
                onClick={() => setShowEscalateForm(false)}
                className="text-xs text-muted-foreground hover:text-foreground px-1"
              >
                ✕
              </button>
            </div>
          )}
          <Link
            href={`/assessments/${risk.assessment_id}`}
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
          >
            Assessment
          </Link>
        </div>
      </td>
    </tr>
  );
}

// ── Risk Heatmap ─────────────────────────────────────────────────────────────

const HEATMAP_COLORS: Record<string, string> = {
  Critical: "#ef4444",
  High:     "#f97316",
  Medium:   "#f59e0b",
  Low:      "#94a3b8",
};

function RiskHeatmap({ risks }: { risks: OrgRisk[] }) {
  const mapped = risks
    .filter((r) => r.probability != null && r.impact != null)
    .map((r) => ({
      x: r.probability!,
      y: r.impact!,
      title: r.title,
      level: r.risk_level,
    }));

  if (mapped.length === 0) return null;

  return (
    <Card>
      <CardContent className="pt-4">
        <p className="text-sm font-semibold mb-3">Risk Heatmap (Probability × Impact)</p>
        <ResponsiveContainer width="100%" height={220}>
          <ScatterChart margin={{ top: 4, right: 16, bottom: 16, left: 4 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="x"
              name="Probability"
              domain={[0, 1]}
              tickCount={6}
              tick={{ fontSize: 10 }}
              label={{ value: "Probability", position: "insideBottom", offset: -10, fontSize: 10 }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Impact"
              domain={[0, 1]}
              tickCount={6}
              tick={{ fontSize: 10 }}
              label={{ value: "Impact", angle: -90, position: "insideLeft", offset: 10, fontSize: 10 }}
            />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={({ payload }) => {
                if (!payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="rounded-md border bg-white px-2 py-1 text-xs shadow">
                    <p className="font-semibold">{d.title}</p>
                    <p className="text-muted-foreground">{d.level} · P:{(d.x * 100).toFixed(0)}% · I:{(d.y * 100).toFixed(0)}%</p>
                  </div>
                );
              }}
            />
            <Scatter data={mapped} r={6}>
              {mapped.map((d, idx) => (
                <Cell key={idx} fill={HEATMAP_COLORS[d.level] ?? "#94a3b8"} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
        <div className="flex items-center gap-3 mt-1 flex-wrap">
          {Object.entries(HEATMAP_COLORS).map(([level, color]) => (
            <span key={level} className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
              {level}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ── 10×10 Risk Matrix ─────────────────────────────────────────────────────────

function cellColor(row: number, col: number): string {
  const score = row * col;
  if (score >= 64) return "bg-red-500";
  if (score >= 36) return "bg-orange-400";
  if (score >= 16) return "bg-amber-300";
  return "bg-emerald-200";
}

function RiskMatrix10x10({ risks }: { risks: OrgRisk[] }) {
  const scored = risks.filter(
    (r) => r.severity_score != null && r.probability_score != null
  );
  const [hovered, setHovered] = useState<{ row: number; col: number } | null>(null);

  if (scored.length === 0) return null;

  // Build cell → risks map
  const cells: Record<string, OrgRisk[]> = {};
  for (const r of scored) {
    const key = `${r.probability_score}-${r.severity_score}`;
    if (!cells[key]) cells[key] = [];
    cells[key].push(r);
  }

  return (
    <Card>
      <CardContent className="pt-4">
        <p className="text-sm font-semibold mb-1">Risk Matrix (Probability × Severity — 1–10)</p>
        <p className="text-xs text-muted-foreground mb-3">
          Only risks with numeric scores are plotted ({scored.length}/{risks.length}).
        </p>
        <div className="overflow-x-auto">
          <div className="inline-flex flex-col gap-0.5 select-none">
            {/* Y-axis label */}
            <div className="flex gap-0.5 items-end">
              <div className="w-5 flex items-center justify-center" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)", fontSize: 9, color: "#94a3b8", height: 10 * 28 }}>
                Probability →
              </div>
              <div className="flex flex-col gap-0.5">
                {Array.from({ length: 10 }, (_, ri) => {
                  const row = 10 - ri; // row 10 (top) → probability 10
                  return (
                    <div key={row} className="flex gap-0.5 items-center">
                      <span className="w-5 text-right text-[9px] text-muted-foreground pr-1">{row}</span>
                      {Array.from({ length: 10 }, (_, ci) => {
                        const col = ci + 1; // col 1–10 = severity
                        const key = `${row}-${col}`;
                        const cellRisks = cells[key] ?? [];
                        const isHovered = hovered?.row === row && hovered?.col === col;
                        return (
                          <div
                            key={col}
                            onMouseEnter={() => setHovered({ row, col })}
                            onMouseLeave={() => setHovered(null)}
                            className={`relative w-7 h-7 rounded-sm flex items-center justify-center text-[10px] font-bold cursor-default transition-all ${cellColor(row, col)} ${
                              cellRisks.length > 0
                                ? "ring-2 ring-offset-0 ring-slate-700/40"
                                : "opacity-60"
                            } ${isHovered ? "scale-110 z-10 shadow-lg" : ""}`}
                          >
                            {cellRisks.length > 0 && (
                              <span className="text-slate-800">{cellRisks.length}</span>
                            )}
                            {isHovered && cellRisks.length > 0 && (
                              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 z-20 w-48 rounded-md border bg-white shadow-xl p-2 text-left pointer-events-none">
                                <p className="text-[10px] font-semibold text-slate-600 mb-1">
                                  P:{row} × S:{col} ({cellRisks.length} risk{cellRisks.length !== 1 ? "s" : ""})
                                </p>
                                {cellRisks.slice(0, 4).map((r) => (
                                  <p key={r.id} className="text-[10px] truncate text-slate-700">• {r.title}</p>
                                ))}
                                {cellRisks.length > 4 && (
                                  <p className="text-[10px] text-muted-foreground">+{cellRisks.length - 4} more</p>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  );
                })}
                {/* X axis labels */}
                <div className="flex gap-0.5 mt-0.5">
                  <span className="w-5" />
                  {Array.from({ length: 10 }, (_, ci) => (
                    <span key={ci + 1} className="w-7 text-center text-[9px] text-muted-foreground">{ci + 1}</span>
                  ))}
                </div>
                <p className="text-[9px] text-muted-foreground text-center mt-0.5 ml-5">Severity →</p>
              </div>
            </div>
          </div>
          {/* Legend */}
          <div className="flex items-center gap-3 mt-3 flex-wrap">
            {[["bg-emerald-200", "Low (1–15)"], ["bg-amber-300", "Moderate (16–35)"], ["bg-orange-400", "High (36–63)"], ["bg-red-500", "Critical (64–100)"]] as const}
            {(
              [
                ["bg-emerald-200", "Low (1–15)"],
                ["bg-amber-300", "Moderate (16–35)"],
                ["bg-orange-400", "High (36–63)"],
                ["bg-red-500", "Critical (64–100)"],
              ] as [string, string][]
            ).map(([cls, label]) => (
              <span key={label} className="flex items-center gap-1 text-[10px] text-muted-foreground">
                <span className={`h-2.5 w-2.5 rounded-sm ${cls}`} />
                {label}
              </span>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Summary Cards ─────────────────────────────────────────────────────────────

function LevelSummary({ risks }: { risks: OrgRisk[] }) {
  const counts: Record<string, number> = {};
  for (const r of risks) {
    counts[r.risk_level] = (counts[r.risk_level] ?? 0) + 1;
  }
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {(["Critical", "High", "Medium", "Low"] as const).map((lvl) => (
        <Card key={lvl} className={`border ${LEVEL_STYLES[lvl] ?? ""}`}>
          <CardContent className="pt-4 pb-3 text-center">
            <p className="text-2xl font-bold tabular-nums">{counts[lvl] ?? 0}</p>
            <p className="text-xs font-medium mt-0.5">{lvl}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Bulk Action Panels ────────────────────────────────────────────────────────

function BulkOwnerPanel({ ids, onDone, onCancel }: { ids: string[]; onDone: () => void; onCancel: () => void }) {
  const qc = useQueryClient();
  const [owner, setOwner] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function apply() {
    setBusy(true);
    await Promise.all(ids.map((id) => apiClient.patch(`/risks/${id}`, { owner })));
    qc.invalidateQueries({ queryKey: ["org-risks"] });
    setDone(true);
    setBusy(false);
    setTimeout(onDone, 800);
  }

  if (done) return (
    <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50/60 px-4 py-3 text-xs text-emerald-700">
      <CheckCircle2 className="h-4 w-4" /> {ids.length} risk{ids.length !== 1 ? "s" : ""} assigned to <strong>{owner}</strong>
    </div>
  );

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50/60 px-4 py-3 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-slate-700">Bulk Assign Owner — {ids.length} risk{ids.length !== 1 ? "s" : ""}</p>
        <button onClick={onCancel}><X className="h-3.5 w-3.5 text-muted-foreground" /></button>
      </div>
      <div className="flex items-center gap-3">
        <input
          className="flex-1 h-8 rounded border border-input bg-background px-2 text-xs"
          placeholder="Owner name or email"
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
        />
        <Button size="sm" className="h-8 text-xs" disabled={!owner.trim() || busy} onClick={apply}>
          {busy ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
          Assign {ids.length}
        </Button>
        <button onClick={onCancel} className="text-xs text-muted-foreground hover:underline">Cancel</button>
      </div>
    </div>
  );
}

function BulkRiskStatusPanel({ ids, onDone, onCancel }: { ids: string[]; onDone: () => void; onCancel: () => void }) {
  const qc = useQueryClient();
  const [status, setStatus] = useState("Active");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function apply() {
    setBusy(true);
    await Promise.all(ids.map((id) => apiClient.patch(`/risks/${id}`, { status })));
    qc.invalidateQueries({ queryKey: ["org-risks"] });
    setDone(true);
    setBusy(false);
    setTimeout(onDone, 800);
  }

  if (done) return (
    <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50/60 px-4 py-3 text-xs text-emerald-700">
      <CheckCircle2 className="h-4 w-4" /> {ids.length} risk{ids.length !== 1 ? "s" : ""} updated to <strong>{status}</strong>
    </div>
  );

  return (
    <div className="rounded-lg border border-orange-200 bg-orange-50/60 px-4 py-3 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-orange-700">Bulk Status Change — {ids.length} risk{ids.length !== 1 ? "s" : ""}</p>
        <button onClick={onCancel}><X className="h-3.5 w-3.5 text-muted-foreground" /></button>
      </div>
      <div className="flex items-center gap-3">
        <select
          className="h-8 rounded border border-input bg-background px-2 text-xs"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="Draft">Open</option>
          <option value="Active">Active</option>
          <option value="Reviewed">In Review</option>
          <option value="Archived">Closed</option>
        </select>
        <Button size="sm" className="h-8 text-xs bg-orange-600 hover:bg-orange-700" disabled={busy} onClick={apply}>
          {busy ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
          Apply to {ids.length}
        </Button>
        <button onClick={onCancel} className="text-xs text-muted-foreground hover:underline">Cancel</button>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function RisksPage() {
  const { t } = useLanguage();
  const searchParams = useSearchParams();
  const initLevel = searchParams.get("risk_level") || "all";
  const initSupplier = searchParams.get("supplier_id") || "";
  const [levelFilter, setLevelFilter] = useState<string>(initLevel);
  const [supplierFilter] = useState<string>(initSupplier);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [showBulkOwner, setShowBulkOwner] = useState(false);
  const [showBulkStatus, setShowBulkStatus] = useState(false);
  const queryClient = useQueryClient();

  const { data: risks, isLoading } = useQuery<OrgRisk[]>({
    queryKey: ["org-risks", levelFilter, supplierFilter],
    queryFn: async () => {
      const p = new URLSearchParams();
      if (levelFilter !== "all") p.set("risk_level", levelFilter);
      if (supplierFilter) p.set("supplier_id", supplierFilter);
      const qs = p.toString() ? `?${p.toString()}` : "";
      const res = await apiClient.get(`/executive/risks${qs}`);
      return res.data;
    },
    staleTime: 30_000,
  });

  const allRisks = risks ?? [];

  function toggleAll() {
    if (selected.size === allRisks.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(allRisks.map((r) => r.id)));
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

  const selectedRisks = allRisks.filter((r) => selected.has(r.id));
  const allSelected = allRisks.length > 0 && selected.size === allRisks.length;

  return (
    <div className="space-y-6">
      <ReadinessBanner stepKey="risks" />
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ShieldAlert className="h-6 w-6 text-orange-500" />
            {t("risks.title")}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("risks.noRisksDesc")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            className="h-8 rounded-md border border-input bg-background px-3 text-sm"
            value={levelFilter}
            onChange={(e) => {
              setLevelFilter(e.target.value);
              setSelected(new Set());
            }}
          >
            <option value="all">{t("risks.allLevels")}</option>
            <option value="Critical">{t("risks.critical")}</option>
            <option value="High">{t("risks.high")}</option>
            <option value="Medium">{t("risks.medium")}</option>
            <option value="Low">{t("risks.low")}</option>
          </select>

          {selected.size > 0 && (
            <>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 border-slate-300 text-slate-700"
                onClick={() => { setShowBulkOwner((v) => !v); setShowBulkStatus(false); }}
              >
                <UserCheck className="h-3.5 w-3.5" />
                Assign Owner {selected.size}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 border-orange-300 text-orange-700"
                onClick={() => { setShowBulkStatus((v) => !v); setShowBulkOwner(false); }}
              >
                <ArrowUpCircle className="h-3.5 w-3.5" />
                Change Status {selected.size}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 border-blue-300 text-blue-700"
                onClick={() =>
                  exportToCsv(
                    selectedRisks,
                    `risks-selected-${new Date().toISOString().split("T")[0]}.csv`
                  )
                }
              >
                <Layers className="h-3.5 w-3.5" />
                Export {selected.size}
              </Button>
            </>
          )}

          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() =>
              exportToCsv(
                allRisks,
                `risks-${new Date().toISOString().split("T")[0]}.csv`
              )
            }
          >
            <Download className="h-3.5 w-3.5" />
            CSV
          </Button>
        </div>
      </div>

      {showBulkOwner && selected.size > 0 && (
        <BulkOwnerPanel
          ids={[...selected]}
          onDone={() => { setShowBulkOwner(false); setSelected(new Set()); }}
          onCancel={() => setShowBulkOwner(false)}
        />
      )}
      {showBulkStatus && selected.size > 0 && (
        <BulkRiskStatusPanel
          ids={[...selected]}
          onDone={() => { setShowBulkStatus(false); setSelected(new Set()); }}
          onCancel={() => setShowBulkStatus(false)}
        />
      )}

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : (
        <>
          {levelFilter === "all" && <LevelSummary risks={allRisks} />}
          {levelFilter === "all" && <RiskHeatmap risks={allRisks} />}
          {levelFilter === "all" && <RiskMatrix10x10 risks={allRisks} />}

          {allRisks.length === 0 ? (
            <div className="rounded-lg border border-dashed">
              <EmptyState
                icon={ShieldAlert}
                title={t("risks.noRisks")}
                description={t("risks.noRisksDesc")}
                actions={levelFilter === "all" ? [
                  { label: t("assessments.newAssessment"), href: "/assessments/new", variant: "primary" },
                  { label: t("risks.newRisk"), href: "/risks/new", variant: "outline" },
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
                      <th className="px-4 py-3 text-left">Risk</th>
                      <th className="px-4 py-3 text-left">Level</th>
                      <th className="px-4 py-3 text-left">Status</th>
                      <th className="px-4 py-3 text-left hidden sm:table-cell">Supplier</th>
                      <th className="px-4 py-3 text-left hidden lg:table-cell">Date</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {allRisks.map((r) => (
                      <RiskRow
                        key={r.id}
                        risk={r}
                        selected={selected.has(r.id)}
                        onToggle={() => toggleOne(r.id)}
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
