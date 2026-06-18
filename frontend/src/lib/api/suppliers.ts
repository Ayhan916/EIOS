import apiClient from "./client";
import type {
  Page,
  SupplierCreate,
  SupplierResponse,
  SupplierRiskProfile,
  SupplierUpdate,
  AssessmentResponse,
} from "@/types/api";

export async function listSuppliers(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  country?: string;
  industry?: string;
  supplier_tier?: string;
  status?: string;
}): Promise<Page<SupplierResponse>> {
  const res = await apiClient.get<Page<SupplierResponse>>("/suppliers/", {
    params,
  });
  return res.data;
}

export async function getSupplier(supplierId: string): Promise<SupplierResponse> {
  const res = await apiClient.get<SupplierResponse>(`/suppliers/${supplierId}`);
  return res.data;
}

export async function createSupplier(body: SupplierCreate): Promise<SupplierResponse> {
  const res = await apiClient.post<SupplierResponse>("/suppliers/", body);
  return res.data;
}

export async function updateSupplier(
  supplierId: string,
  body: SupplierUpdate
): Promise<SupplierResponse> {
  const res = await apiClient.patch<SupplierResponse>(`/suppliers/${supplierId}`, body);
  return res.data;
}

export async function archiveSupplier(supplierId: string): Promise<void> {
  await apiClient.delete(`/suppliers/${supplierId}`);
}

export async function listSupplierAssessments(
  supplierId: string,
  params?: { page?: number; page_size?: number }
): Promise<Page<AssessmentResponse>> {
  const res = await apiClient.get<Page<AssessmentResponse>>(
    `/suppliers/${supplierId}/assessments`,
    { params }
  );
  return res.data;
}

export async function getSupplierRiskProfile(
  supplierId: string
): Promise<SupplierRiskProfile> {
  const res = await apiClient.get<SupplierRiskProfile>(
    `/suppliers/${supplierId}/risk-profile`
  );
  return res.data;
}
