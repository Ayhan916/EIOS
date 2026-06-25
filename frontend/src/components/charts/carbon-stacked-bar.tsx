"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

export interface CarbonDataPoint {
  period: string;
  scope1: number;
  scope2: number;
  scope3: number;
}

interface Props {
  data: CarbonDataPoint[];
  unit?: string;
  height?: number;
}

export function CarbonStackedBarChart({ data, unit = "tCO₂e", height = 300 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={height} aria-label="Scope 1, 2 and 3 emissions stacked bar chart">
      <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="currentColor" strokeOpacity={0.1} />
        <XAxis dataKey="period" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} unit={` ${unit}`} />
        <Tooltip
          formatter={(value: number, name: string) => [
            `${value.toLocaleString()} ${unit}`,
            name,
          ]}
        />
        <Legend />
        <Bar dataKey="scope1" name="Scope 1" stackId="ghg" fill="#ef4444" radius={[0, 0, 0, 0]} />
        <Bar dataKey="scope2" name="Scope 2" stackId="ghg" fill="#f97316" />
        <Bar dataKey="scope3" name="Scope 3" stackId="ghg" fill="#f59e0b" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
