"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api/client";

interface UncertaintyData {
  assessment_id: string;
  uncertainty: "Low" | "Medium" | "High";
  uncertainty_reason: string;
  data_completeness: number;
}

const META: Record<string, { label: string; color: string; dot: string }> = {
  Low:    { label: "Niedrig",  color: "text-emerald-700 bg-emerald-50 border-emerald-200", dot: "bg-emerald-500" },
  Medium: { label: "Mittel",   color: "text-amber-700 bg-amber-50 border-amber-200",       dot: "bg-amber-500" },
  High:   { label: "Hoch",     color: "text-red-700 bg-red-50 border-red-200",             dot: "bg-red-500" },
};

interface UncertaintyBadgeProps {
  assessmentId: string;
  showReason?: boolean;
  size?: "xs" | "sm";
}

export function UncertaintyBadge({ assessmentId, showReason = false, size = "sm" }: UncertaintyBadgeProps) {
  const { data } = useQuery<UncertaintyData>({
    queryKey: ["uncertainty", assessmentId],
    queryFn: async () => {
      const res = await apiClient.get<UncertaintyData>(`/assessments/${assessmentId}/uncertainty`);
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  if (!data) return null;

  const meta = META[data.uncertainty] ?? META.Medium;
  const textSize = size === "xs" ? "text-[10px]" : "text-xs";

  return (
    <div className="flex flex-col gap-0.5">
      <span
        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-semibold ${textSize} ${meta.color}`}
        title={data.uncertainty_reason}
      >
        <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
        ⚠ Unsicherheit: {meta.label}
        <span className="opacity-60">({data.data_completeness}%)</span>
      </span>
      {showReason && (
        <p className={`${textSize} text-muted-foreground italic`}>{data.uncertainty_reason}</p>
      )}
    </div>
  );
}
