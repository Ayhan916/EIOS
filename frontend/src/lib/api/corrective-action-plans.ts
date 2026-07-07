import apiClient from "./client";

export interface CAP {
  id: string;
  finding_id: string;
  organization_id: string;
  title: string;
  description: string;
  responsible_party: string;
  deadline: string | null;
  cap_status:
    | "DRAFT"
    | "COMMITTED"
    | "IN_PROGRESS"
    | "EVIDENCE_SUBMITTED"
    | "VERIFIED"
    | "CLOSED";
  evidence_note: string;
  evidence_file_url: string | null;
  evidence_submitted_at: string | null;
  verification_note: string;
  verified_by_user_id: string | null;
  verified_at: string | null;
  insufficient_reason: string;
  closed_at: string | null;
  closed_by_user_id: string | null;
  is_overdue: boolean;
  overdue_days: number;
  created_at: string;
  updated_at: string;
}

export interface CAPKPIs {
  total: number;
  open: number;
  overdue: number;
  verified: number;
  closed: number;
  completion_rate: number;
}

export const capApi = {
  create: async (data: {
    finding_id: string;
    title: string;
    description: string;
    responsible_party?: string;
    deadline?: string | null;
  }): Promise<CAP> => {
    const res = await apiClient.post("/corrective-action-plans/", data);
    return res.data;
  },

  getById: async (id: string): Promise<CAP> => {
    const res = await apiClient.get(`/corrective-action-plans/${id}`);
    return res.data;
  },

  listForOrg: async (capStatus?: string): Promise<CAP[]> => {
    const params = capStatus ? { cap_status: capStatus } : {};
    const res = await apiClient.get("/corrective-action-plans/", { params });
    return res.data;
  },

  getByFinding: async (findingId: string): Promise<CAP | null> => {
    const res = await apiClient.get(`/corrective-action-plans/by-finding/${findingId}`);
    return res.data;
  },

  getKPIs: async (): Promise<CAPKPIs> => {
    const res = await apiClient.get("/corrective-action-plans/kpis");
    return res.data;
  },

  commit: async (id: string): Promise<CAP> => {
    const res = await apiClient.patch(`/corrective-action-plans/${id}/commit`);
    return res.data;
  },

  start: async (id: string): Promise<CAP> => {
    const res = await apiClient.patch(`/corrective-action-plans/${id}/start`);
    return res.data;
  },

  submitEvidence: async (
    id: string,
    data: { evidence_note: string; evidence_file_url?: string | null }
  ): Promise<CAP> => {
    const res = await apiClient.patch(`/corrective-action-plans/${id}/submit-evidence`, data);
    return res.data;
  },

  verify: async (id: string, verification_note: string): Promise<CAP> => {
    const res = await apiClient.patch(`/corrective-action-plans/${id}/verify`, {
      verification_note,
    });
    return res.data;
  },

  markInsufficient: async (id: string, insufficient_reason: string): Promise<CAP> => {
    const res = await apiClient.patch(`/corrective-action-plans/${id}/mark-insufficient`, {
      insufficient_reason,
    });
    return res.data;
  },

  close: async (id: string): Promise<CAP> => {
    const res = await apiClient.patch(`/corrective-action-plans/${id}/close`);
    return res.data;
  },
};
