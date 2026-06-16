import apiClient from "./client";
import type {
  Page,
  WorkflowJobResponse,
  WorkflowRunRequest,
  WorkflowRunResponse,
} from "@/types/api";

export interface StartWorkflowResponse {
  job_id: string;
  status: string;
  message: string;
}

export async function startWorkflow(
  data: WorkflowRunRequest
): Promise<StartWorkflowResponse> {
  const res = await apiClient.post<StartWorkflowResponse>(
    "/workflows/run",
    data
  );
  return res.data;
}

export async function getJob(jobId: string): Promise<WorkflowJobResponse> {
  const res = await apiClient.get<WorkflowJobResponse>(
    `/workflows/jobs/${jobId}`
  );
  return res.data;
}

export async function listJobs(params: {
  page?: number;
  page_size?: number;
  job_status?: string;
} = {}): Promise<Page<WorkflowJobResponse>> {
  const res = await apiClient.get<Page<WorkflowJobResponse>>(
    "/workflows/jobs",
    { params }
  );
  return res.data;
}

export async function listRuns(params: {
  page?: number;
  page_size?: number;
} = {}): Promise<Page<WorkflowRunResponse>> {
  const res = await apiClient.get<Page<WorkflowRunResponse>>(
    "/workflows/runs",
    { params }
  );
  return res.data;
}

export async function getWorkflowTypes(): Promise<
  { workflow_type: string; description: string; step_count: number }[]
> {
  const res = await apiClient.get<
    { workflow_type: string; description: string; step_count: number }[]
  >("/workflows/types");
  return res.data;
}
