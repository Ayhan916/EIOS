import apiClient from "./client";
import type { FindingResponse } from "@/types/api";

export async function listFindings(
  assessmentId: string
): Promise<FindingResponse[]> {
  const res = await apiClient.get<FindingResponse[]>(`/findings/`, {
    params: { assessment_id: assessmentId },
  });
  return res.data;
}
