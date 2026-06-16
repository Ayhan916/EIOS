import apiClient from "./client";
import type { ReportGenerateRequest, ReportResponse } from "@/types/api";

const BACKEND_ORIGIN =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function generateReport(
  assessmentId: string
): Promise<ReportResponse> {
  const body: ReportGenerateRequest = { assessment_id: assessmentId };
  const res = await apiClient.post<ReportResponse>("/reports/generate", body);
  return res.data;
}

export async function listReports(
  assessmentId: string
): Promise<ReportResponse[]> {
  const res = await apiClient.get<ReportResponse[]>("/reports/", {
    params: { assessment_id: assessmentId },
  });
  return res.data;
}

export async function getReport(reportId: string): Promise<ReportResponse> {
  const res = await apiClient.get<ReportResponse>(`/reports/${reportId}`);
  return res.data;
}

export function getReportDownloadUrl(reportId: string): string {
  // Build a direct download URL. The browser will handle the PDF download.
  // The token is injected via the Authorization header by the axios interceptor,
  // but for direct browser navigation we need to pass it differently.
  // We redirect through a signed URL endpoint instead — for now, download
  // via fetch and trigger a blob URL.
  return `${BACKEND_ORIGIN}/api/v1/reports/${reportId}/download`;
}

export async function downloadReportPdf(
  reportId: string,
  filename: string
): Promise<void> {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("eios_access_token")
      : null;

  const res = await fetch(
    `${BACKEND_ORIGIN}/api/v1/reports/${reportId}/download`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }
  );

  if (!res.ok) {
    throw new Error(`Download failed: ${res.status}`);
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".pdf") ? filename : `${filename}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
