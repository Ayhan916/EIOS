import apiClient from "./client";

export interface ImprovementProposal {
  id: string;
  weakness_type: string;
  affected_module: string;
  current_value: number;
  target_value: number;
  expected_impact: number;
  priority_score: number;
  title: string;
  description: string;
  suggested_action: string;
  approval_status: "DRAFT" | "APPROVED" | "IN_PROGRESS" | "VERIFIED" | "REJECTED";
  approved_by_user_id: string | null;
  approved_at: string | null;
  rejected_by_user_id: string | null;
  rejected_at: string | null;
  reject_reason: string | null;
  before_evaluation_run_id: string | null;
  after_evaluation_run_id: string | null;
  verified_improvement: number | null;
  verified_at: string | null;
  created_at: string;
}

export interface DetectResponse {
  proposals_created: number;
  proposals: ImprovementProposal[];
  evaluation_run_id: string | null;
  message: string;
}

export interface SummaryResponse {
  status_counts: Record<string, number>;
  total: number;
  open_draft: number;
  approved: number;
  verified: number;
  rejected: number;
  latest_health_score: number | null;
  latest_benchmark_status: string | null;
}

export const selfImprovementApi = {
  detect: async (): Promise<DetectResponse> => {
    const res = await apiClient.post("/self-improvement/detect");
    return res.data;
  },

  listProposals: async (status?: string): Promise<ImprovementProposal[]> => {
    const params = status ? { approval_status: status } : {};
    const res = await apiClient.get("/self-improvement/proposals", { params });
    return res.data;
  },

  approve: async (id: string): Promise<ImprovementProposal> => {
    const res = await apiClient.patch(`/self-improvement/proposals/${id}/approve`);
    return res.data;
  },

  reject: async (id: string, reason: string): Promise<ImprovementProposal> => {
    const res = await apiClient.patch(`/self-improvement/proposals/${id}/reject`, { reason });
    return res.data;
  },

  verify: async (id: string, after_evaluation_run_id: string): Promise<ImprovementProposal> => {
    const res = await apiClient.patch(`/self-improvement/proposals/${id}/verify`, {
      after_evaluation_run_id,
    });
    return res.data;
  },

  getSummary: async (): Promise<SummaryResponse> => {
    const res = await apiClient.get("/self-improvement/summary");
    return res.data;
  },
};
