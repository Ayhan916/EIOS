"""M44 — Strategy Platform Integration Tests.

Uses a real async PostgreSQL database (no mocks).
Requires DATABASE_URL env var or defaults to local dev DB.

Run with:
    pytest tests/integration/test_m44_strategy_integration.py -v -m integration
"""

from __future__ import annotations

import contextlib
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from infrastructure.persistence.models.base import Base

pytestmark = pytest.mark.integration

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://eios:eios_dev@localhost:5432/eios_test_db",
)

_ORG = "int-test-org"
_ACTOR = "int-test-actor"


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        with contextlib.suppress(Exception):
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as s:
        yield s
        await s.rollback()


# ── Digital Twin integration ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_list_digital_twin(session):
    from application.strategy import digital_twin_service

    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    twin = await session.run_sync(
        lambda s: digital_twin_service.create_digital_twin(
            org_id,
            "Integration Twin",
            _ACTOR,
            s,
            emissions_baseline_tco2e=5000.0,
            financial_baseline={"revenue": 100_000.0},
        )
    )
    assert twin.id is not None
    assert twin.organization_id == org_id

    twins = await session.run_sync(lambda s: digital_twin_service.list_digital_twins(org_id, s))
    assert len(twins) == 1
    assert twins[0].name == "Integration Twin"


@pytest.mark.asyncio
async def test_create_snapshot_for_twin(session):
    from application.strategy import digital_twin_service

    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    twin = await session.run_sync(
        lambda s: digital_twin_service.create_digital_twin(
            org_id,
            "Twin With Snapshot",
            _ACTOR,
            s,
            emissions_baseline_tco2e=1000.0,
        )
    )
    twin_id = twin.id
    snap = await session.run_sync(
        lambda s: digital_twin_service.create_snapshot(
            org_id,
            twin_id,
            "ANNUAL",
            "2024",
            _ACTOR,
            s,
            sustainability_state={"emissions_tco2e": 950.0},
            financial_esg_state={"revenue": 80_000.0},
        )
    )
    assert snap.twin_id == twin_id
    assert snap.snapshot_type == "ANNUAL"
    assert snap.sustainability_state["emissions_tco2e"] == 950.0


# ── Baseline resolution integration ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_baseline_from_twin(session):
    from application.strategy import digital_twin_service
    from application.strategy.scenario_service import resolve_strategy_baseline

    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    await session.run_sync(
        lambda s: digital_twin_service.create_digital_twin(
            org_id,
            "Twin For Baseline",
            _ACTOR,
            s,
            emissions_baseline_tco2e=3000.0,
            financial_baseline={"revenue": 200_000.0},
        )
    )
    baseline = await session.run_sync(lambda s: resolve_strategy_baseline(org_id, s))
    assert baseline.get("emissions_tco2e") == 3000.0
    assert baseline.get("revenue") == 200_000.0


@pytest.mark.asyncio
async def test_resolve_baseline_no_twin_raises(session):
    from application.strategy.digital_twin_service import StrategyError
    from application.strategy.scenario_service import resolve_strategy_baseline

    org_id = f"empty-org-{uuid.uuid4().hex[:8]}"

    with pytest.raises(StrategyError, match="No baseline found"):
        await session.run_sync(lambda s: resolve_strategy_baseline(org_id, s))


# ── Scenario + Execution integration ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_scenario_execution_workflow(session):
    from application.strategy import digital_twin_service, scenario_service

    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    twin = await session.run_sync(
        lambda s: digital_twin_service.create_digital_twin(
            org_id,
            "Workflow Twin",
            _ACTOR,
            s,
            emissions_baseline_tco2e=2000.0,
            financial_baseline={"revenue": 500_000.0},
        )
    )
    twin_id = twin.id

    scenario = await session.run_sync(
        lambda s: scenario_service.create_scenario(
            org_id,
            "Workflow Scenario",
            "CLIMATE",
            _ACTOR,
            s,
            time_horizon_years=5,
        )
    )
    scenario_id = scenario.id

    await session.run_sync(
        lambda s: scenario_service.create_assumption(
            org_id,
            scenario_id,
            "emissions_growth_pct_annual",
            "Emissions Growth Rate",
            -3.0,
            _ACTOR,
            s,
            unit="pct/yr",
        )
    )

    baseline = await session.run_sync(
        lambda s: scenario_service.resolve_strategy_baseline(org_id, s)
    )
    execution = await session.run_sync(
        lambda s: scenario_service.execute_scenario(
            org_id,
            scenario_id,
            _ACTOR,
            s,
            twin_id=twin_id,
            baseline_override=baseline,
        )
    )
    assert execution.execution_status == "Completed"
    assert execution.projected_emissions["emissions_tco2e"] < 2000.0


# ── Template integration ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_instantiate_scenario_template(session):
    from application.strategy import template_service

    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    template = await session.run_sync(
        lambda s: template_service.create_scenario_template(
            org_id,
            "NZ Template",
            "NET_ZERO",
            "CLIMATE",
            _ACTOR,
            s,
            default_assumptions={"emissions_growth_pct_annual": -5.0},
            default_time_horizon_years=10,
        )
    )
    assert template.template_name == "NZ Template"
    assert template.usage_count == 0

    template_id = template.id
    scenario = await session.run_sync(
        lambda s: template_service.instantiate_from_template(
            org_id,
            template_id,
            "NZ Scenario from Template",
            _ACTOR,
            s,
        )
    )
    assert scenario.name == "NZ Scenario from Template"
    assert template.usage_count == 1


# ── Methodology integration ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_methodology_approval_lifecycle(session):
    from application.strategy import methodology_service

    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    methodology = await session.run_sync(
        lambda s: methodology_service.create_methodology(
            org_id,
            "SBTi 1.5C Linear",
            _ACTOR,
            s,
            formula_description="Linear reduction from 2024 baseline",
            applicable_to=["FORECAST", "PATHWAY"],
        )
    )
    assert methodology.approval_status == "DRAFT"

    methodology_id = methodology.id
    approved = await session.run_sync(
        lambda s: methodology_service.approve_methodology(org_id, methodology_id, _ACTOR, s)
    )
    assert approved.approval_status == "APPROVED"
    assert approved.approved_by == _ACTOR

    deprecated = await session.run_sync(
        lambda s: methodology_service.deprecate_methodology(org_id, methodology_id, _ACTOR, s)
    )
    assert deprecated.approval_status == "DEPRECATED"


# ── Comparison integration ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scenario_comparison_integration(session):
    from application.strategy import comparison_service, scenario_service

    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    s1 = await session.run_sync(
        lambda s: scenario_service.create_scenario(org_id, "Base", "CLIMATE", _ACTOR, s)
    )
    s2 = await session.run_sync(
        lambda s: scenario_service.create_scenario(org_id, "Alt", "CLIMATE", _ACTOR, s)
    )
    s1_id, s2_id = s1.id, s2.id

    baseline_a = {"emissions_tco2e": 1000.0, "revenue": 50_000.0}
    baseline_b = {"emissions_tco2e": 800.0, "revenue": 60_000.0}

    await session.run_sync(
        lambda s: scenario_service.execute_scenario(
            org_id, s1_id, _ACTOR, s, baseline_override=baseline_a
        )
    )
    await session.run_sync(
        lambda s: scenario_service.execute_scenario(
            org_id, s2_id, _ACTOR, s, baseline_override=baseline_b
        )
    )

    comparison = await session.run_sync(
        lambda s: comparison_service.compare_scenarios(
            org_id, "Base vs Alt", [s1_id, s2_id], _ACTOR, s
        )
    )
    assert comparison.comparison_name == "Base vs Alt"
    assert s2_id in comparison.emissions_delta


# ── Pathway frequency integration ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pathway_quarterly_milestones_integration(session):
    from application.strategy import pathway_service

    org_id = f"{_ORG}-{uuid.uuid4().hex[:8]}"

    import datetime

    current_year = datetime.datetime.now(datetime.UTC).year
    target_year = current_year + 2

    pathway = await session.run_sync(
        lambda s: pathway_service.create_pathway(
            org_id,
            "Quarterly Pathway",
            "EXPECTED",
            target_year,
            _ACTOR,
            s,
            baseline_emissions_tco2e=1000.0,
            target_emissions_tco2e=0.0,
            milestone_frequency="QUARTERLY",
        )
    )
    assert pathway.milestone_frequency == "QUARTERLY"
    milestones = pathway.milestones["milestones"]
    assert len(milestones) == 8  # 2 years × 4 quarters
    assert "Q" in milestones[0]["period"]
