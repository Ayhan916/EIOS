import apiClient from "./client";
import type { AssessmentResponse, Page } from "@/types/api";

export interface AssessmentListParams {
  page?: number;
  page_size?: number;
  status?: string;
  assessment_type?: string;
  search?: string;
}

export async function listAssessments(
  params: AssessmentListParams = {}
): Promise<Page<AssessmentResponse>> {
  const res = await apiClient.get<Page<AssessmentResponse>>("/assessments/", {
    params,
  });
  return res.data;
}

export async function getAssessment(id: string): Promise<AssessmentResponse> {
  const res = await apiClient.get<AssessmentResponse>(`/assessments/${id}`);
  return res.data;
}
