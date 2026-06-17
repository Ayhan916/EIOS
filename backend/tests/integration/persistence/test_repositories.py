"""
Integration tests for EIOS repositories.

Requires a running PostgreSQL instance.
Start with: docker compose up -d

To run only these tests: pytest tests/integration/ -v
To skip in CI without PostgreSQL: pytest tests/unit/ -v
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from domain.assessment import Assessment
from domain.evidence import Evidence
from domain.finding import Finding
from domain.risk import Risk
from infrastructure.persistence.models import Base
from infrastructure.persistence.repositories import (
    SQLAssessmentRepository,
    SQLEvidenceRepository,
    SQLFindingRepository,
    SQLRiskRepository,
)

TEST_DATABASE_URL = "postgresql+asyncpg://eios:eios_dev@localhost:5432/eios_db"

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(scope="session")
async def engine():  # type: ignore[no-untyped-def]
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):  # type: ignore[no-untyped-def]
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as s, s.begin():
        yield s
        await s.rollback()


class TestAssessmentRepository:
    async def test_save_and_retrieve(self, session: AsyncSession) -> None:
        repo = SQLAssessmentRepository(session)
        assessment = Assessment(title="NACE B ESG", description="Mining sector assessment")

        saved = await repo.save(assessment)
        retrieved = await repo.get_by_id(saved.id)

        assert retrieved is not None
        assert retrieved.id == assessment.id
        assert retrieved.title == "NACE B ESG"
        assert retrieved.description == "Mining sector assessment"

    async def test_get_nonexistent_returns_none(self, session: AsyncSession) -> None:
        repo = SQLAssessmentRepository(session)
        result = await repo.get_by_id("does-not-exist")
        assert result is None

    async def test_delete(self, session: AsyncSession) -> None:
        repo = SQLAssessmentRepository(session)
        assessment = Assessment(title="To Delete", description="D")
        saved = await repo.save(assessment)

        await repo.delete(saved.id)
        result = await repo.get_by_id(saved.id)
        assert result is None

    async def test_list_by_sector(self, session: AsyncSession) -> None:
        repo = SQLAssessmentRepository(session)
        sector_id = "sector-test-001"
        a1 = Assessment(title="A1", description="D", sector_id=sector_id)
        a2 = Assessment(title="A2", description="D", sector_id=sector_id)
        a3 = Assessment(title="A3", description="D", sector_id="other-sector")
        await repo.save(a1)
        await repo.save(a2)
        await repo.save(a3)

        results = await repo.list_by_sector(sector_id)
        assert len(results) == 2
        titles = {r.title for r in results}
        assert titles == {"A1", "A2"}


class TestEvidenceRepository:
    async def test_save_and_retrieve(self, session: AsyncSession) -> None:
        repo = SQLEvidenceRepository(session)
        evidence = Evidence(
            title="ILO Report 2025",
            source="ilo.org",
            description="Labour risk data for mining",
        )
        saved = await repo.save(evidence)
        retrieved = await repo.get_by_id(saved.id)

        assert retrieved is not None
        assert retrieved.title == "ILO Report 2025"
        assert retrieved.source == "ilo.org"

    async def test_reliability_score_persists(self, session: AsyncSession) -> None:
        repo = SQLEvidenceRepository(session)
        evidence = Evidence(
            title="High Quality Source",
            source="academic.org",
            description="Peer-reviewed",
            reliability_score=0.95,
        )
        saved = await repo.save(evidence)
        retrieved = await repo.get_by_id(saved.id)

        assert retrieved is not None
        assert retrieved.reliability_score == pytest.approx(0.95)


class TestFindingRepository:
    async def test_save_and_retrieve(self, session: AsyncSession) -> None:
        a_repo = SQLAssessmentRepository(session)
        f_repo = SQLFindingRepository(session)

        assessment = await a_repo.save(Assessment(title="Base Assessment", description="D"))
        finding = Finding(
            title="Child Labour Risk",
            description="Elevated risk in Tier-1 supply chain",
            assessment_id=assessment.id,
        )
        saved = await f_repo.save(finding)
        retrieved = await f_repo.get_by_id(saved.id)

        assert retrieved is not None
        assert retrieved.assessment_id == assessment.id
        assert retrieved.title == "Child Labour Risk"

    async def test_list_by_assessment(self, session: AsyncSession) -> None:
        a_repo = SQLAssessmentRepository(session)
        f_repo = SQLFindingRepository(session)

        assessment = await a_repo.save(Assessment(title="Test Assessment", description="D"))
        for i in range(3):
            await f_repo.save(
                Finding(title=f"Finding {i}", description="D", assessment_id=assessment.id)
            )

        results = await f_repo.list_by_assessment(assessment.id)
        assert len(results) == 3


class TestRiskRepository:
    async def test_save_and_retrieve(self, session: AsyncSession) -> None:
        repo = SQLRiskRepository(session)
        risk = Risk(
            title="Supply Chain Labour Risk",
            description="Elevated risk in NACE B sectors",
            sector_id="sector-mining-001",
        )
        saved = await repo.save(risk)
        retrieved = await repo.get_by_id(saved.id)

        assert retrieved is not None
        assert retrieved.title == "Supply Chain Labour Risk"
        assert retrieved.sector_id == "sector-mining-001"

    async def test_list_by_sector(self, session: AsyncSession) -> None:
        repo = SQLRiskRepository(session)
        sector_id = "sector-for-risk-test"
        await repo.save(Risk(title="R1", description="D", sector_id=sector_id))
        await repo.save(Risk(title="R2", description="D", sector_id=sector_id))
        await repo.save(Risk(title="R3", description="D", sector_id="other"))

        results = await repo.list_by_sector(sector_id)
        assert len(results) == 2
