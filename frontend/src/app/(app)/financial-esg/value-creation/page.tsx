"use client";

import { useQuery } from "@tanstack/react-query";
import { listValueInitiatives, listClimateFinance, listValuations } from "@/lib/api/financial-esg";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "text-blue-600",
  COMPLETED: "text-green-600",
  PAUSED: "text-amber-600",
  CANCELLED: "text-red-600",
  PLANNED: "text-slate-600",
};

export default function ValueCreationPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";

  const { data: initiatives, isLoading: l1 } = useQuery({
    queryKey: ["fin-esg", "value-creation", orgId],
    queryFn: () => listValueInitiatives(orgId),
  });
  const { data: climateItems, isLoading: l2 } = useQuery({
    queryKey: ["fin-esg", "climate-finance", orgId],
    queryFn: () => listClimateFinance(orgId),
  });
  const { data: valuations, isLoading: l3 } = useQuery({
    queryKey: ["fin-esg", "valuations", orgId],
    queryFn: () => listValuations(orgId),
  });

  if (l1 || l2 || l3) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const totalInvestment = (initiatives ?? []).reduce((s, i) => s + i.investment_amount, 0);
  const totalRealized = (initiatives ?? []).reduce((s, i) => s + i.realized_value, 0);
  const avgROI = (initiatives ?? []).filter((i) => i.roi_percent !== null);
  const avgROIVal =
    avgROI.length > 0
      ? (avgROI.reduce((s, i) => s + (i.roi_percent ?? 0), 0) / avgROI.length).toFixed(1)
      : null;
  const totalSustValue = (valuations ?? []).reduce((s, v) => s + v.total_sustainability_value, 0);

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">{t("finEsg.valueCreationTitle")}</h1>
        <p className="text-muted-foreground">
          {t("finEsg.valueCreationSubtitle")}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Total Investment", value: `$${totalInvestment.toLocaleString()}` },
          { label: "Realized Value", value: `$${totalRealized.toLocaleString()}` },
          { label: "Avg ROI", value: avgROIVal ? `${avgROIVal}%` : "—" },
          { label: "Sustainability Value", value: `$${totalSustValue.toLocaleString()}` },
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
          <CardTitle>{t("finEsg.valueCreationTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {(initiatives ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("common.noData")}</p>
          ) : (
            <div className="space-y-3">
              {(initiatives ?? []).map((i) => {
                const pct =
                  i.investment_amount > 0
                    ? Math.min(100, (i.realized_value / i.investment_amount) * 100)
                    : 0;
                return (
                  <div key={i.id} className="rounded border p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium">{i.name}</p>
                        {i.description && (
                          <p className="mt-1 text-sm text-muted-foreground">{i.description}</p>
                        )}
                      </div>
                      <span
                        className={`text-sm font-medium ${STATUS_COLORS[i.initiative_status] ?? "text-slate-600"}`}
                      >
                        {i.initiative_status}
                      </span>
                    </div>
                    <div className="mt-3 flex gap-6 text-sm">
                      <span>
                        <span className="text-muted-foreground">Investment: </span>
                        <span className="font-medium">${i.investment_amount.toLocaleString()}</span>
                      </span>
                      <span>
                        <span className="text-muted-foreground">Realized: </span>
                        <span className="font-medium text-green-600">
                          ${i.realized_value.toLocaleString()}
                        </span>
                      </span>
                      {i.roi_percent !== null && (
                        <span>
                          <span className="text-muted-foreground">ROI: </span>
                          <span
                            className={`font-medium ${i.roi_percent >= 0 ? "text-green-600" : "text-red-600"}`}
                          >
                            {i.roi_percent.toFixed(1)}%
                          </span>
                        </span>
                      )}
                    </div>
                    <div className="mt-2 h-1.5 rounded-full bg-muted">
                      <div
                        className="h-1.5 rounded-full bg-green-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Climate Finance Analytics</CardTitle>
          </CardHeader>
          <CardContent>
            {(climateItems ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("common.noData")}</p>
            ) : (
              <div className="space-y-2">
                {(climateItems ?? []).map((c) => (
                  <div key={c.id} className="rounded border px-3 py-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{c.analysis_name}</p>
                      <p className="text-xs text-muted-foreground">{c.analysis_year}</p>
                    </div>
                    <div className="mt-1 flex gap-4 text-xs">
                      <span>
                        Investment: ${c.transition_investment.toLocaleString()}
                      </span>
                      <span>
                        Reduction: {c.emissions_reduction.toLocaleString()} tCO2e
                      </span>
                      {c.roi_percent !== null && (
                        <span className={c.roi_percent >= 0 ? "text-green-600" : "text-red-600"}>
                          ROI: {c.roi_percent.toFixed(1)}%
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Sustainability Valuations</CardTitle>
          </CardHeader>
          <CardContent>
            {(valuations ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("common.noData")}</p>
            ) : (
              <div className="space-y-2">
                {(valuations ?? []).map((v) => (
                  <div key={v.id} className="rounded border px-3 py-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{v.valuation_name}</p>
                      <p className="text-sm font-bold text-green-600">
                        ${v.total_sustainability_value.toLocaleString()}
                      </p>
                    </div>
                    <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                      <span>Risk: ${v.risk_reduction_value.toLocaleString()}</span>
                      <span>Carbon: ${v.carbon_reduction_value.toLocaleString()}</span>
                      <span>Ops: ${v.operational_efficiency_value.toLocaleString()}</span>
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
