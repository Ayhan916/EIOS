"""
Unit tests for ORM model structure.

Validates that all models are registered, tables are named correctly,
and required columns are present — without a database connection.
"""

from infrastructure.persistence.models import (
    ApiKeyModel,
    AssessmentModel,
    AssetModel,
    Base,
    ControlModel,
    DecisionModel,
    EvidenceModel,
    FindingModel,
    OrganizationModel,
    PolicyModel,
    ProcessModel,
    ProjectModel,
    RecommendationModel,
    RequirementModel,
    RiskModel,
    SectorModel,
    ServiceAccountModel,
    StandardModel,
    TaskModel,
    UserModel,
    WebhookDeliveryModel,
    WebhookSubscriptionModel,
)
# M31/M31.1: ensure new regulatory models are registered
from infrastructure.persistence.models.regulatory import (  # noqa: F401
    ComplianceGapModel,
    ComplianceReportModel,
    RegulationModel,
    RegulationRequirementModel,
    RequirementMappingModel,
)
# M32: ensure disclosure models are registered
from infrastructure.persistence.models.disclosure import (  # noqa: F401
    DisclosureFrameworkModel,
    DisclosureRequirementModel,
    DisclosureResponseModel,
    ReportingPackageModel,
)
# M32.1: ensure due diligence model is registered
from infrastructure.persistence.models.due_diligence import DueDiligenceReportModel  # noqa: F401
# M33: ensure copilot models are registered
from infrastructure.persistence.models.copilot import CopilotConversationModel, CopilotMessageModel  # noqa: F401
# M33.2: ensure copilot audit models are registered
from infrastructure.persistence.models.copilot_audit import (  # noqa: F401
    CopilotContradictionModel,
    CopilotCitationIntegrityModel,
    CopilotFeedbackModel,
    CopilotAnswerReviewModel,
    CopilotAuditPackageModel,
)
# M34: ensure external intelligence models are registered
from infrastructure.persistence.models.external_intelligence import (  # noqa: F401
    ExternalDatasetModel,
    CountryRiskProfileModel,
    SectorBenchmarkModel,
    ExternalRiskSignalModel,
    SupplierEnrichmentModel,
)
# M34.1: ensure connector run models are registered
from infrastructure.persistence.models.connector_run import (  # noqa: F401
    ConnectorRunModel,
    DatasetValidationResultModel,
)

EXPECTED_ENTITY_TABLES = {
    "organizations",
    "users",
    "sectors",
    "assessments",
    "evidences",
    "evidence_chunks",
    "agent_runs",
    "workflow_runs",
    "workflow_jobs",
    "audit_events",
    "findings",
    "finding_evidence_links",
    "notifications",
    "comments",
    "review_actions",
    "risks",
    "recommendations",
    "decisions",
    "controls",
    "requirements",
    "policies",
    "standards",
    "assets",
    "processes",
    "projects",
    "tasks",
    "reports",
    "suppliers",
    "supplier_scores",
    "board_reports",
    "report_schedules",
    "service_accounts",
    "api_keys",
    "webhook_subscriptions",
    "webhook_deliveries",
    "regulations",
    "regulation_requirements",
    "requirement_mappings",
    "compliance_gaps",
    "compliance_reports",
    "disclosure_frameworks",
    "disclosure_requirements",
    "disclosure_responses",
    "reporting_packages",
    "due_diligence_reports",
    "copilot_conversations",
    "copilot_messages",
    "copilot_contradictions",
    "copilot_citation_integrity",
    "copilot_feedback",
    "copilot_answer_reviews",
    "copilot_audit_packages",
    # M34: External Intelligence
    "external_datasets",
    "country_risk_profiles",
    "sector_benchmarks",
    "external_risk_signals",
    "supplier_enrichments",
    # M34.1: Connector runs & validation
    "connector_runs",
    "dataset_validation_results",
}

EXPECTED_ASSOCIATION_TABLES = {
    "assessment_evidence",
    "finding_evidence",
    "risk_finding",
    "recommendation_risk",
    "recommendation_finding",
    "control_risk",
    "control_requirement",
    "policy_requirement",
    "policy_control",
    "standard_requirement",
    "decision_recommendation",
}

COMMON_COLUMNS = {
    "id",
    "status",
    "version",
    "owner",
    "created_by",
    "updated_by",
    "created_at",
    "updated_at",
}


class TestTableRegistration:
    def test_all_entity_tables_registered(self) -> None:
        registered = set(Base.metadata.tables.keys())
        assert EXPECTED_ENTITY_TABLES.issubset(registered)

    def test_all_association_tables_registered(self) -> None:
        registered = set(Base.metadata.tables.keys())
        assert EXPECTED_ASSOCIATION_TABLES.issubset(registered)

    def test_total_table_count(self) -> None:
        assert len(Base.metadata.tables) == 70  # M34.1 adds 2: connector_runs, dataset_validation_results

    def test_no_unexpected_tables(self) -> None:
        registered = set(Base.metadata.tables.keys())
        expected = EXPECTED_ENTITY_TABLES | EXPECTED_ASSOCIATION_TABLES
        assert registered == expected


class TestCommonColumns:
    def _columns(self, model: type) -> set[str]:
        return {c.name for c in model.__table__.columns}  # type: ignore[attr-defined]

    def test_assessment_has_common_columns(self) -> None:
        assert COMMON_COLUMNS.issubset(self._columns(AssessmentModel))

    def test_evidence_has_common_columns(self) -> None:
        assert COMMON_COLUMNS.issubset(self._columns(EvidenceModel))

    def test_finding_has_common_columns(self) -> None:
        assert COMMON_COLUMNS.issubset(self._columns(FindingModel))

    def test_risk_has_common_columns(self) -> None:
        assert COMMON_COLUMNS.issubset(self._columns(RiskModel))

    def test_all_models_have_common_columns(self) -> None:
        models = [
            AssessmentModel,
            EvidenceModel,
            FindingModel,
            RiskModel,
            RecommendationModel,
            DecisionModel,
            ControlModel,
            RequirementModel,
            PolicyModel,
            StandardModel,
            AssetModel,
            ProcessModel,
            ProjectModel,
            TaskModel,
            UserModel,
            OrganizationModel,
            SectorModel,
        ]
        for model in models:
            cols = self._columns(model)
            missing = COMMON_COLUMNS - cols
            assert not missing, f"{model.__name__} missing columns: {missing}"


class TestSpecificColumns:
    def test_assessment_columns(self) -> None:
        cols = {c.name for c in AssessmentModel.__table__.columns}
        assert {"title", "description", "sector_id", "confidence"}.issubset(cols)

    def test_finding_has_assessment_fk(self) -> None:
        cols = {c.name for c in FindingModel.__table__.columns}
        assert "assessment_id" in cols

    def test_risk_has_sector_fk(self) -> None:
        cols = {c.name for c in RiskModel.__table__.columns}
        assert "sector_id" in cols

    def test_sector_is_self_referential(self) -> None:
        cols = {c.name for c in SectorModel.__table__.columns}
        assert "parent_sector_id" in cols
        assert "nace_code" in cols

    def test_user_has_unique_email(self) -> None:
        table = UserModel.__table__
        unique_constraints = {c.name for c in table.constraints if hasattr(c, "name")}
        assert "uq_users_email" in unique_constraints

    def test_evidence_has_reliability_score(self) -> None:
        cols = {c.name for c in EvidenceModel.__table__.columns}
        assert "reliability_score" in cols

    def test_process_has_steps_column(self) -> None:
        cols = {c.name for c in ProcessModel.__table__.columns}
        assert "steps" in cols


class TestRelationships:
    def test_assessment_has_findings_relationship(self) -> None:
        assert hasattr(AssessmentModel, "findings")

    def test_assessment_has_evidence_relationship(self) -> None:
        assert hasattr(AssessmentModel, "evidence")

    def test_assessment_has_risks_relationship(self) -> None:
        assert hasattr(AssessmentModel, "risks")

    def test_finding_has_assessment_relationship(self) -> None:
        assert hasattr(FindingModel, "assessment")

    def test_risk_has_recommendations_relationship(self) -> None:
        assert hasattr(RiskModel, "recommendations")

    def test_sector_is_self_referential_relationship(self) -> None:
        assert hasattr(SectorModel, "parent")
        assert hasattr(SectorModel, "children")
