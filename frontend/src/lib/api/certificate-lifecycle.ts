import apiClient from "./client";

export interface CertificateAlertEntry {
  cert_id: string;
  supplier_id: string;
  supplier_name: string;
  cert_type: string;
  custom_cert_name: string | null;
  issuing_body: string | null;
  valid_until: string | null;
  days_until_expiry: number | null;
  lifecycle_status: "EXPIRED" | "EXPIRING_SOON" | "EXPIRING_60D" | "EXPIRING_90D" | "ACTIVE";
  is_verified: boolean;
}

export interface CertTypeCount {
  cert_type: string;
  total: number;
  expired: number;
  expiring_soon: number;
}

export interface CertificateLifecycleResponse {
  total: number;
  active: number;
  expiring_soon: number;
  expiring_60d: number;
  expiring_90d: number;
  expired: number;
  verified: number;
  alerts: CertificateAlertEntry[];
  by_cert_type: CertTypeCount[];
}

export const certLifecycleApi = {
  getLifecycle: async (daysWindow = 90): Promise<CertificateLifecycleResponse> => {
    const res = await apiClient.get("/suppliers/analytics/certificate-lifecycle", {
      params: { days_window: daysWindow },
    });
    return res.data;
  },
};
