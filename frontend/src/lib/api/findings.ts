import apiClient from "./client";
import type {
  EvidenceInsightsResponse,
  FindingEvidenceLinkResponse,
  FindingResponse,
} from "@/types/api";

export async function listFindings(
  assessmentId: string
): Promise<FindingResponse[]> {
  const res = await apiClient.get<FindingResponse[]>(`/findings/`, {
    params: { assessment_id: assessmentId },
  });
  return res.data;
}

export async function getFindingEvidenceLinks(
  findingId: string
): Promise<FindingEvidenceLinkResponse[]> {
  const res = await apiClient.get<FindingEvidenceLinkResponse[]>(
    `/findings/${findingId}/evidence-links`
  );
  return res.data;
}

export async function getAssessmentEvidenceInsights(
  assessmentId: string
): Promise<EvidenceInsightsResponse> {
  const res = await apiClient.get<EvidenceInsightsResponse>(
    `/assessments/${assessmentId}/evidence-insights`
  );
  return res.data;
}
