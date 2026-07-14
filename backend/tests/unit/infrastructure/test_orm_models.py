"""
Unit tests for ORM model structure.

Validates that all models are registered, tables are named correctly,
and required columns are present — without a database connection.
"""

from infrastructure.persistence.models import (
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
    StandardModel,
    TaskModel,
    UserModel,
)

# M36: ensure agent monitoring models are registered
from infrastructure.persistence.models.agent_monitoring import (  # noqa: F401
    AgentAlertModel,
    AgentFindingModel,
    EscalationRuleModel,
    MonitoringAgentModel,
    MonitoringAgentRunModel,
    RecommendationDraftModel,
)

# M41: ensure AI Governance models are registered
from infrastructure.persistence.models.ai_governance import (  # noqa: F401
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

# CSDDD (M90–M98): ensure all CSDDD compliance models are registered
from infrastructure.persistence.models.board_signoff import (  # noqa: F401
    BoardDecisionModel,
    BoardSignoffRequestModel,
)

# M34.1: ensure connector run models are registered
from infrastructure.persistence.models.connector_run import (  # noqa: F401
    ConnectorRunModel,
    DatasetValidationResultModel,
)
from infrastructure.persistence.models.contractual_assurance import (  # noqa: F401
    ClauseAuditLogModel,
    ContractAssuranceModel,
    ContractClauseModel,
)

# M33: ensure copilot models are registered
from infrastructure.persistence.models.copilot import (  # noqa: F401
    CopilotConversationModel,
    CopilotMessageModel,
)

# M33.2: ensure copilot audit models are registered
from infrastructure.persistence.models.copilot_audit import (  # noqa: F401
    CopilotAnswerReviewModel,
    CopilotAuditPackageModel,
    CopilotCitationIntegrityModel,
    CopilotContradictionModel,
    CopilotFeedbackModel,
)
from infrastructure.persistence.models.corrective_action_plan import (
    CorrectiveActionPlanModel,  # noqa: F401
)
from infrastructure.persistence.models.dd_policy import (  # noqa: F401
    CoCAcceptanceModel,
    CodeOfConductModel,
    DDPolicyModel,
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
from infrastructure.persistence.models.effectiveness import (  # noqa: F401
    EffectivenessIndicatorModel,
    EffectivenessReviewModel,
    ReviewLineModel,
)

# M40: ensure enterprise models are registered (includes M40.1 SecretReference + SCIMToken)
from infrastructure.persistence.models.enterprise import (  # noqa: F401
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
from infrastructure.persistence.models.esap import ESAPSubmissionModel  # noqa: F401
from infrastructure.persistence.models.evaluation import (  # noqa: F401
    BenchmarkResultModel,
    CalibrationEventModel,
    EvaluationRunModel,
)

# M34: ensure external intelligence models are registered
from infrastructure.persistence.models.external_intelligence import (  # noqa: F401
    CountryRiskProfileModel,
    ExternalDatasetModel,
    ExternalRiskSignalModel,
    SectorBenchmarkModel,
    SupplierEnrichmentModel,
)

# M43: ensure Financial ESG models are registered
from infrastructure.persistence.models.financial_esg import (  # noqa: F401
    CapitalMarketsAssessmentModel,
    CarbonCostModelRecord,
    ClimateFinanceAnalysisModel,
    CostOfRiskAssessmentModel,
    ESGFinancialCorrelationModel,
    FinanceLinkedKPIModel,
    FinancialESGKPIModel,
    FinancialESGReportModel,
    FinancialKPIMeasurementModel,
    FinancialScenarioAnalysisModel,
    GreenCapexRecordModel,
    GreenOpexRecordModel,
    GreenRevenueRecordModel,
    InvestorDisclosurePackageModel,
    SustainabilityValuationModelRecord,
    SustainableFinanceInstrumentModel,
    TaxonomyAlignmentAssessmentModel,
    TransitionPlanMilestoneModel,
    TransitionPlanModel,
    ValueCreationInitiativeModel,
)
from infrastructure.persistence.models.impact_assessment import ImpactAssessmentModel  # noqa: F401
from infrastructure.persistence.models.improvement import ImprovementProposalModel  # noqa: F401

# M38: ensure network intelligence models are registered
from infrastructure.persistence.models.network import (  # noqa: F401
    DependencyAnalysisModel,
    IncidentClusterModel,
    NetworkExposureSignalModel,
    NetworkWatchlistEntryModel,
    ResilienceAssessmentModel,
    SuggestedRelationshipModel,
    SupplierCriticalityModel,
    SupplierRelationshipModel,
)

# M39: ensure operating system models are registered
from infrastructure.persistence.models.operating_system import (  # noqa: F401
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
from infrastructure.persistence.models.prioritization import (
    PrioritizationDecisionModel,  # noqa: F401
)
from infrastructure.persistence.models.readiness import ReadinessSnapshotModel  # noqa: F401

# M31/M31.1: ensure new regulatory models are registered
from infrastructure.persistence.models.regulatory import (  # noqa: F401
    ComplianceGapModel,
    ComplianceReportModel,
    RegulationModel,
    RegulationRequirementModel,
    RequirementMappingModel,
)
from infrastructure.persistence.models.regulatory_change import (  # noqa: F401
    RegulatoryChangeModel as LegacyRegulatoryChangeModel,
)
from infrastructure.persistence.models.regulatory_radar import (  # noqa: F401
    RegulatoryFeedEntryModel,
    RegulatorySourceModel,
)
from infrastructure.persistence.models.remedy_case import (  # noqa: F401
    RemedyActionModel,
    RemedyAuditLogModel,
    RemedyBeneficiaryModel,
    RemedyCaseModel,
)
from infrastructure.persistence.models.scoping import (  # noqa: F401
    ScopingConfigAuditLogModel,
    ScopingConfigModel,
    ScopingStudyModel,
)
from infrastructure.persistence.models.sme_support import (  # noqa: F401
    SMEProfileModel,
    SupportMeasureModel,
    SupportProgramModel,
)
from infrastructure.persistence.models.stakeholder import (  # noqa: F401
    StakeholderConsultationModel,
    StakeholderFeedbackModel,
    StakeholderModel,
)

# M44: ensure Strategy models are registered
from infrastructure.persistence.models.strategy import (  # noqa: F401
    BoardSimulationModel,
    ClimateStressTestModel,
    DigitalTwinSnapshotModel,
    EnterpriseDigitalTwinModel,
    FinancialStressTestModel,
    ForecastMethodologyRecordModel,
    ForecastModelRecord,
    ForecastResultModel,
    ForecastWindowPolicyModel,
    InvestmentScenarioModel,
    NetZeroPathwayRecord,
    PortfolioOptimizationModel,
    ScenarioAssumptionModel,
    ScenarioComparisonModel,
    ScenarioExecutionModel,
    # M44.1 additions
    ScenarioTemplateModel,
    StrategicForecastSummaryModel,
    StrategicObjectiveModel,
    StrategicPlanModel,
    StrategicRiskProjectionModel,
    StrategicScenarioReportModel,
    StrategyMethodologyModel,
    StrategyScenarioModel,
    StressTestTemplateModel,
    SupplierShockScenarioModel,
    TransitionPathwayModel,
)
from infrastructure.persistence.models.supplier_assessment import (  # noqa: F401
    AssessmentQuestionModel,
    AssessmentResponseModel,
    AssessmentTemplateModel,
    SupplierAssessmentModel,
)

# M35: ensure supplier portal models are registered
from infrastructure.persistence.models.supplier_portal import (  # noqa: F401
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

# M37: ensure surveillance models are registered
from infrastructure.persistence.models.surveillance import (  # noqa: F401
    RiskEpisodeModel,
    RiskTrendModel,
    SupplierWatchlistModel,
    SurveillanceSignalModel,
)
from infrastructure.persistence.models.threshold_monitor import CompanyProfileModel  # noqa: F401

# RAG + Intelligence pipeline models (E2-F3, E3-F3, E5-F3) — imported explicitly
# so that test_total_table_count is deterministic regardless of test execution order.
from infrastructure.persistence.models.rag_documents import RagDocumentModel  # noqa: F401
from infrastructure.persistence.models.document_pipeline import DocumentFileModel, DocumentSourceModel  # noqa: F401
from infrastructure.persistence.models.company_intelligence import CompanyMetricModel, CompanySignalModel  # noqa: F401
from infrastructure.persistence.models.supply_chain_edge import SupplyChainEdgeModel  # noqa: F401
from infrastructure.persistence.models.prompt_version import PromptVersionModel  # noqa: F401
from infrastructure.persistence.models.historical_knowledge import HistoricalKnowledgeModel  # noqa: F401
from infrastructure.persistence.models.entity_alias import EntityAliasModel  # noqa: F401

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
    # M35: Supplier Portal (15 tables)
    "supplier_users",
    "supplier_invitations",
    "evidence_requests",
    "evidence_submissions",
    "evidence_submission_files",
    "questionnaire_templates",
    "questionnaire_questions",
    "questionnaire_assignments",
    "questionnaire_answers",
    "remediation_plans",
    "conversations",
    "conversation_participants",
    "messages",
    "message_attachments",
    "supplier_activity_events",
    "supplier_password_reset_tokens",
    # M36: Agent Monitoring (6 tables)
    "monitoring_agents",
    "monitoring_agent_runs",
    "agent_findings",
    "agent_alerts",
    "escalation_rules",
    "recommendation_drafts",
    # M37: Surveillance (4 tables)
    "surveillance_signals",
    "supplier_watchlists",
    "risk_episodes",
    "risk_trends",
    # M38: Network Intelligence (7 tables)
    "supplier_relationships",
    "suggested_relationships",
    "network_exposure_signals",
    "supplier_criticality",
    "dependency_analyses",
    "resilience_assessments",
    "incident_clusters",
    # M38.1: Network Watchlist (1 table)
    "network_watchlist_entries",
    # M39: ESG Operating System (15 tables)
    "esg_objectives",
    "esg_key_results",
    "esg_initiatives",
    "governance_calendar_events",
    "esg_programs",
    "esg_controls",
    "control_tests",
    "compliance_operations",
    "esg_actions",
    "accountability_assignments",
    "esg_playbooks",
    "workflow_executions",
    "governance_escalation_rules",
    "esg_health_scores",
    "strategic_risks",
    # M40: Enterprise Multi-Tenant Scale (10 tables)
    "enterprises",
    "business_units",
    "legal_entities",
    "enterprise_regions",
    "identity_providers",
    "group_mappings",
    "enterprise_policies",
    "retention_rules",
    "notification_policies",
    "enterprise_risks",
    # M40.1: Identity & Provisioning Hardening (2 tables)
    "secret_references",
    "scim_tokens",
    # M41: AI Governance (17 tables)
    "ai_models",
    "ai_use_cases",
    "ai_risk_assessments",
    "ai_controls",
    "ai_control_tests",
    "model_approval_workflows",
    "prompt_templates",
    "prompt_changes",
    "ai_decision_logs",
    "ai_explanations",
    "human_reviews",
    "model_monitoring_records",
    "model_drift_alerts",
    "ai_incidents",
    "ai_policies",
    "ai_assurance_reports",
    "ai_regulation_mappings",
    "ai_regulation_mapping_history",
    # M42 — Sustainability Performance Management
    "sustainability_objectives",
    "esg_targets",
    "esg_kpis",
    "kpi_measurements",
    "kpi_alerts",
    "sustainability_scorecards",
    "emission_sources",
    "carbon_inventories",
    "decarbonization_initiatives",
    "net_zero_roadmaps",
    "net_zero_milestones",
    "science_based_targets",
    "climate_risk_assessments",
    "sustainability_assurance_records",
    "csrd_performance_mappings",
    "issb_sustainability_mappings",
    "performance_forecasts",
    "scenario_analyses",
    "sustainability_performance_reports",
    # M43 — Financial ESG, Value Creation & Capital Markets (20 tables)
    "financial_esg_kpis",
    "financial_kpi_measurements",
    "carbon_cost_models",
    "cost_of_risk_assessments",
    "value_creation_initiatives",
    "sustainable_finance_instruments",
    "taxonomy_alignment_assessments",
    "green_revenue_records",
    "green_capex_records",
    "green_opex_records",
    "transition_plans",
    "transition_plan_milestones",
    "finance_linked_kpis",
    "capital_markets_assessments",
    "investor_disclosure_packages",
    "climate_finance_analyses",
    "sustainability_valuation_models",
    "esg_financial_correlations",
    "financial_scenario_analyses",
    "financial_esg_reports",
    # M44 — Digital Twin, Strategic Planning & Scenario Intelligence (21 tables)
    "enterprise_digital_twins",
    "digital_twin_snapshots",
    "strategic_plans",
    "strategic_objectives",
    "strategy_scenarios",
    "scenario_assumptions",
    "scenario_executions",
    "climate_stress_tests",
    "supplier_shock_scenarios",
    "financial_stress_tests",
    "transition_pathways",
    "net_zero_pathways",
    "strategic_risk_projections",
    "portfolio_optimizations",
    "investment_scenarios",
    "forecast_methodology_records",
    "forecast_models",
    "forecast_results",
    "board_simulations",
    "strategic_forecast_summaries",
    "strategic_scenario_reports",
    # M44.1 additions (5 tables)
    "scenario_templates",
    "strategy_methodologies",
    "scenario_comparisons",
    "stress_test_templates",
    "forecast_window_policies",
    # M45 — MFA
    "mfa_backup_codes",
    # M46.2 — Enterprise Data Layer
    "ghg_emission_factors",
    "ghg_calculations",
    "evidence_versions",
    # M46.3 — Scheduling & Alerts
    "remediation_milestones",
    "assessment_schedules",
    "supplier_certificates",
    "risk_drafts",
    # M47 — Multi-Region Data Residency
    "data_residency_audit_log",
    # M47 — Regulatory Reporting
    "regulatory_deadlines",
    "control_framework_mappings",
    # M48.2 — Commercial Readiness
    "organization_settings",
    "custom_roles",
    "board_access_tokens",
    "soc2_controls",
    "pentest_findings",
    "production_checklist_items",
    # Pre-existing tables imported via __init__.py (supplier extensions, materials, products, etc.)
    "supplier_esg_metrics",
    "supplier_external_esg_ratings",
    "supplier_locations",
    "supplier_contacts",
    "supplier_certifications",
    "supplier_ownerships",
    "supplier_digital_twins",
    "intelligence_timeline_events",
    "materials",
    "material_compositions",
    "material_sourcing",
    "material_compliance_flags",
    "material_sustainability_metrics",
    "products",
    "product_bom_items",
    "product_compliance_scans",
    "digital_product_passports",
    "scope3_inventories",
    "product_carbon_footprints",
    "event_outbox",
    "event_log",
    "erp_connectors",
    "erp_sync_jobs",
    "erp_field_mappings",
    "news_articles",
    "news_supplier_assignments",
    "calibration_suggestions",
    "scenario_suggestions",
    "sector_right_scores",
    "grievance_reports",
    # CSDDD (M90–M98) tables
    "board_signoff_requests",
    "board_decisions",
    "company_profiles",
    "regulatory_sources",
    "csddd_regulatory_changes",
    "regulatory_feed_entries",
    "assessment_templates",
    "assessment_questions",
    "supplier_assessments",
    "assessment_responses",
    "esap_submissions",
    # CSDDD due-diligence domain tables
    "effectiveness_indicators",
    "effectiveness_reviews",
    "review_lines",
    "scoping_configs",
    "scoping_config_audit_logs",
    "scoping_studies",
    "remedy_cases",
    "remedy_beneficiaries",
    "remedy_actions",
    "remedy_audit_logs",
    "corrective_action_plans",
    "dd_policies",
    "codes_of_conduct",
    "coc_acceptances",
    "contract_clauses",
    "contract_assurances",
    "clause_audit_logs",
    "readiness_snapshots",
    "impact_assessments",
    "stakeholders",
    "stakeholder_consultations",
    "stakeholder_feedback",
    "regulatory_changes",
    "regulatory_change_impacts",
    "evaluation_runs",
    "benchmark_results",
    "calibration_events",
    "improvement_proposals",
    "prioritization_decisions",
    "sme_profiles",
    "sme_support_programs",
    "sme_support_measures",
    # RAG + Intelligence pipeline tables (E2-F3, E3-F3, E5-F3)
    "historical_knowledge",
    "rag_documents",
    "document_files",
    "document_sources",
    "company_metrics",
    "company_signals",
    "supply_chain_edges",
    "prompt_versions",
    "entity_aliases",
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
        assert (
            len(Base.metadata.tables) == 313
        )  # 231 baseline +30 supply-chain/material/product +11 CSDDD Phase4 +32 CSDDD due-diligence domain +9 RAG/Intelligence/EntityLinker pipeline

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
