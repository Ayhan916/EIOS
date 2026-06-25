"use client";

import { useQuery } from "@tanstack/react-query";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { listGreenRevenue, listGreenCapex, listGreenOpex } from "@/lib/api/financial-esg";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";

const ALIGN_COLORS: Record<string, string> = {
  ALIGNED: "bg-green-100 text-green-700",
  ELIGIBLE: "bg-blue-100 text-blue-700",
  NOT_ELIGIBLE: "bg-slate-100 text-slate-600",
};

export default function GreenRevenuePage() {
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";

  const { data: revenues, isLoading: l1 } = useQuery({
    queryKey: ["fin-esg", "revenue", orgId],
    queryFn: () => listGreenRevenue(orgId),
  });
  const { data: capex, isLoading: l2 } = useQuery({
    queryKey: ["fin-esg", "capex", orgId],
    queryFn: () => listGreenCapex(orgId),
  });
  const { data: opex, isLoading: l3 } = useQuery({
    queryKey: ["fin-esg", "opex", orgId],
    queryFn: () => listGreenOpex(orgId),
  });

  if (l1 || l2 || l3) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const totalGreen = (revenues ?? []).reduce(
    (s, r) =>
      r.alignment_status === "ALIGNED" || r.alignment_status === "ELIGIBLE"
        ? s + r.amount
        : s,
    0
  );
  const avgGreenPct =
    (revenues ?? []).length > 0
      ? (revenues ?? []).reduce((s, r) => s + r.green_revenue_percent, 0) /
        (revenues ?? []).length
      : null;
  const totalCapex = (capex ?? []).reduce((s, c) => s + c.amount, 0);
  const avgCapexAlign =
    (capex ?? []).length > 0
      ? (capex ?? []).reduce((s, c) => s + c.alignment_percent, 0) / (capex ?? []).length
      : null;
  const totalOpex = (opex ?? []).reduce((s, o) => s + o.amount, 0);

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Green Revenue</h1>
        <p className="text-muted-foreground">
          Green revenue, CapEx, and OpEx tracking
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          {
            label: "Green Revenue",
            value: `$${totalGreen.toLocaleString()}`,
            sub: avgGreenPct ? `${avgGreenPct.toFixed(1)}% avg` : undefined,
          },
          {
            label: "Green CapEx",
            value: `$${totalCapex.toLocaleString()}`,
            sub: avgCapexAlign ? `${avgCapexAlign.toFixed(1)}% avg alignment` : undefined,
          },
          { label: "Green OpEx", value: `$${totalOpex.toLocaleString()}` },
          { label: "Revenue Records", value: (revenues ?? []).length },
        ].map((s) => (
          <Card key={s.label}>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">{s.label}</p>
              <p className="mt-1 text-2xl font-bold">{s.value}</p>
              {s.sub && <p className="mt-1 text-xs text-muted-foreground">{s.sub}</p>}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* #67 Green revenue % trend line */}
      {(revenues ?? []).length > 1 && (() => {
        const trendData = [...(revenues ?? [])]
          .sort((a, b) => a.period.localeCompare(b.period))
          .map((r) => ({ period: r.period, pct: parseFloat(r.green_revenue_percent.toFixed(1)) }));
        return (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Green Revenue % — Trend</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={(v) => `${v}%`} domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => [`${v}%`, "Green Revenue %"]} />
                  <Line
                    type="monotone"
                    dataKey="pct"
                    stroke="#22c55e"
                    strokeWidth={2}
                    dot={{ r: 4, fill: "#22c55e" }}
                    name="Green Revenue %"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        );
      })()}

      <Card>
        <CardHeader>
          <CardTitle>Green Revenue Records</CardTitle>
        </CardHeader>
        <CardContent>
          {(revenues ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No revenue records</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-4">Revenue Stream</th>
                    <th className="pb-2 pr-4">Period</th>
                    <th className="pb-2 pr-4">Amount</th>
                    <th className="pb-2 pr-4">Green %</th>
                    <th className="pb-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(revenues ?? []).map((r) => (
                    <tr key={r.id} className="border-b last:border-0">
                      <td className="py-2 pr-4 font-medium">{r.revenue_stream}</td>
                      <td className="py-2 pr-4 text-muted-foreground">{r.period}</td>
                      <td className="py-2 pr-4">
                        {r.currency} {r.amount.toLocaleString()}
                      </td>
                      <td className="py-2 pr-4 font-semibold text-green-600">
                        {r.green_revenue_percent.toFixed(1)}%
                      </td>
                      <td className="py-2">
                        <span
                          className={`rounded px-2 py-0.5 text-xs font-medium ${
                            ALIGN_COLORS[r.alignment_status] ?? "bg-muted text-muted-foreground"
                          }`}
                        >
                          {r.alignment_status}
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

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Green CapEx Projects</CardTitle>
          </CardHeader>
          <CardContent>
            {(capex ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No CapEx records</p>
            ) : (
              <div className="space-y-2">
                {(capex ?? []).map((c) => (
                  <div key={c.id} className="rounded border px-3 py-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{c.project_name}</p>
                      <p className="text-sm font-semibold">
                        ${c.amount.toLocaleString()}
                      </p>
                    </div>
                    <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                      <span>Period: {c.period}</span>
                      <span className="text-green-600">
                        {c.alignment_percent.toFixed(1)}% aligned
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Green OpEx</CardTitle>
          </CardHeader>
          <CardContent>
            {(opex ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">No OpEx records</p>
            ) : (
              <div className="space-y-2">
                {(opex ?? []).map((o) => (
                  <div key={o.id} className="rounded border px-3 py-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{o.description}</p>
                      <p className="text-sm font-semibold">
                        ${o.amount.toLocaleString()}
                      </p>
                    </div>
                    <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                      <span>Period: {o.period}</span>
                      <span className="text-green-600">
                        {o.alignment_percent.toFixed(1)}% aligned
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
