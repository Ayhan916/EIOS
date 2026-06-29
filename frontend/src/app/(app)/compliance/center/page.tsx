"use client";

import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  Clock,
  Shield,
  ShieldCheck,
  AlertTriangle,
  Lock,
  FileText,
  BarChart3,
} from "lucide-react";
import Link from "next/link";
import apiClient from "@/lib/api/client";
import { operatingSystemApi, type ESGControl } from "@/lib/api/operating-system";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ComplianceControl {
  id: string;
  control_id: string;
  title: string;
  category: string;
  status: "Implemented" | "In Progress" | "Not Started" | "Exempt";
  owner?: string;
  last_tested?: string;
  notes?: string;
}

interface ComplianceCenterData {
  soc2_readiness_pct: number;
  soc2_implemented: number;
  soc2_in_progress: number;
  soc2_not_started: number;
  soc2_total: number;
  open_critical_findings: number;
  controls?: ComplianceControl[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusBadge(status: string) {
  const map: Record<string, string> = {
    Implemented:  "bg-emerald-100 text-emerald-700",
    "In Progress": "bg-blue-100 text-blue-700",
    "Not Started": "bg-slate-100 text-slate-600",
    Exempt:       "bg-amber-100 text-amber-700",
  };
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${map[status] ?? "bg-slate-100 text-slate-600"}`}>
      {status}
    </span>
  );
}

// ── #136 Control Coverage Heatmap ────────────────────────────────────────────

const STATUSES = ["Implemented", "In Progress", "Not Started", "Exempt"] as const;
const STATUS_COLORS: Record<string, string> = {
  Implemented:  "bg-emerald-500",
  "In Progress": "bg-blue-400",
  "Not Started": "bg-slate-200",
  Exempt:       "bg-amber-300",
};
const STATUS_TEXT: Record<string, string> = {
  Implemented:  "text-white",
  "In Progress": "text-white",
  "Not Started": "text-slate-500",
  Exempt:       "text-amber-900",
};

function ControlHeatmap({ controls }: { controls: ESGControl[] }) {
  const types = Array.from(new Set(controls.map((c) => c.control_type))).sort();

  if (!types.length) {
    return <p className="text-sm text-muted-foreground py-4 text-center">No control data available.</p>;
  }

  const matrix: Record<string, Record<string, number>> = {};
  for (const t of types) {
    matrix[t] = {};
    for (const s of STATUSES) matrix[t][s] = 0;
  }
  for (const c of controls) {
    if (matrix[c.control_type] && STATUSES.includes(c.control_status as typeof STATUSES[number])) {
      matrix[c.control_type][c.control_status]++;
    }
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="text-left py-2 pr-4 font-semibold text-muted-foreground uppercase tracking-wide">Control Type</th>
            {STATUSES.map((s) => (
              <th key={s} className="text-center py-2 px-2 font-semibold text-muted-foreground uppercase tracking-wide whitespace-nowrap">{s}</th>
            ))}
            <th className="text-center py-2 px-2 font-semibold text-muted-foreground uppercase tracking-wide">Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {types.map((type) => {
            const row = matrix[type];
            const total = STATUSES.reduce((s, k) => s + (row[k] ?? 0), 0);
            return (
              <tr key={type}>
                <td className="py-2 pr-4 font-medium capitalize text-foreground whitespace-nowrap">
                  {type.replace(/_/g, " ")}
                </td>
                {STATUSES.map((s) => {
                  const count = row[s] ?? 0;
                  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                  return (
                    <td key={s} className="py-2 px-2 text-center">
                      {count > 0 ? (
                        <span className={`inline-flex items-center justify-center rounded px-2 py-0.5 font-semibold ${STATUS_COLORS[s]} ${STATUS_TEXT[s]}`}>
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
        {STATUSES.map((s) => (
          <div key={s} className="flex items-center gap-1.5">
            <span className={`inline-block h-2.5 w-2.5 rounded-sm ${STATUS_COLORS[s]}`} />
            <span className="text-xs text-muted-foreground">{s}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

const ADMIN_ROLES = new Set(["admin", "enterprise_admin", "bu_admin"]);

export default function ComplianceCenterPage() {
  const { user } = useAuth();

  const { data, isLoading } = useQuery<ComplianceCenterData>({
    queryKey: ["compliance-center"],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/executive/command-center");
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

  if (!user || !ADMIN_ROLES.has(user.role)) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3 text-center">
        <Lock className="h-10 w-10 text-muted-foreground/40" />
        <p className="text-sm font-medium">Admin access required</p>
        <p className="text-xs text-muted-foreground">This page is restricted to organization administrators.</p>
        <Link href="/dashboard" className="text-xs text-blue-600 hover:underline">← Back to Dashboard</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Compliance Center</h1>
          <p className="mt-1 text-sm text-muted-foreground">SOC 2 readiness, control status, and audit trail</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/enterprise/audit"
            className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium hover:bg-muted transition-colors"
          >
            <FileText className="h-4 w-4" />
            Audit Trail
          </Link>
          <Link
            href="/reports"
            className="flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <BarChart3 className="h-4 w-4" />
            Compliance Reports
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : (
        <>
          {/* KPI strip */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Card>
              <CardContent className="pt-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">SOC 2 Readiness</p>
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
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">Implemented</p>
                    <p className="mt-1 text-3xl font-bold text-emerald-600">{data?.soc2_implemented ?? "—"}</p>
                    <p className="text-xs text-muted-foreground">of {data?.soc2_total ?? "—"} controls</p>
                  </div>
                  <CheckCircle2 className="h-5 w-5 text-emerald-500 mt-0.5" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">In Progress</p>
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
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">Critical Findings</p>
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
                SOC 2 Type II Control Progress
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { label: "Implemented", count: data?.soc2_implemented ?? 0, color: "bg-emerald-500", textColor: "text-emerald-600" },
                { label: "In Progress",  count: data?.soc2_in_progress  ?? 0, color: "bg-blue-500",    textColor: "text-blue-600" },
                { label: "Not Started",  count: data?.soc2_not_started  ?? 0, color: "bg-slate-300",   textColor: "text-slate-500" },
              ].map(({ label, count, color, textColor }) => {
                const total = data?.soc2_total ?? 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={label}>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-medium">{label}</span>
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

          {/* #136 Control Coverage Heatmap */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-blue-500" />
                Control Coverage Heatmap
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ControlHeatmap controls={controls ?? []} />
            </CardContent>
          </Card>

          {/* Quick links */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {[
              { icon: Shield,      label: "View all controls",            href: "/operating-system/controls",            desc: "Control library and test status" },
              { icon: FileText,    label: "Compliance operations",         href: "/operating-system/compliance-operations", desc: "Operational compliance tracking" },
              { icon: ShieldCheck, label: "Compliance gap analysis",       href: "/compliance/gaps",                      desc: "Framework gap identification" },
            ].map(({ icon: Icon, label, href, desc }) => (
              <Link
                key={href}
                href={href}
                className="flex items-start gap-3 rounded-xl border border-border p-4 hover:bg-muted/50 transition-colors group"
              >
                <div className="rounded-lg bg-muted p-2 flex-shrink-0">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-sm font-semibold group-hover:text-primary">{label}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
