"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

export interface KpiDataPoint {
  period: string;
  actual: number | null;
  target: number | null;
}

interface Props {
  data: KpiDataPoint[];
  unit?: string;
  targetLabel?: string;
  height?: number;
}

export function KpiLineChart({ data, unit = "", targetLabel = "Ziel", height = 280 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={height} aria-label="KPI trend vs target line chart">
      <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="currentColor" strokeOpacity={0.1} />
        <XAxis dataKey="period" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} unit={unit} />
        <Tooltip formatter={(v: number, name: string) => [`${v}${unit}`, name === "actual" ? "Ist" : targetLabel]} />
        <Legend />
        <Line
          type="monotone"
          dataKey="actual"
          stroke="#10b981"
          strokeWidth={2}
          dot={{ r: 3 }}
          name="Ist"
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="target"
          stroke="#6366f1"
          strokeWidth={1.5}
          strokeDasharray="4 4"
          dot={false}
          name={targetLabel}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
