"use client";

import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";

export interface ScenarioKpiPoint {
  kpi: string;
  baseline: number;
  scenario: number;
}

interface Props {
  data: ScenarioKpiPoint[];
  scenarioLabel?: string;
  height?: number;
}

export function ScenarioRadarChart({
  data,
  scenarioLabel = "Szenario",
  height = 350,
}: Props) {
  return (
    <ResponsiveContainer width="100%" height={height} aria-label="Scenario KPI impact radar chart">
      <RadarChart data={data} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
        <PolarGrid stroke="currentColor" strokeOpacity={0.15} />
        <PolarAngleAxis dataKey="kpi" tick={{ fontSize: 11 }} />
        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
        <Tooltip />
        <Legend />
        <Radar
          name="Baseline"
          dataKey="baseline"
          stroke="#64748b"
          fill="#64748b"
          fillOpacity={0.2}
        />
        <Radar
          name={scenarioLabel}
          dataKey="scenario"
          stroke="#3b82f6"
          fill="#3b82f6"
          fillOpacity={0.3}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
