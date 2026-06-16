"""
Comprehensive instantiation tests for all 16 canonical EIOS domain objects
plus Sector (per Founder Decision BC-11).

Every object must:
1. Instantiate with minimal required fields
2. Inherit BaseEntity fields correctly
3. Default optional fields to None or appropriate defaults
4. Carry the correct default EntityStatus (DRAFT)
"""

import pytest

from domain import (
    Asset,
    Assessment,
    BaseEntity,
    ConfidenceLevel,
    Control,
    ControlType,
    Decision,
    EntityStatus,
    Evidence,
    EvidenceType,
    Finding,
    Organization,
    Policy,
    Process,
    Project,
    Recommendation,
    Requirement,
    Risk,
    RiskLevel,
    Sector,
    Standard,
    Task,
    User,
)


class TestAssessment:
    def test_minimal_instantiation(self) -> None:
        a = Assessment(title="ESG Q1 2026", description="Sector assessment")
        assert a.title == "ESG Q1 2026"
        assert a.description == "Sector assessment"

    def test_inherits_base_entity(self) -> None:
        a = Assessment(title="T", description="D")
        assert isinstance(a, BaseEntity)
        assert a.status == EntityStatus.DRAFT
        assert a.version == 1
        assert a.id is not None

    def test_optional_defaults(self) -> None:
        a = Assessment(title="T", description="D")
        assert a.sector_id is None
        assert a.methodology is None
        assert a.approved_by is None
        assert a.approval_date is None
        assert a.finding_ids == []
        assert a.risk_ids == []
        assert a.evidence_ids == []

    def test_confidence_default(self) -> None:
        a = Assessment(title="T", description="D")
        assert a.confidence == ConfidenceLevel.HIGH

    def test_full_construction(self) -> None:
        a = Assessment(
            title="NACE B Mining",
            description="Sector-level ESG assessment",
            assessment_type="ESG",
            scope="NACE B",
            sector_id="sector-001",
            methodology="CSRD",
            finding_ids=["f-1", "f-2"],
        )
        assert a.sector_id == "sector-001"
        assert len(a.finding_ids) == 2


class TestEvidence:
    def test_minimal_instantiation(self) -> None:
        e = Evidence(title="ILO Report 2025", source="ilo.org", description="Labour risk data")
        assert e.title == "ILO Report 2025"

    def test_inherits_base_entity(self) -> None:
        e = Evidence(title="T", source="S", description="D")
        assert isinstance(e, BaseEntity)
        assert e.status == EntityStatus.DRAFT

    def test_evidence_type_default(self) -> None:
        e = Evidence(title="T", source="S", description="D")
        assert e.evidence_type == EvidenceType.DOCUMENT

    def test_optional_defaults(self) -> None:
        e = Evidence(title="T", source="S", description="D")
        assert e.url is None
        assert e.published_at is None
        assert e.retrieved_at is None
        assert e.reliability_score is None
        assert e.assessment_ids == []


class TestFinding:
    def test_minimal_instantiation(self) -> None:
        f = Finding(title="Child Labour Risk", description="Elevated risk detected", assessment_id="a-001")
        assert f.title == "Child Labour Risk"
        assert f.assessment_id == "a-001"

    def test_inherits_base_entity(self) -> None:
        f = Finding(title="T", description="D", assessment_id="a-1")
        assert isinstance(f, BaseEntity)
        assert f.status == EntityStatus.DRAFT

    def test_defaults(self) -> None:
        f = Finding(title="T", description="D", assessment_id="a-1")
        assert f.severity == RiskLevel.MEDIUM
        assert f.confidence == ConfidenceLevel.HIGH
        assert f.evidence_ids == []
        assert f.reasoning is None
        assert f.uncertainty is None


class TestRisk:
    def test_minimal_instantiation(self) -> None:
        r = Risk(title="Supply Chain Labour Risk", description="Risk in Tier-1 suppliers")
        assert r.title == "Supply Chain Labour Risk"

    def test_inherits_base_entity(self) -> None:
        r = Risk(title="T", description="D")
        assert isinstance(r, BaseEntity)

    def test_defaults(self) -> None:
        r = Risk(title="T", description="D")
        assert r.risk_level == RiskLevel.MEDIUM
        assert r.probability is None
        assert r.impact is None
        assert r.sector_id is None
        assert r.assessment_id is None
        assert r.finding_ids == []
        assert r.reasoning is None

    def test_explicit_risk_level(self) -> None:
        r = Risk(title="T", description="D", risk_level=RiskLevel.CRITICAL)
        assert r.risk_level == RiskLevel.CRITICAL


class TestRecommendation:
    def test_minimal_instantiation(self) -> None:
        rec = Recommendation(title="Audit Suppliers", description="Conduct third-party audit")
        assert rec.title == "Audit Suppliers"

    def test_inherits_base_entity(self) -> None:
        rec = Recommendation(title="T", description="D")
        assert isinstance(rec, BaseEntity)

    def test_defaults(self) -> None:
        rec = Recommendation(title="T", description="D")
        assert rec.priority == RiskLevel.MEDIUM
        assert rec.confidence == ConfidenceLevel.HIGH
        assert rec.action_required is True
        assert rec.risk_ids == []
        assert rec.finding_ids == []
        assert rec.due_date is None
        assert rec.approved_by is None


class TestDecision:
    def test_minimal_instantiation(self) -> None:
        d = Decision(
            title="Adopt sector-level scope",
            description="Scope decision",
            rationale="FR-002 alignment",
            decided_by="Founder",
        )
        assert d.decided_by == "Founder"

    def test_inherits_base_entity(self) -> None:
        d = Decision(title="T", description="D", rationale="R", decided_by="Founder")
        assert isinstance(d, BaseEntity)

    def test_defaults(self) -> None:
        d = Decision(title="T", description="D", rationale="R", decided_by="Founder")
        assert d.decided_at is None
        assert d.context is None
        assert d.recommendation_ids == []
        assert d.affected_object_ids == []


class TestControl:
    def test_minimal_instantiation(self) -> None:
        c = Control(title="Supplier Code of Conduct", description="Mandatory supplier sign-off")
        assert c.title == "Supplier Code of Conduct"

    def test_inherits_base_entity(self) -> None:
        c = Control(title="T", description="D")
        assert isinstance(c, BaseEntity)

    def test_defaults(self) -> None:
        c = Control(title="T", description="D")
        assert c.control_type == ControlType.PREVENTIVE
        assert c.effectiveness is None
        assert c.automated is False
        assert c.risk_ids == []
        assert c.requirement_ids == []

    def test_control_types(self) -> None:
        for ct in ControlType:
            c = Control(title="T", description="D", control_type=ct)
            assert c.control_type == ct


class TestRequirement:
    def test_minimal_instantiation(self) -> None:
        r = Requirement(title="CSDDD Art. 5", description="Human rights due diligence", source="CSDDD")
        assert r.source == "CSDDD"

    def test_inherits_base_entity(self) -> None:
        r = Requirement(title="T", description="D", source="LkSG")
        assert isinstance(r, BaseEntity)

    def test_defaults(self) -> None:
        r = Requirement(title="T", description="D", source="CSRD")
        assert r.article is None
        assert r.mandatory is True
        assert r.control_ids == []


class TestPolicy:
    def test_minimal_instantiation(self) -> None:
        p = Policy(title="ESG Risk Policy", description="Governs ESG risk management")
        assert p.title == "ESG Risk Policy"

    def test_inherits_base_entity(self) -> None:
        p = Policy(title="T", description="D")
        assert isinstance(p, BaseEntity)

    def test_defaults(self) -> None:
        p = Policy(title="T", description="D")
        assert p.effective_date is None
        assert p.expiry_date is None
        assert p.approved_by is None
        assert p.requirement_ids == []
        assert p.control_ids == []


class TestStandard:
    def test_minimal_instantiation(self) -> None:
        s = Standard(title="GRI 401", description="Employment reporting standard")
        assert s.title == "GRI 401"

    def test_inherits_base_entity(self) -> None:
        s = Standard(title="T", description="D")
        assert isinstance(s, BaseEntity)

    def test_defaults(self) -> None:
        s = Standard(title="T", description="D")
        assert s.reference is None
        assert s.version_label is None
        assert s.requirement_ids == []


class TestAsset:
    def test_minimal_instantiation(self) -> None:
        a = Asset(title="ESG Database", description="Internal ESG knowledge base")
        assert a.title == "ESG Database"

    def test_inherits_base_entity(self) -> None:
        a = Asset(title="T", description="D")
        assert isinstance(a, BaseEntity)

    def test_defaults(self) -> None:
        a = Asset(title="T", description="D")
        assert a.asset_class is None
        assert a.location is None
        assert a.organization_id is None


class TestProcess:
    def test_minimal_instantiation(self) -> None:
        p = Process(title="ESG Assessment Process", description="Standard assessment workflow")
        assert p.title == "ESG Assessment Process"

    def test_inherits_base_entity(self) -> None:
        p = Process(title="T", description="D")
        assert isinstance(p, BaseEntity)

    def test_defaults(self) -> None:
        p = Process(title="T", description="D")
        assert p.steps == []
        assert p.owner_domain is None
        assert p.automated is False

    def test_steps_can_be_set(self) -> None:
        p = Process(title="T", description="D", steps=["Collect", "Evaluate", "Report"])
        assert len(p.steps) == 3


class TestProject:
    def test_minimal_instantiation(self) -> None:
        p = Project(title="EIOS Phase 1", description="Environment setup milestone")
        assert p.title == "EIOS Phase 1"

    def test_inherits_base_entity(self) -> None:
        p = Project(title="T", description="D")
        assert isinstance(p, BaseEntity)

    def test_defaults(self) -> None:
        p = Project(title="T", description="D")
        assert p.priority == RiskLevel.MEDIUM
        assert p.start_date is None
        assert p.end_date is None
        assert p.organization_id is None


class TestTask:
    def test_minimal_instantiation(self) -> None:
        t = Task(title="Implement Finding model", description="Domain object implementation")
        assert t.title == "Implement Finding model"

    def test_inherits_base_entity(self) -> None:
        t = Task(title="T", description="D")
        assert isinstance(t, BaseEntity)

    def test_defaults(self) -> None:
        t = Task(title="T", description="D")
        assert t.project_id is None
        assert t.assignee_id is None
        assert t.priority == RiskLevel.MEDIUM
        assert t.due_date is None
        assert t.completed is False


class TestUser:
    def test_minimal_instantiation(self) -> None:
        u = User(email="founder@eios.io", display_name="Founder")
        assert u.email == "founder@eios.io"
        assert u.display_name == "Founder"

    def test_inherits_base_entity(self) -> None:
        u = User(email="a@b.com", display_name="User")
        assert isinstance(u, BaseEntity)

    def test_defaults(self) -> None:
        u = User(email="a@b.com", display_name="User")
        assert u.role == ""
        assert u.organization_id is None
        assert u.is_active is True
        assert u.last_login_at is None
        assert u.password_hash is None

    def test_password_hash_field(self) -> None:
        u = User(email="a@b.com", display_name="User", password_hash="$2b$12$hash")
        assert u.password_hash == "$2b$12$hash"


class TestOrganization:
    def test_minimal_instantiation(self) -> None:
        o = Organization(name="EIOS GmbH")
        assert o.name == "EIOS GmbH"

    def test_inherits_base_entity(self) -> None:
        o = Organization(name="Org")
        assert isinstance(o, BaseEntity)

    def test_defaults(self) -> None:
        o = Organization(name="Org")
        assert o.description is None
        assert o.country is None
        assert o.industry is None


class TestSector:
    def test_minimal_instantiation(self) -> None:
        s = Sector(name="Mining", nace_code="B")
        assert s.name == "Mining"
        assert s.nace_code == "B"

    def test_inherits_base_entity(self) -> None:
        s = Sector(name="Mining", nace_code="B")
        assert isinstance(s, BaseEntity)

    def test_defaults(self) -> None:
        s = Sector(name="Mining", nace_code="B")
        assert s.nace_description is None
        assert s.risk_profile is None
        assert s.parent_sector_id is None
        assert s.organization_id is None

    def test_hierarchical_sector(self) -> None:
        parent = Sector(name="Mining", nace_code="B")
        child = Sector(name="Coal Mining", nace_code="B.05", parent_sector_id=parent.id)
        assert child.parent_sector_id == parent.id


class TestCanonicalObjectCount:
    def test_sixteen_canonical_objects_plus_sector(self) -> None:
        canonical = [
            Assessment, Evidence, Finding, Risk, Recommendation,
            Decision, Control, Requirement, Policy, Standard,
            Asset, Process, Project, Task, User, Organization,
        ]
        assert len(canonical) == 16

    def test_all_inherit_base_entity(self) -> None:
        objects = [
            Assessment(title="T", description="D"),
            Evidence(title="T", source="S", description="D"),
            Finding(title="T", description="D", assessment_id="a-1"),
            Risk(title="T", description="D"),
            Recommendation(title="T", description="D"),
            Decision(title="T", description="D", rationale="R", decided_by="Founder"),
            Control(title="T", description="D"),
            Requirement(title="T", description="D", source="CSDDD"),
            Policy(title="T", description="D"),
            Standard(title="T", description="D"),
            Asset(title="T", description="D"),
            Process(title="T", description="D"),
            Project(title="T", description="D"),
            Task(title="T", description="D"),
            User(email="a@b.com", display_name="U"),
            Organization(name="O"),
            Sector(name="S", nace_code="A"),
        ]
        for obj in objects:
            assert isinstance(obj, BaseEntity), f"{type(obj).__name__} does not inherit BaseEntity"
            assert obj.status == EntityStatus.DRAFT, f"{type(obj).__name__} default status is not DRAFT"
            assert obj.version == 1, f"{type(obj).__name__} default version is not 1"
            assert obj.id is not None, f"{type(obj).__name__} has no ID"

    def test_all_ids_are_unique(self) -> None:
        objects = [
            Assessment(title="T", description="D"),
            Evidence(title="T", source="S", description="D"),
            Finding(title="T", description="D", assessment_id="a-1"),
            Risk(title="T", description="D"),
            Recommendation(title="T", description="D"),
        ]
        ids = [o.id for o in objects]
        assert len(ids) == len(set(ids))
