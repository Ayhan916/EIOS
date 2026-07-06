import apiClient from "./client";
import type { TokenResponse } from "@/types/api";

export interface DemoStatusResponse {
  seeded: boolean;
  demo_org_id: string;
  demo_user_email: string;
}

export async function getDemoStatus(): Promise<DemoStatusResponse> {
  const res = await apiClient.get<DemoStatusResponse>("/demo/status");
  return res.data;
}

export async function activateDemo(): Promise<TokenResponse> {
  const res = await apiClient.post<TokenResponse>("/demo/activate");
  return res.data;
}

export async function resetDemo(): Promise<TokenResponse> {
  const res = await apiClient.post<TokenResponse>("/demo/reset");
  return res.data;
}
