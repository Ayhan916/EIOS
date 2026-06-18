import apiClient from "./client";
import type {
  AssessmentResponse,
  ActivityEvent,
  ReviewActionResponse,
  Page,
} from "@/types/api";

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

export async function submitForReview(
  id: string,
  body: { reviewer_id?: string; review_due_date?: string } = {}
): Promise<AssessmentResponse> {
  const { data } = await apiClient.post<AssessmentResponse>(
    `/assessments/${id}/submit-for-review`,
    body
  );
  return data;
}

export async function assignReviewer(
  id: string,
  body: { reviewer_id: string; review_due_date?: string }
): Promise<AssessmentResponse> {
  const { data } = await apiClient.post<AssessmentResponse>(
    `/assessments/${id}/assign-reviewer`,
    body
  );
  return data;
}

export async function submitReviewAction(
  id: string,
  body: { action_type: string; comment?: string }
): Promise<ReviewActionResponse> {
  const { data } = await apiClient.post<ReviewActionResponse>(
    `/assessments/${id}/review-action`,
    body
  );
  return data;
}

export async function listReviewActions(
  id: string
): Promise<ReviewActionResponse[]> {
  const { data } = await apiClient.get<ReviewActionResponse[]>(
    `/assessments/${id}/review-actions`
  );
  return data;
}

export async function getActivityTimeline(
  id: string
): Promise<ActivityEvent[]> {
  const { data } = await apiClient.get<ActivityEvent[]>(
    `/assessments/${id}/activity`
  );
  return data;
}
