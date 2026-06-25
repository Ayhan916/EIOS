"use client";

import { useQuery } from "@tanstack/react-query";
import { listFinanceInstruments } from "@/lib/api/financial-esg";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";

const INSTRUMENT_LABELS: Record<string, string> = {
  GREEN_BOND: "Green Bond",
  SUSTAINABILITY_LINKED_LOAN: "SLL",
  SUSTAINABILITY_LINKED_BOND: "SLB",
  TRANSITION_FINANCE: "Transition Finance",
  ESG_FUND: "ESG Fund",
};

const COVENANT_COLORS: Record<string, string> = {
  COMPLIANT: "bg-green-100 text-green-700",
  AT_RISK: "bg-amber-100 text-amber-700",
  BREACHED: "bg-red-100 text-red-700",
};

export default function SustainableFinancePage() {
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";

  const { data: instruments, isLoading } = useQuery({
    queryKey: ["fin-esg", "finance", orgId],
    queryFn: () => listFinanceInstruments(orgId),
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const totalExposure = (instruments ?? []).reduce((s, i) => s + i.amount, 0);
  const byType = (instruments ?? []).reduce<Record<string, number>>((acc, i) => {
    acc[i.instrument_type] = (acc[i.instrument_type] ?? 0) + i.amount;
    return acc;
  }, {});
  const breached = (instruments ?? []).filter((i) => i.covenant_status === "BREACHED").length;
  const atRisk = (instruments ?? []).filter((i) => i.covenant_status === "AT_RISK").length;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Sustainable Finance</h1>
        <p className="text-muted-foreground">
          Green bonds, sustainability-linked loans, and transition finance instruments
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Total Exposure", value: `$${totalExposure.toLocaleString()}` },
          { label: "Instruments", value: (instruments ?? []).length },
          { label: "Breached Covenants", value: breached },
          { label: "At Risk", value: atRisk },
        ].map((s) => (
          <Card key={s.label}>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">{s.label}</p>
              <p
                className={`mt-1 text-2xl font-bold ${
                  s.label === "Breached Covenants" && breached > 0
                    ? "text-red-600"
                    : s.label === "At Risk" && atRisk > 0
                    ? "text-amber-600"
                    : ""
                }`}
              >
                {s.value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {Object.keys(byType).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">By Instrument Type</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(byType).map(([type, amount]) => {
                const pct = totalExposure > 0 ? (amount / totalExposure) * 100 : 0;
                return (
                  <div key={type}>
                    <div className="flex justify-between text-sm">
                      <span>{INSTRUMENT_LABELS[type] ?? type}</span>
                      <span className="font-medium">${amount.toLocaleString()}</span>
                    </div>
                    <div className="mt-1 h-2 rounded-full bg-muted">
                      <div
                        className="h-2 rounded-full bg-blue-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>All Instruments</CardTitle>
        </CardHeader>
        <CardContent>
          {(instruments ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No instruments yet</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-4">Name</th>
                    <th className="pb-2 pr-4">Type</th>
                    <th className="pb-2 pr-4">Amount</th>
                    <th className="pb-2 pr-4">Maturity</th>
                    <th className="pb-2">Covenant</th>
                  </tr>
                </thead>
                <tbody>
                  {(instruments ?? []).map((i) => (
                    <tr key={i.id} className="border-b last:border-0">
                      <td className="py-2 pr-4 font-medium">{i.name}</td>
                      <td className="py-2 pr-4 text-muted-foreground">
                        {INSTRUMENT_LABELS[i.instrument_type] ?? i.instrument_type}
                      </td>
                      <td className="py-2 pr-4">
                        {i.currency} {i.amount.toLocaleString()}
                      </td>
                      <td className="py-2 pr-4 text-muted-foreground">
                        {i.maturity_date
                          ? new Date(i.maturity_date).toLocaleDateString()
                          : "—"}
                      </td>
                      <td className="py-2">
                        <span
                          className={`rounded px-2 py-0.5 text-xs font-medium ${
                            COVENANT_COLORS[i.covenant_status] ?? "bg-muted text-muted-foreground"
                          }`}
                        >
                          {i.covenant_status}
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
