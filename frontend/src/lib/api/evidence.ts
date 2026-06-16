import apiClient from "./client";
import type {
  DocumentUploadResponse,
  EvidenceCreate,
  EvidenceResponse,
  Page,
} from "@/types/api";

export async function listEvidence(params: {
  page?: number;
  page_size?: number;
  evidence_type?: string;
  search?: string;
} = {}): Promise<Page<EvidenceResponse>> {
  const res = await apiClient.get<Page<EvidenceResponse>>("/evidences/", {
    params,
  });
  return res.data;
}

export async function createEvidence(
  data: EvidenceCreate
): Promise<EvidenceResponse> {
  const res = await apiClient.post<EvidenceResponse>("/evidences/", data);
  return res.data;
}

export async function uploadDocument(
  evidenceId: string,
  file: File,
  onProgress?: (pct: number) => void
): Promise<DocumentUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiClient.post<DocumentUploadResponse>(
    `/evidences/${evidenceId}/upload`,
    form,
    {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded * 100) / e.total));
        }
      },
    }
  );
  return res.data;
}
