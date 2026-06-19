"""M34 sector benchmark service tests."""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

from application.external_intelligence.sector_benchmark_service import (
    get_benchmark_by_nace,
    get_sector_benchmark,
    list_sector_benchmarks,
    upsert_sector_benchmark,
)
from domain.enums import ExternalSourceName
from domain.external_intelligence import SectorBenchmark


def _now():
    return datetime.now(UTC)


def _make_model(**kwargs):
    m = MagicMock()
    m.id = "sb-001"
    m.status = "Active"
    m.version = 1
    m.owner = None
    m.created_by = None
    m.updated_by = None
    m.created_at = _now()
    m.updated_at = _now()
    m.sector_id = "sec-001"
    m.sector_name = "Manufacturing"
    m.nace_code = "C28"
    m.dataset_id = "ds-bench-001"
    m.average_esg_score = 60.0
    m.average_risk_score = 40.0
    m.average_compliance_coverage = 70.0
    m.average_disclosure_readiness = 65.0
    m.supplier_count = 150
    m.p10_esg_score = 20.0
    m.p25_esg_score = 40.0
    m.p50_esg_score = 60.0
    m.p75_esg_score = 75.0
    m.p90_esg_score = 90.0
    m.source_name = "sector_esg_benchmark"
    m.source_version = "2025-Q1"
    m.benchmark_date = "2025-03-01"
    for k, v in kwargs.items():
        setattr(m, k, v)
    return m


def _make_session_first(model_or_none):
    """Mock session where execute().first() returns (model,) or None."""
    session = AsyncMock()
    result = MagicMock()
    if model_or_none is None:
        result.first.return_value = None
    else:
        result.first.return_value = (model_or_none,)
    result.scalar_one_or_none.return_value = model_or_none
    session.execute = AsyncMock(return_value=result)
    return session


def _make_benchmark_domain(**kwargs):
    defaults = dict(
        sector_id="sec-001",
        sector_name="Manufacturing",
        nace_code="C28",
        dataset_id="ds-bench-001",
        average_esg_score=60.0,
        average_risk_score=40.0,
        average_compliance_coverage=70.0,
        average_disclosure_readiness=65.0,
        supplier_count=150,
        p10_esg_score=20.0,
        p25_esg_score=40.0,
        p50_esg_score=60.0,
        p75_esg_score=75.0,
        p90_esg_score=90.0,
        source_name=ExternalSourceName.SECTOR_ESG_BENCHMARK,
        source_version="2025-Q1",
        benchmark_date="2025-03-01",
    )
    defaults.update(kwargs)
    return SectorBenchmark(**defaults)


@pytest.mark.asyncio
async def test_get_sector_benchmark_returns_benchmark():
    model = _make_model()
    session = _make_session_first(model)
    benchmark = await get_sector_benchmark("sec-001", session)
    assert benchmark is not None
    assert benchmark.sector_name == "Manufacturing"
    assert benchmark.p50_esg_score == 60.0


@pytest.mark.asyncio
async def test_get_sector_benchmark_not_found():
    session = _make_session_first(None)
    benchmark = await get_sector_benchmark("sec-999", session)
    assert benchmark is None


@pytest.mark.asyncio
async def test_get_benchmark_by_nace_returns_benchmark():
    model = _make_model()
    session = _make_session_first(model)
    benchmark = await get_benchmark_by_nace("C28", session)
    assert benchmark is not None
    assert benchmark.nace_code == "C28"


@pytest.mark.asyncio
async def test_get_benchmark_by_nace_not_found():
    session = _make_session_first(None)
    benchmark = await get_benchmark_by_nace("Z99", session)
    assert benchmark is None


@pytest.mark.asyncio
async def test_list_sector_benchmarks():
    models = [_make_model(sector_id=f"sec-{i}", sector_name=f"Sector {i}") for i in range(3)]
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = models
    session.execute = AsyncMock(return_value=result)
    benchmarks = await list_sector_benchmarks(session)
    assert len(benchmarks) == 3


@pytest.mark.asyncio
async def test_upsert_sector_benchmark_creates_when_missing():
    session = AsyncMock()
    no_existing = MagicMock()
    no_existing.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=no_existing)
    session.flush = AsyncMock()

    benchmark = _make_benchmark_domain()
    b = await upsert_sector_benchmark(benchmark, session)
    assert b is not None
    assert b.sector_name == "Manufacturing"
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_sector_benchmark_returns_existing():
    existing = _make_model()
    session = AsyncMock()
    found = MagicMock()
    found.scalar_one_or_none.return_value = existing
    session.execute = AsyncMock(return_value=found)

    benchmark = _make_benchmark_domain(sector_name="Manufacturing Updated", average_esg_score=65.0)
    b = await upsert_sector_benchmark(benchmark, session)
    assert b is not None
    # When existing, returns domain from existing model (sector_name = "Manufacturing")
    assert b.sector_name == "Manufacturing"
    session.add.assert_not_called()
