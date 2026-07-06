"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { listTaxonomyAssessments } from "@/lib/api/financial-esg";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  IN_REVIEW: "bg-blue-100 text-blue-700",
  VERIFIED: "bg-green-100 text-green-700",
};

export default function TaxonomyPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";

  const { data: assessments, isLoading } = useQuery({
    queryKey: ["fin-esg", "taxonomy", orgId],
    queryFn: () => listTaxonomyAssessments(orgId),
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const sorted = [...(assessments ?? [])].sort((a, b) => b.assessment_year - a.assessment_year);
  const latest = sorted[0];
  const avgAligned =
    (assessments ?? []).length > 0
      ? (assessments ?? []).reduce((s, a) => s + a.aligned_percent, 0) / (assessments ?? []).length
      : null;

  // #66 Waterfall data: per-year aligned/eligible/non-eligible breakdown
  const waterfallData = [...sorted].reverse().map((a) => {
    const nonEligible = Math.max(0, 100 - a.eligible_percent);
    const eligibleNotAligned = Math.max(0, a.eligible_percent - a.aligned_percent);
    return {
      year: String(a.assessment_year),
      aligned: parseFloat(a.aligned_percent.toFixed(1)),
      eligibleOnly: parseFloat(eligibleNotAligned.toFixed(1)),
      nonEligible: parseFloat(nonEligible.toFixed(1)),
    };
  });

  // #68 Donut data from latest assessment
  const donutData = latest
    ? [
        { name: t("taxonomy.aligned"), value: parseFloat(latest.aligned_percent.toFixed(1)), color: "#22c55e" },
        {
          name: t("taxonomy.eligibleNotAligned"),
          value: parseFloat(Math.max(0, latest.eligible_percent - latest.aligned_percent).toFixed(1)),
          color: "#60a5fa",
        },
        {
          name: t("taxonomy.nonEligible"),
          value: parseFloat(Math.max(0, 100 - latest.eligible_percent).toFixed(1)),
          color: "#e2e8f0",
        },
      ]
    : [];

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">{t("taxonomy.title")}</h1>
        <p className="text-muted-foreground">{t("taxonomy.subtitle")}</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">{t("taxonomy.latestAligned")}</p>
            <p className="mt-1 text-3xl font-bold text-green-600">
              {latest ? `${latest.aligned_percent.toFixed(1)}%` : "—"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {latest?.taxonomy_framework} · {latest?.assessment_year}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">{t("taxonomy.latestEligible")}</p>
            <p className="mt-1 text-3xl font-bold text-blue-600">
              {latest ? `${latest.eligible_percent.toFixed(1)}%` : "—"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">{t("taxonomy.avgAligned")}</p>
            <p className="mt-1 text-3xl font-bold">
              {avgAligned !== null ? `${avgAligned.toFixed(1)}%` : "—"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* #66 Waterfall / stacked bar chart: aligned vs eligible-only vs non-eligible per year */}
      {waterfallData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("taxonomy.waterfallTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={waterfallData} barSize={32}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v) => `${v}%`} domain={[0, 100]} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number, name: string) => [`${v}%`, name]} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="aligned" stackId="a" fill="#22c55e" name={t("taxonomy.aligned")} radius={[0, 0, 0, 0]} />
                <Bar dataKey="eligibleOnly" stackId="a" fill="#60a5fa" name={t("taxonomy.eligibleNotAligned")} />
                <Bar dataKey="nonEligible" stackId="a" fill="#e2e8f0" name={t("taxonomy.nonEligible")} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* #68 Donut: eligible vs aligned vs non-aligned for latest year */}
      {donutData.length > 0 && latest && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {t("taxonomy.breakdownTitle").replace("{year}", String(latest.assessment_year))}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={donutData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, value }) => `${value}%`}
                    labelLine={false}
                  >
                    {donutData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => `${v}%`} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Latest assessment progress bars (existing) */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("taxonomy.latestAssessmentTitle").replace("{year}", String(latest.assessment_year))}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm">
                    <span>{t("taxonomy.aligned")}</span>
                    <span className="font-medium">{latest.aligned_percent.toFixed(1)}%</span>
                  </div>
                  <div className="mt-1 h-3 rounded-full bg-muted">
                    <div
                      className="h-3 rounded-full bg-green-500"
                      style={{ width: `${Math.min(100, latest.aligned_percent)}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm">
                    <span>{t("taxonomy.eligible")}</span>
                    <span className="font-medium">{latest.eligible_percent.toFixed(1)}%</span>
                  </div>
                  <div className="mt-1 h-3 rounded-full bg-muted">
                    <div
                      className="h-3 rounded-full bg-blue-400"
                      style={{ width: `${Math.min(100, latest.eligible_percent)}%` }}
                    />
                  </div>
                </div>
              </div>
              {latest.justification && (
                <p className="mt-4 text-sm text-muted-foreground">{latest.justification}</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>{t("taxonomy.allAssessments")}</CardTitle>
        </CardHeader>
        <CardContent>
          {sorted.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("taxonomy.noAssessments")}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-4">{t("taxonomy.year")}</th>
                    <th className="pb-2 pr-4">{t("esgOs.framework")}</th>
                    <th className="pb-2 pr-4">{t("taxonomy.alignedPct")}</th>
                    <th className="pb-2 pr-4">{t("taxonomy.eligiblePct")}</th>
                    <th className="pb-2">{t("common.status")}</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((a) => (
                    <tr key={a.id} className="border-b last:border-0">
                      <td className="py-2 pr-4 font-medium">{a.assessment_year}</td>
                      <td className="py-2 pr-4 text-muted-foreground">{a.taxonomy_framework}</td>
                      <td className="py-2 pr-4 font-semibold text-green-600">
                        {a.aligned_percent.toFixed(1)}%
                      </td>
                      <td className="py-2 pr-4 text-blue-600">
                        {a.eligible_percent.toFixed(1)}%
                      </td>
                      <td className="py-2">
                        <span
                          className={`rounded px-2 py-0.5 text-xs font-medium ${
                            STATUS_COLORS[a.assessment_status] ?? "bg-muted text-muted-foreground"
                          }`}
                        >
                          {a.assessment_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
