"""M44 — Strategy Platform Integration Tests.

Uses a real async PostgreSQL database (no mocks).
Requires DATABASE_URL env var or defaults to local dev DB.

Run with:
    pytest tests/integration/test_m44_strategy_integration.py -v -m integration
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from infrastructure.persistence.models.base import Base

pytestmark = pytest.mark.integration

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://eios:eios_dev@localhost:5432/eios_db",
)

_ORG = "int-test-org"
_ACTOR = "int-test-actor"


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception:
            pass
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as s:
        yield s
        await s.rollback()


def _make_sync_session_from_async(async_session: AsyncSession):
    """Wrap the async session's sync connection for service calls."""
    return async_session.sync_session


# ── Digital Twin integration ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_and_list_digital_twin(session):
    from application.strategy import digital_twin_service
    sync_s = _make_sync_session_from_async(session)
    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    twin = digital_twin_service.create_digital_twin(
        org_id, "Integration Twin", _ACTOR, sync_s,
        emissions_baseline_tco2e=5000.0,
        financial_baseline={"revenue": 100_000.0},
    )
    assert twin.id is not None
    assert twin.organization_id == org_id

    twins = digital_twin_service.list_digital_twins(org_id, sync_s)
    assert len(twins) == 1
    assert twins[0].name == "Integration Twin"


@pytest.mark.asyncio
async def test_create_snapshot_for_twin(session):
    from application.strategy import digital_twin_service
    sync_s = _make_sync_session_from_async(session)
    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    twin = digital_twin_service.create_digital_twin(
        org_id, "Twin With Snapshot", _ACTOR, sync_s,
        emissions_baseline_tco2e=1000.0,
    )
    snap = digital_twin_service.create_snapshot(
        org_id, twin.id, "ANNUAL", "2024", _ACTOR, sync_s,
        sustainability_state={"emissions_tco2e": 950.0},
        financial_esg_state={"revenue": 80_000.0},
    )
    assert snap.twin_id == twin.id
    assert snap.snapshot_type == "ANNUAL"
    assert snap.sustainability_state["emissions_tco2e"] == 950.0


# ── Baseline resolution integration ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_baseline_from_twin(session):
    from application.strategy import digital_twin_service
    from application.strategy.scenario_service import resolve_strategy_baseline
    sync_s = _make_sync_session_from_async(session)
    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    digital_twin_service.create_digital_twin(
        org_id, "Twin For Baseline", _ACTOR, sync_s,
        emissions_baseline_tco2e=3000.0,
        financial_baseline={"revenue": 200_000.0},
    )
    baseline = resolve_strategy_baseline(org_id, sync_s)
    assert baseline.get("emissions_tco2e") == 3000.0
    assert baseline.get("revenue") == 200_000.0


@pytest.mark.asyncio
async def test_resolve_baseline_no_twin_raises(session):
    from application.strategy.scenario_service import resolve_strategy_baseline
    from application.strategy.digital_twin_service import StrategyError
    sync_s = _make_sync_session_from_async(session)
    org_id = f"empty-org-{uuid.uuid4().hex[:8]}"

    with pytest.raises(StrategyError, match="No baseline found"):
        resolve_strategy_baseline(org_id, sync_s)


# ── Scenario + Execution integration ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_scenario_execution_workflow(session):
    from application.strategy import digital_twin_service, scenario_service
    sync_s = _make_sync_session_from_async(session)
    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    twin = digital_twin_service.create_digital_twin(
        org_id, "Workflow Twin", _ACTOR, sync_s,
        emissions_baseline_tco2e=2000.0,
        financial_baseline={"revenue": 500_000.0},
    )

    scenario = scenario_service.create_scenario(
        org_id, "Workflow Scenario", "CLIMATE", _ACTOR, sync_s,
        time_horizon_years=5,
    )
    scenario_service.create_assumption(
        org_id, scenario.id, "emissions_growth_pct_annual", "Emissions Growth Rate",
        -3.0, _ACTOR, sync_s, unit="pct/yr",
    )

    baseline = scenario_service.resolve_strategy_baseline(org_id, sync_s)
    execution = scenario_service.execute_scenario(
        org_id, scenario.id, _ACTOR, sync_s,
        twin_id=twin.id,
        baseline_override=baseline,
    )
    assert execution.execution_status == "Completed"
    assert execution.projected_emissions["emissions_tco2e"] < 2000.0


# ── Template integration ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_and_instantiate_scenario_template(session):
    from application.strategy import template_service
    sync_s = _make_sync_session_from_async(session)
    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    template = template_service.create_scenario_template(
        org_id, "NZ Template", "NET_ZERO", "CLIMATE", _ACTOR, sync_s,
        default_assumptions={"emissions_growth_pct_annual": -5.0},
        default_time_horizon_years=10,
    )
    assert template.template_name == "NZ Template"
    assert template.usage_count == 0

    scenario = template_service.instantiate_from_template(
        org_id, template.id, "NZ Scenario from Template", _ACTOR, sync_s,
    )
    assert scenario.name == "NZ Scenario from Template"
    assert template.usage_count == 1


# ── Methodology integration ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_methodology_approval_lifecycle(session):
    from application.strategy import methodology_service
    sync_s = _make_sync_session_from_async(session)
    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    methodology = methodology_service.create_methodology(
        org_id, "SBTi 1.5C Linear", _ACTOR, sync_s,
        formula_description="Linear reduction from 2024 baseline",
        applicable_to=["FORECAST", "PATHWAY"],
    )
    assert methodology.approval_status == "DRAFT"

    approved = methodology_service.approve_methodology(org_id, methodology.id, _ACTOR, sync_s)
    assert approved.approval_status == "APPROVED"
    assert approved.approved_by == _ACTOR

    deprecated = methodology_service.deprecate_methodology(org_id, methodology.id, _ACTOR, sync_s)
    assert deprecated.approval_status == "DEPRECATED"


# ── Comparison integration ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scenario_comparison_integration(session):
    from application.strategy import comparison_service, scenario_service
    sync_s = _make_sync_session_from_async(session)
    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    s1 = scenario_service.create_scenario(org_id, "Base", "CLIMATE", _ACTOR, sync_s)
    s2 = scenario_service.create_scenario(org_id, "Alt", "CLIMATE", _ACTOR, sync_s)

    baseline_a = {"emissions_tco2e": 1000.0, "revenue": 50_000.0}
    baseline_b = {"emissions_tco2e": 800.0, "revenue": 60_000.0}

    scenario_service.execute_scenario(org_id, s1.id, _ACTOR, sync_s, baseline_override=baseline_a)
    scenario_service.execute_scenario(org_id, s2.id, _ACTOR, sync_s, baseline_override=baseline_b)

    comparison = comparison_service.compare_scenarios(
        org_id, "Base vs Alt", [s1.id, s2.id], _ACTOR, sync_s
    )
    assert comparison.comparison_name == "Base vs Alt"
    assert s2.id in comparison.emissions_delta


# ── Pathway frequency integration ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pathway_quarterly_milestones_integration(session):
    from application.strategy import pathway_service
    sync_s = _make_sync_session_from_async(session)
    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    import datetime
    current_year = datetime.datetime.now(datetime.timezone.utc).year
    target_year = current_year + 2

    pathway = pathway_service.create_pathway(
        org_id, "Quarterly Pathway", "EXPECTED", target_year, _ACTOR, sync_s,
        baseline_emissions_tco2e=1000.0,
        target_emissions_tco2e=0.0,
        milestone_frequency="QUARTERLY",
    )
    assert pathway.milestone_frequency == "QUARTERLY"
    milestones = pathway.milestones["milestones"]
    assert len(milestones) == 8  # 2 years × 4 quarters
    assert "Q" in milestones[0]["period"]
