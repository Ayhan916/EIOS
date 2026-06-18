"""
EIOS Persistence Models

Importing this package registers all ORM models with SQLAlchemy metadata.
Alembic and the database engine depend on this import to discover the schema.
"""

from .agent_run import AgentRunModel
from .assessment import AssessmentModel
from .asset import AssetModel
from .associations import (
    assessment_evidence,
    control_requirement,
    control_risk,
    decision_recommendation,
    finding_evidence,
    policy_control,
    policy_requirement,
    recommendation_finding,
    recommendation_risk,
    risk_finding,
    standard_requirement,
)
from .audit_event import AuditEventModel
from .base import Base, BaseModel
from .control import ControlModel
from .decision import DecisionModel
from .evidence import EvidenceModel
from .evidence_chunk import EvidenceChunkModel
from .finding import FindingModel
from .notification import NotificationModel
from .organization import OrganizationModel
from .policy import PolicyModel
from .process import ProcessModel
from .project import ProjectModel
from .recommendation import RecommendationModel
from .report import ReportModel
from .requirement import RequirementModel
from .risk import RiskModel
from .sector import SectorModel
from .standard import StandardModel
from .task import TaskModel
from .user import UserModel
from .workflow_job import WorkflowJobModel
from .workflow_run import WorkflowRunModel

__all__ = [
    "AgentRunModel",
    "AuditEventModel",
    "AssetModel",
    "AssessmentModel",
    "Base",
    "BaseModel",
    "ControlModel",
    "DecisionModel",
    "EvidenceChunkModel",
    "EvidenceModel",
    "FindingModel",
    "NotificationModel",
    "OrganizationModel",
    "PolicyModel",
    "ProcessModel",
    "ProjectModel",
    "RecommendationModel",
    "ReportModel",
    "RequirementModel",
    "RiskModel",
    "SectorModel",
    "StandardModel",
    "TaskModel",
    "UserModel",
    "WorkflowJobModel",
    "WorkflowRunModel",
    "assessment_evidence",
    "control_requirement",
    "control_risk",
    "decision_recommendation",
    "finding_evidence",
    "policy_control",
    "policy_requirement",
    "recommendation_finding",
    "recommendation_risk",
    "risk_finding",
    "standard_requirement",
]
