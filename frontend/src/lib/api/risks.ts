import apiClient from "./client";
import type { RiskResponse } from "@/types/api";

export async function listRisks(
  assessmentId: string
): Promise<RiskResponse[]> {
  const res = await apiClient.get<RiskResponse[]>(`/risks/`, {
    params: { assessment_id: assessmentId },
  });
  return res.data;
}
