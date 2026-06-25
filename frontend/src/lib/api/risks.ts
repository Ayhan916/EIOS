import apiClient from "./client";
import type { FindingResponse, RiskResponse } from "@/types/api";

export async function listRisks(assessmentId: string): Promise<RiskResponse[]> {
  const res = await apiClient.get<RiskResponse[]>(`/risks/`, {
    params: { assessment_id: assessmentId },
  });
  return res.data;
}

export async function getRisk(riskId: string): Promise<RiskResponse> {
  const res = await apiClient.get<RiskResponse>(`/risks/${riskId}`);
  return res.data;
}

export async function getRiskLinkedFindings(riskId: string): Promise<FindingResponse[]> {
  const res = await apiClient.get<FindingResponse[]>(`/risks/${riskId}/findings`);
  return res.data;
}

export async function patchRisk(
  riskId: string,
  patch: { status?: string; risk_level?: string; owner?: string }
): Promise<RiskResponse> {
  const res = await apiClient.patch<RiskResponse>(`/risks/${riskId}`, patch);
  return res.data;
}
