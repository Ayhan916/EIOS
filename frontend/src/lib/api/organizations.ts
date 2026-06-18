import apiClient from "./client";
import type { OrganizationResponse, OrganizationUpdate } from "@/types/api";

export async function getMyOrganization(): Promise<OrganizationResponse> {
  const { data } = await apiClient.get<OrganizationResponse>(
    "/organizations/me"
  );
  return data;
}

export async function updateMyOrganization(
  update: OrganizationUpdate
): Promise<OrganizationResponse> {
  const { data } = await apiClient.patch<OrganizationResponse>(
    "/organizations/me",
    update
  );
  return data;
}
