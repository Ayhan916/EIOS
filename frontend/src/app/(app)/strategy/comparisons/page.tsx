"use client";

import { useQuery } from "@tanstack/react-query";
import { listComparisons } from "@/lib/api/strategy";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";

function DeltaValue({ value }: { value: number }) {
  const color =
    value < 0 ? "text-green-600" : value > 0 ? "text-red-600" : "text-muted-foreground";
  const sign = value > 0 ? "+" : "";
  return (
    <span className={`font-semibold ${color}`}>
      {sign}
      {value.toLocaleString(undefined, { maximumFractionDigits: 2 })}
    </span>
  );
}

export default function ScenarioComparisonsPage() {
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";

  const { data: comparisons, isLoading } = useQuery({
    queryKey: ["strategy", "comparisons", orgId],
    queryFn: () => listComparisons(orgId),
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Scenario Comparison Engine</h1>
        <p className="text-muted-foreground">
          Delta analysis across 2–10 scenarios — KPI, emissions, risk, and value
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Total Comparisons</p>
            <p className="mt-1 text-3xl font-bold">{(comparisons ?? []).length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Finalized</p>
            <p className="mt-1 text-3xl font-bold text-green-600">
              {(comparisons ?? []).filter((c) => c.is_final).length}
            </p>
          </CardContent>
        </Card>
      </div>

      {(comparisons ?? []).length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              No comparisons computed yet. Execute at least 2 scenarios and compare via the API.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {(comparisons ?? []).map((c) => {
            const baseId = (c.scenario_ids as { base_scenario_id?: string } | null)
              ?.base_scenario_id;
            const allIds = (c.scenario_ids as { scenario_ids?: string[] } | null)?.scenario_ids ?? [];
            const compareIds = allIds.filter((id) => id !== baseId);

            return (
              <Card key={c.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-base">{c.comparison_name}</CardTitle>
                    <div className="flex gap-2">
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                        {c.comparison_methodology ?? "delta_vs_baseline"}
                      </span>
                      {c.is_final && (
                        <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                          FINAL
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {allIds.length} scenarios compared
                    {baseId && ` · Baseline: ${baseId.slice(0, 8)}…`}
                  </p>
                </CardHeader>
                <CardContent>
                  {compareIds.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No comparison data.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b text-left text-xs text-muted-foreground">
                            <th className="pb-2 pr-4">Scenario</th>
                            <th className="pb-2 pr-4">Emissions Δ (tCO₂e)</th>
                            <th className="pb-2 pr-4">Risk Score Δ</th>
                            <th className="pb-2">Revenue Δ</th>
                          </tr>
                        </thead>
                        <tbody>
                          {compareIds.map((sid) => {
                            const emDelta = (c.emissions_delta as Record<string, { emissions_tco2e_delta?: number }> | null)?.[sid];
                            const riskDelta = (c.risk_delta as Record<string, { risk_score_delta?: number }> | null)?.[sid];
                            const valDelta = (c.value_delta as Record<string, { revenue_delta?: number }> | null)?.[sid];
                            return (
                              <tr key={sid} className="border-b last:border-0">
                                <td className="py-2 pr-4 font-mono text-xs text-muted-foreground">
                                  {sid.slice(0, 8)}…
                                </td>
                                <td className="py-2 pr-4">
                                  {emDelta?.emissions_tco2e_delta !== undefined ? (
                                    <DeltaValue value={emDelta.emissions_tco2e_delta} />
                                  ) : "—"}
                                </td>
                                <td className="py-2 pr-4">
                                  {riskDelta?.risk_score_delta !== undefined ? (
                                    <DeltaValue value={riskDelta.risk_score_delta} />
                                  ) : "—"}
                                </td>
                                <td className="py-2">
                                  {valDelta?.revenue_delta !== undefined ? (
                                    <DeltaValue value={valDelta.revenue_delta} />
                                  ) : "—"}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <p className="mt-3 text-xs text-muted-foreground">
                    Created {new Date(c.created_at).toLocaleDateString()}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
