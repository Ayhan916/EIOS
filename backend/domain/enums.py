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
    ADMIN = "admin"


_ROLE_ORDER: dict[str, int] = {
    UserRole.VIEWER: 1,
    UserRole.ANALYST: 2,
    UserRole.REVIEWER: 3,
    UserRole.ADMIN: 4,
}


def has_min_role(user_role: str, min_role: UserRole) -> bool:
    """Return True if user_role meets or exceeds min_role."""
    user_order = _ROLE_ORDER.get(user_role, 0)
    return user_order >= _ROLE_ORDER[min_role]
