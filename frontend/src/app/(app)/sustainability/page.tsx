"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle,
  Download,
  Leaf,
  Target,
  TrendingDown,
  Zap,
} from "lucide-react";
import { getDashboard, listScorecards, type SustainabilityScorecard } from "@/lib/api/sustainability";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

const ORG_ID = "default";

function KpiCard({
  label,
  value,
  icon: Icon,
  accent = "text-emerald-600",
  sub,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  accent?: string;
  sub?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="mt-1 text-3xl font-bold">{value}</p>
            {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
          </div>
          <Icon className={`h-6 w-6 ${accent}`} />
        </div>
      </CardContent>
    </Card>
  );
}

function ragBadge(status: string) {
  const cls =
    status === "GREEN"
      ? "bg-emerald-100 text-emerald-800"
      : status === "AMBER"
      ? "bg-amber-100 text-amber-800"
      : "bg-red-100 text-red-800";
  return (
    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold ${cls}`}>
      {status}
    </span>
  );
}

function downloadScorecardPDF(scorecards: SustainabilityScorecard[]) {
  const rows = scorecards.map((s) => `
    <tr>
      <td>${s.period_start} – ${s.period_end}</td>
      <td class="num">${s.environmental_score.toFixed(1)}</td>
      <td class="num">${s.social_score.toFixed(1)}</td>
      <td class="num">${s.governance_score.toFixed(1)}</td>
      <td class="num bold">${s.overall_score.toFixed(1)}</td>
      <td>${s.calculation_method ?? "—"}</td>
    </tr>`).join("");

  const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>Sustainability Scorecard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; padding: 32px; color: #0f172a; font-size: 13px; }
  h1 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
  .sub { color: #64748b; font-size: 11px; margin-bottom: 24px; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; }
  th { background: #f1f5f9; text-align: left; padding: 9px 12px; border: 1px solid #e2e8f0; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; color: #475569; }
  td { padding: 8px 12px; border: 1px solid #e2e8f0; }
  tr:nth-child(even) td { background: #f8fafc; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .bold { font-weight: 700; }
  @media print { body { padding: 0; } }
</style>
</head>
<body>
  <h1>Sustainability Scorecard</h1>
  <p class="sub">Generated ${new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" })} · EIOS Platform</p>
  <table>
    <thead>
      <tr>
        <th>Period</th>
        <th>Environmental</th>
        <th>Social</th>
        <th>Governance</th>
        <th>Overall</th>
        <th>Method</th>
      </tr>
    </thead>
    <tbody>${rows}</tbody>
  </table>
</body>
</html>`;

  const win = window.open("", "_blank", "width=900,height=650");
  if (!win) return;
  win.document.write(html);
  win.document.close();
  win.focus();
  // Short delay so styles render before print dialog opens
  setTimeout(() => { win.print(); }, 300);
}

export default function SustainabilityDashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["sustainability-dashboard", ORG_ID],
    queryFn: () => getDashboard(ORG_ID),
    retry: false,
  });

  const { data: scorecards } = useQuery({
    queryKey: ["sustainability-scorecards", ORG_ID],
    queryFn: () => listScorecards(ORG_ID),
    staleTime: 300_000,
  });

  if (isLoading) return <div className="flex justify-center p-12"><Spinner /></div>;
  if (error || !data)
    return (
      <div className="p-6 text-sm text-muted-foreground">
        No sustainability data yet. Create objectives and KPIs to get started.
      </div>
    );

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Sustainability Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">
            ESG performance, carbon accounting, and decarbonization progress
          </p>
        </div>
        {scorecards && scorecards.length > 0 && (
          <button
            onClick={() => downloadScorecardPDF(scorecards)}
            className="flex items-center gap-2 rounded-lg border px-4 py-2 text-sm hover:bg-muted/50 transition-colors flex-shrink-0"
          >
            <Download className="h-4 w-4" />
            Download Scorecard PDF
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
        <KpiCard label="Total Objectives" value={data.total_objectives} icon={Target} />
        <KpiCard
          label="Active Objectives"
          value={data.active_objectives}
          icon={CheckCircle}
          accent="text-blue-600"
        />
        <KpiCard label="Total KPIs" value={data.total_kpis} icon={BarChart3} />
        <KpiCard
          label="Open Alerts"
          value={data.open_alerts}
          icon={AlertTriangle}
          accent={data.open_alerts > 0 ? "text-amber-500" : "text-emerald-600"}
        />
        <KpiCard
          label="Total Emissions"
          value={
            data.total_emissions_tco2e != null
              ? `${data.total_emissions_tco2e.toLocaleString()} tCO₂e`
              : "—"
          }
          icon={Zap}
          accent="text-orange-500"
          sub={data.latest_inventory_year ? `${data.latest_inventory_year} (finalized)` : undefined}
        />
        <KpiCard
          label="Active Initiatives"
          value={data.active_initiatives}
          icon={TrendingDown}
          accent="text-emerald-600"
        />
        <KpiCard
          label="Active SBTs"
          value={data.active_sbts}
          icon={Leaf}
        />
        <KpiCard
          label="ESG Score"
          value={
            data.latest_overall_score != null
              ? `${data.latest_overall_score.toFixed(1)}`
              : "—"
          }
          icon={BarChart3}
          accent="text-purple-600"
          sub="Latest scorecard"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Objective Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total</span>
                <span className="font-medium">{data.total_objectives}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Active</span>
                <span className="font-medium text-blue-600">{data.active_objectives}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Completed</span>
                <span className="font-medium text-emerald-600">{data.completed_objectives}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Carbon Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Latest Inventory Year</span>
                <span className="font-medium">{data.latest_inventory_year ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Emissions</span>
                <span className="font-medium">
                  {data.total_emissions_tco2e != null
                    ? `${data.total_emissions_tco2e.toLocaleString()} tCO₂e`
                    : "—"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Active Initiatives</span>
                <span className="font-medium text-emerald-600">{data.active_initiatives}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
