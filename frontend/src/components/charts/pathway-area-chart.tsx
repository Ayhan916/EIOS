"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

export interface PathwayDataPoint {
  year: number | string;
  emissions: number | null;
  target_pathway?: number | null;
  net_zero_level?: number | null;
}

interface Props {
  data: PathwayDataPoint[];
  unit?: string;
  height?: number;
}

export function PathwayAreaChart({ data, unit = "tCO₂e", height = 320 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={height} aria-label="Emissions reduction pathway chart">
      <AreaChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
        <defs>
          <linearGradient id="emissionsGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="targetGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="currentColor" strokeOpacity={0.1} />
        <XAxis dataKey="year" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} unit={` ${unit}`} />
        <Tooltip
          formatter={(value: number, name: string) => [
            `${value} ${unit}`,
            name === "emissions" ? "Ist-Emissionen" : name === "target_pathway" ? "Zielpfad" : "Net Zero",
          ]}
        />
        <Legend />
        <Area
          type="monotone"
          dataKey="emissions"
          stroke="#f59e0b"
          fill="url(#emissionsGrad)"
          strokeWidth={2}
          name="Ist-Emissionen"
          connectNulls
        />
        {data.some((d) => d.target_pathway != null) && (
          <Area
            type="monotone"
            dataKey="target_pathway"
            stroke="#10b981"
            fill="url(#targetGrad)"
            strokeWidth={2}
            strokeDasharray="6 3"
            name="Zielpfad"
            connectNulls
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  );
}
