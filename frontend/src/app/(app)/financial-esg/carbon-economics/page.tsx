"use client";

import { useQuery } from "@tanstack/react-query";
import { listCarbonCostModels, listRiskAssessments } from "@/lib/api/financial-esg";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";

export default function CarbonEconomicsPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";

  const { data: carbonModels, isLoading: l1 } = useQuery({
    queryKey: ["fin-esg", "carbon-cost", orgId],
    queryFn: () => listCarbonCostModels(orgId),
  });
  const { data: riskItems, isLoading: l2 } = useQuery({
    queryKey: ["fin-esg", "risk", orgId],
    queryFn: () => listRiskAssessments(orgId),
  });

  if (l1 || l2) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const totalCarbonCost = (carbonModels ?? []).reduce((s, m) => s + m.total_carbon_cost, 0);
  const totalRegulatory = (carbonModels ?? []).reduce((s, m) => s + m.regulatory_exposure, 0);
  const totalAvoided = (carbonModels ?? []).reduce((s, m) => s + m.avoided_cost, 0);

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">{t("finEsg.carbonEconTitle")}</h1>
        <p className="text-muted-foreground">{t("finEsg.carbonEconSubtitle")}</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Total Carbon Cost", value: `$${totalCarbonCost.toLocaleString()}` },
          { label: "Regulatory Exposure", value: `$${totalRegulatory.toLocaleString()}` },
          { label: "Avoided Cost", value: `$${totalAvoided.toLocaleString()}` },
        ].map((s) => (
          <Card key={s.label}>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">{s.label}</p>
              <p className="mt-1 text-2xl font-bold">{s.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Carbon Cost Models</CardTitle>
        </CardHeader>
        <CardContent>
          {(carbonModels ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No carbon cost models yet</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-4">{t("common.name")}</th>
                    <th className="pb-2 pr-4">Year</th>
                    <th className="pb-2 pr-4">Emissions (tCO2e)</th>
                    <th className="pb-2 pr-4">Internal Price</th>
                    <th className="pb-2 pr-4">Total Cost</th>
                    <th className="pb-2">Regulatory Exp.</th>
                  </tr>
                </thead>
                <tbody>
                  {(carbonModels ?? []).map((m) => (
                    <tr key={m.id} className="border-b last:border-0">
                      <td className="py-2 pr-4 font-medium">{m.name}</td>
                      <td className="py-2 pr-4">{m.assessment_year}</td>
                      <td className="py-2 pr-4">{m.total_emissions.toLocaleString()}</td>
                      <td className="py-2 pr-4">
                        {m.currency} {m.internal_carbon_price}/t
                      </td>
                      <td className="py-2 pr-4 font-semibold">
                        ${m.total_carbon_cost.toLocaleString()}
                      </td>
                      <td className="py-2 text-orange-600">
                        ${m.regulatory_exposure.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Cost of Risk Assessments</CardTitle>
        </CardHeader>
        <CardContent>
          {(riskItems ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No risk assessments yet</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-4">{t("common.name")}</th>
                    <th className="pb-2 pr-4">Composite Score</th>
                    <th className="pb-2 pr-4">Exposure Base</th>
                    <th className="pb-2 pr-4">Expected Loss</th>
                    <th className="pb-2">{t("common.date")}</th>
                  </tr>
                </thead>
                <tbody>
                  {(riskItems ?? []).map((r) => (
                    <tr key={r.id} className="border-b last:border-0">
                      <td className="py-2 pr-4 font-medium">{r.name}</td>
                      <td className="py-2 pr-4">
                        <span
                          className={`font-semibold ${
                            r.composite_risk_score >= 70
                              ? "text-red-600"
                              : r.composite_risk_score >= 40
                              ? "text-amber-600"
                              : "text-green-600"
                          }`}
                        >
                          {r.composite_risk_score.toFixed(1)}
                        </span>
                      </td>
                      <td className="py-2 pr-4">${r.exposure_base.toLocaleString()}</td>
                      <td className="py-2 pr-4">${r.expected_loss.toLocaleString()}</td>
                      <td className="py-2 text-muted-foreground">
                        {new Date(r.assessment_date).toLocaleDateString()}
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
