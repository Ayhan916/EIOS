import apiClient from "./client";

export type DPPFormat =
  | "BATTERY_REGULATION"
  | "ESPR_GENERAL"
  | "TEXTILE"
  | "ELECTRONICS"
  | "PACKAGING"
  | "CUSTOM";

export type DPPStatus = "DRAFT" | "ACTIVE" | "WITHDRAWN" | "EXPIRED";

export interface DPP {
  id: string;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
  organization_id: string;
  product_id: string;
  format: DPPFormat;
  dpp_status: DPPStatus;
  passport_uid: string;
  qr_payload: string | null;
  product_category: string | null;
  battery_chemistry: string | null;
  capacity_wh: number | null;
  nominal_voltage_v: number | null;
  declared_capacity_cycles: number | null;
  carbon_footprint_kg_co2e: number | null;
  carbon_footprint_source: string | null;
  recycled_content_pct: number | null;
  renewable_content_pct: number | null;
  substances_of_concern_count: number;
  non_compliant_regulations_count: number;
  manufacturer_name: string | null;
  manufacturer_country: string | null;
  manufacturing_date: string | null;
  valid_from: string | null;
  valid_until: string | null;
  disclosed_at: string | null;
  is_public: boolean;
  is_expired: boolean;
  evidence_id: string | null;
  notes: string | null;
}

export interface DPPListResponse {
  items: DPP[];
  total: number;
  limit: number;
  offset: number;
}

export interface DPPCreate {
  product_id: string;
  format: DPPFormat;
  product_category?: string | null;
  battery_chemistry?: string | null;
  capacity_wh?: number | null;
  nominal_voltage_v?: number | null;
  declared_capacity_cycles?: number | null;
  carbon_footprint_kg_co2e?: number | null;
  carbon_footprint_source?: string | null;
  recycled_content_pct?: number | null;
  renewable_content_pct?: number | null;
  manufacturer_name?: string | null;
  manufacturer_country?: string | null;
  manufacturing_date?: string | null;
  valid_from?: string | null;
  valid_until?: string | null;
  evidence_id?: string | null;
  notes?: string | null;
}

export interface DPPUpdate {
  dpp_status?: DPPStatus | null;
  product_category?: string | null;
  battery_chemistry?: string | null;
  capacity_wh?: number | null;
  nominal_voltage_v?: number | null;
  declared_capacity_cycles?: number | null;
  carbon_footprint_kg_co2e?: number | null;
  carbon_footprint_source?: string | null;
  recycled_content_pct?: number | null;
  renewable_content_pct?: number | null;
  manufacturer_name?: string | null;
  manufacturer_country?: string | null;
  manufacturing_date?: string | null;
  valid_from?: string | null;
  valid_until?: string | null;
  evidence_id?: string | null;
  notes?: string | null;
}

export async function listDPPs(params?: {
  dpp_status?: DPPStatus;
  format?: DPPFormat;
  product_id?: string;
  is_public?: boolean;
  limit?: number;
  offset?: number;
}): Promise<DPPListResponse> {
  const { data } = await apiClient.get<DPPListResponse>("/dpp", { params });
  return data;
}

export async function getDPP(id: string): Promise<DPP> {
  const { data } = await apiClient.get<DPP>(`/dpp/${id}`);
  return data;
}

export async function getDPPByUID(passportUID: string): Promise<DPP> {
  const { data } = await apiClient.get<DPP>(`/dpp/passport/${passportUID}`);
  return data;
}

export async function createDPP(body: DPPCreate): Promise<DPP> {
  const { data } = await apiClient.post<DPP>("/dpp", body);
  return data;
}

export async function updateDPP(id: string, body: DPPUpdate): Promise<DPP> {
  const { data } = await apiClient.put<DPP>(`/dpp/${id}`, body);
  return data;
}

export async function refreshDPP(id: string): Promise<DPP> {
  const { data } = await apiClient.post<DPP>(`/dpp/${id}/refresh`);
  return data;
}

export async function publishDPP(id: string): Promise<DPP> {
  const { data } = await apiClient.post<DPP>(`/dpp/${id}/publish`);
  return data;
}

export async function withdrawDPP(id: string): Promise<void> {
  await apiClient.delete(`/dpp/${id}`);
}

export async function listProductDPPs(productId: string): Promise<DPP[]> {
  const { data } = await apiClient.get<DPP[]>(`/products/${productId}/dpp`);
  return data;
}
