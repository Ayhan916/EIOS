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
from .comment import CommentModel
from .finding_evidence_link import FindingEvidenceLinkModel
from .notification import NotificationModel
from .review_action import ReviewActionModel
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
from .supplier import SupplierModel
from .supplier_score import SupplierScoreModel
from .board_report import BoardReportModel, ReportScheduleModel
from .workflow_run import WorkflowRunModel
from .api_key import ApiKeyModel
from .service_account import ServiceAccountModel
from .webhook import WebhookSubscriptionModel, WebhookDeliveryModel
from .regulatory import (
    RegulationModel,
    RegulationRequirementModel,
    RequirementMappingModel,
    ComplianceGapModel,
    ComplianceReportModel,
)
from .disclosure import (
    DisclosureFrameworkModel,
    DisclosureRequirementModel,
    DisclosureResponseModel,
    ReportingPackageModel,
)
from .due_diligence import DueDiligenceReportModel
from .copilot import CopilotConversationModel, CopilotMessageModel
from .copilot_audit import (
    CopilotContradictionModel,
    CopilotCitationIntegrityModel,
    CopilotFeedbackModel,
    CopilotAnswerReviewModel,
    CopilotAuditPackageModel,
)
from .external_intelligence import (
    ExternalDatasetModel,
    CountryRiskProfileModel,
    SectorBenchmarkModel,
    ExternalRiskSignalModel,
    SupplierEnrichmentModel,
)
from .connector_run import ConnectorRunModel, DatasetValidationResultModel
from .agent_monitoring import (
    MonitoringAgentModel,
    MonitoringAgentRunModel,
    AgentFindingModel,
    AgentAlertModel,
    EscalationRuleModel,
    RecommendationDraftModel,
)
from .operating_system import (
    ESGObjectiveModel,
    ESGKeyResultModel,
    ESGInitiativeModel,
    GovernanceCalendarEventModel,
    ESGProgramModel,
    ESGControlModel,
    ControlTestModel,
    ComplianceOperationModel,
    ESGActionModel,
    AccountabilityAssignmentModel,
    ESGPlaybookModel,
    WorkflowExecutionModel,
    GovernanceEscalationRuleModel,
    OrganizationESGHealthScoreModel,
    StrategicRiskModel,
)
from .enterprise import (
    EnterpriseModel,
    BusinessUnitModel,
    LegalEntityModel,
    RegionModel,
    IdentityProviderModel,
    GroupMappingModel,
    EnterprisePolicyModel,
    RetentionRuleModel,
    NotificationPolicyModel,
    EnterpriseRiskModel,
    SecretReferenceModel,
    SCIMTokenModel,
)
from .supplier_portal import (
    SupplierUserModel,
    SupplierInvitationModel,
    EvidenceRequestModel,
    EvidenceSubmissionModel,
    EvidenceSubmissionFileModel,
    QuestionnaireTemplateModel,
    QuestionnaireQuestionModel,
    QuestionnaireAssignmentModel,
    QuestionnaireAnswerModel,
    RemediationPlanModel,
    ConversationModel,
    ConversationParticipantModel,
    MessageModel,
    MessageAttachmentModel,
    SupplierActivityEventModel,
    SupplierPasswordResetTokenModel,
)
from .ai_governance import (
    AIModelModel,
    AIUseCaseModel,
    AIRiskAssessmentModel,
    AIControlModel,
    AIControlTestModel,
    ModelApprovalWorkflowModel,
    PromptTemplateModel,
    PromptChangeModel,
    AIDecisionLogModel,
    AIExplanationModel,
    HumanReviewModel,
    ModelMonitoringRecordModel,
    ModelDriftAlertModel,
    AIIncidentModel,
    AIPolicyModel,
    AIAssuranceReportModel,
    AIRegulationMappingModel,
)
from .mfa import MFABackupCodeModel
from .ghg import GHGEmissionFactorModel, GHGCalculationModel
from .evidence_version import EvidenceVersionModel
from .m46_3 import (
    RemediationMilestoneModel,
    AssessmentScheduleModel,
    SupplierCertificateModel,
    RiskDraftModel,
)
from .region import DataResidencyAuditLogModel
from .regulatory_calendar import RegulatoryDeadlineModel
from .framework_mapping import ControlFrameworkMappingModel
from .org_settings import OrganizationSettingsModel
from .custom_role import CustomRoleModel
from .board_access_token import BoardAccessTokenModel
from .soc2_control import Soc2ControlModel
from .pentest_finding import PentestFindingModel
from .production_checklist import ProductionChecklistItemModel
from .supplier_digital_twin import SupplierDigitalTwinModel, IntelligenceTimelineEventModel
from .supplier_extensions import (
    SupplierLocationModel,
    SupplierContactModel,
    SupplierCertificationModel,
    SupplierOwnershipModel,
    SupplierESGMetricModel,
    SupplierExternalESGRatingModel,
)
from .material import (
    MaterialModel,
    MaterialCompositionModel,
    MaterialSourcingModel,
    MaterialComplianceFlagModel,
    MaterialSustainabilityMetricModel,
)
from .sustainability import (
    SustainabilityObjectiveModel,
    ESGTargetModel,
    ESGKPIModel,
    KPIMeasurementModel,
    KPIAlertModel,
    SustainabilityScorecardModel,
    EmissionSourceModel,
    CarbonInventoryModel,
    DecarbonizationInitiativeModel,
    NetZeroRoadmapModel,
    NetZeroMilestoneModel,
    ScienceBasedTargetModel,
    ClimateRiskAssessmentModel,
    SustainabilityPerformanceReportModel,
    SustainabilityAssuranceRecordModel,
    CSRDPerformanceMappingModel,
    ISSBSustainabilityMappingModel,
    PerformanceForecastModel,
    ScenarioAnalysisModel,
)

__all__ = [
    "AgentRunModel",
    "AuditEventModel",
    "AssetModel",
    "AssessmentModel",
    "Base",
    "BaseModel",
    "CommentModel",
    "ControlModel",
    "DecisionModel",
    "EvidenceChunkModel",
    "EvidenceModel",
    "FindingModel",
    "FindingEvidenceLinkModel",
    "NotificationModel",
    "OrganizationModel",
    "ReviewActionModel",
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
    "SupplierModel",
    "SupplierScoreModel",
    "BoardReportModel",
    "ReportScheduleModel",
    "WorkflowJobModel",
    "WorkflowRunModel",
    "ApiKeyModel",
    "ServiceAccountModel",
    "WebhookSubscriptionModel",
    "WebhookDeliveryModel",
    "RegulationModel",
    "RegulationRequirementModel",
    "RequirementMappingModel",
    "ComplianceGapModel",
    "ComplianceReportModel",
    "DisclosureFrameworkModel",
    "DisclosureRequirementModel",
    "DisclosureResponseModel",
    "ReportingPackageModel",
    "DueDiligenceReportModel",
    "CopilotConversationModel",
    "CopilotMessageModel",
    "CopilotContradictionModel",
    "CopilotCitationIntegrityModel",
    "CopilotFeedbackModel",
    "CopilotAnswerReviewModel",
    "CopilotAuditPackageModel",
    "ExternalDatasetModel",
    "CountryRiskProfileModel",
    "SectorBenchmarkModel",
    "ExternalRiskSignalModel",
    "SupplierEnrichmentModel",
    "ConnectorRunModel",
    "DatasetValidationResultModel",
    "SupplierUserModel",
    "SupplierInvitationModel",
    "EvidenceRequestModel",
    "EvidenceSubmissionModel",
    "EvidenceSubmissionFileModel",
    "QuestionnaireTemplateModel",
    "QuestionnaireQuestionModel",
    "QuestionnaireAssignmentModel",
    "QuestionnaireAnswerModel",
    "RemediationPlanModel",
    "ConversationModel",
    "ConversationParticipantModel",
    "MessageModel",
    "MessageAttachmentModel",
    "SupplierActivityEventModel",
    "SupplierPasswordResetTokenModel",
    "MonitoringAgentModel",
    "MonitoringAgentRunModel",
    "AgentFindingModel",
    "AgentAlertModel",
    "EscalationRuleModel",
    "RecommendationDraftModel",
    "ESGObjectiveModel",
    "ESGKeyResultModel",
    "ESGInitiativeModel",
    "GovernanceCalendarEventModel",
    "ESGProgramModel",
    "ESGControlModel",
    "ControlTestModel",
    "ComplianceOperationModel",
    "ESGActionModel",
    "AccountabilityAssignmentModel",
    "ESGPlaybookModel",
    "WorkflowExecutionModel",
    "GovernanceEscalationRuleModel",
    "OrganizationESGHealthScoreModel",
    "StrategicRiskModel",
    "EnterpriseModel",
    "BusinessUnitModel",
    "LegalEntityModel",
    "RegionModel",
    "IdentityProviderModel",
    "GroupMappingModel",
    "EnterprisePolicyModel",
    "RetentionRuleModel",
    "NotificationPolicyModel",
    "EnterpriseRiskModel",
    "SecretReferenceModel",
    "SCIMTokenModel",
    "AIModelModel",
    "AIUseCaseModel",
    "AIRiskAssessmentModel",
    "AIControlModel",
    "AIControlTestModel",
    "ModelApprovalWorkflowModel",
    "PromptTemplateModel",
    "PromptChangeModel",
    "AIDecisionLogModel",
    "AIExplanationModel",
    "HumanReviewModel",
    "ModelMonitoringRecordModel",
    "ModelDriftAlertModel",
    "AIIncidentModel",
    "AIPolicyModel",
    "AIAssuranceReportModel",
    "AIRegulationMappingModel",
    "SustainabilityObjectiveModel",
    "ESGTargetModel",
    "ESGKPIModel",
    "KPIMeasurementModel",
    "KPIAlertModel",
    "SustainabilityScorecardModel",
    "EmissionSourceModel",
    "CarbonInventoryModel",
    "DecarbonizationInitiativeModel",
    "NetZeroRoadmapModel",
    "NetZeroMilestoneModel",
    "ScienceBasedTargetModel",
    "ClimateRiskAssessmentModel",
    "SustainabilityPerformanceReportModel",
    "SustainabilityAssuranceRecordModel",
    "CSRDPerformanceMappingModel",
    "ISSBSustainabilityMappingModel",
    "PerformanceForecastModel",
    "ScenarioAnalysisModel",
    "MFABackupCodeModel",
    "GHGEmissionFactorModel",
    "GHGCalculationModel",
    "EvidenceVersionModel",
    "RemediationMilestoneModel",
    "AssessmentScheduleModel",
    "SupplierCertificateModel",
    "RiskDraftModel",
    "DataResidencyAuditLogModel",
    "RegulatoryDeadlineModel",
    "ControlFrameworkMappingModel",
    "OrganizationSettingsModel",
    "CustomRoleModel",
    "BoardAccessTokenModel",
    "Soc2ControlModel",
    "PentestFindingModel",
    "ProductionChecklistItemModel",
    "SupplierDigitalTwinModel",
    "IntelligenceTimelineEventModel",
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
