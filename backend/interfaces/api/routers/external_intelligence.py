"""M34 External Intelligence API Router.

Endpoints:
  GET  /external-intelligence/datasets
  GET  /external-intelligence/countries/{country_code}
  GET  /external-intelligence/countries
  GET  /external-intelligence/sectors/{sector_id}
  GET  /external-intelligence/sectors
  GET  /external-intelligence/signals/supplier/{supplier_id}
  GET  /external-intelligence/signals/country/{country_code}
  POST /external-intelligence/signals
  POST /external-intelligence/enrich
  GET  /external-intelligence/enrichments/{supplier_id}
  GET  /external-intelligence/enrichments/high-risk

All read endpoints require scope "external_intelligence:read".
Write endpoints (signal creation, enrichment) require "external_intelligence:write".
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.external_intelligence.country_risk_service import (
    get_country_risk,
    list_country_risks,
)
from application.external_intelligence.dataset_service import (
    get_active_dataset,
    list_datasets,
)
from application.external_intelligence.enrichment_service import (
    enrich_supplier,
    get_enrichment,
    list_high_risk_suppliers,
)
from application.external_intelligence.signal_service import (
    create_signal,
    list_active_signals,
    list_signals_for_country,
    list_signals_for_supplier,
)
from application.external_intelligence.sector_benchmark_service import (
    get_sector_benchmark,
    get_benchmark_by_nace,
    list_sector_benchmarks,
)
from domain.external_intelligence import ExternalRiskSignal
from interfaces.api.deps import get_current_user, get_db, scope_gate
from interfaces.api.schemas.external_intelligence import (
    CountryRiskListResponse,
    CountryRiskResponse,
    CreateSignalRequest,
    DatasetListResponse,
    EnrichmentListResponse,
    EnrichSupplierRequest,
    ExternalDatasetResponse,
    ExternalRiskSignalResponse,
    SectorBenchmarkListResponse,
    SectorBenchmarkResponse,
    SignalListResponse,
    SupplierEnrichmentResponse,
)
from domain.user import User

router = APIRouter(
    prefix="/external-intelligence",
    tags=["External Intelligence"],
)

_READ = Depends(scope_gate("external_intelligence:read"))
_WRITE = Depends(scope_gate("external_intelligence:write"))


# ── Datasets ──────────────────────────────────────────────────────────────────

@router.get(
    "/datasets",
    response_model=DatasetListResponse,
    dependencies=[_READ],
)
async def list_external_datasets(
    source_name: str | None = None,
    dataset_status: str | None = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DatasetListResponse:
    datasets = await list_datasets(session, source_name=source_name, status=dataset_status, limit=limit)
    return DatasetListResponse(
        datasets=[_dataset_to_response(d) for d in datasets],
        total=len(datasets),
    )


# ── Country Risk ──────────────────────────────────────────────────────────────

@router.get(
    "/countries/{country_code}",
    response_model=CountryRiskResponse,
    dependencies=[_READ],
)
async def get_country_risk_profile(
    country_code: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CountryRiskResponse:
    profile = await get_country_risk(country_code, session)
    if profile is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Country risk profile not found")
    return _country_risk_to_response(profile)


@router.get(
    "/countries",
    response_model=CountryRiskListResponse,
    dependencies=[_READ],
)
async def list_country_risk_profiles(
    risk_level: str | None = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CountryRiskListResponse:
    profiles = await list_country_risks(session, risk_level=risk_level, limit=limit)
    return CountryRiskListResponse(
        profiles=[_country_risk_to_response(p) for p in profiles],
        total=len(profiles),
    )


# ── Sector Benchmarks ─────────────────────────────────────────────────────────

@router.get(
    "/sectors/{sector_id}",
    response_model=SectorBenchmarkResponse,
    dependencies=[_READ],
)
async def get_sector_benchmark_profile(
    sector_id: str,
    nace_code: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SectorBenchmarkResponse:
    benchmark = None
    if nace_code:
        benchmark = await get_benchmark_by_nace(nace_code, session)
    if benchmark is None:
        benchmark = await get_sector_benchmark(sector_id, session)
    if benchmark is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Sector benchmark not found")
    return _sector_benchmark_to_response(benchmark)


@router.get(
    "/sectors",
    response_model=SectorBenchmarkListResponse,
    dependencies=[_READ],
)
async def list_sector_benchmark_profiles(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SectorBenchmarkListResponse:
    benchmarks = await list_sector_benchmarks(session, limit=limit)
    return SectorBenchmarkListResponse(
        benchmarks=[_sector_benchmark_to_response(b) for b in benchmarks],
        total=len(benchmarks),
    )


# ── Signals ───────────────────────────────────────────────────────────────────

@router.get(
    "/signals",
    response_model=SignalListResponse,
    dependencies=[_READ],
)
async def list_org_signals(
    limit: int = 20,
    severity: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SignalListResponse:
    signals = await list_active_signals(
        session,
        organization_id=current_user.organization_id,
        severity=severity,
        limit=limit,
    )
    return SignalListResponse(signals=[_signal_to_response(s) for s in signals], total=len(signals))


@router.get(
    "/signals/by-connector",
    response_model=dict,
    dependencies=[_READ],
)
async def signals_by_connector(
    top_n: int = 10,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Return top N active signals per connector/source for the organisation.

    Response shape:
    {
      "connectors": [
        { "source_name": "world_bank", "label": "World Bank", "signals": [...], "total": N },
        ...
      ]
    }
    """
    from sqlalchemy import select
    from infrastructure.persistence.models.external_intelligence import ExternalRiskSignalModel

    _SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    _CONNECTOR_LABELS = {
        "world_bank":                  "World Bank",
        "transparency_international":  "Transparency International",
        "ilo":                         "ILO",
        "unicef":                      "UNICEF",
        "un_sanctions":                "UN Sanctions",
        "eu_sanctions":                "EU Sanctions",
    }

    # Pull all active signals for this org (max 1000)
    stmt = (
        select(ExternalRiskSignalModel)
        .where(
            ExternalRiskSignalModel.organization_id == current_user.organization_id,
            ExternalRiskSignalModel.is_active.is_(True),
        )
        .order_by(ExternalRiskSignalModel.observed_at.desc())
        .limit(1000)
    )
    rows = (await session.execute(stmt)).scalars().all()

    # Group by source_name
    grouped: dict[str, list] = {k: [] for k in _CONNECTOR_LABELS}
    for r in rows:
        src = r.source_name if isinstance(r.source_name, str) else r.source_name.value
        if src in grouped:
            grouped[src].append(r)

    connectors = []
    for src, label in _CONNECTOR_LABELS.items():
        bucket = grouped[src]
        # Sort by severity then observed_at desc
        bucket.sort(key=lambda r: (
            _SEV_ORDER.get((r.severity if isinstance(r.severity, str) else r.severity.value).lower(), 9),
            -(r.observed_at.timestamp() if r.observed_at else 0),
        ))
        top = bucket[:top_n]
        connectors.append({
            "source_name": src,
            "label": label,
            "total": len(bucket),
            "signals": [_signal_to_response(r) for r in top],
        })

    return {"connectors": connectors}


@router.get(
    "/signals/supplier/{supplier_id}",
    response_model=SignalListResponse,
    dependencies=[_READ],
)
async def list_supplier_signals(
    supplier_id: str,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SignalListResponse:
    signals = await list_signals_for_supplier(
        supplier_id, current_user.organization_id, session, active_only=active_only
    )
    return SignalListResponse(
        signals=[_signal_to_response(s) for s in signals],
        total=len(signals),
    )


@router.get(
    "/signals/country/{country_code}",
    response_model=SignalListResponse,
    dependencies=[_READ],
)
async def list_country_signals(
    country_code: str,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SignalListResponse:
    signals = await list_signals_for_country(country_code, session, active_only=active_only)
    return SignalListResponse(
        signals=[_signal_to_response(s) for s in signals],
        total=len(signals),
    )


@router.post(
    "/signals",
    response_model=ExternalRiskSignalResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_WRITE],
)
async def create_risk_signal(
    body: CreateSignalRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ExternalRiskSignalResponse:
    from domain.enums import EntityStatus, RiskSignalType, SignalSeverity
    signal = await create_signal(
        signal_type=RiskSignalType(body.signal_type),
        severity=SignalSeverity(body.severity),
        description=body.description,
        source_name=body.source_name,
        source_version=body.source_version,
        observed_at=body.observed_at,
        organization_id=current_user.organization_id,
        session=session,
        dataset_id=body.dataset_id or "",
        country_code=body.country_code,
        sector_code=body.sector_code,
        supplier_id=body.supplier_id,
    )
    return _signal_to_response(signal)


# ── Enrichments ───────────────────────────────────────────────────────────────

@router.post(
    "/enrich",
    response_model=SupplierEnrichmentResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[_WRITE],
)
async def enrich_supplier_endpoint(
    body: EnrichSupplierRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SupplierEnrichmentResponse:
    enrichment = await enrich_supplier(
        supplier_id=body.supplier_id,
        organization_id=current_user.organization_id,
        country_code=body.country_code,
        sector_id=body.sector_id,
        nace_code=body.nace_code,
        internal_esg_score=body.internal_esg_score,
        session=session,
        dataset_version=body.dataset_version,
    )
    return _enrichment_to_response(enrichment)


@router.get(
    "/enrichments/{supplier_id}",
    response_model=SupplierEnrichmentResponse,
    dependencies=[_READ],
)
async def get_supplier_enrichment(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SupplierEnrichmentResponse:
    enrichment = await get_enrichment(supplier_id, current_user.organization_id, session)
    if enrichment is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Supplier enrichment not found")
    return _enrichment_to_response(enrichment)


@router.get(
    "/enrichments/high-risk",
    response_model=EnrichmentListResponse,
    dependencies=[_READ],
)
async def list_high_risk_supplier_enrichments(
    min_combined_risk: float = 60.0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EnrichmentListResponse:
    enrichments = await list_high_risk_suppliers(
        current_user.organization_id, session, min_combined_risk=min_combined_risk, limit=limit
    )
    return EnrichmentListResponse(
        enrichments=[_enrichment_to_response(e) for e in enrichments],
        total=len(enrichments),
    )


# ── Serialiser helpers ────────────────────────────────────────────────────────

def _dataset_to_response(d) -> ExternalDatasetResponse:
    return ExternalDatasetResponse(
        id=d.id,
        source_name=d.source_name.value if hasattr(d.source_name, "value") else d.source_name,
        source_version=d.source_version,
        dataset_hash=d.dataset_hash,
        imported_at=d.imported_at,
        row_count=d.row_count,
        dataset_status=d.dataset_status.value if hasattr(d.dataset_status, "value") else d.dataset_status,
        description=d.description,
        created_at=d.created_at,
    )


def _country_risk_to_response(p) -> CountryRiskResponse:
    return CountryRiskResponse(
        id=p.id,
        country_code=p.country_code,
        country_name=p.country_name,
        dataset_id=p.dataset_id,
        governance_score=p.governance_score,
        corruption_score=p.corruption_score,
        labour_rights_score=p.labour_rights_score,
        environmental_risk_score=p.environmental_risk_score,
        human_rights_score=p.human_rights_score,
        sanctions_status=p.sanctions_status,
        overall_risk_score=p.overall_risk_score,
        risk_level=p.risk_level.value if hasattr(p.risk_level, "value") else p.risk_level,
        source_name=p.source_name.value if hasattr(p.source_name, "value") else p.source_name,
        source_version=p.source_version,
        data_date=p.data_date,
        created_at=p.created_at,
    )


def _sector_benchmark_to_response(b) -> SectorBenchmarkResponse:
    return SectorBenchmarkResponse(
        id=b.id,
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
        source_name=b.source_name.value if hasattr(b.source_name, "value") else b.source_name,
        source_version=b.source_version,
        benchmark_date=b.benchmark_date,
        created_at=b.created_at,
    )


def _signal_to_response(s) -> ExternalRiskSignalResponse:
    return ExternalRiskSignalResponse(
        id=s.id,
        signal_type=s.signal_type.value if hasattr(s.signal_type, "value") else s.signal_type,
        severity=s.severity.value if hasattr(s.severity, "value") else s.severity,
        description=s.description,
        source_name=s.source_name.value if hasattr(s.source_name, "value") else s.source_name,
        source_version=s.source_version,
        observed_at=s.observed_at,
        dataset_id=s.dataset_id or None,
        country_code=s.country_code,
        sector_code=s.sector_code,
        supplier_id=s.supplier_id,
        organization_id=s.organization_id,
        is_active=s.is_active,
        created_at=s.created_at,
    )


def _enrichment_to_response(e) -> SupplierEnrichmentResponse:
    return SupplierEnrichmentResponse(
        id=e.id,
        supplier_id=e.supplier_id,
        organization_id=e.organization_id,
        country_code=e.country_code,
        country_risk_level=e.country_risk_level.value if hasattr(e.country_risk_level, "value") else e.country_risk_level,
        country_risk_score=e.country_risk_score,
        sanctions_exposure=e.sanctions_exposure.value if hasattr(e.sanctions_exposure, "value") else e.sanctions_exposure,
        sector_percentile=e.sector_percentile,
        percentile_rank=e.percentile_rank.value if hasattr(e.percentile_rank, "value") else e.percentile_rank,
        benchmark_score=e.benchmark_score,
        benchmark_explanation=e.benchmark_explanation,
        external_risk_score=e.external_risk_score,
        combined_risk_score=e.combined_risk_score,
        enriched_at=e.enriched_at,
        dataset_version=e.dataset_version,
        active_signal_count=e.active_signal_count,
    )
