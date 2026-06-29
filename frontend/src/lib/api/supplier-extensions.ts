import apiClient from "./client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface SupplierLocation {
  id: string;
  supplier_id: string;
  organization_id: string;
  location_type: string;
  name: string;
  address: string | null;
  city: string | null;
  country: string | null;
  postal_code: string | null;
  region: string | null;
  latitude: number | null;
  longitude: number | null;
  capacity_description: string | null;
  employee_count: number | null;
  is_primary: boolean;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SupplierContact {
  id: string;
  supplier_id: string;
  organization_id: string;
  first_name: string;
  last_name: string | null;
  full_name: string;
  email: string | null;
  phone: string | null;
  role: string;
  job_title: string | null;
  department: string | null;
  language: string | null;
  is_primary: boolean;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SupplierCertification {
  id: string;
  supplier_id: string;
  organization_id: string;
  cert_type: string;
  custom_cert_name: string | null;
  issuing_body: string | null;
  certificate_number: string | null;
  scope_description: string | null;
  valid_from: string | null;
  valid_until: string | null;
  is_expired: boolean;
  days_until_expiry: number | null;
  evidence_id: string | null;
  location_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SupplierOwnership {
  id: string;
  supplier_id: string;
  organization_id: string;
  ownership_type: string;
  parent_company_name: string | null;
  parent_company_country: string | null;
  ultimate_parent_name: string | null;
  ultimate_parent_country: string | null;
  is_state_owned: boolean;
  state_ownership_pct: number | null;
  publicly_listed: boolean;
  stock_exchange: string | null;
  ticker_symbol: string | null;
  lei_code: string | null;
  duns_number: string | null;
  notes: string | null;
  updated_at: string;
}

export interface SupplierESGMetric {
  id: string;
  supplier_id: string;
  organization_id: string;
  reporting_year: number;
  reporting_period: string | null;
  metric_type: string;
  custom_metric_name: string | null;
  value: number;
  unit: string | null;
  esrs_reference: string | null;
  gri_reference: string | null;
  data_source: string | null;
  is_third_party_verified: boolean;
  verification_standard: string | null;
  evidence_id: string | null;
  notes: string | null;
  recorded_at: string;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function listLocations(supplierId: string): Promise<SupplierLocation[]> {
  const res = await apiClient.get(`/api/v1/suppliers/${supplierId}/locations`);
  return res.data;
}

export async function createLocation(
  supplierId: string,
  body: {
    location_type: string;
    name: string;
    address?: string;
    city?: string;
    country?: string;
    postal_code?: string;
    region?: string;
    latitude?: number;
    longitude?: number;
    capacity_description?: string;
    employee_count?: number;
    is_primary?: boolean;
    notes?: string;
  }
): Promise<SupplierLocation> {
  const res = await apiClient.post(`/api/v1/suppliers/${supplierId}/locations`, body);
  return res.data;
}

export async function deleteLocation(supplierId: string, locationId: string): Promise<void> {
  await apiClient.delete(`/api/v1/suppliers/${supplierId}/locations/${locationId}`);
}

export async function listContacts(supplierId: string): Promise<SupplierContact[]> {
  const res = await apiClient.get(`/api/v1/suppliers/${supplierId}/contacts`);
  return res.data;
}

export async function createContact(
  supplierId: string,
  body: {
    first_name: string;
    last_name?: string;
    email?: string;
    phone?: string;
    role: string;
    job_title?: string;
    department?: string;
    language?: string;
    is_primary?: boolean;
    notes?: string;
  }
): Promise<SupplierContact> {
  const res = await apiClient.post(`/api/v1/suppliers/${supplierId}/contacts`, body);
  return res.data;
}

export async function listCertifications(supplierId: string): Promise<SupplierCertification[]> {
  const res = await apiClient.get(`/api/v1/suppliers/${supplierId}/certifications`);
  return res.data;
}

export async function createCertification(
  supplierId: string,
  body: {
    cert_type: string;
    custom_cert_name?: string;
    issuing_body?: string;
    certificate_number?: string;
    scope_description?: string;
    valid_from?: string;
    valid_until?: string;
    evidence_id?: string;
    location_id?: string;
    notes?: string;
  }
): Promise<SupplierCertification> {
  const res = await apiClient.post(`/api/v1/suppliers/${supplierId}/certifications`, body);
  return res.data;
}

export async function getOwnership(supplierId: string): Promise<SupplierOwnership | null> {
  const res = await apiClient.get(`/api/v1/suppliers/${supplierId}/ownership`);
  return res.data ?? null;
}

export async function upsertOwnership(
  supplierId: string,
  body: {
    ownership_type: string;
    parent_company_name?: string;
    parent_company_country?: string;
    ultimate_parent_name?: string;
    ultimate_parent_country?: string;
    is_state_owned?: boolean;
    state_ownership_pct?: number;
    publicly_listed?: boolean;
    stock_exchange?: string;
    ticker_symbol?: string;
    lei_code?: string;
    duns_number?: string;
    notes?: string;
  }
): Promise<SupplierOwnership> {
  const res = await apiClient.put(`/api/v1/suppliers/${supplierId}/ownership`, body);
  return res.data;
}

export async function listESGMetrics(
  supplierId: string,
  reportingYear?: number
): Promise<SupplierESGMetric[]> {
  const params = reportingYear ? `?reporting_year=${reportingYear}` : "";
  const res = await apiClient.get(`/api/v1/suppliers/${supplierId}/esg-metrics${params}`);
  return res.data;
}

export async function recordESGMetric(
  supplierId: string,
  body: {
    reporting_year: number;
    metric_type: string;
    value: number;
    unit?: string;
    reporting_period?: string;
    custom_metric_name?: string;
    esrs_reference?: string;
    gri_reference?: string;
    data_source?: string;
    is_third_party_verified?: boolean;
    verification_standard?: string;
    evidence_id?: string;
    notes?: string;
  }
): Promise<SupplierESGMetric> {
  const res = await apiClient.post(`/api/v1/suppliers/${supplierId}/esg-metrics`, body);
  return res.data;
}

// ── External ESG Ratings (KAN-90) ─────────────────────────────────────────────

export interface ExternalESGRating {
  id: string;
  supplier_id: string;
  organization_id: string;
  provider: string;
  rating_date: string;
  score: number | null;
  max_score: number | null;
  score_pct: number | null;
  grade: string | null;
  percentile: number | null;
  peer_group: string | null;
  environmental_score: number | null;
  social_score: number | null;
  governance_score: number | null;
  ethics_score: number | null;
  sustainable_procurement_score: number | null;
  valid_until: string | null;
  is_expired: boolean;
  days_until_expiry: number | null;
  report_url: string | null;
  methodology_version: string | null;
  evidence_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export async function listESGRatings(
  supplierId: string,
  provider?: string
): Promise<ExternalESGRating[]> {
  const params = provider ? `?provider=${provider}` : "";
  const res = await apiClient.get(`/api/v1/suppliers/${supplierId}/esg-ratings${params}`);
  return res.data;
}

export async function createESGRating(
  supplierId: string,
  body: {
    provider: string;
    rating_date: string;
    score?: number;
    max_score?: number;
    score_pct?: number;
    grade?: string;
    percentile?: number;
    peer_group?: string;
    environmental_score?: number;
    social_score?: number;
    governance_score?: number;
    ethics_score?: number;
    sustainable_procurement_score?: number;
    valid_until?: string;
    report_url?: string;
    methodology_version?: string;
    evidence_id?: string;
    notes?: string;
  }
): Promise<ExternalESGRating> {
  const res = await apiClient.post(`/api/v1/suppliers/${supplierId}/esg-ratings`, body);
  return res.data;
}

export async function deleteESGRating(supplierId: string, ratingId: string): Promise<void> {
  await apiClient.delete(`/api/v1/suppliers/${supplierId}/esg-ratings/${ratingId}`);
}
