import apiClient from "./client";
import type {
  ApiKeyCreate,
  ApiKeyCreatedResponse,
  ApiKeyResponse,
  ApiKeyUsageSummary,
  ServiceAccountCreate,
  ServiceAccountResponse,
  WebhookCreate,
  WebhookDeliveryResponse,
  WebhookResponse,
  WebhookUpdate,
} from "@/types/api";

const BASE = "/platform";

// ── Service Accounts ──────────────────────────────────────────────────────────

export async function createServiceAccount(
  data: ServiceAccountCreate
): Promise<ServiceAccountResponse> {
  const r = await apiClient.post<ServiceAccountResponse>(
    `${BASE}/service-accounts`,
    data
  );
  return r.data;
}

export async function listServiceAccounts(): Promise<ServiceAccountResponse[]> {
  const r = await apiClient.get<ServiceAccountResponse[]>(
    `${BASE}/service-accounts`
  );
  return r.data;
}

export async function deactivateServiceAccount(id: string): Promise<void> {
  await apiClient.post(`${BASE}/service-accounts/${id}/deactivate`);
}

// ── API Keys ──────────────────────────────────────────────────────────────────

export async function createApiKey(
  data: ApiKeyCreate
): Promise<ApiKeyCreatedResponse> {
  const r = await apiClient.post<ApiKeyCreatedResponse>(
    `${BASE}/api-keys`,
    data
  );
  return r.data;
}

export async function listApiKeys(): Promise<ApiKeyResponse[]> {
  const r = await apiClient.get<ApiKeyResponse[]>(`${BASE}/api-keys`);
  return r.data;
}

export async function revokeApiKey(id: string): Promise<void> {
  await apiClient.post(`${BASE}/api-keys/${id}/revoke`);
}

export async function getApiKeyUsage(): Promise<ApiKeyUsageSummary[]> {
  const r = await apiClient.get<ApiKeyUsageSummary[]>(`${BASE}/api-keys/usage`);
  return r.data;
}

// ── Webhooks ──────────────────────────────────────────────────────────────────

export async function createWebhook(
  data: WebhookCreate
): Promise<WebhookResponse> {
  const r = await apiClient.post<WebhookResponse>(`${BASE}/webhooks`, data);
  return r.data;
}

export async function listWebhooks(): Promise<WebhookResponse[]> {
  const r = await apiClient.get<WebhookResponse[]>(`${BASE}/webhooks`);
  return r.data;
}

export async function updateWebhook(
  id: string,
  data: WebhookUpdate
): Promise<WebhookResponse> {
  const r = await apiClient.patch<WebhookResponse>(
    `${BASE}/webhooks/${id}`,
    data
  );
  return r.data;
}

export async function deleteWebhook(id: string): Promise<void> {
  await apiClient.delete(`${BASE}/webhooks/${id}`);
}

export async function listWebhookDeliveries(
  webhookId: string,
  limit = 50
): Promise<WebhookDeliveryResponse[]> {
  const r = await apiClient.get<WebhookDeliveryResponse[]>(
    `${BASE}/webhooks/${webhookId}/deliveries`,
    { params: { limit } }
  );
  return r.data;
}

export async function listAllDeliveries(
  limit = 100
): Promise<WebhookDeliveryResponse[]> {
  const r = await apiClient.get<WebhookDeliveryResponse[]>(
    `${BASE}/deliveries`,
    { params: { limit } }
  );
  return r.data;
}
