import apiClient from "./client";

export interface ChainNode {
  id: string;
  node_type: "finding" | "risk" | "recommendation" | "evidence" | "cap";
  label: string;
  detail: string;
  href: string | null;
}

export interface ChainEdge {
  source: string;
  target: string;
  label: string;
}

export interface FindingFilterOption {
  id: string;
  title: string;
  severity: string;
}

export interface EvidenceChainResponse {
  assessment_id: string;
  nodes: ChainNode[];
  edges: ChainEdge[];
  finding_filter_options: FindingFilterOption[];
}

export async function getEvidenceChain(
  assessmentId: string,
  findingId?: string
): Promise<EvidenceChainResponse> {
  const params = findingId ? `?finding_id=${findingId}` : "";
  const { data } = await apiClient.get<EvidenceChainResponse>(
    `/assessments/${assessmentId}/evidence-chain${params}`
  );
  return data;
}
