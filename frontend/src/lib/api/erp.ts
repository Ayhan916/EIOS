import apiClient from "./client";

export type AdapterType = "SAP_ODATA" | "ORACLE_REST" | "REST" | "CSV";
export type ConnectorStatus = "ACTIVE" | "INACTIVE";
export type JobStatus = "PENDING" | "RUNNING" | "SUCCESS" | "FAILED";
export type SyncDirection = "INBOUND" | "OUTBOUND";
export type EntityType = "Material" | "BOM" | "DPP";

export interface ERPConnector {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  adapter_type: AdapterType;
  base_url: string | null;
  secret_reference_id: string | null;
  auth_scheme: string;
  connector_status: ConnectorStatus;
  schedule_cron: string | null;
  last_sync_at: string | null;
  last_sync_status: string | null;
  timeout_seconds: number;
  config_json: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface ERPConnectorListResponse {
  items: ERPConnector[];
  total: number;
  limit: number;
  offset: number;
}

export interface ERPConnectorCreate {
  name: string;
  adapter_type: AdapterType;
  description?: string | null;
  base_url?: string | null;
  secret_reference_id?: string | null;
  auth_scheme?: string;
  schedule_cron?: string | null;
  timeout_seconds?: number;
  config_json?: string | null;
}

export interface ERPConnectorUpdate {
  name?: string;
  description?: string | null;
  base_url?: string | null;
  auth_scheme?: string;
  connector_status?: string;
  schedule_cron?: string | null;
  timeout_seconds?: number;
  config_json?: string | null;
}

export interface ERPSyncJob {
  id: string;
  organization_id: string;
  connector_id: string;
  direction: SyncDirection;
  entity_type: EntityType;
  job_status: JobStatus;
  trigger_source: string;
  records_fetched: number;
  records_created: number;
  records_updated: number;
  records_failed: number;
  error_message: string | null;
  error_details_json: string | null;
  started_at: string | null;
  completed_at: string | null;
  runtime_seconds: string | null;
  initiated_by: string | null;
  created_at: string;
}

export interface ERPSyncJobListResponse {
  items: ERPSyncJob[];
  total: number;
  limit: number;
  offset: number;
}

export interface ERPFieldMapping {
  id: string;
  organization_id: string;
  connector_id: string;
  entity_type: string;
  erp_field: string;
  eios_field: string;
  transform_fn: string | null;
  is_required: string;
  default_value: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ERPFieldMappingUpsert {
  entity_type: string;
  erp_field: string;
  eios_field: string;
  transform_fn?: string | null;
  is_required?: boolean;
  default_value?: string | null;
  notes?: string | null;
}

export interface ERPSyncTriggerRequest {
  direction?: SyncDirection;
  entity_type?: EntityType;
  materials_csv?: string | null;
  bom_csv?: string | null;
}

export async function listConnectors(params?: {
  adapter_type?: AdapterType;
  connector_status?: ConnectorStatus;
  limit?: number;
  offset?: number;
}): Promise<ERPConnectorListResponse> {
  const { data } = await apiClient.get<ERPConnectorListResponse>("/erp/connectors", { params });
  return data;
}

export async function getConnector(id: string): Promise<ERPConnector> {
  const { data } = await apiClient.get<ERPConnector>(`/erp/connectors/${id}`);
  return data;
}

export async function createConnector(body: ERPConnectorCreate): Promise<ERPConnector> {
  const { data } = await apiClient.post<ERPConnector>("/erp/connectors", body);
  return data;
}

export async function updateConnector(id: string, body: ERPConnectorUpdate): Promise<ERPConnector> {
  const { data } = await apiClient.put<ERPConnector>(`/erp/connectors/${id}`, body);
  return data;
}

export async function deactivateConnector(id: string): Promise<void> {
  await apiClient.delete(`/erp/connectors/${id}`);
}

export async function triggerSync(id: string, body: ERPSyncTriggerRequest): Promise<ERPSyncJob> {
  const { data } = await apiClient.post<ERPSyncJob>(`/erp/connectors/${id}/sync`, body);
  return data;
}

export async function listSyncJobs(
  connectorId: string,
  params?: { job_status?: JobStatus; limit?: number; offset?: number }
): Promise<ERPSyncJobListResponse> {
  const { data } = await apiClient.get<ERPSyncJobListResponse>(
    `/erp/connectors/${connectorId}/jobs`,
    { params }
  );
  return data;
}

export async function listFieldMappings(
  connectorId: string,
  entityType?: string
): Promise<ERPFieldMapping[]> {
  const { data } = await apiClient.get<ERPFieldMapping[]>(
    `/erp/connectors/${connectorId}/mappings`,
    { params: entityType ? { entity_type: entityType } : undefined }
  );
  return data;
}

export async function upsertFieldMapping(
  connectorId: string,
  body: ERPFieldMappingUpsert
): Promise<ERPFieldMapping> {
  const { data } = await apiClient.post<ERPFieldMapping>(
    `/erp/connectors/${connectorId}/mappings`,
    body
  );
  return data;
}

export async function deleteFieldMapping(connectorId: string, mappingId: string): Promise<void> {
  await apiClient.delete(`/erp/connectors/${connectorId}/mappings/${mappingId}`);
}
