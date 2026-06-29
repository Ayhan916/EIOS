"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Building2, Search } from "lucide-react";
import { getEnterpriseRollup, getBusinessUnitRollup, type RollupSummary } from "@/lib/api/sustainability";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";

type EntityType = "enterprise" | "business-unit";

function MetricTile({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="rounded bg-muted p-3 text-center">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-bold text-sm">{value ?? "—"}</p>
    </div>
  );
}

function RollupDetail({ data }: { data: RollupSummary }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-semibold capitalize">{data.entity_type.replace("_", " ")} Rollup</p>
          <p className="text-xs text-muted-foreground">
            {data.organization_ids.length} organization{data.organization_ids.length !== 1 ? "s" : ""} ·
            Computed {new Date(data.computed_at).toLocaleString()}
          </p>
        </div>
      </div>

      <div>
        <p className="text-sm font-medium mb-2">Emissions</p>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          <MetricTile label="Total (tCO₂e)" value={data.emissions.total_emissions.toLocaleString()} />
          <MetricTile label="Scope 1" value={data.emissions.scope1.toLocaleString()} />
          <MetricTile label="Scope 2" value={data.emissions.scope2.toLocaleString()} />
          <MetricTile label="Scope 3" value={data.emissions.scope3.toLocaleString()} />
          <MetricTile label="Inventories" value={data.emissions.inventories_count} />
        </div>
      </div>

      <div>
        <p className="text-sm font-medium mb-2">Objectives</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <MetricTile label="Total" value={data.objectives.total} />
          <MetricTile label="Active" value={data.objectives.active} />
          <MetricTile label="Completed" value={data.objectives.completed} />
          <MetricTile label="Completion %" value={`${data.objectives.completion_percent}%`} />
        </div>
      </div>

      <div>
        <p className="text-sm font-medium mb-2">Targets</p>
        <div className="grid grid-cols-3 gap-2">
          <MetricTile label="Total" value={data.targets.total} />
          <MetricTile label="With Measurements" value={data.targets.with_measurements} />
          <MetricTile label="Attainment %" value={`${data.targets.attainment_percent}%`} />
        </div>
      </div>

      <div>
        <p className="text-sm font-medium mb-2">KPIs</p>
        <div className="grid grid-cols-2 gap-2">
          <MetricTile label="Total" value={data.kpis.total} />
          <MetricTile label="Active" value={data.kpis.active} />
        </div>
      </div>

      <div>
        <p className="text-sm font-medium mb-2">Sustainability Scores</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <MetricTile label="Overall" value={data.scores.avg_overall_score} />
          <MetricTile label="Environmental" value={data.scores.avg_environmental_score} />
          <MetricTile label="Social" value={data.scores.avg_social_score} />
          <MetricTile label="Governance" value={data.scores.avg_governance_score} />
        </div>
      </div>

      <div>
        <p className="text-sm font-medium mb-2">Climate Risk</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <MetricTile label="Overall Risk" value={data.climate_risks.avg_overall_risk} />
          <MetricTile label="Transition" value={data.climate_risks.avg_transition_risk} />
          <MetricTile label="Physical" value={data.climate_risks.avg_physical_risk} />
          <MetricTile label="Regulatory" value={data.climate_risks.avg_regulatory_risk} />
        </div>
      </div>
    </div>
  );
}

export default function RollupsPage() {
  const [entityType, setEntityType] = useState<EntityType>("enterprise");
  const [entityId, setEntityId] = useState("");
  const [queryId, setQueryId] = useState("");

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["rollup", entityType, queryId],
    queryFn: () =>
      entityType === "enterprise"
        ? getEnterpriseRollup(queryId)
        : getBusinessUnitRollup(queryId),
    enabled: !!queryId,
    retry: false,
  });

  function handleSearch() {
    setQueryId(entityId.trim());
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Enterprise Sustainability Rollup</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Aggregate sustainability data across all organizations in an enterprise hierarchy entity.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            Rollup Query
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button
              variant={entityType === "enterprise" ? "default" : "outline"}
              size="sm"
              onClick={() => setEntityType("enterprise")}
            >
              Enterprise
            </Button>
            <Button
              variant={entityType === "business-unit" ? "default" : "outline"}
              size="sm"
              onClick={() => setEntityType("business-unit")}
            >
              Business Unit
            </Button>
          </div>

          <div className="flex gap-2">
            <Input
              placeholder={`Enter ${entityType} ID…`}
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="max-w-sm"
            />
            <Button onClick={handleSearch} disabled={!entityId.trim() || isLoading}>
              <Search className="mr-1 h-4 w-4" />
              {isLoading ? "Loading…" : "Load Rollup"}
            </Button>
          </div>

          {isLoading && <Spinner />}
          {isError && (
            <p className="text-sm text-destructive">
              {(error as Error)?.message ?? "Failed to load rollup"}
            </p>
          )}
          {data && <RollupDetail data={data} />}
          {!data && !isLoading && queryId && !isError && (
            <p className="text-sm text-muted-foreground">No data found for this entity.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
