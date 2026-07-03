// TypeScript types mirroring EIOS backend Pydantic schemas

export interface UserResponse {
  id: string;
  email: string;
  display_name: string;
  role: string;
  organization_id: string | null;
  is_active: boolean;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
  mfa_enabled: boolean;
}

export interface UserUpdate {
  role?: string;
  is_active?: boolean;
  display_name?: string;
}

export interface UserInviteRequest {
  email: string;
  display_name: string;
  role?: string;
}

export interface UserInviteResponse {
  user: UserResponse;
  temp_password: string;
}

export interface OrganizationResponse {
  id: string;
  name: string;
  description: string | null;
  organization_type: string;
  country: string | null;
  industry: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface OrganizationUpdate {
  name?: string;
  description?: string | null;
  country?: string | null;
  industry?: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserResponse;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterRequest {
  email: string;
  display_name: string;
  password: string;
  organization_name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface EntityResponse {
  id: string;
  status: string;
  version: number;
  owner: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssessmentResponse extends EntityResponse {
  title: string;
  description: string;
  assessment_type: string;
  scope: string;
  sector_id: string | null;
  methodology: string | null;
  confidence: string;
  approved_by: string | null;
  approval_date: string | null;
  quality_score: number | null;
  review_status: string;
  assigned_reviewer_id: string | null;
  review_due_date: string | null;
  // Supplier ownership (M27)
  supplier_id: string | null;
}

export type SupplierTier = "Tier 1" | "Tier 2" | "Tier 3" | "Other";
export type SupplierStatus = "Active" | "Inactive";

export interface SupplierResponse extends EntityResponse {
  organization_id: string;
  name: string;
  legal_name: string | null;
  country: string;
  industry: string;
  nace_code: string | null;
  website: string | null;
  supplier_tier: SupplierTier;
  supplier_status: SupplierStatus;
  notes: string | null;
}

export interface SupplierCreate {
  name: string;
  legal_name?: string | null;
  country?: string;
  industry?: string;
  nace_code?: string | null;
  website?: string | null;
  supplier_tier?: SupplierTier;
  notes?: string | null;
}

export interface SupplierUpdate {
  name?: string;
  legal_name?: string | null;
  country?: string;
  industry?: string;
  nace_code?: string | null;
  website?: string | null;
  supplier_tier?: SupplierTier;
  supplier_status?: SupplierStatus;
  notes?: string | null;
}

export interface SupplierRiskProfile {
  supplier_id: string;
  supplier_name: string;
  total_assessments: number;
  approved_assessments: number;
  assessments_in_review: number;
  last_assessment_date: string | null;
  total_findings: number;
  findings_by_severity: Record<string, number>;
  total_risks: number;
  risks_by_severity: Record<string, number>;
  open_recommendations: number;
  open_actions: number;
  overdue_actions: number;
}

export interface SupplierWatchlistItem {
  id: string;
  name: string;
  country: string;
  supplier_tier: SupplierTier;
  critical_findings: number;
  high_findings: number;
  open_actions: number;
  overdue_actions: number;
  last_assessment_date: string | null;
}

export interface CommentResponse {
  id: string;
  entity_type: string;
  entity_id: string;
  author_id: string;
  author_name: string | null;
  content: string;
  is_edited: boolean;
  is_deleted: boolean;
  edited_at: string | null;
  deleted_at: string | null;
  mentioned_user_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface CommentCreate {
  entity_type: string;
  entity_id: string;
  content: string;
}

export interface CommentEdit {
  content: string;
}

export interface ReviewActionResponse {
  id: string;
  assessment_id: string;
  actor_id: string;
  actor_email: string;
  action_type: string;
  comment: string | null;
  created_at: string;
}

export interface ActivityEvent {
  event_type: string;
  timestamp: string;
  actor_id: string | null;
  actor_name: string | null;
  action: string;
  detail: string | null;
  entity_type: string | null;
  entity_id: string | null;
  comment_id: string | null;
  comment_content: string | null;
}

export interface ReviewQueueItem {
  id: string;
  title: string;
  review_status: string;
  assigned_reviewer_id: string | null;
  review_due_date: string | null;
  created_at: string;
  is_overdue: boolean;
}

export interface FindingResponse extends EntityResponse {
  title: string;
  description: string;
  assessment_id: string;
  category: string;
  severity: string;
  confidence: string;
  reasoning: string | null;
  uncertainty: string | null;
  evidence_strength: "Weak" | "Moderate" | "Strong" | "Very Strong" | null;
  evidence_source_count: number;
  severity_score: number | null;
  probability_score: number | null;
}

export interface FindingEvidenceLinkResponse extends EntityResponse {
  finding_id: string;
  evidence_id: string;
  evidence_chunk_id: string | null;
  page_number: number | null;
  confidence_score: number | null;
  supporting_excerpt: string | null;
  link_method: string;
}

export interface FindingWithLinksResponse {
  finding: FindingResponse;
  evidence_links: FindingEvidenceLinkResponse[];
}

export interface EvidenceInsightsResponse {
  assessment_id: string;
  total_findings: number;
  linked_findings: number;
  total_evidence_links: number;
  strength_distribution: Record<string, number>;
  findings: FindingWithLinksResponse[];
}

export interface RiskResponse extends EntityResponse {
  title: string;
  description: string;
  risk_level: string;
  category: string;
  assessment_id: string | null;
  sector_id: string | null;
  probability: number | null;
  impact: number | null;
  confidence: string;
  reasoning: string | null;
  uncertainty: string | null;
  status: string;
  owner: string | null;
  severity_score: number | null;
  probability_score: number | null;
}

export type ActionStatus = "open" | "in_progress" | "resolved" | "verified";

export interface RecommendationResponse extends EntityResponse {
  title: string;
  description: string;
  priority: string;
  confidence: string;
  reasoning: string | null;
  action_required: boolean;
  due_date: string | null;
  approved_by: string | null;
  action_status: ActionStatus;
  assigned_to_id: string | null;
  expected_benefit: string | null;
  expected_risk: string | null;
  expected_roi: string | null;
  implementation_complexity: string | null;
}

export interface RecommendationUpdate {
  action_status?: ActionStatus;
  assigned_to_id?: string | null;
  due_date?: string | null;
  expected_benefit?: string | null;
  expected_risk?: string | null;
  expected_roi?: string | null;
  implementation_complexity?: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface WorkflowRunRequest {
  workflow_type: string;
  query: string;
  metadata?: Record<string, unknown>;
}

export interface WorkflowJobResponse {
  id: string;
  workflow_type: string;
  query: string;
  job_status: string;
  workflow_run_id: string | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentStepSummary {
  agent_run_id: string;
  agent_type: string;
  step_index: number;
  status: string;
  input_tokens: number;
  output_tokens: number;
  error: string | null;
}

export interface WorkflowRunResponse {
  id: string;
  workflow_type: string;
  query: string;
  verdict: string | null;
  verdict_reasoning: string | null;
  overall_risk_level: string | null;
  steps_completed: number;
  total_steps: number;
  total_input_tokens: number;
  total_output_tokens: number;
  error: string | null;
  assessment_id: string | null;
  finding_count: number;
  risk_count: number;
  recommendation_count: number;
  run_metadata: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
  steps: AgentStepSummary[];
}

export interface EvidenceResponse extends EntityResponse {
  title: string;
  source: string;
  description: string;
  evidence_type: string;
  confidence: string;
  url: string | null;
  language: string;
  published_at: string | null;
  retrieved_at: string | null;
  reliability_score: number | null;
  organization_id: string | null;
  ingestion_status: string;
  chunk_count: number;
  file_name: string | null;
  file_size_bytes: number | null;
  file_mime_type: string | null;
}

export interface EvidenceCreate {
  title: string;
  source: string;
  description: string;
  evidence_type?: string;
  language?: string;
}

export interface DocumentUploadResponse {
  evidence_id: string;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  ingestion_status: string;
  chunks_created: number;
  warnings: string[];
  parser_used: string;
}

export interface ArticleCoverageResponse {
  code: string;
  framework: string;
  article: string;
  title: string;
  obligation_type: string;
  esg_categories: string[];
  covered: boolean;
}

export interface FrameworkCoverageResponse {
  framework: string;
  total_articles: number;
  covered_count: number;
  coverage_ratio: number;
  articles: ArticleCoverageResponse[];
}

export interface GapResponse {
  article_code: string;
  framework: string;
  article: string;
  title: string;
  obligation_type: string;
  esg_categories: string[];
  regulatory_exposure: number;
  gap_severity: string;
  explanation: string;
  remediation_hint: string;
}

export interface ComplianceVerdictResponse {
  status: string;
  mandatory_coverage_ratio: number;
  total_mandatory_articles: number;
  covered_mandatory_count: number;
  mandatory_gap_count: number;
  critical_gap_count: number;
  high_gap_count: number;
  weighted_gap_score: number;
  explanation: string;
  top_gap_codes: string[];
}

export interface ComplianceCoverageResponse {
  assessment_id: string;
  covered_article_codes: string[];
  framework_coverage: FrameworkCoverageResponse[];
  overall_coverage_ratio: number;
  mandatory_coverage_ratio: number;
  quality_score: number | null;
  gaps: GapResponse[];
  verdict: ComplianceVerdictResponse;
}

export interface OrganizationResponse {
  id: string;
  name: string;
  description: string | null;
  organization_type: string;
  country: string | null;
  industry: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface SectorESGProfileResponse {
  nace_section: string;
  section_name: string;
  environmental_risk: string;
  social_risk: string;
  governance_risk: string;
  overall_risk: string;
  key_risk_themes: string[];
  applicable_frameworks: string[];
  baseline_mandatory_coverage: number;
  expected_min_findings: number;
  expected_min_risks: number;
  regulatory_exposure_notes: string;
  esg_priority_categories: string[];
}

export interface SeverityDistributionResponse {
  critical: number;
  high: number;
  medium: number;
  low: number;
  total: number;
  high_or_critical_count: number;
}

export interface PeerSummaryResponse {
  assessment_id: string;
  title: string;
  quality_score: number | null;
  finding_count: number;
  risk_count: number;
  high_critical_finding_count: number;
}

export interface SectorBenchmarkResponse {
  assessment_id: string;
  assessment_title: string;
  sector_id: string | null;
  sector_nace_code: string;
  sector_name: string;
  profile_nace_section: string;
  finding_distribution: SeverityDistributionResponse;
  risk_distribution: SeverityDistributionResponse;
  quality_score: number | null;
  baseline_mandatory_coverage: number;
  expected_min_findings: number;
  expected_min_risks: number;
  environmental_risk: string;
  social_risk: string;
  governance_risk: string;
  overall_sector_risk: string;
  key_risk_themes: string[];
  applicable_frameworks: string[];
  esg_priority_categories: string[];
  regulatory_exposure_notes: string;
  mandatory_coverage: number | null;
  coverage_vs_baseline: number | null;
  coverage_rating: string;
  coverage_explanation: string;
  finding_adequacy: string;
  finding_explanation: string;
  key_themes_identified: string[];
  key_themes_not_addressed: string[];
  peer_count: number;
  peers: PeerSummaryResponse[];
  org_avg_quality_score: number | null;
  org_avg_finding_count: number | null;
  benchmark_rating: string;
  benchmark_explanation: string;
}

export interface ReportResponse extends EntityResponse {
  assessment_id: string;
  title: string;
  generated_by: string;
  organization_id: string | null;
  format: string;
  finding_count: number;
  risk_count: number;
  recommendation_count: number;
  evidence_count: number;
  content_snapshot: Record<string, unknown> | null;
}

export interface ReportGenerateRequest {
  assessment_id: string;
}

export interface NotificationResponse {
  id: string;
  notification_type: string;
  title: string;
  body: string;
  entity_type: string | null;
  entity_id: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationResponse[];
  unread_count: number;
}

export interface NotificationPreferences {
  email_workflow_completed: boolean;
  email_action_overdue: boolean;
  email_assessment_approved: boolean;
  email_recommendation_assigned: boolean;
  // #134 Weekly ESG digest
  email_weekly_digest?: boolean;
  digest_day?: "Monday" | "Tuesday" | "Wednesday" | "Thursday" | "Friday";
}

export interface ApiError {
  detail: string | { msg: string; type: string }[];
}

// ── M28 Supplier Intelligence ─────────────────────────────────────────────────

export interface ScoreDriver {
  factor: string;
  count: number;
  impact: "high" | "medium" | "low";
  description: string;
}

export interface SupplierScoreResponse {
  supplier_id: string;
  supplier_name: string;
  calculated_at: string;
  score_version: string;
  esg_score: number;
  environmental_score: number;
  social_score: number;
  governance_score: number;
  risk_score: number;
  risk_band: "Low" | "Moderate" | "High" | "Critical";
  trend: "Improving" | "Stable" | "Deteriorating";
  trend_delta: number;
  sector_percentile: number | null;
  drivers: ScoreDriver[];
  inputs: Record<string, number>;
}

export interface SupplierScoreHistoryEntry {
  calculated_at: string;
  esg_score: number;
  risk_score: number;
  risk_band: string;
  trend: string;
}

export interface SupplierBenchmark {
  supplier_id: string;
  supplier_name: string;
  risk_score: number;
  risk_band: string;
  sector_percentile: number | null;
  peer_comparison: string;
  peers_evaluated: number;
  industry: string;
}

export interface WatchlistEntry {
  supplier_id: string;
  supplier_name: string;
  country: string;
  industry: string;
  supplier_tier: string;
  risk_score: number;
  risk_band: string;
  trend: string;
  trend_delta: number;
  critical_findings: number;
  overdue_actions: number;
  alert_reasons: string[];
}

export interface PortfolioAnalytics {
  total_suppliers: number;
  scored_suppliers: number;
  critical_risk_suppliers: number;
  high_risk_suppliers: number;
  improving_suppliers: number;
  deteriorating_suppliers: number;
  avg_esg_score: number | null;
  avg_risk_score: number | null;
  risk_distribution: Record<string, number>;
}

export interface ExecutiveRankingEntry {
  rank: number;
  supplier_id: string;
  supplier_name: string;
  country: string;
  industry: string;
  supplier_tier: string;
  risk_score: number;
  risk_band: string;
  esg_score: number;
  trend: string;
  trend_delta: number;
  critical_findings: number;
  overdue_actions: number;
}

export interface HeatmapCell {
  pillar: string;
  severity: string;
  count: number;
}

export interface RiskHeatmap {
  cells: HeatmapCell[];
  total_findings: number;
  supplier_id: string | null;
}

// ── M29 Executive & Board Reporting ──────────────────────────────────────────

export interface PortfolioSummary {
  total_suppliers: number;
  scored_suppliers: number;
  critical_risk_suppliers: number;
  high_risk_suppliers: number;
  moderate_risk_suppliers: number;
  low_risk_suppliers: number;
  improving_suppliers: number;
  deteriorating_suppliers: number;
  avg_esg_score: number | null;
  avg_risk_score: number | null;
  risk_distribution: Record<string, number>;
}

export interface ActionSummary {
  open_actions: number;
  overdue_actions: number;
  total_actions: number;
  resolution_rate: number | null;
}

export interface GovernanceSummary {
  assessments_awaiting_review: number;
  assessments_approved: number;
  critical_findings_total: number;
}

export interface ExecutiveDashboard {
  portfolio_summary: PortfolioSummary;
  action_summary: ActionSummary;
  governance_summary: GovernanceSummary;
}

export interface MonthlyDataPoint {
  month: string;
  avg_esg_score: number | null;
  avg_risk_score: number | null;
  supplier_count: number;
  high_risk_count: number;
  critical_risk_count: number;
  risk_distribution: Record<string, number>;
}

export interface KPITrendResponse {
  period_days: number;
  data_points: MonthlyDataPoint[];
  esg_delta: number | null;
  risk_delta: number | null;
}

export interface RiskRegisterEntry {
  rank: number;
  supplier_id: string;
  supplier_name: string;
  country: string;
  industry: string;
  supplier_tier: string;
  risk_score: number;
  risk_band: string;
  esg_score: number;
  trend: string;
  trend_delta: number;
  critical_findings: number;
  overdue_actions: number;
}

export interface HeatmapBucket {
  label: string;
  supplier_count: number;
  avg_risk_score: number;
  critical_count: number;
  high_count: number;
}

export interface ExecutiveHeatmapResponse {
  view: string;
  buckets: HeatmapBucket[];
}

export interface ActionEffectivenessResponse {
  opened_this_period: number;
  closed_this_period: number;
  total_open: number;
  total_overdue: number;
  resolution_rate: number | null;
  avg_resolution_days: number | null;
}

export interface GovernanceMetricsResponse {
  total_review_decisions: number;
  approved: number;
  rejected: number;
  changes_requested: number;
  approval_rate: number | null;
  rejection_rate: number | null;
  changes_requested_rate: number | null;
  avg_review_days: number | null;
}

export interface BoardReportSummary {
  id: string;
  title: string;
  report_version: string;
  period_start: string;
  period_end: string;
  generated_at: string;
  executive_summary: string;
}

export interface BoardReportDetail extends BoardReportSummary {
  report_data: Record<string, unknown>;
  supplier_snapshot: unknown[];
}

export interface BoardReportRequest {
  title?: string;
  period_start: string;
  period_end: string;
  kpi_period_days?: number;
}

export interface ReportScheduleResponse {
  id: string;
  frequency: string;
  next_run_at: string;
  last_run_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ReportScheduleRequest {
  frequency: "monthly" | "quarterly";
  next_run_at: string;
  report_config?: Record<string, unknown>;
}

// ── M30 API Platform ──────────────────────────────────────────────────────────

export interface ServiceAccountResponse {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  is_active: boolean;
  created_at: string;
  created_by: string | null;
}

export interface ServiceAccountCreate {
  name: string;
  description?: string;
}

export interface ApiKeyCreatedResponse {
  id: string;
  name: string;
  key_prefix: string;
  raw_key: string;
  scopes: string[];
  rate_limit_per_minute: number;
  rate_limit_per_hour: number;
  created_at: string;
}

export interface ApiKeyResponse {
  id: string;
  name: string;
  description: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  service_account_id: string | null;
  last_used_at: string | null;
  requests_total: number;
  rate_limit_per_minute: number;
  rate_limit_per_hour: number;
  revoked_at: string | null;
  created_at: string;
}

export interface ApiKeyCreate {
  name: string;
  description?: string;
  service_account_id?: string | null;
  scopes: string[];
  rate_limit_per_minute?: number;
  rate_limit_per_hour?: number;
}

export interface ApiKeyUsageSummary {
  id: string;
  name: string;
  key_prefix: string;
  requests_total: number;
  last_used_at: string | null;
  is_active: boolean;
}

export interface WebhookResponse {
  id: string;
  name: string;
  target_url: string;
  events: string[];
  is_active: boolean;
  failure_count: number;
  last_triggered_at: string | null;
  created_at: string;
}

export interface WebhookCreate {
  name: string;
  target_url: string;
  events: string[];
  secret: string;
}

export interface WebhookUpdate {
  name?: string;
  target_url?: string;
  events?: string[];
  is_active?: boolean;
}

export interface WebhookDeliveryResponse {
  id: string;
  subscription_id: string;
  event_type: string;
  delivery_status: string;
  response_code: number | null;
  duration_ms: number | null;
  retry_count: number;
  error_message: string | null;
  delivered_at: string | null;
  created_at: string;
}

export const API_SCOPES = [
  "assessments:read",
  "assessments:write",
  "suppliers:read",
  "suppliers:write",
  "findings:read",
  "risks:read",
  "recommendations:read",
  "executive:read",
  "reports:read",
] as const;

export type ApiScope = (typeof API_SCOPES)[number];

export const WEBHOOK_EVENT_TYPES = [
  "assessment.created",
  "assessment.approved",
  "finding.created",
  "risk.created",
  "recommendation.created",
  "recommendation.assigned",
  "workflow.completed",
  "supplier.created",
  "supplier.risk_changed",
  "board_report.generated",
  "notification.created",
] as const;

export type WebhookEventType = (typeof WEBHOOK_EVENT_TYPES)[number];
