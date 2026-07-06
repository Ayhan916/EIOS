import apiClient from "./client";

export interface WorkflowStepResponse {
  key: string;
  label: string;
  count: number;
  status: "done" | "partial" | "missing";
  current: boolean;
  route: string | null;
  entities: Array<{ id: string; title: string }>;
  next_action_label: string | null;
  next_action_route: string | null;
}

export interface WorkflowContextResponse {
  workflow_id: string;
  workflow_name: string;
  entity_type: string;
  entity_id: string;
  assessment_id: string | null;
  supplier_id: string | null;
  supplier_name: string | null;
  steps: WorkflowStepResponse[];
  completion_pct: number;
  next_step: WorkflowStepResponse | null;
}

export async function getWorkflowContext(
  entityType: string,
  entityId: string
): Promise<WorkflowContextResponse> {
  const r = await apiClient.get(`/workflow/context/${entityType}/${entityId}`);
  return r.data as WorkflowContextResponse;
}
