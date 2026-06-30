import apiClient from "./client";

export type ScanResult = "COMPLIANT" | "NON_COMPLIANT" | "PARTIAL" | "UNKNOWN";

export interface ProductComplianceScan {
  id: string;
  organization_id: string;
  product_id: string;
  regulation_code: string;
  scan_result: ScanResult;
  total_materials: number;
  compliant_count: number;
  non_compliant_count: number;
  unknown_count: number;
  flagged_material_ids: string[];
  scan_version: string;
  scanned_at: string;
  scanned_by: string | null;
}

export interface ProductComplianceScanListResponse {
  items: ProductComplianceScan[];
  total: number;
}

export interface MaterialStats {
  total_active: number;
  non_compliant: number;
  substances_of_concern_in_bom: number;
}

export interface ProductStats {
  total_active: number;
  scanned: number;
  non_compliant: number;
}

export interface DPPStats {
  total: number;
  disclosed: number;
  non_compliant: number;
}

export interface AtRiskRegulation {
  regulation_code: string;
  non_compliant_materials: number;
}

export interface SupplyChainComplianceSummary {
  organization_id: string;
  materials: MaterialStats;
  products: ProductStats;
  digital_product_passports: DPPStats;
  top_at_risk_regulations: AtRiskRegulation[];
}

export async function triggerProductScan(
  productId: string,
  regulationCode: string
): Promise<ProductComplianceScan> {
  const { data } = await apiClient.post<ProductComplianceScan>(
    `/compliance/supply-chain/scan/${productId}`,
    { regulation_code: regulationCode }
  );
  return data;
}

export async function listProductScans(
  productId: string,
  limit = 50
): Promise<ProductComplianceScanListResponse> {
  const { data } = await apiClient.get<ProductComplianceScanListResponse>(
    `/compliance/supply-chain/scan/${productId}`,
    { params: { limit } }
  );
  return data;
}

export async function listNonCompliantProducts(
  limit = 100
): Promise<ProductComplianceScanListResponse> {
  const { data } = await apiClient.get<ProductComplianceScanListResponse>(
    "/compliance/supply-chain/non-compliant",
    { params: { limit } }
  );
  return data;
}

export async function getSupplyChainSummary(): Promise<SupplyChainComplianceSummary> {
  const { data } = await apiClient.get<SupplyChainComplianceSummary>(
    "/compliance/supply-chain/summary"
  );
  return data;
}
