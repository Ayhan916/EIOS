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


_ROLE_ORDER: dict[str, int] = {
    UserRole.VIEWER: 1,
    UserRole.ANALYST: 2,
    UserRole.REVIEWER: 3,
    UserRole.EXECUTIVE: 4,
    UserRole.ADMIN: 5,
}


def has_min_role(user_role: str, min_role: UserRole) -> bool:
    """Return True if user_role meets or exceeds min_role."""
    user_order = _ROLE_ORDER.get(user_role, 0)
    return user_order >= _ROLE_ORDER[min_role]


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
