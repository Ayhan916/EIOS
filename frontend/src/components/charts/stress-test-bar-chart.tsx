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
  Cell,
} from "recharts";

export interface StressTestDataPoint {
  test_type: string;
  impact_low: number;
  impact_high: number;
  expected_impact: number;
}

const TYPE_COLORS: Record<string, string> = {
  CLIMATE: "#ef4444",
  SUPPLIER: "#f59e0b",
  FINANCIAL: "#8b5cf6",
  REGULATORY: "#3b82f6",
  DEFAULT: "#64748b",
};

interface Props {
  data: StressTestDataPoint[];
  unit?: string;
  height?: number;
}

export function StressTestBarChart({ data, unit = "%", height = 300 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={height} aria-label="Stress test impact comparison chart">
      <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="currentColor" strokeOpacity={0.1} />
        <XAxis dataKey="test_type" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 12 }} unit={unit} />
        <Tooltip formatter={(v: number) => `${v}${unit}`} />
        <Legend />
        <Bar dataKey="impact_low" name="Minimal" stackId="range" fill="#94a3b8" radius={[0, 0, 0, 0]} />
        <Bar dataKey="expected_impact" name="Erwartet" fill="#3b82f6" radius={[0, 0, 0, 0]} />
        <Bar dataKey="impact_high" name="Maximal" stackId="max" fill="#ef4444" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
