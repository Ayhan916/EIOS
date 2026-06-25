"use client";

import { useQuery } from "@tanstack/react-query";
import { getStrategyRollup } from "@/lib/api/strategy";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import Link from "next/link";

const NAV = [
  { href: "strategy/digital-twin", label: "Digital Twin", desc: "Enterprise state snapshots" },
  { href: "strategy/scenarios", label: "Scenarios", desc: "Climate, regulatory, financial scenarios" },
  { href: "strategy/stress-tests", label: "Stress Tests", desc: "Climate, supplier & financial shocks" },
  { href: "strategy/pathways", label: "Pathways", desc: "Transition & net zero pathways" },
  { href: "strategy/forecasts", label: "Forecasts", desc: "Deterministic KPI & emissions forecasts" },
  { href: "strategy/board-simulation", label: "Board Simulation", desc: "Compare scenarios at board level" },
  { href: "strategy/reports", label: "Reports", desc: "Immutable scenario reports" },
];

export default function StrategyDashboard() {
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";

  const { data: rollup, isLoading } = useQuery({
    queryKey: ["strategy", "rollup", orgId],
    queryFn: () => getStrategyRollup(orgId),
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const stats = rollup
    ? [
        { label: "Digital Twins", value: rollup.digital_twins },
        { label: "Scenarios", value: rollup.scenarios },
        { label: "Executions", value: rollup.scenario_executions },
        { label: "Stress Tests", value: rollup.total_stress_tests },
        { label: "Forecasts", value: rollup.forecasts },
        { label: "Board Simulations", value: rollup.board_simulations },
        { label: "Pathways", value: rollup.transition_pathways },
        { label: "Finalized Reports", value: rollup.finalized_reports },
      ]
    : [];

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Strategy Intelligence Platform</h1>
        <p className="text-muted-foreground">
          Simulate, forecast, stress-test and optimize future sustainability outcomes
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">{s.label}</p>
              <p className="mt-1 text-3xl font-bold">{s.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {NAV.map((n) => (
          <Link key={n.href} href={`/${n.href}`}>
            <Card className="cursor-pointer transition-shadow hover:shadow-md">
              <CardHeader>
                <CardTitle className="text-base">{n.label}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{n.desc}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
