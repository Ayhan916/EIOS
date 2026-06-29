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
