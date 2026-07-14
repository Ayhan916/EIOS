"""E5-F1 / E5-F2 / E5-F3 — Risk Score Explainability, AuditPackage, Supply Chain Graph.

Endpoints:
  GET /suppliers/{supplier_id}/risk-score/explanation
      Returns factor breakdown of the supplier's latest composite risk score.

  GET /suppliers/{supplier_id}/audit-package
      Assembles and returns a complete AuditPackage for the given period.

  GET /suppliers/{supplier_id}/supply-chain-graph
      BFS-expanded Tier-2/3 supply chain graph with per-tier risk exposure.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel as _BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.audit_package_service import AuditPackageService
from application.supply_chain.graph_service import SupplyChainGraphService
from application.scoring.explainability_service import (
    ExplainabilityService,
    FactorExplanation,
    RiskScoreExplanation,
)
from application.scoring.risk_score_calculator import calculate
from application.scoring.supplier_scorer import ScoreInputs
from domain.user import User
from infrastructure.persistence.models.supplier import SupplierModel
from infrastructure.persistence.models.supplier_score import SupplierScoreModel
from interfaces.api.deps import get_current_user, get_db
from shared.config import settings

router = APIRouter(prefix="/suppliers", tags=["explainability"])

_explainability = ExplainabilityService()


# ── Response schemas ──────────────────────────────────────────────────────────


class FactorExplanationResponse(_BaseModel):
    factor: str
    label: str
    count: int
    weight: float
    contribution: float
    pct_of_total: float
    impact: str


class RiskScoreExplanationResponse(_BaseModel):
    composite_score: float
    band: str
    formula_version: str
    factors: list[FactorExplanationResponse]
    top_drivers: list[FactorExplanationResponse]
    confidence_level: str
    confidence_score: float
    confidence_basis: str
    limitations: list[str]


class MethodologyResponse(_BaseModel):
    formula_version: str
    extraction_model: str
    main_model: str
    active_prompt_names: list[str]


class AuditPackageResponse(_BaseModel):
    package_id: str
    supplier_id: str
    period_from: datetime
    period_to: datetime
    generated_at: datetime
    generator_version: str
    methodology: MethodologyResponse
    assessment_ids: list[str]
    findings_count: int
    risks_count: int
    evidence_count: int
    audit_event_count: int
    risk_score: float
    risk_band: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _factor_resp(fe: FactorExplanation) -> FactorExplanationResponse:
    return FactorExplanationResponse(
        factor=fe.factor,
        label=fe.label,
        count=fe.count,
        weight=fe.weight,
        contribution=fe.contribution,
        pct_of_total=fe.pct_of_total,
        impact=fe.impact,
    )


async def _assert_supplier_access(
    supplier_id: str,
    session: AsyncSession,
    user: User,
) -> SupplierModel:
    row = await session.get(SupplierModel, supplier_id)
    if not row or row.status == "Deleted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    if row.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return row


# ── E5-F1: Risk Score Explanation ─────────────────────────────────────────────


@router.get(
    "/{supplier_id}/risk-score/explanation",
    response_model=RiskScoreExplanationResponse,
    summary="Risk score factor breakdown for a supplier (E5-F1)",
)
async def get_risk_score_explanation(
    supplier_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RiskScoreExplanationResponse:
    """Return the full factor breakdown of the supplier's latest composite risk score."""
    await _assert_supplier_access(supplier_id, session, current_user)

    latest = (
        await session.execute(
            select(SupplierScoreModel)
            .where(SupplierScoreModel.supplier_id == supplier_id)
            .order_by(SupplierScoreModel.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if not latest or not latest.inputs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk score found for this supplier. Run a score calculation first.",
        )

    inp = latest.inputs
    score_inputs = ScoreInputs(
        total_assessments=inp.get("total_assessments", 0),
        approved_assessments=inp.get("approved_assessments", 0),
        critical_findings=inp.get("critical_findings", 0),
        high_findings=inp.get("high_findings", 0),
        medium_findings=inp.get("medium_findings", 0),
        low_findings=inp.get("low_findings", 0),
        critical_risks=inp.get("critical_risks", 0),
        high_risks=inp.get("high_risks", 0),
        medium_risks=inp.get("medium_risks", 0),
        overdue_actions=inp.get("overdue_actions", 0),
        open_actions=inp.get("open_actions", 0),
    )

    risk_score = calculate(score_inputs)
    explanation = _explainability.explain(risk_score)

    return RiskScoreExplanationResponse(
        composite_score=explanation.composite_score,
        band=explanation.band,
        formula_version=explanation.formula_version,
        factors=[_factor_resp(f) for f in explanation.factors],
        top_drivers=[_factor_resp(f) for f in explanation.top_drivers],
        confidence_level=explanation.confidence_level,
        confidence_score=explanation.confidence_score,
        confidence_basis=explanation.confidence_basis,
        limitations=list(explanation.limitations),
    )


# ── E5-F2: Audit Package ──────────────────────────────────────────────────────


@router.get(
    "/{supplier_id}/audit-package",
    response_model=AuditPackageResponse,
    summary="Generate a complete AuditPackage for a supplier (E5-F2)",
)
async def get_audit_package(
    supplier_id: str,
    period_from: datetime = Query(..., description="Start of audit period (ISO 8601)"),
    period_to: datetime = Query(..., description="End of audit period (ISO 8601)"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditPackageResponse:
    """Assemble a complete AuditPackage with methodology snapshot and evidence counts."""
    await _assert_supplier_access(supplier_id, session, current_user)

    if period_from >= period_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="period_from must be before period_to",
        )

    service = AuditPackageService(
        session=session,
        extraction_model=settings.extraction_llm_model,
        main_model=settings.llm_model,
    )
    pkg = await service.generate(supplier_id, period_from, period_to)

    return AuditPackageResponse(
        package_id=pkg.package_id,
        supplier_id=pkg.supplier_id,
        period_from=pkg.period_from,
        period_to=pkg.period_to,
        generated_at=pkg.generated_at,
        generator_version=pkg.generator_version,
        methodology=MethodologyResponse(
            formula_version=pkg.methodology.formula_version,
            extraction_model=pkg.methodology.extraction_model,
            main_model=pkg.methodology.main_model,
            active_prompt_names=list(pkg.methodology.active_prompt_names),
        ),
        assessment_ids=list(pkg.assessment_ids),
        findings_count=pkg.findings_count,
        risks_count=pkg.risks_count,
        evidence_count=pkg.evidence_count,
        audit_event_count=pkg.audit_event_count,
        risk_score=pkg.risk_score,
        risk_band=pkg.risk_band,
    )


# ── E5-F3: Supply Chain Graph ─────────────────────────────────────────────────


class TierExposureResponse(_BaseModel):
    tier: int
    supplier_count: int
    avg_risk_score: float
    max_risk_score: float
    critical_count: int
    high_count: int


class SupplyChainNodeResponse(_BaseModel):
    supplier_id: str
    name: str
    tier: int
    risk_score: float
    risk_band: str


class SupplyChainEdgeResponse(_BaseModel):
    buyer_id: str
    supplier_id: str
    tier: int
    commodity_code: str
    confidence: float


class SupplyChainGraphResponse(_BaseModel):
    root_supplier_id: str
    nodes: list[SupplyChainNodeResponse]
    edges: list[SupplyChainEdgeResponse]
    tier_exposure: dict[int, TierExposureResponse]
    aggregated_risk_score: float
    max_tier_reached: int


@router.get(
    "/{supplier_id}/supply-chain-graph",
    response_model=SupplyChainGraphResponse,
    summary="BFS-expanded supply chain graph for Tier-2/3 risk exposure (E5-F3)",
)
async def get_supply_chain_graph(
    supplier_id: str,
    max_tier: int = Query(default=3, ge=1, le=5, description="Maximum tier depth to traverse"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SupplyChainGraphResponse:
    """Return the BFS-expanded supply chain graph with per-tier risk aggregation."""
    await _assert_supplier_access(supplier_id, session, current_user)

    svc = SupplyChainGraphService(session)
    graph = await svc.build_graph(supplier_id, max_tier=max_tier)

    return SupplyChainGraphResponse(
        root_supplier_id=graph.root_supplier_id,
        nodes=[
            SupplyChainNodeResponse(
                supplier_id=n.supplier_id,
                name=n.name,
                tier=n.tier,
                risk_score=n.risk_score,
                risk_band=n.risk_band,
            )
            for n in graph.nodes.values()
        ],
        edges=[
            SupplyChainEdgeResponse(
                buyer_id=e.buyer_id,
                supplier_id=e.supplier_id,
                tier=e.tier,
                commodity_code=e.commodity_code,
                confidence=e.confidence,
            )
            for e in graph.edges
        ],
        tier_exposure={
            tier: TierExposureResponse(
                tier=te.tier,
                supplier_count=te.supplier_count,
                avg_risk_score=te.avg_risk_score,
                max_risk_score=te.max_risk_score,
                critical_count=te.critical_count,
                high_count=te.high_count,
            )
            for tier, te in graph.tier_exposure.items()
        },
        aggregated_risk_score=graph.aggregated_risk_score,
        max_tier_reached=graph.max_tier_reached,
    )
