import apiClient from "./client";
import type { RecommendationResponse } from "@/types/api";

export async function listRecommendations(
  assessmentId: string
): Promise<RecommendationResponse[]> {
  const res = await apiClient.get<RecommendationResponse[]>(
    `/recommendations/`,
    { params: { assessment_id: assessmentId } }
  );
  return res.data;
}
