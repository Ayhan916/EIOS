import apiClient from "./client";

// ── Domain enums ──────────────────────────────────────────────────────────────

export const PRODUCT_TYPES = [
  "FINISHED_GOOD", "SEMI_FINISHED", "COMPONENT", "SPARE_PART", "SERVICE", "OTHER",
] as const;
export type ProductType = typeof PRODUCT_TYPES[number];

export const PRODUCT_STATUSES = ["DRAFT", "ACTIVE", "DISCONTINUED", "ARCHIVED"] as const;
export type ProductStatus = typeof PRODUCT_STATUSES[number];

export const TARGET_MARKETS = ["EU", "US", "UK", "CN", "GLOBAL", "OTHER"] as const;
export type TargetMarket = typeof TARGET_MARKETS[number];

// ── Interfaces ────────────────────────────────────────────────────────────────

export interface Product {
  id: string;
  organization_id: string;
  name: string;
  product_type: ProductType;
  product_status: ProductStatus;
  sku: string | null;
  internal_code: string | null;
  gtin: string | null;
  category: string | null;
  brand: string | null;
  unit_of_measure: string;
  weight_kg: number | null;
  country_of_manufacture: string | null;
  is_regulated_product: boolean;
  target_market: TargetMarket | null;
  description: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProductBOMItem {
  id: string;
  organization_id: string;
  product_id: string;
  material_id: string;
  weight_pct: number | null;
  quantity: number | null;
  unit: string | null;
  is_substance_of_concern: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductComplianceSummary {
  regulation: string;
  worst_status: string;
  material_count: number;
  non_compliant_material_ids: string[];
}

export interface ProductSustainabilitySummary {
  has_data: boolean;
  bom_materials_total: number;
  bom_materials_with_lca: number;
  weight_coverage_pct: number;
  product_carbon_footprint_kg_co2e_per_kg: number | null;
  product_water_footprint_l_per_kg: number | null;
  materials_with_concern: number;
}

// ── API functions ─────────────────────────────────────────────────────────────

export const listProducts = (params?: {
  product_type?: ProductType;
  product_status?: ProductStatus;
  search?: string;
  category?: string;
  regulated_only?: boolean;
  limit?: number;
  offset?: number;
}) => apiClient.get<ProductListResponse>("/products", { params });

export const createProduct = (body: {
  name: string;
  product_type: ProductType;
  sku?: string;
  internal_code?: string;
  gtin?: string;
  category?: string;
  brand?: string;
  unit_of_measure?: string;
  weight_kg?: number;
  country_of_manufacture?: string;
  is_regulated_product?: boolean;
  target_market?: TargetMarket;
  description?: string;
  notes?: string;
}) => apiClient.post<Product>("/products", body);

export const getProduct = (id: string) =>
  apiClient.get<Product>(`/products/${id}`);

export const updateProduct = (id: string, body: Partial<{
  name: string;
  product_type: ProductType;
  product_status: ProductStatus;
  sku: string;
  gtin: string;
  category: string;
  brand: string;
  is_regulated_product: boolean;
  target_market: TargetMarket;
  description: string;
  notes: string;
}>) => apiClient.put<Product>(`/products/${id}`, body);

export const archiveProduct = (id: string) =>
  apiClient.delete(`/products/${id}`);

// BOM
export const listBOM = (productId: string) =>
  apiClient.get<ProductBOMItem[]>(`/products/${productId}/bom`);

export const addBOMItem = (productId: string, body: {
  material_id: string;
  weight_pct?: number;
  quantity?: number;
  unit?: string;
  is_substance_of_concern?: boolean;
  notes?: string;
}) => apiClient.post<ProductBOMItem>(`/products/${productId}/bom`, body);

export const deleteBOMItem = (productId: string, itemId: string) =>
  apiClient.delete(`/products/${productId}/bom/${itemId}`);

// Aggregated views
export const getProductCompliance = (productId: string) =>
  apiClient.get<ProductComplianceSummary[]>(`/products/${productId}/compliance`);

export const getProductSustainability = (productId: string, reportingYear?: number) =>
  apiClient.get<ProductSustainabilitySummary>(`/products/${productId}/sustainability`, {
    params: reportingYear ? { reporting_year: reportingYear } : undefined,
  });
