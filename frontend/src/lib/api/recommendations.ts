import apiClient from "./client";
import type { RecommendationResponse, RecommendationUpdate } from "@/types/api";

export async function listRecommendations(
  assessmentId: string
): Promise<RecommendationResponse[]> {
  const res = await apiClient.get<RecommendationResponse[]>(
    `/recommendations/`,
    { params: { assessment_id: assessmentId } }
  );
  return res.data;
}

export async function updateRecommendation(
  recommendationId: string,
  data: RecommendationUpdate
): Promise<RecommendationResponse> {
  const res = await apiClient.patch<RecommendationResponse>(
    `/recommendations/${recommendationId}`,
    data
  );
  return res.data;
}
