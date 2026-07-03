import apiClient from "./client";

export interface RegulatoryChange {
  id: string;
  organization_id: string | null;
  framework_code: string;
  change_title: string;
  change_description: string;
  affected_article: string;
  effective_date: string | null;
  severity: "minor" | "moderate" | "major" | "critical";
  change_status: "new" | "scanning" | "impacts_identified" | "notified" | "acknowledged";
  source_name: string;
  source_url: string;
  affected_sectors: string[];
  affected_frameworks: string[];
  impact_summary: string;
  impacted_assessment_count: number;
  impacted_gap_count: number;
  regulation_refs: string;
  created_at: string;
  updated_at: string;
}

export interface RegulatoryChangeImpact {
  id: string;
  organization_id: string;
  change_id: string;
  assessment_id: string | null;
  compliance_gap_id: string | null;
  impact_type: string;
  re_review_required: boolean;
  notification_sent: boolean;
  acknowledged_by_user_id: string | null;
  acknowledged_at: string | null;
  created_at: string;
}

export interface ChangeSummary {
  new_changes: number;
  pending_re_reviews: number;
  total_changes: number;
}

export interface RegulatoryChangeCreate {
  framework_code: string;
  change_title: string;
  change_description: string;
  affected_article?: string;
  effective_date?: string;
  severity?: string;
  source_name?: string;
  source_url?: string;
  affected_sectors?: string[];
  regulation_refs?: string;
}

export const regulatoryChangesApi = {
  getSummary: async (): Promise<ChangeSummary> => {
    const res = await apiClient.get("/regulatory-changes/summary");
    return res.data;
  },

  list: async (params?: {
    framework?: string;
    change_status?: string;
    limit?: number;
    offset?: number;
  }): Promise<RegulatoryChange[]> => {
    const res = await apiClient.get("/regulatory-changes/", { params });
    return res.data;
  },

  create: async (body: RegulatoryChangeCreate): Promise<RegulatoryChange> => {
    const res = await apiClient.post("/regulatory-changes/", body);
    return res.data;
  },

  seed: async (): Promise<RegulatoryChange[]> => {
    const res = await apiClient.get("/regulatory-changes/seed");
    return res.data;
  },

  scanImpact: async (changeId: string): Promise<RegulatoryChange> => {
    const res = await apiClient.post(`/regulatory-changes/${changeId}/scan`);
    return res.data;
  },

  listImpacts: async (changeId: string): Promise<RegulatoryChangeImpact[]> => {
    const res = await apiClient.get(`/regulatory-changes/${changeId}/impacts`);
    return res.data;
  },

  acknowledgeImpact: async (impactId: string): Promise<RegulatoryChangeImpact> => {
    const res = await apiClient.patch(
      `/regulatory-changes/impacts/${impactId}/acknowledge`
    );
    return res.data;
  },
};
