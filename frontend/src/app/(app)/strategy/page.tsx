"use client";

import { useQuery } from "@tanstack/react-query";
import { getStrategyRollup } from "@/lib/api/strategy";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import Link from "next/link";

const NAV = [
  { href: "strategy/digital-twin", labelKey: "nav.digitalTwin", desc: "Enterprise state snapshots" },
  { href: "strategy/scenarios", labelKey: "nav.scenarios", desc: "Climate, regulatory, financial scenarios" },
  { href: "strategy/stress-tests", labelKey: "nav.stressTests", desc: "Climate, supplier & financial shocks" },
  { href: "strategy/pathways", labelKey: "nav.pathways", desc: "Transition & net zero pathways" },
  { href: "strategy/forecasts", labelKey: "nav.forecasts", desc: "Deterministic KPI & emissions forecasts" },
  { href: "strategy/board-simulation", labelKey: "nav.boardSimulation", desc: "Compare scenarios at board level" },
  { href: "strategy/reports", labelKey: "nav.strategyReports", desc: "Immutable scenario reports" },
] as const;

export default function StrategyDashboard() {
  const { user } = useAuth();
  const { t } = useLanguage();
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
                <CardTitle className="text-base">{t(n.labelKey)}</CardTitle>
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
