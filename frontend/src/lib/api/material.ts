import apiClient from "./client";

// ── Domain enums (mirror backend) ────────────────────────────────────────────

export const MATERIAL_TYPES = [
  "RAW_MATERIAL", "CHEMICAL", "METAL", "PLASTIC", "TEXTILE",
  "ELECTRONIC_COMPONENT", "PACKAGING", "INTERMEDIATE", "COMPOSITE", "OTHER",
] as const;
export type MaterialType = typeof MATERIAL_TYPES[number];

export const MATERIAL_STATUSES = ["ACTIVE", "UNDER_REVIEW", "RESTRICTED", "PHASING_OUT", "ARCHIVED"] as const;
export type MaterialStatus = typeof MATERIAL_STATUSES[number];

export const COMPLIANCE_REGULATIONS = [
  "REACH_SVHC", "ROHS", "CONFLICT_MINERALS", "EUDR", "BATTERY_REGULATION",
  "UFLPA", "CBAM", "POP", "WEEE", "SCIP", "TSCA", "PACKAGING_REGULATION", "CUSTOM",
] as const;
export type ComplianceRegulation = typeof COMPLIANCE_REGULATIONS[number];

export const COMPLIANCE_STATUSES = ["COMPLIANT", "NON_COMPLIANT", "PARTIALLY_COMPLIANT", "UNDER_ASSESSMENT", "EXEMPT", "UNKNOWN"] as const;
export type ComplianceStatus = typeof COMPLIANCE_STATUSES[number];

export const SOURCING_RISKS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
export type SourcingRisk = typeof SOURCING_RISKS[number];

// ── Interfaces ────────────────────────────────────────────────────────────────

export interface Material {
  id: string;
  organization_id: string;
  name: string;
  material_type: MaterialType;
  material_status: MaterialStatus;
  internal_code: string | null;
  cas_number: string | null;
  ec_number: string | null;
  iupac_name: string | null;
  molecular_formula: string | null;
  hs_code: string | null;
  un_number: string | null;
  ghs_hazard_class: string | null;
  unit_of_measure: string;
  weight_per_unit_kg: number | null;
  country_of_origin: string | null;
  is_critical_raw_material: boolean;
  recycled_content_pct: number | null;
  description: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface MaterialListResponse {
  items: Material[];
  total: number;
  limit: number;
  offset: number;
}

export interface MaterialComposition {
  id: string;
  organization_id: string;
  parent_material_id: string;
  child_material_id: string;
  weight_pct: number | null;
  quantity: number | null;
  unit: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface MaterialSourcing {
  id: string;
  organization_id: string;
  material_id: string;
  supplier_id: string;
  country_of_origin: string | null;
  annual_volume: number | null;
  unit: string | null;
  price_per_unit_eur: number | null;
  is_primary: boolean;
  lead_time_days: number | null;
  sourcing_risk: SourcingRisk;
  certification_required: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface MaterialCompliance {
  id: string;
  organization_id: string;
  material_id: string;
  regulation: ComplianceRegulation;
  custom_regulation_name: string | null;
  compliance_status: ComplianceStatus;
  assessed_at: string | null;
  valid_until: string | null;
  assessor: string | null;
  evidence_id: string | null;
  notes: string | null;
  is_expired: boolean;
  created_at: string;
  updated_at: string;
}

export interface MaterialSustainability {
  id: string;
  organization_id: string;
  material_id: string;
  reporting_year: number;
  carbon_footprint_kg_co2e_per_kg: number | null;
  carbon_scope: string;
  water_footprint_l_per_kg: number | null;
  energy_mj_per_kg: number | null;
  energy_renewable_pct: number | null;
  recycled_content_pct: number | null;
  recyclability_pct: number | null;
  biodegradable: boolean | null;
  data_source: string | null;
  is_third_party_verified: boolean;
  verification_standard: string | null;
  evidence_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// ── API client functions ──────────────────────────────────────────────────────

// Materials
export const listMaterials = (params?: {
  material_type?: MaterialType;
  material_status?: MaterialStatus;
  search?: string;
  crm_only?: boolean;
  limit?: number;
  offset?: number;
}) => apiClient.get<MaterialListResponse>("/materials", { params });

export const createMaterial = (body: {
  name: string;
  material_type: MaterialType;
  internal_code?: string;
  cas_number?: string;
  ec_number?: string;
  iupac_name?: string;
  molecular_formula?: string;
  hs_code?: string;
  un_number?: string;
  ghs_hazard_class?: string;
  unit_of_measure?: string;
  weight_per_unit_kg?: number;
  country_of_origin?: string;
  is_critical_raw_material?: boolean;
  recycled_content_pct?: number;
  description?: string;
  notes?: string;
}) => apiClient.post<Material>("/materials", body);

export const getMaterial = (id: string) =>
  apiClient.get<Material>(`/materials/${id}`);

export const updateMaterial = (id: string, body: Partial<{
  name: string;
  material_type: MaterialType;
  material_status: MaterialStatus;
  internal_code: string;
  cas_number: string;
  unit_of_measure: string;
  is_critical_raw_material: boolean;
  recycled_content_pct: number;
  description: string;
  notes: string;
}>) => apiClient.put<Material>(`/materials/${id}`, body);

export const archiveMaterial = (id: string) =>
  apiClient.delete(`/materials/${id}`);

// Composition / BOM
export const listComposition = (materialId: string) =>
  apiClient.get<MaterialComposition[]>(`/materials/${materialId}/composition`);

export const addComposition = (materialId: string, body: {
  child_material_id: string;
  weight_pct?: number;
  quantity?: number;
  unit?: string;
  notes?: string;
}) => apiClient.post<MaterialComposition>(`/materials/${materialId}/composition`, body);

export const deleteComposition = (materialId: string, compositionId: string) =>
  apiClient.delete(`/materials/${materialId}/composition/${compositionId}`);

// Sourcing
export const listSourcing = (materialId: string) =>
  apiClient.get<MaterialSourcing[]>(`/materials/${materialId}/sourcing`);

export const addSourcing = (materialId: string, body: {
  supplier_id: string;
  country_of_origin?: string;
  annual_volume?: number;
  unit?: string;
  price_per_unit_eur?: number;
  is_primary?: boolean;
  lead_time_days?: number;
  sourcing_risk?: SourcingRisk;
  certification_required?: string;
  notes?: string;
}) => apiClient.post<MaterialSourcing>(`/materials/${materialId}/sourcing`, body);

export const deleteSourcing = (materialId: string, sourcingId: string) =>
  apiClient.delete(`/materials/${materialId}/sourcing/${sourcingId}`);

// Compliance
export const listCompliance = (materialId: string) =>
  apiClient.get<MaterialCompliance[]>(`/materials/${materialId}/compliance`);

export const upsertCompliance = (materialId: string, body: {
  regulation: ComplianceRegulation;
  compliance_status: ComplianceStatus;
  custom_regulation_name?: string;
  assessed_at?: string;
  valid_until?: string;
  assessor?: string;
  evidence_id?: string;
  notes?: string;
}) => apiClient.post<MaterialCompliance>(`/materials/${materialId}/compliance`, body);

export const deleteComplianceFlag = (materialId: string, flagId: string) =>
  apiClient.delete(`/materials/${materialId}/compliance/${flagId}`);

// Sustainability
export const listSustainability = (materialId: string) =>
  apiClient.get<MaterialSustainability[]>(`/materials/${materialId}/sustainability`);

export const upsertSustainability = (materialId: string, body: {
  reporting_year: number;
  carbon_footprint_kg_co2e_per_kg?: number;
  carbon_scope?: string;
  water_footprint_l_per_kg?: number;
  energy_mj_per_kg?: number;
  energy_renewable_pct?: number;
  recycled_content_pct?: number;
  recyclability_pct?: number;
  biodegradable?: boolean;
  data_source?: string;
  is_third_party_verified?: boolean;
  verification_standard?: string;
  evidence_id?: string;
  notes?: string;
}) => apiClient.post<MaterialSustainability>(`/materials/${materialId}/sustainability`, body);
