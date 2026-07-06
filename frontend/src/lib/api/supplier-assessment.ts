import apiClient from "./client";

export interface AssessmentTemplate {
  id: string;
  organization_id: string;
  title: string;
  description: string;
  is_default: boolean;
  created_by: string;
  created_at: string;
  question_count: number;
}

export interface AssessmentQuestion {
  id: string;
  section: string;
  question_text: string;
  question_type: string;
  options: string[];
  csddd_article: string;
  weight: number;
  is_required: boolean;
  sort_order: number;
}

export interface SupplierAssessment {
  id: string;
  organization_id: string;
  template_id: string;
  supplier_id: string;
  status: string;
  reference_code: string;
  token_expires_at: string;
  created_at: string;
  submitted_at: string | null;
  portal_link?: string;
}

export interface GapItem {
  question_id: string;
  section: string;
  csddd_article: string;
  question_text: string;
  answer_given: string;
  expected_answer: string;
  severity: string;
  recommendation: string;
}

export interface SectionScore {
  section: string;
  total_questions: number;
  answered: number;
  gaps: number;
  traffic_light: string;
}

export interface GapReport {
  assessment_id: string;
  supplier_id: string;
  section_scores: SectionScore[];
  gaps: GapItem[];
  overall_traffic_light: string;
  total_gaps: number;
  critical_gaps: number;
  generated_at: string;
}

// Portal types (public)
export interface PortalQuestion extends AssessmentQuestion {
  saved_answer: string;
}

export interface PortalAssessment {
  assessment_id: string;
  template_title: string;
  status: string;
  reference_code: string;
  expires_at: string;
  questions: PortalQuestion[];
}

const BASE = "/supplier-assessments";
const PUBLIC = "/supplier-portal";

export async function seedDefaultTemplate(): Promise<AssessmentTemplate> {
  const { data } = await apiClient.post(`${BASE}/templates/seed`);
  return data;
}

export async function listTemplates(): Promise<AssessmentTemplate[]> {
  const { data } = await apiClient.get(`${BASE}/templates`);
  return data;
}

export async function getTemplate(id: string): Promise<AssessmentTemplate & { questions: AssessmentQuestion[] }> {
  const { data } = await apiClient.get(`${BASE}/templates/${id}`);
  return data;
}

export async function createAssessment(templateId: string, supplierId: string): Promise<SupplierAssessment> {
  const { data } = await apiClient.post(`${BASE}/`, { template_id: templateId, supplier_id: supplierId });
  return data;
}

export async function listAssessments(status?: string): Promise<SupplierAssessment[]> {
  const { data } = await apiClient.get(`${BASE}/`, { params: status ? { status } : {} });
  return data;
}

export async function getAssessment(id: string): Promise<SupplierAssessment> {
  const { data } = await apiClient.get(`${BASE}/${id}`);
  return data;
}

export async function getGapReport(id: string): Promise<GapReport> {
  const { data } = await apiClient.get(`${BASE}/${id}/gap-report`);
  return data;
}

// Public portal functions (no auth required — called directly by browser)
export async function portalGetAssessment(token: string): Promise<PortalAssessment> {
  const { data } = await apiClient.get(`${PUBLIC}/assessment/${token}`);
  return data;
}

export async function portalSaveProgress(token: string, answers: Record<string, string>): Promise<void> {
  await apiClient.post(`${PUBLIC}/assessment/${token}/save`, { answers });
}

export async function portalSubmit(token: string, answers: Record<string, string>, email: string): Promise<{ reference_code: string }> {
  const { data } = await apiClient.post(`${PUBLIC}/assessment/${token}/submit`, {
    answers,
    submitter_email: email,
    confirm_accuracy: true,
  });
  return data;
}
