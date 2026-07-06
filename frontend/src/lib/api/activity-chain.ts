import apiClient from "./client";

export interface ChainNode {
  id: string;
  type: string;
  label: string;
  chain_direction: "upstream" | "downstream" | "both" | "company";
  downstream_type?: string | null;
  tier: number;
  country?: string;
  industry?: string;
  risk_score: number | null;
  risk_band: string | null;
  color: string;
}

export interface ChainEdge {
  id: string;
  source: string;
  target: string;
  direction: string;
}

export interface VisualizationData {
  nodes: ChainNode[];
  edges: ChainEdge[];
  summary: {
    total: number;
    upstream: number;
    downstream: number;
    both: number;
    high_risk: number;
  };
}

export interface ChainStats {
  total: number;
  upstream_count: number;
  downstream_count: number;
  both_count: number;
  downstream_coverage_pct: number;
  downstream_type_breakdown: Record<string, number>;
}

export async function getVisualizationData(): Promise<VisualizationData> {
  const res = await apiClient.get<VisualizationData>("/activity-chain/visualization-data");
  return res.data;
}

export async function getChainStats(): Promise<ChainStats> {
  const res = await apiClient.get<ChainStats>("/activity-chain/stats");
  return res.data;
}
