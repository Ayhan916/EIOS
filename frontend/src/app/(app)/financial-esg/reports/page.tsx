"use client";

import { useQuery } from "@tanstack/react-query";
import { listReports, listScenarios, listCorrelations } from "@/lib/api/financial-esg";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";

export default function FinancialReportsPage() {
  const { user } = useAuth();
  const { t } = useLanguage();
  const orgId = user?.organization_id ?? "default";

  const { data: reports, isLoading: l1 } = useQuery({
    queryKey: ["fin-esg", "reports", orgId],
    queryFn: () => listReports(orgId),
  });
  const { data: scenarios, isLoading: l2 } = useQuery({
    queryKey: ["fin-esg", "scenarios", orgId],
    queryFn: () => listScenarios(orgId),
  });
  const { data: correlations, isLoading: l3 } = useQuery({
    queryKey: ["fin-esg", "correlations", orgId],
    queryFn: () => listCorrelations(orgId),
  });

  if (l1 || l2 || l3) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">{t("finEsg.reportsTitle")}</h1>
        <p className="text-muted-foreground">
          Reports, scenario analyses, and ESG–financial correlations
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("reports.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          {(reports ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("finEsg.noReports")}</p>
          ) : (
            <div className="space-y-2">
              {(reports ?? []).map((r) => (
                <div
                  key={r.id}
                  className="flex items-center justify-between rounded border px-4 py-3"
                >
                  <div>
                    <p className="font-medium">{r.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(r.report_period_start).toLocaleDateString()} –{" "}
                      {new Date(r.report_period_end).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        r.is_final
                          ? "bg-green-100 text-green-700"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {r.overall_status}
                    </span>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {new Date(r.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Scenario Analyses</CardTitle>
          </CardHeader>
          <CardContent>
            {(scenarios ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("strategy.noScenarios")}</p>
            ) : (
              <div className="space-y-2">
                {(scenarios ?? []).map((s) => (
                  <div key={s.id} className="rounded border px-3 py-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{s.scenario_name}</p>
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                        {s.scenario_type.replace(/_/g, " ")}
                      </span>
                    </div>
                    {s.outputs && (
                      <div className="mt-1 text-xs text-muted-foreground">
                        {Object.entries(s.outputs)
                          .filter(([k]) => k !== "formula")
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(" · ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">ESG Financial Correlations</CardTitle>
          </CardHeader>
          <CardContent>
            {(correlations ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No correlations</p>
            ) : (
              <div className="space-y-2">
                {(correlations ?? []).map((c) => (
                  <div key={c.id} className="rounded border px-3 py-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{c.correlation_period}</p>
                      <span
                        className={`text-sm font-bold ${
                          (c.correlation_coefficient ?? 0) > 0
                            ? "text-green-600"
                            : "text-red-600"
                        }`}
                      >
                        r = {c.correlation_coefficient?.toFixed(4) ?? "—"}
                      </span>
                    </div>
                    <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
                      <span>ESG: {c.esg_score}</span>
                      <span>Risk ↓: {c.risk_reduction}%</span>
                      <span>Cost ↓: {c.cost_reduction}%</span>
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
