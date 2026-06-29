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

export interface ForecastDataPoint {
  period: string;
  baseline: number | null;
  forecast: number | null;
  target?: number | null;
}

interface Props {
  data: ForecastDataPoint[];
  unit?: string;
  height?: number;
}

export function ForecastLineChart({ data, unit = "", height = 300 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={height} aria-label="Forecast trend chart">
      <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="currentColor" strokeOpacity={0.1} />
        <XAxis dataKey="period" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} unit={unit} />
        <Tooltip
          formatter={(value: number, name: string) => [
            `${value}${unit}`,
            name === "baseline" ? "Baseline" : name === "forecast" ? "Prognose" : "Ziel",
          ]}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="baseline"
          stroke="#64748b"
          strokeWidth={2}
          dot={{ r: 3 }}
          name="Baseline"
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="forecast"
          stroke="#3b82f6"
          strokeWidth={2}
          strokeDasharray="5 5"
          dot={{ r: 3 }}
          name="Prognose"
          connectNulls
        />
        {data.some((d) => d.target != null) && (
          <Line
            type="monotone"
            dataKey="target"
            stroke="#10b981"
            strokeWidth={1.5}
            strokeDasharray="2 4"
            dot={false}
            name="Ziel"
            connectNulls
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
