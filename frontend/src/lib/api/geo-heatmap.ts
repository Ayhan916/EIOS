import apiClient from "./client";

export interface GeoSupplierSummary {
  supplier_id: string;
  name: string;
  industry: string;
  supplier_tier: string;
  risk_score: number;
  risk_band: string;
  esg_score: number;
  trend: string;
}

export interface GeoCountryEntry {
  country: string;
  supplier_count: number;
  avg_risk_score: number;
  avg_esg_score: number;
  worst_band: string;
  critical_count: number;
  high_count: number;
  improving: number;
  deteriorating: number;
  country_risk_score: number | null;
  country_risk_level: string | null;
  sanctions_status: string | null;
  suppliers: GeoSupplierSummary[];
}

export interface GeoHeatmapResponse {
  countries: GeoCountryEntry[];
  total_suppliers: number;
  countries_count: number;
}

export const geoHeatmapApi = {
  getHeatmap: async (): Promise<GeoHeatmapResponse> => {
    const res = await apiClient.get("/suppliers/analytics/geo-heatmap");
    return res.data;
  },
};
