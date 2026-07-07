"""Sector Benchmark Service — M34.

Stores and retrieves SectorBenchmarks from the database.
The BenchmarkEngine (benchmark_engine.py) performs the pure calculations;
this service handles the persistence layer.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.external_intelligence import SectorBenchmark


async def upsert_sector_benchmark(
    benchmark: SectorBenchmark,
    session: AsyncSession,
) -> SectorBenchmark:
    """Insert or update a SectorBenchmark (idempotent on sector_id + dataset_id)."""
    from infrastructure.persistence.models.external_intelligence import SectorBenchmarkModel

    existing_stmt = select(SectorBenchmarkModel).where(
        SectorBenchmarkModel.sector_id == benchmark.sector_id,
        SectorBenchmarkModel.dataset_id == benchmark.dataset_id,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        return _model_to_domain(existing)

    model = _domain_to_model(benchmark)
    session.add(model)
    await session.flush()
    return benchmark


async def get_sector_benchmark(
    sector_id: str,
    session: AsyncSession,
    dataset_id: str | None = None,
) -> SectorBenchmark | None:
    """Return the most recent SectorBenchmark for a sector."""
    from infrastructure.persistence.models.external_intelligence import SectorBenchmarkModel

    stmt = (
        select(SectorBenchmarkModel)
        .where(SectorBenchmarkModel.sector_id == sector_id)
        .order_by(SectorBenchmarkModel.created_at.desc())
    )
    if dataset_id:
        stmt = stmt.where(SectorBenchmarkModel.dataset_id == dataset_id)

    row = (await session.execute(stmt)).first()
    return _model_to_domain(row[0]) if row else None


async def get_benchmark_by_nace(
    nace_code: str,
    session: AsyncSession,
) -> SectorBenchmark | None:
    """Return the most recent SectorBenchmark matching a NACE code."""
    from infrastructure.persistence.models.external_intelligence import SectorBenchmarkModel

    stmt = (
        select(SectorBenchmarkModel)
        .where(SectorBenchmarkModel.nace_code == nace_code)
        .order_by(SectorBenchmarkModel.created_at.desc())
    )
    row = (await session.execute(stmt)).first()
    return _model_to_domain(row[0]) if row else None


async def list_sector_benchmarks(
    session: AsyncSession,
    limit: int = 100,
) -> list[SectorBenchmark]:
    """List all sector benchmarks ordered by sector name."""
    from infrastructure.persistence.models.external_intelligence import SectorBenchmarkModel

    stmt = (
        select(SectorBenchmarkModel).order_by(SectorBenchmarkModel.sector_name.asc()).limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_model_to_domain(r) for r in rows]


def _domain_to_model(b: SectorBenchmark):
    from infrastructure.persistence.models.external_intelligence import SectorBenchmarkModel

    return SectorBenchmarkModel(
        id=b.id,
        status=b.status.value if hasattr(b.status, "value") else b.status,
        version=b.version,
        owner=b.owner,
        created_by=b.created_by,
        updated_by=b.updated_by,
        created_at=b.created_at,
        updated_at=b.updated_at,
        sector_id=b.sector_id,
        sector_name=b.sector_name,
        nace_code=b.nace_code,
        dataset_id=b.dataset_id,
        average_esg_score=b.average_esg_score,
        average_risk_score=b.average_risk_score,
        average_compliance_coverage=b.average_compliance_coverage,
        average_disclosure_readiness=b.average_disclosure_readiness,
        supplier_count=b.supplier_count,
        p10_esg_score=b.p10_esg_score,
        p25_esg_score=b.p25_esg_score,
        p50_esg_score=b.p50_esg_score,
        p75_esg_score=b.p75_esg_score,
        p90_esg_score=b.p90_esg_score,
        source_name=b.source_name,
        source_version=b.source_version,
        benchmark_date=b.benchmark_date,
    )


def _model_to_domain(m) -> SectorBenchmark:
    return SectorBenchmark(
        id=m.id,
        status=m.status,
        version=m.version,
        owner=m.owner,
        created_by=m.created_by,
        updated_by=m.updated_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
        sector_id=m.sector_id,
        sector_name=m.sector_name or "",
        nace_code=m.nace_code or "",
        dataset_id=m.dataset_id,
        average_esg_score=m.average_esg_score or 0.0,
        average_risk_score=m.average_risk_score or 0.0,
        average_compliance_coverage=m.average_compliance_coverage or 0.0,
        average_disclosure_readiness=m.average_disclosure_readiness or 0.0,
        supplier_count=m.supplier_count or 0,
        p10_esg_score=m.p10_esg_score or 0.0,
        p25_esg_score=m.p25_esg_score or 0.0,
        p50_esg_score=m.p50_esg_score or 0.0,
        p75_esg_score=m.p75_esg_score or 0.0,
        p90_esg_score=m.p90_esg_score or 0.0,
        source_name=m.source_name or "",
        source_version=m.source_version or "",
        benchmark_date=m.benchmark_date or "",
    )
