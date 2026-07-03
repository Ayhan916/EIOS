import apiClient from "./client";

export interface MissingItem {
  type: "upload" | "data" | "action";
  label: string;
  count: number;
  href: string;
}

export interface StepReadiness {
  key: string;
  status: "ok" | "warning" | "error";
  score: number;
  open_count: number;
  missing: MissingItem[];
}

export interface PipelineReadiness {
  overall_score: number;
  steps: StepReadiness[];
  checked_at: string;
}

export async function getPipelineReadiness(): Promise<PipelineReadiness> {
  const { data } = await apiClient.get<PipelineReadiness>("/pipeline/readiness");
  return data;
}
