import apiClient from "./client";

export interface EventLog {
  id: string;
  organization_id: string;
  topic: string;
  event_type: string;
  aggregate_type: string;
  aggregate_id: string;
  payload_json: string;
  handler_status: "OK" | "ERROR";
  handler_error: string | null;
  kafka_partition: number | null;
  kafka_offset: number | null;
  consumed_at: string;
  processed_at: string | null;
}

export interface EventLogListResponse {
  items: EventLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface EventOutbox {
  id: string;
  organization_id: string;
  topic: string;
  event_type: string;
  aggregate_type: string;
  aggregate_id: string;
  outbox_status: "PENDING" | "PUBLISHED" | "FAILED";
  attempts: number;
  last_error: string | null;
  created_at: string;
  published_at: string | null;
  failed_at: string | null;
}

export interface EventOutboxListResponse {
  items: EventOutbox[];
  total: number;
  limit: number;
  offset: number;
}

export async function listEvents(params?: {
  event_type?: string;
  aggregate_type?: string;
  aggregate_id?: string;
  limit?: number;
  offset?: number;
}): Promise<EventLogListResponse> {
  const { data } = await apiClient.get<EventLogListResponse>(
    "/supply-chain/events",
    { params }
  );
  return data;
}

export async function getEvent(id: string): Promise<EventLog> {
  const { data } = await apiClient.get<EventLog>(`/supply-chain/events/${id}`);
  return data;
}

export async function listOutbox(params?: {
  outbox_status?: string;
  limit?: number;
  offset?: number;
}): Promise<EventOutboxListResponse> {
  const { data } = await apiClient.get<EventOutboxListResponse>(
    "/supply-chain/outbox",
    { params }
  );
  return data;
}

export async function retryOutboxEntry(id: string): Promise<EventOutbox> {
  const { data } = await apiClient.post<EventOutbox>(
    `/supply-chain/outbox/${id}/retry`
  );
  return data;
}
