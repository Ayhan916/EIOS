"""
EIOS Domain Enumerations

EntityStatus: 9-state lifecycle per architecture/012 (ASTATE-0001).
All other enums are architecturally stable classifications.
"""

from enum import Enum


class EntityStatus(str, Enum):
    CREATED = "Created"
    DRAFT = "Draft"
    VALIDATED = "Validated"
    REVIEWED = "Reviewed"
    APPROVED = "Approved"
    ACTIVE = "Active"
    SUSPENDED = "Suspended"
    ARCHIVED = "Archived"
    DELETED = "Deleted"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ConfidenceLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class ControlType(str, Enum):
    PREVENTIVE = "Preventive"
    DETECTIVE = "Detective"
    CORRECTIVE = "Corrective"


class EvidenceType(str, Enum):
    DOCUMENT = "Document"
    REPORT = "Report"
    PUBLICATION = "Publication"
    WEBSITE = "Website"
    DATA = "Data"
    TESTIMONY = "Testimony"


class UserRole(str, Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    EXECUTIVE = "executive"
    ADMIN = "admin"
    # Out-of-hierarchy role — time-limited read-only access for external auditors.
    # Not included in _ROLE_ORDER so has_min_role() always returns False for this role,
    # preventing accidental access escalation through internal role checks.
    EXTERNAL_AUDITOR = "external_auditor"


_ROLE_ORDER: dict[str, int] = {
    UserRole.VIEWER: 1,
    UserRole.ANALYST: 2,
    UserRole.REVIEWER: 3,
    UserRole.EXECUTIVE: 4,
    UserRole.ADMIN: 5,
}


def has_min_role(user_role: str, min_role: UserRole) -> bool:
    """Return True if user_role meets or exceeds min_role in the internal hierarchy.

    EXTERNAL_AUDITOR is not in _ROLE_ORDER, so:
    - has_min_role(any, EXTERNAL_AUDITOR) always returns False
    - has_min_role("external_auditor", any) always returns False
    Use require_external_auditor_or_internal() for endpoints that accept both.
    """
    user_order = _ROLE_ORDER.get(user_role, 0)
    min_order = _ROLE_ORDER.get(min_role)
    if min_order is None:
        return False
    return user_order >= min_order


class ActionStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    VERIFIED = "verified"


class NotificationType(str, Enum):
    WORKFLOW_COMPLETED = "workflow_completed"
    ACTION_OVERDUE = "action_overdue"
    ASSESSMENT_APPROVED = "assessment_approved"
    RECOMMENDATION_ASSIGNED = "recommendation_assigned"
    REVIEWER_ASSIGNED = "reviewer_assigned"
    REVIEW_SUBMITTED = "review_submitted"
    CHANGES_REQUESTED = "changes_requested"
    COMMENT_MENTION = "comment_mention"
    REGULATORY_CHANGE = "regulatory_change"


class EvidenceStrength(str, Enum):
    WEAK = "Weak"
    MODERATE = "Moderate"
    STRONG = "Strong"
    VERY_STRONG = "Very Strong"


class ReviewStatus(str, Enum):
    DRAFT = "Draft"
    IN_REVIEW = "InReview"
    CHANGES_REQUESTED = "ChangesRequested"
    APPROVED = "Approved"
    ARCHIVED = "Archived"


class ReviewActionType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


# Allowed review status transitions: {from_status: {to_status, ...}}
_REVIEW_TRANSITIONS: dict[ReviewStatus, set[ReviewStatus]] = {
    ReviewStatus.DRAFT: {ReviewStatus.IN_REVIEW},
    ReviewStatus.IN_REVIEW: {ReviewStatus.APPROVED, ReviewStatus.CHANGES_REQUESTED},
    ReviewStatus.CHANGES_REQUESTED: {ReviewStatus.IN_REVIEW},
    ReviewStatus.APPROVED: {ReviewStatus.ARCHIVED},
    ReviewStatus.ARCHIVED: set(),
}


def is_valid_review_transition(from_status: ReviewStatus, to_status: ReviewStatus) -> bool:
    return to_status in _REVIEW_TRANSITIONS.get(from_status, set())


# ── M27 Supplier Management ───────────────────────────────────────────────────


class SupplierTier(str, Enum):
    TIER_1 = "Tier 1"
    TIER_2 = "Tier 2"
    TIER_3 = "Tier 3"
    OTHER = "Other"


class SupplierStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"


# ── M28 Supplier Intelligence ─────────────────────────────────────────────────


class RiskBand(str, Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"


class TrendDirection(str, Enum):
    IMPROVING = "Improving"
    STABLE = "Stable"
    DETERIORATING = "Deteriorating"


# ── M30 API Platform ──────────────────────────────────────────────────────────


class ApiScope(str, Enum):
    ASSESSMENTS_READ = "assessments:read"
    ASSESSMENTS_WRITE = "assessments:write"
    SUPPLIERS_READ = "suppliers:read"
    SUPPLIERS_WRITE = "suppliers:write"
    FINDINGS_READ = "findings:read"
    RISKS_READ = "risks:read"
    RECOMMENDATIONS_READ = "recommendations:read"
    EXECUTIVE_READ = "executive:read"
    REPORTS_READ = "reports:read"
    REPORTING_READ = "reporting:read"
    REPORTING_WRITE = "reporting:write"
    DUE_DILIGENCE_READ = "due_diligence:read"
    DUE_DILIGENCE_WRITE = "due_diligence:write"
    COPILOT_READ = "copilot:read"
    COPILOT_WRITE = "copilot:write"
    EXTERNAL_INTELLIGENCE_READ = "external_intelligence:read"
    EXTERNAL_INTELLIGENCE_WRITE = "external_intelligence:write"


class WebhookEventType(str, Enum):
    ASSESSMENT_CREATED = "assessment.created"
    ASSESSMENT_APPROVED = "assessment.approved"
    FINDING_CREATED = "finding.created"
    RISK_CREATED = "risk.created"
    RECOMMENDATION_CREATED = "recommendation.created"
    RECOMMENDATION_ASSIGNED = "recommendation.assigned"
    WORKFLOW_COMPLETED = "workflow.completed"
    SUPPLIER_CREATED = "supplier.created"
    SUPPLIER_RISK_CHANGED = "supplier.risk_changed"
    BOARD_REPORT_GENERATED = "board_report.generated"
    NOTIFICATION_CREATED = "notification.created"


class WebhookDeliveryStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


# ── M32 Sustainability Reporting ──────────────────────────────────────────────


class DisclosureStatus(str, Enum):
    NOT_STARTED = "Not Started"
    DRAFT = "Draft"
    IN_REVIEW = "In Review"
    APPROVED = "Approved"
    PUBLISHED = "Published"


class CoverageCategory(str, Enum):
    WEAK = "Weak"
    MODERATE = "Moderate"
    STRONG = "Strong"
    COMPLETE = "Complete"


class ReadinessStatus(str, Enum):
    NOT_STARTED = "Not Started"
    DRAFT = "Draft"
    READY_FOR_REVIEW = "Ready for Review"
    READY_FOR_APPROVAL = "Ready for Approval"
    READY_FOR_PUBLICATION = "Ready for Publication"
    BLOCKED = "Blocked"


# Allowed disclosure status transitions: {from_status: allowed_to_statuses}
_DISCLOSURE_TRANSITIONS: dict[DisclosureStatus, set[DisclosureStatus]] = {
    DisclosureStatus.NOT_STARTED: {DisclosureStatus.DRAFT},
    DisclosureStatus.DRAFT: {DisclosureStatus.IN_REVIEW},
    DisclosureStatus.IN_REVIEW: {DisclosureStatus.APPROVED, DisclosureStatus.DRAFT},
    DisclosureStatus.APPROVED: {DisclosureStatus.PUBLISHED, DisclosureStatus.IN_REVIEW},
    DisclosureStatus.PUBLISHED: set(),
}


def is_valid_disclosure_transition(
    from_status: DisclosureStatus, to_status: DisclosureStatus
) -> bool:
    return to_status in _DISCLOSURE_TRANSITIONS.get(from_status, set())


# ── M33 AI Copilot ───────────────────────────────────────────────────────────


class CopilotIntentType(str, Enum):
    RISK = "risk"
    COMPLIANCE = "compliance"
    DISCLOSURE = "disclosure"
    DUE_DILIGENCE = "due_diligence"
    EXECUTIVE = "executive"
    ACTION = "action"
    GENERAL = "general"


class CopilotMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class CitationType(str, Enum):
    SUPPLIER = "Supplier"
    FINDING = "Finding"
    RISK = "Risk"
    RECOMMENDATION = "Recommendation"
    EVIDENCE = "Evidence"
    ASSESSMENT = "Assessment"
    COMPLIANCE_GAP = "ComplianceGap"
    DISCLOSURE = "Disclosure"
    REPORT = "Report"


class CopilotContextType(str, Enum):
    GENERAL = "general"
    SUPPLIER = "supplier"
    COMPLIANCE = "compliance"
    DISCLOSURE = "disclosure"
    DUE_DILIGENCE = "due_diligence"
    EXECUTIVE = "executive"


# ── M32 ──────────────────────────────────────────────────────────────────────
# scope entries added below ApiScope above; keep M33 scopes here for ordering


# ── M32.1 Due Diligence Reporting ─────────────────────────────────────────────


# ── M33.2 Copilot Enterprise Hardening ───────────────────────────────────────


class CopilotConfidenceLevel(str, Enum):
    VERY_HIGH = "Very High"
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"


class ContradictionType(str, Enum):
    RISK_VS_COMPLIANCE = "risk_vs_compliance"
    DISCLOSURE_COMPLETENESS = "disclosure_completeness"
    FINDING_WITHOUT_ACTION = "finding_without_action"
    SUPPLIER_SCORE_VS_FINDINGS = "supplier_score_vs_findings"
    EXECUTIVE_SUMMARY_MISMATCH = "executive_summary_mismatch"


class CitationIntegrityStatus(str, Enum):
    VERIFIED = "verified"
    STALE = "stale"
    DELETED = "deleted"


class FeedbackRating(str, Enum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    INCORRECT = "incorrect"
    OUTDATED = "outdated"


class ReviewDecision(str, Enum):
    APPROVED = "approved"
    MISLEADING = "misleading"
    INVESTIGATE = "investigate"


class AuditVerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    TAMPERED = "tampered"


# ── M32.1 Due Diligence Reporting ─────────────────────────────────────────────


class DueDiligenceReportType(str, Enum):
    LKSGG_ANNUAL = "lksgg_annual"
    LKSG_STATEMENT = "lksg_statement"      # LkSG §10 annual declaration (5 mandatory sections)
    CSDDD = "csddd"
    HUMAN_RIGHTS = "human_rights"
    ENVIRONMENTAL = "environmental"
    PREVENTIVE_MEASURES = "preventive_measures"
    REMEDIATION = "remediation"


class PreventiveMeasureEffectiveness(str, Enum):
    EFFECTIVE = "Effective"
    PARTIALLY_EFFECTIVE = "Partially Effective"
    INEFFECTIVE = "Ineffective"
    UNKNOWN = "Unknown"


# ── M34 External Data & Benchmarking Intelligence ─────────────────────────────


class ExternalSourceName(str, Enum):
    # Country risk
    WORLD_BANK = "world_bank"
    TRANSPARENCY_INTERNATIONAL = "transparency_international"
    FRAGILE_STATES_INDEX = "fragile_states_index"
    # Human rights
    ILO = "ilo"
    UNICEF = "unicef"
    UN_HUMAN_RIGHTS = "un_human_rights"
    # Sanctions
    EU_SANCTIONS = "eu_sanctions"
    UN_SANCTIONS = "un_sanctions"
    OFAC = "ofac"
    # Environmental
    CLIMATE_VULNERABILITY = "climate_vulnerability"
    WATER_STRESS = "water_stress"
    BIODIVERSITY_RISK = "biodiversity_risk"
    # Sector intelligence
    SECTOR_ESG_BENCHMARK = "sector_esg_benchmark"
    SECTOR_RISK_CLASSIFICATION = "sector_risk_classification"
    SECTOR_INCIDENT_STATISTICS = "sector_incident_statistics"


class DatasetStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    INVALID = "invalid"
    QUARANTINED = "quarantined"


class RiskSignalType(str, Enum):
    SANCTIONS = "sanctions"
    CORRUPTION = "corruption"
    LABOUR_RIGHTS = "labour_rights"
    ENVIRONMENTAL = "environmental"
    GOVERNANCE = "governance"


class EsgCategory(str, Enum):
    """Top-level ESG pillar for event attribution (GAP-10 / FR-005)."""
    ENVIRONMENTAL = "Environmental"
    SOCIAL = "Social"
    GOVERNANCE = "Governance"


class SignalSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PercentileRank(str, Enum):
    TOP_10 = "top_10"
    TOP_25 = "top_25"
    MEDIAN = "median"
    BOTTOM_25 = "bottom_25"
    BOTTOM_10 = "bottom_10"


class SanctionsExposure(str, Enum):
    NONE = "none"
    POTENTIAL = "potential"
    CONFIRMED = "confirmed"


class CountryRiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


# ── M34.1 Live Connector enums ────────────────────────────────────────────────

class ConnectorStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class FreshnessStatus(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"


# ── M35 Supplier Portal ────────────────────────────────────────────────────────


class SupplierUserRole(str, Enum):
    SUPPLIER_USER = "supplier_user"
    SUPPLIER_MANAGER = "supplier_manager"


class EvidenceRequestStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class EvidenceSubmissionStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class QuestionType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    FILE_UPLOAD = "file_upload"


class QuestionnaireStatus(str, Enum):
    DRAFT = "draft"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class RemediationStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"


class SupplierActivityEventType(str, Enum):
    LOGIN = "login"
    QUESTIONNAIRE_SUBMISSION = "questionnaire_submission"
    EVIDENCE_UPLOAD = "evidence_upload"
    REMEDIATION_UPDATE = "remediation_update"
    COMMENT = "comment"
    MESSAGE = "message"
    STATUS_CHANGE = "status_change"
    INVITATION_ACCEPTED = "invitation_accepted"
    PASSWORD_RESET = "password_reset"
    PROFILE_UPDATE = "profile_update"


# ── CSDDD Sector Risk Register (TASK-003) ─────────────────────────────────────

class CSDDDRight(str, Enum):
    """21 protected rights from CSDDD Annex I and referenced ILO/UN conventions."""
    CHILD_LABOUR = "child_labour"                          # ILO C138, C182
    FORCED_LABOUR = "forced_labour"                        # ILO C029, C105
    FREEDOM_OF_ASSOCIATION = "freedom_of_association"      # ILO C087
    COLLECTIVE_BARGAINING = "collective_bargaining"        # ILO C098
    DISCRIMINATION = "discrimination"                      # ILO C100, C111
    MINIMUM_WAGE = "minimum_wage"                          # ILO C131
    WORKING_HOURS = "working_hours"                        # ILO C001
    OCCUPATIONAL_SAFETY = "occupational_safety"            # ILO C155, C187
    LAND_RIGHTS = "land_rights"                            # UNDRIP, VGGT
    WATER_RIGHTS = "water_rights"                          # UN Resolution A/RES/64/292
    ENVIRONMENTAL_DESTRUCTION = "environmental_destruction"
    HARMFUL_CHEMICALS = "harmful_chemicals"                # Stockholm, Rotterdam Conventions
    BIODIVERSITY = "biodiversity"                          # CBD
    MERCURY = "mercury"                                    # Minamata Convention
    HAZARDOUS_WASTE = "hazardous_waste"                    # Basel Convention
    PRIVACY = "privacy"                                    # ICCPR Art. 17
    FREEDOM_OF_EXPRESSION = "freedom_of_expression"        # ICCPR Art. 19
    HUMAN_DIGNITY = "human_dignity"                        # UDHR Art. 1
    MODERN_SLAVERY = "modern_slavery"                      # Palermo Protocol
    MIGRANT_WORKER_RIGHTS = "migrant_worker_rights"        # ICRMW
    COMMUNITY_RIGHTS = "community_rights"                  # ILO C169, UNDRIP


class ScenarioType(str, Enum):
    """Predefined scenario types for deterministic sector risk simulation."""
    GEOPOLITICAL_CONFLICT = "geopolitical_conflict"
    SANCTIONS_ESCALATION = "sanctions_escalation"
    NATURAL_DISASTER = "natural_disaster"
    REGULATORY_CHANGE = "regulatory_change"
    LABOUR_UNREST = "labour_unrest"
    SUPPLY_SHORTAGE = "supply_shortage"


class CalibrationStatus(str, Enum):
    """Lifecycle of a RAG-generated score suggestion awaiting human review."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ScenarioSuggestionStatus(str, Enum):
    """Lifecycle of a news-triggered scenario suggestion."""
    PENDING = "pending"
    ACTIVE = "active"
    DISMISSED = "dismissed"


class GrievanceStatus(str, Enum):
    """Lifecycle of a GrievanceReport — LkSG §8, CSDDD Art. 14."""
    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class GrievanceCategory(str, Enum):
    """Category of a grievance report — aligned to LkSG risk areas."""
    LABOUR_RIGHTS = "labour_rights"
    CHILD_LABOUR = "child_labour"
    FORCED_LABOUR = "forced_labour"
    HEALTH_AND_SAFETY = "health_and_safety"
    ENVIRONMENTAL = "environmental"
    DISCRIMINATION = "discrimination"
    CORRUPTION = "corruption"
    HUMAN_RIGHTS = "human_rights"
    OTHER = "other"


class RegulatoryChangeSeverity(str, Enum):
    """How significantly the change impacts existing assessments and compliance programmes."""
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


class RegulatoryChangeStatus(str, Enum):
    """Lifecycle of a detected regulatory change."""
    NEW = "new"
    SCANNING = "scanning"
    IMPACTS_IDENTIFIED = "impacts_identified"
    NOTIFIED = "notified"
    ACKNOWLEDGED = "acknowledged"


# ── CSDDD-001 Stakeholder Engagement (Art. 13) ────────────────────────────────

# ── CSDDD-003 Effectiveness Monitoring (Art. 15) ─────────────────────────────

class IndicatorType(str, Enum):
    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"


class IndicatorDataSource(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class EffectivenessReviewStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    CLOSED = "closed"


# ── CSDDD-004 Remedy Case Manager (Art. 12) ──────────────────────────────────

class RemedyCaseStatus(str, Enum):
    """Lifecycle of a Remedy Case — Art. 12 CSDDD."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"


class RemedyType(str, Enum):
    """Types of remedy per Art. 12 CSDDD."""
    COMPENSATION = "compensation"
    RESTORATION = "restoration"
    REHABILITATION = "rehabilitation"
    RESTITUTION = "restitution"
    SOCIETAL_COMPENSATION = "societal_compensation"
    NON_REPETITION = "non_repetition"


class AffectedPartyType(str, Enum):
    WORKER = "worker"
    COMMUNITY = "community"
    ENVIRONMENT = "environment"
    OTHER = "other"


class ImpactCausation(str, Enum):
    """Own impact vs. jointly caused with third parties — Art. 12 Abs. 5 CSDDD."""
    OWN = "own"
    JOINT_WITH_THIRD_PARTY = "joint_with_third_party"


class RemedyActionStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


# ── CSDDD-002 DD-Governance (Art. 7) ─────────────────────────────────────────

class DDPolicyStatus(str, Enum):
    """Lifecycle of a DD-Policy document — Art. 7 CSDDD."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class GovernanceEventType(str, Enum):
    """Types of governance deadline tracked in the calendar."""
    POLICY_REVIEW = "policy_review"
    COC_ACCEPTANCE = "coc_acceptance"
    ANNUAL_REPORT = "annual_report"
    BOARD_REVIEW = "board_review"


# ── CSDDD-005 Downstream Activity Chain (Art. 2/3) ───────────────────���───────

class ChainDirection(str, Enum):
    UPSTREAM = "upstream"
    DOWNSTREAM = "downstream"
    BOTH = "both"


class DownstreamPartnerType(str, Enum):
    DISTRIBUTOR = "distributor"
    LOGISTICS = "logistics"
    LICENSEE = "licensee"
    DISPOSAL = "disposal"
    RETAILER = "retailer"
    OTHER = "other"


# ── CSDDD-008 Scoping Study (Art. 8 Abs. 3) ──────────────────────────────────

class ScopingPriority(str, Enum):
    PRIORITY_1 = "priority_1"  # Immediate DD required
    PRIORITY_2 = "priority_2"  # Scheduled DD
    PRIORITY_3 = "priority_3"  # Simplified DD


class ScopingStudyStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"


# ── CSDDD-001 Stakeholder Engagement (Art. 13) ────────────────────────────────

class StakeholderType(str, Enum):
    """Category of an affected stakeholder per CSDDD Art. 13 Abs. 1."""
    WORKER = "worker"
    TRADE_UNION = "trade_union"
    NGO = "ngo"
    SUPPLIER_COMMUNITY = "supplier_community"
    AUTHORITY = "authority"
    OTHER = "other"


class ConsultationFormat(str, Enum):
    """Format of a stakeholder consultation."""
    MEETING = "meeting"
    WORKSHOP = "workshop"
    QUESTIONNAIRE = "questionnaire"
    AUDIT = "audit"
    OTHER = "other"


class ConsultationBarrier(str, Enum):
    """Barriers to participation — Art. 13 Abs. 1 explicit documentation requirement."""
    NONE = "none"
    LANGUAGE = "language"
    ACCESS = "access"
    RESOURCES = "resources"
    FEAR_OF_REPRISALS = "fear_of_reprisals"
    OTHER = "other"


# ── CSDDD-006 Contractual Assurance (Art. 10) ─────────────────────────────────


class ClauseCategory(str, Enum):
    """Subject-matter categories for contractual DD clauses (Art. 10 Abs. 2)."""
    LABOR_RIGHTS = "labor_rights"
    HUMAN_RIGHTS = "human_rights"
    ENVIRONMENT = "environment"
    ANTI_CORRUPTION = "anti_corruption"
    HEALTH_SAFETY = "health_safety"
    DATA_PROTECTION = "data_protection"
    OTHER = "other"


class AssuranceStatus(str, Enum):
    """Lifecycle state of a supplier's acceptance of a contractual clause."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WAIVED = "waived"


# ── CSDDD-007 SME Support Tracker (Art. 10 Abs. 2 lit. b) ────────────────────


class SMEClassification(str, Enum):
    """EU SME definition (2003/361/EC): headcount + revenue/balance sheet ceiling."""
    MICRO = "micro"        # <10 employees, ≤€2M revenue
    SMALL = "small"        # <50 employees, ≤€10M revenue
    MEDIUM = "medium"      # <250 employees, ≤€50M revenue
    LARGE = "large"        # ≥250 employees or >€50M revenue (not an SME)


class SupportType(str, Enum):
    """Category of support measure offered to an SME supplier."""
    TRAINING = "training"
    FINANCIAL_AID = "financial_aid"
    TOOLS_RESOURCES = "tools_resources"
    CAPACITY_BUILDING = "capacity_building"
    CO_INVESTMENT = "co_investment"
    MENTORING = "mentoring"
    AUDIT_SUPPORT = "audit_support"
    OTHER = "other"


class SupportProgramStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SupportMeasureStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ── CSDDD-011 Readiness Score ─────────────────────────────────────────────────


class ReadinessLevel(str, Enum):
    NOT_READY = "not_ready"       # <40%
    PARTIAL = "partial"           # 40–79%
    READY = "ready"               # 80–99%
    FULLY_READY = "fully_ready"   # 100%


# ── CSDDD-012 Impact Severity Calculator (Art. 3/6) ───────────────────────────


class ImpactType(str, Enum):
    """Subject-matter category of the adverse impact (CSDDD Annex I reference)."""
    HUMAN_RIGHTS = "human_rights"
    LABOR_RIGHTS = "labor_rights"
    ENVIRONMENT = "environment"
    HEALTH_SAFETY = "health_safety"
    ANTI_CORRUPTION = "anti_corruption"
    OTHER = "other"


class SeverityLevel(str, Enum):
    """OECD RBC / CSDDD severity classification."""
    CRITICAL = "critical"   # severity ≥ 8.0
    HIGH = "high"           # severity ≥ 6.0
    MEDIUM = "medium"       # severity ≥ 3.0
    LOW = "low"             # severity < 3.0


class ImpactEntityType(str, Enum):
    """The EIOS entity this assessment is linked to."""
    FINDING = "finding"
    RISK = "risk"
    SUPPLIER = "supplier"
    ASSESSMENT = "assessment"
    STANDALONE = "standalone"


# ── CSDDD-013 Board Sign-off Trail (Art. 22) ──────────────────────────────────


class BoardSignoffType(str, Enum):
    """What category of document/decision requires board sign-off."""
    DD_POLICY = "dd_policy"
    DD_STRATEGY = "dd_strategy"
    ANNUAL_REPORT = "annual_report"
    SCOPING_STUDY = "scoping_study"
    CAP_PLAN = "cap_plan"
    REMEDY_SETTLEMENT = "remedy_settlement"
    OTHER = "other"


class BoardSignoffStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class BoardMemberRole(str, Enum):
    CEO = "ceo"
    CFO = "cfo"
    CSO = "cso"            # Chief Sustainability Officer
    BOARD_MEMBER = "board_member"
    SUPERVISORY_BOARD = "supervisory_board"
    COMPLIANCE_OFFICER = "compliance_officer"
    OTHER = "other"


# ── CSDDD-015 — Supplier Self-Assessment ──────────────────────────────────────

class QuestionType(str, Enum):
    YES_NO = "yes_no"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    FILE_UPLOAD = "file_upload"
    SCALE_1_5 = "scale_1_5"


class AssessmentSection(str, Enum):
    COMPANY_STRUCTURE = "company_structure"    # A — Art. 7
    HR_POLICIES = "hr_policies"                # B — Art. 10 + Annex I
    ENVIRONMENT = "environment"                # C — Art. 10 + Annex II
    GRIEVANCE = "grievance"                    # D — Art. 14
    SUB_SUPPLIERS = "sub_suppliers"            # E — Art. 10 Abs. 2 lit. b


class AssessmentStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class GapSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrafficLight(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


# ── CSDDD-009 — ESAP Export ───────────────────────────────────────────────────

class ESAPSubmissionStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    SUBMITTED = "submitted"
    ARCHIVED = "archived"


class ESAPExportFormat(str, Enum):
    JSON = "json"
    XML = "xml"


# ── CSDDD-010 — Threshold Monitor ────────────────────────────────────────────

class CSDDDThresholdLevel(str, Enum):
    NOT_APPLICABLE = "not_applicable"    # below both thresholds
    BORDERLINE = "borderline"            # < 20% below a threshold
    TIER_2 = "tier_2"                    # ≥1000 MA + ≥450M€ (from 2028)
    TIER_1 = "tier_1"                    # ≥5000 MA + ≥1500M€ (from 2027)


# ── CSDDD-014 — Regulatory Change Radar ──────────────────────────────────────

class RegulatoryChangeStatus(str, Enum):
    NEW = "new"
    ANALYSED = "analysed"
    IMPLEMENTED = "implemented"
    NOT_RELEVANT = "not_relevant"

class RegulatoryChangeActionRequired(str, Enum):
    YES = "yes"
    NO = "no"
    PENDING = "pending"
