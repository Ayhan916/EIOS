import apiClient from "./client";

export interface MaterialBreakdownItem {
  material_id: string;
  material_name: string;
  weight_pct: number;
  co2e_per_kg: number | null;
  contribution_kg_co2e: number | null;
}

export interface ProductCarbonFootprint {
  id: string;
  organization_id: string;
  product_id: string;
  reporting_year: number;
  pcf_kg_co2e_per_unit: number | null;
  pcf_source: string;
  bom_materials_total: number;
  bom_materials_with_lca: number;
  weight_coverage_pct: number | null;
  material_breakdown: MaterialBreakdownItem[];
  calc_version: string;
  calculated_at: string;
  calculated_by: string | null;
  notes: string | null;
}

export interface ProductCarbonFootprintListResponse {
  items: ProductCarbonFootprint[];
  total: number;
}

export interface Scope3Inventory {
  id: string;
  organization_id: string;
  reporting_year: number;
  total_pcf_kg_co2e: number;
  total_pcf_tco2e: number;
  products_included: number;
  products_with_full_lca: number;
  products_with_partial_lca: number;
  products_without_lca: number;
  top_contributors: Array<{
    product_id: string;
    pcf_kg_co2e: number;
    weight_coverage_pct: number | null;
  }>;
  calc_version: string;
  calculated_at: string;
  calculated_by: string | null;
}

export interface Scope3InventoryListResponse {
  items: Scope3Inventory[];
  total: number;
}

export interface Scope3OrgSummary {
  organization_id: string;
  reporting_year: number | null;
  total_products_with_pcf: number;
  total_pcf_kg_co2e: number;
  total_pcf_tco2e: number;
  avg_pcf_kg_co2e_per_product: number | null;
  lca_coverage_pct: number | null;
}

export async function calculatePCF(
  productId: string,
  reportingYear: number,
  notes?: string
): Promise<ProductCarbonFootprint> {
  const { data } = await apiClient.post<ProductCarbonFootprint>(
    `/scope3/pcf/${productId}`,
    { reporting_year: reportingYear, notes: notes ?? null }
  );
  return data;
}

export async function listProductPCFs(
  productId: string,
  limit = 20
): Promise<ProductCarbonFootprintListResponse> {
  const { data } = await apiClient.get<ProductCarbonFootprintListResponse>(
    `/scope3/pcf/${productId}`,
    { params: { limit } }
  );
  return data;
}

export async function listOrgPCFs(params?: {
  reporting_year?: number;
  limit?: number;
}): Promise<ProductCarbonFootprintListResponse> {
  const { data } = await apiClient.get<ProductCarbonFootprintListResponse>(
    "/scope3/pcf",
    { params }
  );
  return data;
}

export async function computeInventory(year: number): Promise<Scope3Inventory> {
  const { data } = await apiClient.post<Scope3Inventory>(`/scope3/inventory/${year}`);
  return data;
}

export async function listInventories(): Promise<Scope3InventoryListResponse> {
  const { data } = await apiClient.get<Scope3InventoryListResponse>("/scope3/inventory");
  return data;
}

export async function getInventory(year: number): Promise<Scope3Inventory> {
  const { data } = await apiClient.get<Scope3Inventory>(`/scope3/inventory/${year}`);
  return data;
}

export async function getScope3Summary(reportingYear?: number): Promise<Scope3OrgSummary> {
  const { data } = await apiClient.get<Scope3OrgSummary>("/scope3/summary", {
    params: reportingYear ? { reporting_year: reportingYear } : undefined,
  });
  return data;
}
