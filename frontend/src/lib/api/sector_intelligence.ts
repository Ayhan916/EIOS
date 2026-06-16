import apiClient from "./client";
import type { SectorBenchmarkResponse, SectorESGProfileResponse } from "@/types/api";

export async function listSectorProfiles(): Promise<SectorESGProfileResponse[]> {
  const res = await apiClient.get<SectorESGProfileResponse[]>("/sectors/profiles");
  return res.data;
}

export async function getSectorProfileByNace(
  naceCode: string
): Promise<SectorESGProfileResponse> {
  const res = await apiClient.get<SectorESGProfileResponse>(
    `/sectors/profile/nace/${encodeURIComponent(naceCode)}`
  );
  return res.data;
}

export async function getSectorProfile(
  sectorId: string
): Promise<SectorESGProfileResponse> {
  const res = await apiClient.get<SectorESGProfileResponse>(
    `/sectors/${sectorId}/profile`
  );
  return res.data;
}

export async function getAssessmentBenchmark(
  assessmentId: string
): Promise<SectorBenchmarkResponse> {
  const res = await apiClient.get<SectorBenchmarkResponse>(
    `/assessments/${assessmentId}/benchmark`
  );
  return res.data;
}
