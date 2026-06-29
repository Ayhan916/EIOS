"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  DollarSign,
  Leaf,
  Shield,
  TrendingUp,
  Activity,
  FileText,
  Building2,
} from "lucide-react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import {
  listCarbonCostModels,
  listValueInitiatives,
  listTaxonomyAssessments,
  listGreenRevenue,
  listFinanceInstruments,
  listCapitalMarketsAssessments,
  listReports,
} from "@/lib/api/financial-esg";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";

const DONUT_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

function KpiCard({
  label,
  value,
  icon: Icon,
  accent = "text-blue-600",
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

export default function FinancialESGDashboard() {
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";

  const { data: carbonModels, isLoading: l1 } = useQuery({
    queryKey: ["fin-esg", "carbon-cost", orgId],
    queryFn: () => listCarbonCostModels(orgId),
  });
  const { data: initiatives, isLoading: l2 } = useQuery({
    queryKey: ["fin-esg", "value-creation", orgId],
    queryFn: () => listValueInitiatives(orgId),
  });
  const { data: taxonomyItems, isLoading: l3 } = useQuery({
    queryKey: ["fin-esg", "taxonomy", orgId],
    queryFn: () => listTaxonomyAssessments(orgId),
  });
  const { data: greenRevRecords, isLoading: l4 } = useQuery({
    queryKey: ["fin-esg", "green-revenue", orgId],
    queryFn: () => listGreenRevenue(orgId),
  });
  const { data: instruments, isLoading: l5 } = useQuery({
    queryKey: ["fin-esg", "finance", orgId],
    queryFn: () => listFinanceInstruments(orgId),
  });
  const { data: readinessItems, isLoading: l6 } = useQuery({
    queryKey: ["fin-esg", "readiness", orgId],
    queryFn: () => listCapitalMarketsAssessments(orgId),
  });
  const { data: reports, isLoading: l7 } = useQuery({
    queryKey: ["fin-esg", "reports", orgId],
    queryFn: () => listReports(orgId),
  });

  const isLoading = l1 || l2 || l3 || l4 || l5 || l6 || l7;

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const totalCarbonCost = (carbonModels ?? []).reduce(
    (s, m) => s + m.total_carbon_cost,
    0
  );
  const totalRegulatoryExposure = (carbonModels ?? []).reduce(
    (s, m) => s + m.regulatory_exposure,
    0
  );
  const totalInvestment = (initiatives ?? []).reduce(
    (s, i) => s + i.investment_amount,
    0
  );
  const totalRealizedValue = (initiatives ?? []).reduce(
    (s, i) => s + i.realized_value,
    0
  );
  const latestTaxonomy = (taxonomyItems ?? []).sort(
    (a, b) => b.assessment_year - a.assessment_year
  )[0];
  const totalGreenRevenue = (greenRevRecords ?? []).reduce(
    (s, r) =>
      r.alignment_status === "ALIGNED" || r.alignment_status === "ELIGIBLE"
        ? s + r.amount
        : s,
    0
  );
  const totalFinanceExposure = (instruments ?? []).reduce(
    (s, i) => s + i.amount,
    0
  );
  const latestReadiness = (readinessItems ?? []).sort(
    (a, b) => new Date(b.assessed_at).getTime() - new Date(a.assessed_at).getTime()
  )[0];

  const readinessBadge =
    latestReadiness?.overall_readiness === "READY"
      ? "text-green-600"
      : latestReadiness?.overall_readiness === "PARTIAL"
      ? "text-amber-600"
      : "text-red-600";

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Financial ESG Dashboard</h1>
        <p className="text-muted-foreground">
          Connect sustainability outcomes to financial value
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard
          label="Total Carbon Cost"
          value={`$${(totalCarbonCost / 1_000_000).toFixed(1)}M`}
          icon={Activity}
          accent="text-orange-600"
          sub={`$${(totalRegulatoryExposure / 1_000_000).toFixed(1)}M regulatory exposure`}
        />
        <KpiCard
          label="Value Created"
          value={`$${(totalRealizedValue / 1_000_000).toFixed(1)}M`}
          icon={TrendingUp}
          accent="text-green-600"
          sub={`of $${(totalInvestment / 1_000_000).toFixed(1)}M invested`}
        />
        <KpiCard
          label="Taxonomy Alignment"
          value={
            latestTaxonomy
              ? `${latestTaxonomy.aligned_percent.toFixed(1)}%`
              : "—"
          }
          icon={Leaf}
          accent="text-emerald-600"
          sub={
            latestTaxonomy
              ? `${latestTaxonomy.taxonomy_framework} · ${latestTaxonomy.assessment_year}`
              : "No assessments"
          }
        />
        <KpiCard
          label="Sustainable Finance"
          value={`$${(totalFinanceExposure / 1_000_000).toFixed(1)}M`}
          icon={DollarSign}
          accent="text-blue-600"
          sub={`${(instruments ?? []).length} instruments`}
        />
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard
          label="Green Revenue"
          value={`$${(totalGreenRevenue / 1_000_000).toFixed(1)}M`}
          icon={BarChart3}
          accent="text-teal-600"
          sub={`${(greenRevRecords ?? []).length} records`}
        />
        <KpiCard
          label="Capital Markets"
          value={latestReadiness?.overall_readiness ?? "—"}
          icon={Building2}
          accent={readinessBadge}
          sub="Overall readiness"
        />
        <KpiCard
          label="Value Initiatives"
          value={(initiatives ?? []).length}
          icon={Shield}
          accent="text-purple-600"
          sub={`${(initiatives ?? []).filter((i) => i.initiative_status === "ACTIVE").length} active`}
        />
        <KpiCard
          label="Reports"
          value={(reports ?? []).length}
          icon={FileText}
          accent="text-slate-600"
          sub={`${(reports ?? []).filter((r) => r.is_final).length} finalized`}
        />
      </div>

      {/* #66 Waterfall: Investment vs Realized Value by initiative */}
      {(initiatives ?? []).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Value Creation Waterfall</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={(initiatives ?? []).slice(0, 8).map((i) => ({
                  name: i.name.length > 16 ? i.name.slice(0, 14) + "…" : i.name,
                  invested: i.investment_amount / 1_000,
                  realized: i.realized_value / 1_000,
                }))}
                margin={{ top: 4, right: 8, bottom: 32, left: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" interval={0} />
                <YAxis tick={{ fontSize: 10 }} unit="k" />
                <Tooltip formatter={(v: number) => `$${v.toFixed(0)}k`} />
                <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="invested" name="Invested ($k)" fill="#6366f1" radius={[3, 3, 0, 0]} />
                <Bar dataKey="realized" name="Realized ($k)" fill="#10b981" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* #67 Trend: Carbon cost by assessment year */}
      {(carbonModels ?? []).length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Carbon Cost Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart
                data={[...new Map(
                  (carbonModels ?? []).map((m) => [m.assessment_year, m])
                ).values()]
                  .sort((a, b) => a.assessment_year - b.assessment_year)
                  .map((m) => ({
                    year: m.assessment_year,
                    cost: m.total_carbon_cost / 1_000_000,
                    exposure: m.regulatory_exposure / 1_000_000,
                  }))}
                margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="year" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} unit="M" />
                <Tooltip formatter={(v: number) => `$${v.toFixed(2)}M`} />
                <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="cost" name="Carbon Cost ($M)" stroke="#f97316" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="exposure" name="Regulatory Exposure ($M)" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} strokeDasharray="4 2" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* #68 Donut: Finance instruments by type */}
      {(instruments ?? []).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Instrument Type Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-6">
            <ResponsiveContainer width="50%" height={180}>
              <PieChart>
                <Pie
                  data={Object.entries(
                    (instruments ?? []).reduce<Record<string, number>>((acc, i) => {
                      acc[i.instrument_type] = (acc[i.instrument_type] ?? 0) + i.amount;
                      return acc;
                    }, {})
                  ).map(([name, value]) => ({ name: name.replace(/_/g, " "), value }))}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  dataKey="value"
                >
                  {Object.keys(
                    (instruments ?? []).reduce<Record<string, number>>((acc, i) => {
                      acc[i.instrument_type] = 1;
                      return acc;
                    }, {})
                  ).map((_, idx) => (
                    <Cell key={idx} fill={DONUT_COLORS[idx % DONUT_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => `$${(v / 1_000_000).toFixed(1)}M`} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-1.5 text-xs">
              {Object.entries(
                (instruments ?? []).reduce<Record<string, number>>((acc, i) => {
                  acc[i.instrument_type] = (acc[i.instrument_type] ?? 0) + i.amount;
                  return acc;
                }, {})
              ).map(([type, amount], idx) => (
                <div key={type} className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full flex-shrink-0" style={{ background: DONUT_COLORS[idx % DONUT_COLORS.length] }} />
                  <span className="text-muted-foreground truncate max-w-28">{type.replace(/_/g, " ")}</span>
                  <span className="font-medium ml-auto">${(amount / 1_000_000).toFixed(1)}M</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Carbon Cost Models</CardTitle>
          </CardHeader>
          <CardContent>
            {(carbonModels ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No carbon cost models</p>
            ) : (
              <div className="space-y-2">
                {(carbonModels ?? []).slice(0, 5).map((m) => (
                  <div
                    key={m.id}
                    className="flex items-center justify-between rounded border px-3 py-2"
                  >
                    <div>
                      <p className="text-sm font-medium">{m.name}</p>
                      <p className="text-xs text-muted-foreground">{m.assessment_year}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold">
                        ${m.total_carbon_cost.toLocaleString()}
                      </p>
                      <p className="text-xs text-muted-foreground">{m.currency}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Sustainable Finance Instruments</CardTitle>
          </CardHeader>
          <CardContent>
            {(instruments ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No instruments</p>
            ) : (
              <div className="space-y-2">
                {(instruments ?? []).slice(0, 5).map((i) => (
                  <div
                    key={i.id}
                    className="flex items-center justify-between rounded border px-3 py-2"
                  >
                    <div>
                      <p className="text-sm font-medium">{i.name}</p>
                      <p className="text-xs text-muted-foreground capitalize">
                        {i.instrument_type.replace(/_/g, " ")}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold">
                        ${i.amount.toLocaleString()}
                      </p>
                      <span
                        className={`text-xs font-medium ${
                          i.covenant_status === "COMPLIANT"
                            ? "text-green-600"
                            : i.covenant_status === "AT_RISK"
                            ? "text-amber-600"
                            : "text-red-600"
                        }`}
                      >
                        {i.covenant_status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
