import apiClient from "./client";

export interface SegmentedSupplierEntry {
  supplier_id: string;
  name: string;
  country: string;
  industry: string;
  supplier_tier: string;
  risk_score: number;
  risk_band: string;
  esg_score: number;
  trend: string;
  trend_delta: number;
}

export interface RiskSegment {
  risk_band: string;
  count: number;
  avg_risk_score: number;
  avg_esg_score: number;
  improving: number;
  deteriorating: number;
  stable: number;
  suppliers: SegmentedSupplierEntry[];
}

export interface SegmentationResponse {
  segments: RiskSegment[];
  unscored_count: number;
  total_suppliers: number;
  total_scored: number;
}

export const segmentationApi = {
  getSegmentation: async (): Promise<SegmentationResponse> => {
    const res = await apiClient.get("/suppliers/analytics/segmentation");
    return res.data;
  },
};
