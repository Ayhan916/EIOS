"""
Integration tests for M25 Evidence Intelligence.

Scenarios covered:
  1.  create_finding_evidence_links — empty chunks → no links
  2.  create_finding_evidence_links — matching chunk creates link
  3.  create_finding_evidence_links — non-matching chunk ignored (below threshold)
  4.  compute_evidence_strength — None when no links
  5.  compute_evidence_strength — Weak for single low-confidence link
  6.  compute_evidence_strength — Very Strong for many high-confidence diverse links
  7.  GET /findings/{id}/evidence-links — 404 on unknown finding
  8.  GET /findings/{id}/evidence-links — empty list when no links
  9.  GET /assessments/{id}/evidence-insights — correct counts and structure
  10. GET /assessments/{id}/evidence-insights — tenant isolation (org B cannot see org A data)
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from application.extraction.evidence_linker import (
    compute_evidence_strength,
    create_finding_evidence_links,
    update_finding_evidence_strength,
)
from domain.enums import EntityStatus, EvidenceStrength
from domain.finding import Finding
from domain.finding_evidence_link import FindingEvidenceLink
from infrastructure.persistence.database import AsyncSessionFactory
from infrastructure.persistence.models.evidence import EvidenceModel
from infrastructure.persistence.repositories.assessment import SQLAssessmentRepository
from infrastructure.persistence.repositories.finding import SQLFindingRepository
from infrastructure.persistence.repositories.finding_evidence_link import (
    SQLFindingEvidenceLinkRepository,
)
from shared.rate_limit import reset_for_tests

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

AUTH = "/api/v1/auth"
FIND = "/api/v1/findings"
ASSESS = "/api/v1/assessments"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _ensure_schema(setup_test_schema: None) -> None:  # type: ignore[misc]
    pass


@pytest.fixture(autouse=True)
def _reset_rl() -> None:
    reset_for_tests()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register(email: str, org: str) -> tuple[str, str, str]:
    """Returns (token, user_id, org_id)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            AUTH + "/register",
            json={
                "email": email,
                "display_name": email.split("@")[0],
                "password": "pw-evidtest-123",
                "organization_name": org,
            },
        )
    assert r.status_code == 201, r.text
    d = r.json()
    return d["access_token"], d["user"]["id"], d["user"]["organization_id"]


def _make_finding(assessment_id: str = "asmnt-1", title: str = "Child labour risk") -> Finding:
    return Finding(
        title=title,
        description="Supplier uses underage workers in stitching operations",
        assessment_id=assessment_id,
        category="Social",
        reasoning="ILO findings indicate violation of minimum age standards",
        status=EntityStatus.ACTIVE,
    )


def _make_chunk(text: str, evidence_id: str = "ev-1", similarity: float = 0.7) -> dict:
    return {
        "chunk_id": f"chunk-{hash(text) % 10000}",
        "evidence_id": evidence_id,
        "page_number": 12,
        "source_section": "Section 3",
        "text": text,
        "similarity_score": similarity,
        "evidence_title": "ILO Child Labour Report",
        "evidence_source": "ilo.org",
    }


# ---------------------------------------------------------------------------
# Unit-level tests for evidence_linker (fast, no DB)
# ---------------------------------------------------------------------------


class TestCreateFindingEvidenceLinks:
    def test_empty_chunks_returns_no_links(self) -> None:
        finding = _make_finding()
        links = create_finding_evidence_links([finding], [])
        assert links == []

    def test_empty_findings_returns_no_links(self) -> None:
        chunk = _make_chunk("child labour violation workers underage stitching")
        links = create_finding_evidence_links([], [chunk])
        assert links == []

    def test_matching_chunk_creates_link(self) -> None:
        finding = _make_finding()
        # This chunk has strong keyword overlap with the finding text
        chunk = _make_chunk(
            "underage workers child labour violation supplier stitching minimum age"
        )
        links = create_finding_evidence_links([finding], [chunk])
        assert len(links) == 1
        link = links[0]
        assert link.finding_id == finding.id
        assert link.evidence_id == "ev-1"
        assert link.page_number == 12
        assert link.confidence_score is not None
        assert link.confidence_score > 0.04
        assert link.supporting_excerpt is not None
        assert link.link_method == "auto"

    def test_unrelated_chunk_ignored(self) -> None:
        finding = _make_finding(title="Carbon emissions reduction target")
        # Chunk about an unrelated topic
        chunk = _make_chunk(
            "board diversity gender parity executive compensation governance",
            similarity=0.05,  # also low semantic similarity
        )
        links = create_finding_evidence_links([finding], [chunk])
        assert links == []

    def test_max_five_links_per_finding(self) -> None:
        finding = _make_finding()
        chunks = [
            _make_chunk(
                f"child labour underage workers supplier stitching violation {i}",
                evidence_id=f"ev-{i}",
            )
            for i in range(10)
        ]
        links = create_finding_evidence_links([finding], chunks)
        assert len(links) <= 5

    def test_links_ordered_by_score(self) -> None:
        finding = _make_finding()
        # High match: many shared words + high semantic score
        high_chunk = _make_chunk(
            "child labour workers underage supplier stitching violation ilo minimum age",
            similarity=0.9,
        )
        # Low match: fewer shared words
        low_chunk = _make_chunk(
            "labour market employment wage workers",
            similarity=0.3,
            evidence_id="ev-2",
        )
        links = create_finding_evidence_links([finding], [low_chunk, high_chunk])
        assert len(links) >= 2
        # First link should be higher confidence than second
        assert links[0].confidence_score >= links[1].confidence_score  # type: ignore[operator]


class TestComputeEvidenceStrength:
    def _link(self, confidence: float, evidence_id: str = "ev-1") -> FindingEvidenceLink:
        return FindingEvidenceLink(
            finding_id="f-1",
            evidence_id=evidence_id,
            confidence_score=confidence,
            status=EntityStatus.ACTIVE,
        )

    def test_no_links_returns_none(self) -> None:
        assert compute_evidence_strength([]) is None

    def test_single_low_confidence_is_weak(self) -> None:
        links = [self._link(0.05)]
        result = compute_evidence_strength(links)
        assert result == EvidenceStrength.WEAK

    def test_many_high_confidence_diverse_is_very_strong(self) -> None:
        links = [self._link(0.9, f"ev-{i}") for i in range(5)]
        result = compute_evidence_strength(links)
        assert result == EvidenceStrength.VERY_STRONG

    def test_moderate_case(self) -> None:
        links = [self._link(0.5), self._link(0.5, "ev-2")]
        result = compute_evidence_strength(links)
        assert result in (EvidenceStrength.MODERATE, EvidenceStrength.STRONG)

    def test_update_finding_evidence_strength_mutates(self) -> None:
        finding = _make_finding()
        links = [self._link(0.9, f"ev-{i}") for i in range(5)]
        update_finding_evidence_strength(finding, links)
        assert finding.evidence_strength is not None
        assert finding.evidence_source_count == 5


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


async def test_list_finding_evidence_links_404_on_unknown(setup_test_schema: None) -> None:
    tok, _, _ = await _register("evid-404@eios.dev", "Org Evid404")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(FIND + "/nonexistent-finding-id/evidence-links")
    assert r.status_code == 404


async def test_list_finding_evidence_links_empty_when_no_links(setup_test_schema: None) -> None:
    tok, uid, org_id = await _register("evid-empty@eios.dev", "Org EvidEmpty")

    # Create an assessment + finding directly via DB
    from domain.assessment import Assessment
    from domain.enums import ConfidenceLevel

    async with AsyncSessionFactory() as session, session.begin():
        assess_repo = SQLAssessmentRepository(session)
        finding_repo = SQLFindingRepository(session)

        assessment = Assessment(
            title="Test assessment",
            description="desc",
            assessment_type="quick_scan",
            scope="quick_scan",
            confidence=ConfidenceLevel.MEDIUM,
            status=EntityStatus.REVIEWED,
            organization_id=org_id,
            created_by=uid,
        )
        saved_assessment = await assess_repo.save(assessment)

        finding = Finding(
            title="Test finding",
            description="A test finding with no evidence links",
            assessment_id=saved_assessment.id,
            category="Environmental",
            status=EntityStatus.ACTIVE,
            created_by=uid,
        )
        saved_finding = await finding_repo.save(finding)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(FIND + f"/{saved_finding.id}/evidence-links")
    assert r.status_code == 200
    assert r.json() == []


async def test_evidence_insights_correct_structure(setup_test_schema: None) -> None:
    tok, uid, org_id = await _register("evid-insights@eios.dev", "Org EvidInsights")

    from domain.assessment import Assessment
    from domain.enums import ConfidenceLevel

    async with AsyncSessionFactory() as session, session.begin():
        assess_repo = SQLAssessmentRepository(session)
        finding_repo = SQLFindingRepository(session)
        link_repo = SQLFindingEvidenceLinkRepository(session)

        assessment = Assessment(
            title="Insights test",
            description="desc",
            assessment_type="due_diligence",
            scope="due_diligence",
            confidence=ConfidenceLevel.HIGH,
            status=EntityStatus.REVIEWED,
            organization_id=org_id,
            created_by=uid,
        )
        saved_assessment = await assess_repo.save(assessment)

        finding = Finding(
            title="Supply chain labour violation",
            description="Workers underage stitching supplier",
            assessment_id=saved_assessment.id,
            category="Social",
            status=EntityStatus.ACTIVE,
            created_by=uid,
        )
        saved_finding = await finding_repo.save(finding)

        _now = datetime.now(UTC)
        session.add(
            EvidenceModel(
                id="ev-test-001",
                organization_id=org_id,
                title="Test Evidence",
                source="test-source",
                description="Evidence for insights test",
                created_at=_now,
                updated_at=_now,
            )
        )
        await session.flush()

        link = FindingEvidenceLink(
            finding_id=saved_finding.id,
            evidence_id="ev-test-001",
            evidence_chunk_id=None,
            page_number=5,
            confidence_score=0.75,
            supporting_excerpt="Child labour violations confirmed.",
            link_method="auto",
            status=EntityStatus.ACTIVE,
            created_by=uid,
        )
        await link_repo.save(link)

        # Update finding strength
        update_finding_evidence_strength(saved_finding, [link])
        await finding_repo.save(saved_finding)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok}"},
    ) as c:
        r = await c.get(ASSESS + f"/{saved_assessment.id}/evidence-insights")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["assessment_id"] == saved_assessment.id
    assert body["total_findings"] == 1
    assert body["linked_findings"] == 1
    assert body["total_evidence_links"] == 1
    assert len(body["findings"]) == 1
    assert len(body["findings"][0]["evidence_links"]) == 1
    assert body["findings"][0]["evidence_links"][0]["page_number"] == 5
    assert "Child labour" in body["findings"][0]["evidence_links"][0]["supporting_excerpt"]


async def test_evidence_insights_tenant_isolation(setup_test_schema: None) -> None:
    tok_a, uid_a, org_a = await _register("evid-iso-a@eios.dev", "Org EvidIsoA")
    tok_b, uid_b, org_b = await _register("evid-iso-b@eios.dev", "Org EvidIsoB")

    from domain.assessment import Assessment
    from domain.enums import ConfidenceLevel

    async with AsyncSessionFactory() as session, session.begin():
        assess_repo = SQLAssessmentRepository(session)
        finding_repo = SQLFindingRepository(session)

        assessment = Assessment(
            title="Org A assessment",
            description="desc",
            assessment_type="quick_scan",
            scope="quick_scan",
            confidence=ConfidenceLevel.MEDIUM,
            status=EntityStatus.REVIEWED,
            organization_id=org_a,
            created_by=uid_a,
        )
        saved = await assess_repo.save(assessment)

    # Org B tries to access Org A's evidence insights — must be 404
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {tok_b}"},
    ) as c:
        r = await c.get(ASSESS + f"/{saved.id}/evidence-insights")
    assert r.status_code == 404
