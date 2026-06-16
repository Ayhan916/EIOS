import apiClient from "./client";
import type { ComplianceCoverageResponse } from "@/types/api";

export async function getComplianceCoverage(
  assessmentId: string
): Promise<ComplianceCoverageResponse> {
  const res = await apiClient.get<ComplianceCoverageResponse>(
    `/assessments/${assessmentId}/compliance`
  );
  return res.data;
}
