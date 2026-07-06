import apiClient from "./client";

export interface ContractClause {
  id: string;
  organization_id: string;
  title: string;
  clause_text: string;
  category: string;
  cascade_required: boolean;
  is_mandatory: boolean;
  version: string;
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ContractAssurance {
  id: string;
  organization_id: string;
  supplier_id: string;
  clause_id: string;
  status: "pending" | "accepted" | "rejected" | "expired" | "waived";
  accepted_at: string | null;
  accepted_by: string | null;
  document_ref: string | null;
  notes: string | null;
  cascade_confirmed: boolean;
  cascade_confirmed_at: string | null;
  valid_until: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: string;
  assurance_id: string;
  changed_by: string;
  from_status: string | null;
  to_status: string;
  note: string | null;
  created_at: string;
}

export interface AssuranceDashboard {
  total: number;
  accepted: number;
  pending: number;
  rejected: number;
  expired: number;
  cascade_unconfirmed: number;
  acceptance_rate_pct: number;
}

export interface ClauseSummary {
  total: number;
  active: number;
  mandatory: number;
  cascade_required: number;
  by_category: Record<string, number>;
}

export interface SupplierCoverage {
  supplier_id: string;
  total: number;
  accepted: number;
  pending: number;
  rejected: number;
}

// Clause API
export async function listClauses(activeOnly = true): Promise<ContractClause[]> {
  const res = await apiClient.get<ContractClause[]>("/contractual-assurance/clauses/", {
    params: { active_only: activeOnly },
  });
  return res.data;
}

export async function getClauseSummary(): Promise<ClauseSummary> {
  const res = await apiClient.get<ClauseSummary>("/contractual-assurance/clauses/summary");
  return res.data;
}

export async function createClause(data: {
  title: string;
  clause_text: string;
  category: string;
  cascade_required: boolean;
  is_mandatory: boolean;
  version?: string;
}): Promise<ContractClause> {
  const res = await apiClient.post<ContractClause>("/contractual-assurance/clauses/", data);
  return res.data;
}

export async function seedClauses(): Promise<{ seeded: number }> {
  const res = await apiClient.post<{ seeded: number }>("/contractual-assurance/clauses/seed");
  return res.data;
}

export async function updateClause(
  id: string,
  data: Partial<Pick<ContractClause, "title" | "clause_text" | "category" | "cascade_required" | "is_mandatory" | "version" | "is_active">>
): Promise<ContractClause> {
  const res = await apiClient.patch<ContractClause>(`/contractual-assurance/clauses/${id}`, data);
  return res.data;
}

// Assurance API
export async function listAssurances(params?: {
  supplier_id?: string;
  clause_id?: string;
  status?: string;
}): Promise<ContractAssurance[]> {
  const res = await apiClient.get<ContractAssurance[]>("/contractual-assurance/assurances/", { params });
  return res.data;
}

export async function createAssurance(data: {
  supplier_id: string;
  clause_id: string;
  document_ref?: string | null;
  notes?: string | null;
  valid_until?: string | null;
}): Promise<ContractAssurance> {
  const res = await apiClient.post<ContractAssurance>("/contractual-assurance/assurances/", data);
  return res.data;
}

export async function acceptAssurance(id: string, document_ref?: string): Promise<ContractAssurance> {
  const res = await apiClient.post<ContractAssurance>(`/contractual-assurance/assurances/${id}/accept`, {
    document_ref: document_ref ?? null,
  });
  return res.data;
}

export async function updateAssuranceStatus(
  id: string,
  status: string,
  note?: string
): Promise<ContractAssurance> {
  const res = await apiClient.patch<ContractAssurance>(`/contractual-assurance/assurances/${id}/status`, {
    status,
    note: note ?? null,
  });
  return res.data;
}

export async function confirmCascade(id: string): Promise<ContractAssurance> {
  const res = await apiClient.post<ContractAssurance>(
    `/contractual-assurance/assurances/${id}/confirm-cascade`
  );
  return res.data;
}

export async function getAssuranceAuditLog(id: string): Promise<AuditLog[]> {
  const res = await apiClient.get<AuditLog[]>(`/contractual-assurance/assurances/${id}/audit-log`);
  return res.data;
}

// Dashboard API
export async function getAssuranceDashboard(): Promise<AssuranceDashboard> {
  const res = await apiClient.get<AssuranceDashboard>("/contractual-assurance/dashboard");
  return res.data;
}

export async function getSupplierCoverage(): Promise<SupplierCoverage[]> {
  const res = await apiClient.get<SupplierCoverage[]>("/contractual-assurance/supplier-coverage");
  return res.data;
}
