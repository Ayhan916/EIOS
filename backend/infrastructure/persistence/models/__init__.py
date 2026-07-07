"""
EIOS Persistence Models

Importing this package registers all ORM models with SQLAlchemy metadata.
Alembic and the database engine depend on this import to discover the schema.
"""

from .agent_monitoring import (
    AgentAlertModel,
    AgentFindingModel,
    EscalationRuleModel,
    MonitoringAgentModel,
    MonitoringAgentRunModel,
    RecommendationDraftModel,
)
from .agent_run import AgentRunModel
from .ai_governance import (
    AIAssuranceReportModel,
    AIControlModel,
    AIControlTestModel,
    AIDecisionLogModel,
    AIExplanationModel,
    AIIncidentModel,
    AIModelModel,
    AIPolicyModel,
    AIRegulationMappingModel,
    AIRiskAssessmentModel,
    AIUseCaseModel,
    HumanReviewModel,
    ModelApprovalWorkflowModel,
    ModelDriftAlertModel,
    ModelMonitoringRecordModel,
    PromptChangeModel,
    PromptTemplateModel,
)
from .api_key import ApiKeyModel
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
from .board_access_token import BoardAccessTokenModel
from .board_report import BoardReportModel, ReportScheduleModel
from .comment import CommentModel
from .connector_run import ConnectorRunModel, DatasetValidationResultModel
from .control import ControlModel
from .copilot import CopilotConversationModel, CopilotMessageModel
from .copilot_audit import (
    CopilotAnswerReviewModel,
    CopilotAuditPackageModel,
    CopilotCitationIntegrityModel,
    CopilotContradictionModel,
    CopilotFeedbackModel,
)
from .custom_role import CustomRoleModel
from .decision import DecisionModel
from .disclosure import (
    DisclosureFrameworkModel,
    DisclosureRequirementModel,
    DisclosureResponseModel,
    ReportingPackageModel,
)
from .dpp import DigitalProductPassportModel
from .due_diligence import DueDiligenceReportModel
from .enterprise import (
    BusinessUnitModel,
    EnterpriseModel,
    EnterprisePolicyModel,
    EnterpriseRiskModel,
    GroupMappingModel,
    IdentityProviderModel,
    LegalEntityModel,
    NotificationPolicyModel,
    RegionModel,
    RetentionRuleModel,
    SCIMTokenModel,
    SecretReferenceModel,
)
from .erp import ERPConnectorModel, ERPFieldMappingModel, ERPSyncJobModel
from .evidence import EvidenceModel
from .evidence_chunk import EvidenceChunkModel
from .evidence_version import EvidenceVersionModel
from .external_intelligence import (
    CountryRiskProfileModel,
    ExternalDatasetModel,
    ExternalRiskSignalModel,
    SectorBenchmarkModel,
    SupplierEnrichmentModel,
)
from .finding import FindingModel
from .finding_evidence_link import FindingEvidenceLinkModel
from .framework_mapping import ControlFrameworkMappingModel
from .ghg import GHGCalculationModel, GHGEmissionFactorModel
from .m46_3 import (
    AssessmentScheduleModel,
    RemediationMilestoneModel,
    RiskDraftModel,
    SupplierCertificateModel,
)
from .material import (
    MaterialComplianceFlagModel,
    MaterialCompositionModel,
    MaterialModel,
    MaterialSourcingModel,
    MaterialSustainabilityMetricModel,
)
from .mfa import MFABackupCodeModel
from .news_feed import NewsArticleModel, NewsSupplierAssignmentModel
from .notification import NotificationModel
from .operating_system import (
    AccountabilityAssignmentModel,
    ComplianceOperationModel,
    ControlTestModel,
    ESGActionModel,
    ESGControlModel,
    ESGInitiativeModel,
    ESGKeyResultModel,
    ESGObjectiveModel,
    ESGPlaybookModel,
    ESGProgramModel,
    GovernanceCalendarEventModel,
    GovernanceEscalationRuleModel,
    OrganizationESGHealthScoreModel,
    StrategicRiskModel,
    WorkflowExecutionModel,
)
from .org_settings import OrganizationSettingsModel
from .organization import OrganizationModel
from .pentest_finding import PentestFindingModel
from .policy import PolicyModel
from .process import ProcessModel
from .product import (
    ProductBOMItemModel,
    ProductModel,
)
from .production_checklist import ProductionChecklistItemModel
from .project import ProjectModel
from .recommendation import RecommendationModel
from .region import DataResidencyAuditLogModel
from .regulatory import (
    ComplianceGapModel,
    ComplianceReportModel,
    ProductComplianceScanModel,
    RegulationModel,
    RegulationRequirementModel,
    RequirementMappingModel,
)
from .regulatory_calendar import RegulatoryDeadlineModel
from .report import ReportModel
from .requirement import RequirementModel
from .review_action import ReviewActionModel
from .risk import RiskModel
from .scope3 import ProductCarbonFootprintModel, Scope3InventoryModel
from .sector import SectorModel
from .sector_risk_register import (
    CalibrationSuggestionModel,
    ScenarioSuggestionModel,
    SectorRightScoreModel,
)
from .historical_knowledge import HistoricalKnowledgeModel
from .service_account import ServiceAccountModel
from .soc2_control import Soc2ControlModel
from .standard import StandardModel
from .supplier import SupplierModel
from .supplier_digital_twin import IntelligenceTimelineEventModel, SupplierDigitalTwinModel
from .supplier_extensions import (
    SupplierCertificationModel,
    SupplierContactModel,
    SupplierESGMetricModel,
    SupplierExternalESGRatingModel,
    SupplierLocationModel,
    SupplierOwnershipModel,
)
from .supplier_portal import (
    ConversationModel,
    ConversationParticipantModel,
    EvidenceRequestModel,
    EvidenceSubmissionFileModel,
    EvidenceSubmissionModel,
    MessageAttachmentModel,
    MessageModel,
    QuestionnaireAnswerModel,
    QuestionnaireAssignmentModel,
    QuestionnaireQuestionModel,
    QuestionnaireTemplateModel,
    RemediationPlanModel,
    SupplierActivityEventModel,
    SupplierInvitationModel,
    SupplierPasswordResetTokenModel,
    SupplierUserModel,
)
from .supplier_score import SupplierScoreModel
from .supply_chain_event import EventLogModel, EventOutboxModel
from .sustainability import (
    CarbonInventoryModel,
    ClimateRiskAssessmentModel,
    CSRDPerformanceMappingModel,
    DecarbonizationInitiativeModel,
    EmissionSourceModel,
    ESGKPIModel,
    ESGTargetModel,
    ISSBSustainabilityMappingModel,
    KPIAlertModel,
    KPIMeasurementModel,
    NetZeroMilestoneModel,
    NetZeroRoadmapModel,
    PerformanceForecastModel,
    ScenarioAnalysisModel,
    ScienceBasedTargetModel,
    SustainabilityAssuranceRecordModel,
    SustainabilityObjectiveModel,
    SustainabilityPerformanceReportModel,
    SustainabilityScorecardModel,
)
from .task import TaskModel
from .user import UserModel
from .webhook import WebhookDeliveryModel, WebhookSubscriptionModel
from .workflow_job import WorkflowJobModel
from .workflow_run import WorkflowRunModel

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
    "ProductComplianceScanModel",
    "DisclosureFrameworkModel",
    "DisclosureRequirementModel",
    "DisclosureResponseModel",
    "ReportingPackageModel",
    "DueDiligenceReportModel",
    "ProductCarbonFootprintModel",
    "Scope3InventoryModel",
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
    "NewsArticleModel",
    "NewsSupplierAssignmentModel",
    "SectorRightScoreModel",
    "CalibrationSuggestionModel",
    "ScenarioSuggestionModel",
    "HistoricalKnowledgeModel",
]
