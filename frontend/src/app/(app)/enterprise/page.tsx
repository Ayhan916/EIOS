"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  BarChart3,
  Building2,
  Globe,
  Shield,
  Users,
} from "lucide-react";
import {
  listEnterprises,
  getEnterpriseDashboard,
  type EnterpriseDashboard,
} from "@/lib/api/enterprise";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";

function gradeColor(grade: string) {
  switch (grade) {
    case "A": return "bg-emerald-100 text-emerald-800";
    case "B": return "bg-blue-100 text-blue-800";
    case "C": return "bg-amber-100 text-amber-800";
    case "D": return "bg-orange-100 text-orange-800";
    default:  return "bg-red-100 text-red-800";
  }
}

function severityColor(s: string) {
  switch (s.toLowerCase()) {
    case "critical": return "bg-red-100 text-red-800";
    case "high":     return "bg-orange-100 text-orange-800";
    case "medium":   return "bg-amber-100 text-amber-800";
    default:         return "bg-emerald-100 text-emerald-800";
  }
}

function KpiCard({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  accent?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className={`mt-1 text-3xl font-semibold ${accent ?? ""}`}>
              {value}
            </p>
          </div>
          <div className="rounded-lg bg-slate-100 p-2">
            <Icon className="h-5 w-5 text-slate-600" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function HealthScoreCard({ data }: { data: EnterpriseDashboard }) {
  const { health_score: hs } = data;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Enterprise ESG Health Score</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-6">
          <div className="text-center">
            <p className="text-5xl font-bold">{hs.score.toFixed(0)}</p>
            <span className={`mt-1 inline-block rounded px-3 py-1 text-sm font-semibold ${gradeColor(hs.grade)}`}>
              Grade {hs.grade}
            </span>
          </div>
          <div className="flex-1 space-y-2">
            {Object.entries(hs.components).map(([key, val]) => (
              <div key={key} className="flex items-center gap-3">
                <p className="w-36 text-xs capitalize text-muted-foreground">
                  {key.replace(/_/g, " ")}
                </p>
                <div className="flex-1 rounded-full bg-slate-100 h-2">
                  <div
                    className="h-2 rounded-full bg-blue-500"
                    style={{ width: `${Math.min(100, val * 100)}%` }}
                  />
                </div>
                <p className="w-10 text-right text-xs font-mono">
                  {(val * 100).toFixed(0)}%
                </p>
              </div>
            ))}
          </div>
        </div>
        {hs.drivers.length > 0 && (
          <div className="mt-4 rounded-lg bg-slate-50 p-3">
            <p className="mb-1 text-xs font-semibold text-muted-foreground">Key Drivers</p>
            <ul className="space-y-1">
              {hs.drivers.map((d, i) => (
                <li key={i} className="text-xs text-slate-600">• {d}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function BURollupsTable({ data }: { data: EnterpriseDashboard }) {
  if (!data.bu_rollups.length) return null;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Business Unit Breakdown</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-xs text-muted-foreground">
              <th className="pb-2 text-left">Business Unit</th>
              <th className="pb-2 text-right">Orgs</th>
              <th className="pb-2 text-right">Suppliers</th>
              <th className="pb-2 text-right">Risks</th>
              <th className="pb-2 text-right">Critical</th>
              <th className="pb-2 text-right">Open Findings</th>
              <th className="pb-2 text-right">Compliance</th>
            </tr>
          </thead>
          <tbody>
            {data.bu_rollups.map((bu) => (
              <tr key={bu.business_unit_id} className="border-b last:border-0">
                <td className="py-2 font-medium">{bu.name}</td>
                <td className="py-2 text-right">{bu.organization_count}</td>
                <td className="py-2 text-right">{bu.supplier_count}</td>
                <td className="py-2 text-right">{bu.total_risks}</td>
                <td className="py-2 text-right text-red-600">{bu.critical_risks}</td>
                <td className="py-2 text-right">{bu.open_findings}</td>
                <td className="py-2 text-right">
                  <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                    bu.compliance_readiness >= 0.8
                      ? "bg-emerald-100 text-emerald-800"
                      : bu.compliance_readiness >= 0.5
                      ? "bg-amber-100 text-amber-800"
                      : "bg-red-100 text-red-800"
                  }`}>
                    {(bu.compliance_readiness * 100).toFixed(0)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function RegionRollupsTable({ data }: { data: EnterpriseDashboard }) {
  if (!data.region_rollups.length) return null;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Regional Breakdown</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-xs text-muted-foreground">
              <th className="pb-2 text-left">Region</th>
              <th className="pb-2 text-right">Orgs</th>
              <th className="pb-2 text-right">Suppliers</th>
              <th className="pb-2 text-right">Risks</th>
              <th className="pb-2 text-right">Open Findings</th>
              <th className="pb-2 text-right">Compliance</th>
            </tr>
          </thead>
          <tbody>
            {data.region_rollups.map((r) => (
              <tr key={r.region_id} className="border-b last:border-0">
                <td className="py-2 font-medium">{r.name}</td>
                <td className="py-2 text-right">{r.organization_count}</td>
                <td className="py-2 text-right">{r.supplier_count}</td>
                <td className="py-2 text-right">{r.total_risks}</td>
                <td className="py-2 text-right">{r.open_findings}</td>
                <td className="py-2 text-right">
                  <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                    r.compliance_readiness >= 0.8
                      ? "bg-emerald-100 text-emerald-800"
                      : r.compliance_readiness >= 0.5
                      ? "bg-amber-100 text-amber-800"
                      : "bg-red-100 text-red-800"
                  }`}>
                    {(r.compliance_readiness * 100).toFixed(0)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

export default function EnterpriseDashboardPage() {
  const { data: enterprises, isLoading: loadingList } = useQuery({
    queryKey: ["enterprises"],
    queryFn: listEnterprises,
  });

  const [selectedId, setSelectedId] = useState<string | null>(null);

  const activeId = selectedId ?? enterprises?.[0]?.id ?? null;

  const { data: dashboard, isLoading: loadingDash } = useQuery({
    queryKey: ["enterprise-dashboard", activeId],
    queryFn: () => getEnterpriseDashboard(activeId!),
    enabled: !!activeId,
  });

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Enterprise</h1>
          <p className="text-sm text-muted-foreground">
            Global ESG oversight across all entities
          </p>
        </div>
        {enterprises && enterprises.length > 1 && (
          <select
            className="rounded-lg border px-3 py-2 text-sm"
            value={activeId ?? ""}
            onChange={(e) => setSelectedId(e.target.value)}
          >
            {enterprises.map((e) => (
              <option key={e.id} value={e.id}>{e.name}</option>
            ))}
          </select>
        )}
      </div>

      {(loadingList || loadingDash) ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : !dashboard ? (
        <Card>
          <CardContent className="py-16 text-center text-muted-foreground">
            No enterprise configured. Create an enterprise to get started.
          </CardContent>
        </Card>
      ) : (
        <>
          {/* KPI strip */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <KpiCard label="Organizations" value={dashboard.rollup.organization_count} icon={Building2} />
            <KpiCard label="Suppliers" value={dashboard.rollup.supplier_count} icon={Globe} />
            <KpiCard label="Total Risks" value={dashboard.rollup.total_risks} icon={AlertTriangle} />
            <KpiCard
              label="Critical Risks"
              value={dashboard.rollup.critical_risks}
              icon={Shield}
              accent={(dashboard.rollup.critical_risks > 0) ? "text-red-600" : ""}
            />
            <KpiCard label="Open Findings" value={dashboard.rollup.open_findings} icon={BarChart3} />
            <KpiCard
              label="Compliance"
              value={`${(dashboard.rollup.compliance_readiness * 100).toFixed(0)}%`}
              icon={Users}
              accent={dashboard.rollup.compliance_readiness >= 0.8 ? "text-emerald-600" : "text-amber-600"}
            />
          </div>

          {/* Health score */}
          <HealthScoreCard data={dashboard} />

          {/* BU breakdown */}
          <BURollupsTable data={dashboard} />

          {/* Region breakdown */}
          <RegionRollupsTable data={dashboard} />
        </>
      )}
    </div>
  );
}
