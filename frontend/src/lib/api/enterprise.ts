import apiClient from "./client";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Enterprise {
  id: string;
  name: string;
  description: string | null;
  hq_country: string | null;
  industry: string | null;
  default_data_residency: string;
  default_data_classification: string;
  is_active: boolean;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface BusinessUnit {
  id: string;
  enterprise_id: string;
  name: string;
  description: string | null;
  region_scope: string | null;
  admin_user_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface LegalEntity {
  id: string;
  enterprise_id: string;
  name: string;
  country: string | null;
  registration_number: string | null;
  legal_form: string | null;
  is_active: boolean;
  created_at: string;
}

export interface EnterpriseRegion {
  id: string;
  enterprise_id: string;
  name: string;
  code: string;
  data_residency: string;
  admin_user_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface IdentityProvider {
  id: string;
  enterprise_id: string;
  name: string;
  provider_type: string;
  issuer: string | null;
  metadata_url: string | null;
  client_id: string | null;
  has_client_secret: boolean;
  is_active: boolean;
  created_at: string;
}

export interface GroupMapping {
  id: string;
  idp_id: string;
  enterprise_id: string;
  idp_group: string;
  mapped_role: string;
  scope: string | null;
  business_unit_id: string | null;
  region_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface EnterprisePolicy {
  id: string;
  enterprise_id: string;
  policy_type: string;
  name: string;
  description: string | null;
  config: Record<string, unknown>;
  cascade_to_children: boolean;
  scope: string;
  scope_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface RetentionRule {
  id: string;
  enterprise_id: string;
  entity_type: string;
  retention_days: number;
  cascade_to_children: boolean;
  legal_hold: boolean;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface NotificationPolicy {
  id: string;
  enterprise_id: string;
  name: string;
  escalation_routes: unknown[];
  regional_routes: Record<string, unknown>;
  executive_routes: unknown[];
  is_active: boolean;
  created_at: string;
}

export interface EnterpriseRisk {
  id: string;
  enterprise_id: string;
  title: string;
  description: string | null;
  severity: string;
  risk_status: string;
  esg_category: string | null;
  owner_user_id: string | null;
  mitigation_plan: string | null;
  linked_region_ids: string[];
  linked_business_unit_ids: string[];
  linked_organization_ids: string[];
  linked_supplier_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface EnterpriseHealthScore {
  score: number;
  grade: string;
  components: {
    compliance: number;
    risk_posture: number;
    finding_rate: number;
    supplier_coverage: number;
    governance: number;
  };
  drivers: string[];
}

export interface BURollupItem {
  business_unit_id: string;
  name: string;
  organization_count: number;
  supplier_count: number;
  total_risks: number;
  critical_risks: number;
  total_findings: number;
  open_findings: number;
  compliance_readiness: number;
}

export interface RegionRollupItem {
  region_id: string;
  name: string;
  organization_count: number;
  supplier_count: number;
  total_risks: number;
  critical_risks: number;
  total_findings: number;
  open_findings: number;
  compliance_readiness: number;
}

export interface EnterpriseDashboard {
  enterprise: Enterprise;
  health_score: EnterpriseHealthScore;
  rollup: {
    organization_count: number;
    supplier_count: number;
    total_risks: number;
    critical_risks: number;
    total_findings: number;
    open_findings: number;
    compliance_readiness: number;
  };
  bu_rollups: BURollupItem[];
  region_rollups: RegionRollupItem[];
}

export interface GlobalSearchResult {
  entity_type: string;
  entity_id: string;
  title: string;
  subtitle: string | null;
  score: number;
}

// ── API calls ─────────────────────────────────────────────────────────────────

const BASE = "/api/v1/enterprise";

export async function listEnterprises(): Promise<Enterprise[]> {
  const res = await apiClient.get(BASE);
  return res.data;
}

export async function createEnterprise(payload: {
  name: string;
  description?: string;
  hq_country?: string;
  industry?: string;
  default_data_residency?: string;
  default_data_classification?: string;
}): Promise<Enterprise> {
  const res = await apiClient.post(BASE, payload);
  return res.data;
}

export async function getEnterprise(id: string): Promise<Enterprise> {
  const res = await apiClient.get(`${BASE}/${id}`);
  return res.data;
}

export async function updateEnterprise(
  id: string,
  payload: Partial<{
    name: string;
    description: string;
    hq_country: string;
    industry: string;
    default_data_residency: string;
    default_data_classification: string;
    settings: Record<string, unknown>;
  }>
): Promise<Enterprise> {
  const res = await apiClient.patch(`${BASE}/${id}`, payload);
  return res.data;
}

export async function getEnterpriseDashboard(
  id: string
): Promise<EnterpriseDashboard> {
  const res = await apiClient.get(`${BASE}/${id}/dashboard`);
  return res.data;
}

// Business Units
export async function listBusinessUnits(
  enterpriseId: string
): Promise<BusinessUnit[]> {
  const res = await apiClient.get(`${BASE}/${enterpriseId}/business-units`);
  return res.data;
}

export async function createBusinessUnit(
  enterpriseId: string,
  payload: { name: string; description?: string; region_scope?: string }
): Promise<BusinessUnit> {
  const res = await apiClient.post(
    `${BASE}/${enterpriseId}/business-units`,
    payload
  );
  return res.data;
}

// Legal Entities
export async function listLegalEntities(
  enterpriseId: string
): Promise<LegalEntity[]> {
  const res = await apiClient.get(`${BASE}/${enterpriseId}/legal-entities`);
  return res.data;
}

// Regions
export async function listRegions(
  enterpriseId: string
): Promise<EnterpriseRegion[]> {
  const res = await apiClient.get(`${BASE}/${enterpriseId}/regions`);
  return res.data;
}

export async function createRegion(
  enterpriseId: string,
  payload: { name: string; code: string; data_residency?: string }
): Promise<EnterpriseRegion> {
  const res = await apiClient.post(`${BASE}/${enterpriseId}/regions`, payload);
  return res.data;
}

// Identity providers
export async function listIdentityProviders(
  enterpriseId: string
): Promise<IdentityProvider[]> {
  const res = await apiClient.get(`${BASE}/${enterpriseId}/identity`);
  return res.data;
}

export async function createIdentityProvider(
  enterpriseId: string,
  payload: {
    name: string;
    provider_type: string;
    issuer?: string;
    metadata_url?: string;
    client_id?: string;
    client_secret?: string;
  }
): Promise<IdentityProvider> {
  const res = await apiClient.post(`${BASE}/${enterpriseId}/identity`, payload);
  return res.data;
}

export async function listGroupMappings(
  enterpriseId: string,
  idpId: string
): Promise<GroupMapping[]> {
  const res = await apiClient.get(
    `${BASE}/${enterpriseId}/identity/${idpId}/group-mappings`
  );
  return res.data;
}

export async function createGroupMapping(
  enterpriseId: string,
  idpId: string,
  payload: {
    idp_group: string;
    mapped_role: string;
    scope?: string;
    business_unit_id?: string;
    region_id?: string;
  }
): Promise<GroupMapping> {
  const res = await apiClient.post(
    `${BASE}/${enterpriseId}/identity/${idpId}/group-mappings`,
    payload
  );
  return res.data;
}

// Policies
export async function listPolicies(
  enterpriseId: string
): Promise<EnterprisePolicy[]> {
  const res = await apiClient.get(`${BASE}/${enterpriseId}/policies`);
  return res.data;
}

export async function createPolicy(
  enterpriseId: string,
  payload: {
    policy_type: string;
    name: string;
    description?: string;
    config?: Record<string, unknown>;
    cascade_to_children?: boolean;
    scope?: string;
  }
): Promise<EnterprisePolicy> {
  const res = await apiClient.post(`${BASE}/${enterpriseId}/policies`, payload);
  return res.data;
}

// Retention rules
export async function listRetentionRules(
  enterpriseId: string
): Promise<RetentionRule[]> {
  const res = await apiClient.get(`${BASE}/${enterpriseId}/retention`);
  return res.data;
}

// Notification policies
export async function listNotificationPolicies(
  enterpriseId: string
): Promise<NotificationPolicy[]> {
  const res = await apiClient.get(`${BASE}/${enterpriseId}/notifications`);
  return res.data;
}

// Enterprise risks
export async function listEnterpriseRisks(
  enterpriseId: string,
  params?: { severity?: string; status?: string }
): Promise<EnterpriseRisk[]> {
  const res = await apiClient.get(`${BASE}/${enterpriseId}/risks`, { params });
  return res.data;
}

export async function createEnterpriseRisk(
  enterpriseId: string,
  payload: {
    title: string;
    description?: string;
    severity: string;
    esg_category?: string;
    mitigation_plan?: string;
  }
): Promise<EnterpriseRisk> {
  const res = await apiClient.post(`${BASE}/${enterpriseId}/risks`, payload);
  return res.data;
}

// Global search
export async function globalSearch(
  enterpriseId: string,
  query: string,
  entity_types?: string[]
): Promise<GlobalSearchResult[]> {
  const res = await apiClient.post(`${BASE}/${enterpriseId}/search`, {
    query,
    entity_types,
  });
  return res.data.results ?? [];
}

// Audit
export async function getEnterpriseAudit(
  enterpriseId: string,
  params?: { limit?: number; offset?: number }
): Promise<unknown[]> {
  const res = await apiClient.get(`${BASE}/${enterpriseId}/audit`, { params });
  return res.data;
}

// SCIM
export async function scimProvisionUser(
  enterpriseId: string,
  payload: {
    username: string;
    email: string;
    display_name: string;
    organization_id: string;
    groups?: string[];
    active?: boolean;
  }
): Promise<unknown> {
  const res = await apiClient.post(
    `${BASE}/${enterpriseId}/scim/users`,
    payload
  );
  return res.data;
}
