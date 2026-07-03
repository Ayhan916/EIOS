import apiClient from "./client";

export interface PrioritizationDecision {
  id: string;
  organization_id: string;
  supplier_id: string;
  supplier_name: string;
  severity_weight: number;
  probability_weight: number;
  people_affected_weight: number;
  priority_score: number;
  priority_rank: number;
  resource_capacity_per_quarter: number;
  reasoning: string;
  overridden_manually: boolean;
  override_comment: string | null;
  decided_by_user_id: string;
  decided_at: string;
  regulation_refs: string;
  created_at: string;
  updated_at: string;
}

export interface PrioritizationRankingResponse {
  organization_id: string;
  total_suppliers: number;
  resource_capacity_per_quarter: number;
  decisions: PrioritizationDecision[];
  computed_at: string | null;
}

export interface ComputeRequest {
  resource_capacity_per_quarter: number;
}

export interface OverrideRequest {
  new_rank: number;
  override_comment: string;
}

export const prioritizationApi = {
  getRanking: async (): Promise<PrioritizationRankingResponse> => {
    const res = await apiClient.get("/prioritization/");
    return res.data;
  },

  computeRanking: async (
    body: ComputeRequest
  ): Promise<PrioritizationRankingResponse> => {
    const res = await apiClient.post("/prioritization/compute", body);
    return res.data;
  },

  overrideRank: async (
    decisionId: string,
    body: OverrideRequest
  ): Promise<PrioritizationDecision> => {
    const res = await apiClient.patch(
      `/prioritization/${decisionId}/override`,
      body
    );
    return res.data;
  },
};
