"""
CSDDD Sector Risk Register API (TASK-003 Phase 6 + Phase 3 + Phase 4)

Endpoints:
  GET  /sector-risk-register/                           — list all calibrated sectors
  GET  /sector-risk-register/{nace_code}                — baseline scores for one sector
  GET  /sector-risk-register/{nace_code}/simulate       — scenario simulation
  GET  /sector-risk-register/scenarios/templates        — available scenario templates

  Phase 3 — RAG Calibration:
  POST /sector-risk-register/calibrate                  — start RAG calibration
  GET  /sector-risk-register/calibrate/suggestions      — list calibration suggestions
  POST /sector-risk-register/calibrate/{id}/approve     — approve suggestion
  POST /sector-risk-register/calibrate/{id}/reject      — reject suggestion

  Phase 4 — News Scenario Trigger:
  POST /sector-risk-register/scenarios/detect           — trigger news detection
  GET  /sector-risk-register/scenarios/suggestions      — list scenario suggestions
  POST /sector-risk-register/scenarios/suggestions/{id}/activate  — activate scenario
  POST /sector-risk-register/scenarios/suggestions/{id}/dismiss   — dismiss suggestion
"""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from application.sector_intelligence.base_matrix import (
    CALIBRATED_NACE_CODES,
    CALIBRATION_DATE,
    CALIBRATION_VERSION,
    get_scores,
    is_calibrated,
)
from application.sector_intelligence.nace_taxonomy import (
    ALL_NACE_2DIGIT_CODES,
    get_division_name,
    get_section,
)
from application.sector_intelligence.simulation_engine import ScenarioSimulationEngine
from domain.enums import CSDDDRight, ScenarioType
from interfaces.api.deps import get_db

router = APIRouter(prefix="/sector-risk-register", tags=["Sector Risk Register"])

_engine = ScenarioSimulationEngine()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class RightScoreResponse(BaseModel):
    right_id: str
    right_name: str
    probability: int = Field(..., ge=1, le=10)
    is_calibrated: bool
    scenario: ScenarioDeltaResponse | None = None


class ScenarioDeltaResponse(BaseModel):
    type: str
    name: str
    adjusted_probability: int = Field(..., ge=1, le=10)
    delta: int
    factor: float
    explanation: str


class SectorBaselineResponse(BaseModel):
    nace_code: str
    nace_section: str
    sector_name: str
    calibration_version: str
    calibration_date: str
    is_fully_calibrated: bool
    rights: list[RightScoreResponse]


class SectorListItemResponse(BaseModel):
    nace_code: str
    nace_section: str
    sector_name: str
    is_calibrated: bool
    highest_probability: int
    highest_right: str | None
    average_probability: float
    rights_above_7: int


class ScenarioTemplateResponse(BaseModel):
    scenario_type: str
    name: str
    description: str
    affected_nace_sections: list[str]
    sources: list[str]
    affected_rights_count: int


class SimulationResponse(BaseModel):
    nace_code: str
    sector_name: str
    scenario_type: str
    scenario_name: str
    calibration_version: str
    simulated_at: str
    rights: list[RightScoreResponse]
    summary: SimulationSummaryResponse


class SimulationSummaryResponse(BaseModel):
    rights_increased: int
    rights_above_7_baseline: int
    rights_above_7_scenario: int
    highest_risk_right: str | None
    highest_risk_score: int


# Rebuild for forward refs
RightScoreResponse.model_rebuild()
SimulationResponse.model_rebuild()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RIGHT_DISPLAY_NAMES: dict[CSDDDRight, str] = {
    CSDDDRight.CHILD_LABOUR: "Child Labour (ILO C138, C182)",
    CSDDDRight.FORCED_LABOUR: "Forced Labour (ILO C029, C105)",
    CSDDDRight.FREEDOM_OF_ASSOCIATION: "Freedom of Association (ILO C087)",
    CSDDDRight.COLLECTIVE_BARGAINING: "Collective Bargaining (ILO C098)",
    CSDDDRight.DISCRIMINATION: "Non-Discrimination (ILO C100, C111)",
    CSDDDRight.MINIMUM_WAGE: "Minimum Wage (ILO C131)",
    CSDDDRight.WORKING_HOURS: "Working Hours (ILO C001)",
    CSDDDRight.OCCUPATIONAL_SAFETY: "Occupational Safety (ILO C155, C187)",
    CSDDDRight.LAND_RIGHTS: "Land Rights (UNDRIP, VGGT)",
    CSDDDRight.WATER_RIGHTS: "Right to Water (UN A/RES/64/292)",
    CSDDDRight.ENVIRONMENTAL_DESTRUCTION: "Environmental Destruction",
    CSDDDRight.HARMFUL_CHEMICALS: "Harmful Chemicals (Stockholm/Rotterdam)",
    CSDDDRight.BIODIVERSITY: "Biodiversity (CBD)",
    CSDDDRight.MERCURY: "Mercury (Minamata Convention)",
    CSDDDRight.HAZARDOUS_WASTE: "Hazardous Waste (Basel Convention)",
    CSDDDRight.PRIVACY: "Right to Privacy (ICCPR Art. 17)",
    CSDDDRight.FREEDOM_OF_EXPRESSION: "Freedom of Expression (ICCPR Art. 19)",
    CSDDDRight.HUMAN_DIGNITY: "Human Dignity (UDHR Art. 1)",
    CSDDDRight.MODERN_SLAVERY: "Modern Slavery (Palermo Protocol)",
    CSDDDRight.MIGRANT_WORKER_RIGHTS: "Migrant Worker Rights (ICRMW)",
    CSDDDRight.COMMUNITY_RIGHTS: "Community Rights (ILO C169, UNDRIP)",
}


def _section_for(code: str) -> str:
    result = get_section(code)
    return result[0] if result else "?"


def _build_rights(scores: dict[CSDDDRight, int], calibrated: bool) -> list[RightScoreResponse]:
    return [
        RightScoreResponse(
            right_id=right.value,
            right_name=_RIGHT_DISPLAY_NAMES[right],
            probability=score,
            is_calibrated=calibrated,
        )
        for right, score in scores.items()
    ]


def _resolve_nace(raw: str) -> str:
    """Normalize and validate a NACE code, raise 404 if unknown."""
    from application.sector_intelligence.nace_taxonomy import normalize_nace

    code = normalize_nace(raw)
    if code is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown NACE code: '{raw}'. Use 2-digit codes like '29', '13', '01'.",
        )
    return code


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[SectorListItemResponse], summary="List calibrated sectors")
async def list_sectors(
    calibrated_only: bool = Query(False, description="Return only sectors with curated scores"),
) -> list[SectorListItemResponse]:
    """List all NACE sectors with summary risk indicators."""
    codes = CALIBRATED_NACE_CODES if calibrated_only else ALL_NACE_2DIGIT_CODES
    result = []
    for code in codes:
        scores = get_scores(code)
        sorted_scores = sorted(scores.values(), reverse=True)
        highest_score = sorted_scores[0] if sorted_scores else 1
        highest_right = next((r.value for r, s in scores.items() if s == highest_score), None)
        avg = round(sum(scores.values()) / len(scores), 1)
        above7 = sum(1 for s in scores.values() if s >= 7)
        result.append(
            SectorListItemResponse(
                nace_code=code,
                nace_section=_section_for(code),
                sector_name=get_division_name(code),
                is_calibrated=is_calibrated(code),
                highest_probability=highest_score,
                highest_right=highest_right,
                average_probability=avg,
                rights_above_7=above7,
            )
        )
    return result


@router.get(
    "/scenarios/templates",
    response_model=list[ScenarioTemplateResponse],
    summary="List available scenario templates",
)
async def list_scenario_templates() -> list[ScenarioTemplateResponse]:
    """Return all predefined scenario templates with their metadata."""
    return [
        ScenarioTemplateResponse(
            scenario_type=t.scenario_type.value,
            name=t.name,
            description=t.description,
            affected_nace_sections=t.affected_nace_sections,
            sources=t.sources,
            affected_rights_count=len(t.factors),
        )
        for t in _engine.available_templates()
    ]


@router.get(
    "/{nace_code}",
    response_model=SectorBaselineResponse,
    summary="Baseline CSDDD risk scores for a sector",
)
async def get_sector_baseline(nace_code: str) -> SectorBaselineResponse:
    """Return approved base probability scores for all 21 CSDDD rights in one sector."""
    code = _resolve_nace(nace_code)
    scores = get_scores(code)
    calibrated = is_calibrated(code)
    return SectorBaselineResponse(
        nace_code=code,
        nace_section=_section_for(code),
        sector_name=get_division_name(code),
        calibration_version=CALIBRATION_VERSION,
        calibration_date=CALIBRATION_DATE,
        is_fully_calibrated=calibrated,
        rights=_build_rights(scores, calibrated),
    )


@router.get(
    "/{nace_code}/simulate",
    response_model=SimulationResponse,
    summary="Scenario simulation for a sector",
)
async def simulate_scenario(
    nace_code: str,
    scenario: ScenarioType = Query(..., description="Scenario type to simulate"),
) -> SimulationResponse:
    """Apply a scenario to the sector baseline and return adjusted risk scores.

    Fully deterministic — same inputs always produce the same output (M43 compliant).
    """
    code = _resolve_nace(nace_code)
    result = _engine.simulate(code, scenario)

    rights_out: list[RightScoreResponse] = []
    for right in CSDDDRight:
        base = result.baseline_scores[right]
        adj = result.scenario_scores[right]
        delta = result.delta[right]
        from application.sector_intelligence.simulation_engine import _SCENARIO_TEMPLATES

        template = _SCENARIO_TEMPLATES[scenario]
        factor = template.factors.get(right, 1.0)
        rights_out.append(
            RightScoreResponse(
                right_id=right.value,
                right_name=_RIGHT_DISPLAY_NAMES[right],
                probability=base,
                is_calibrated=is_calibrated(code),
                scenario=ScenarioDeltaResponse(
                    type=scenario.value,
                    name=result.scenario_name,
                    adjusted_probability=adj,
                    delta=delta,
                    factor=factor,
                    explanation=result.explanation[right],
                ),
            )
        )

    above7_baseline = sum(1 for s in result.baseline_scores.values() if s >= 7)
    above7_scenario = sum(1 for s in result.scenario_scores.values() if s >= 7)
    top = _engine.highest_risk_rights(result, top_n=1)
    highest_right = top[0][0].value if top else None
    highest_score = top[0][1] if top else 1

    return SimulationResponse(
        nace_code=code,
        sector_name=result.sector_name,
        scenario_type=scenario.value,
        scenario_name=result.scenario_name,
        calibration_version=result.calibration_version,
        simulated_at=result.simulated_at,
        rights=rights_out,
        summary=SimulationSummaryResponse(
            rights_increased=sum(1 for d in result.delta.values() if d > 0),
            rights_above_7_baseline=above7_baseline,
            rights_above_7_scenario=above7_scenario,
            highest_risk_right=highest_right,
            highest_risk_score=highest_score,
        ),
    )


# ---------------------------------------------------------------------------
# Phase 3 — RAG Calibration endpoints
# ---------------------------------------------------------------------------


class CalibrateRequest(BaseModel):
    nace_code: str
    right: CSDDDRight


class CalibrationSuggestionResponse(BaseModel):
    id: str
    nace_code: str
    csddd_right: str
    suggested_probability: int
    confidence: str
    reasoning: str
    sources: list[str]
    status: str
    created_at: str


class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)


@router.post(
    "/calibrate",
    response_model=CalibrationSuggestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start RAG calibration for one sector × CSDDD right",
)
async def start_calibration(
    body: CalibrateRequest,
    session: AsyncSession = Depends(get_db),
) -> CalibrationSuggestionResponse:
    """Run RAG + Groq LLM to generate a score suggestion. Requires human approval."""
    code = _resolve_nace(body.nace_code)

    from application.sector_intelligence.rag_calibration import (
        SectorRiskCalibrationPipeline,
        save_suggestion,
    )
    from infrastructure.embeddings.deps import get_embedding_provider
    from infrastructure.knowledge_search import EvidenceChunkSearchAdapter
    from infrastructure.llm.deps import get_llm_provider
    from infrastructure.persistence.repositories.evidence_chunk import SQLEvidenceChunkRepository

    llm = get_llm_provider()
    chunk_repo = SQLEvidenceChunkRepository(session)
    embeddings = get_embedding_provider()
    search_adapter = EvidenceChunkSearchAdapter(chunk_repo, embeddings)

    pipeline = SectorRiskCalibrationPipeline(
        llm=llm,
        knowledge_search=search_adapter.search,
    )

    dto = await pipeline.calibrate(code, body.right)
    await save_suggestion(dto, session)

    return CalibrationSuggestionResponse(
        id=dto.id,
        nace_code=dto.nace_2digit,
        csddd_right=dto.csddd_right.value,
        suggested_probability=dto.suggested_probability,
        confidence=dto.confidence.value,
        reasoning=dto.reasoning,
        sources=dto.sources,
        status=dto.status.value,
        created_at=dto.created_at,
    )


@router.get(
    "/calibrate/suggestions",
    response_model=list[CalibrationSuggestionResponse],
    summary="List calibration suggestions",
)
async def list_calibration_suggestions(
    status_filter: str | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_db),
) -> list[CalibrationSuggestionResponse]:
    from application.sector_intelligence.rag_calibration import list_suggestions
    from domain.enums import CalibrationStatus

    status_enum = None
    if status_filter:
        try:
            status_enum = CalibrationStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status: {status_filter}")

    models = await list_suggestions(status_enum, session)
    return [
        CalibrationSuggestionResponse(
            id=m.id,
            nace_code=m.nace_2digit,
            csddd_right=m.csddd_right,
            suggested_probability=m.suggested_probability,
            confidence=m.confidence,
            reasoning=m.reasoning,
            sources=m.sources or [],
            status=m.status,
            created_at=m.created_at.isoformat() if m.created_at else "",
        )
        for m in models
    ]


@router.post(
    "/calibrate/{suggestion_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Approve a calibration suggestion (Founder only)",
)
async def approve_calibration(
    suggestion_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    from application.sector_intelligence.rag_calibration import approve_suggestion

    ok = await approve_suggestion(suggestion_id, reviewer_id="founder", session=session)
    if not ok:
        raise HTTPException(status_code=404, detail="Suggestion not found or not pending")
    return {"approved": True, "suggestion_id": suggestion_id}


@router.post(
    "/calibrate/{suggestion_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Reject a calibration suggestion",
)
async def reject_calibration(
    suggestion_id: str,
    body: RejectRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    from application.sector_intelligence.rag_calibration import reject_suggestion

    ok = await reject_suggestion(
        suggestion_id, reviewer_id="founder", reason=body.reason, session=session
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Suggestion not found or not pending")
    return {"rejected": True, "suggestion_id": suggestion_id}


# ---------------------------------------------------------------------------
# Phase 4 — News Scenario Trigger endpoints
# ---------------------------------------------------------------------------


class ScenarioSuggestionResponse(BaseModel):
    id: str
    scenario_type: str
    affected_nace_codes: list[str]
    trigger_article_count: int
    trigger_keywords_matched: list[str]
    sample_headlines: list[str]
    status: str
    created_at: str
    expires_at: str | None = None


class DetectRequest(BaseModel):
    organization_id: str
    lookback_days: int = Field(default=7, ge=1, le=30)


@router.post(
    "/scenarios/detect",
    response_model=list[ScenarioSuggestionResponse],
    status_code=status.HTTP_200_OK,
    summary="Trigger news-based scenario detection",
)
async def detect_scenarios(
    body: DetectRequest,
    session: AsyncSession = Depends(get_db),
) -> list[ScenarioSuggestionResponse]:
    """Scan recent news articles for scenario signals. Creates pending suggestions."""
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from application.sector_intelligence.news_scenario_detector import (
        NewsScenarioDetector,
        get_active_scenario_types,
        save_suggestions,
    )
    from infrastructure.persistence.models.news_feed import NewsArticleModel

    cutoff = datetime.now(UTC) - timedelta(days=body.lookback_days)
    result = await session.execute(
        select(NewsArticleModel)
        .where(
            NewsArticleModel.organization_id == body.organization_id,
            NewsArticleModel.fetched_at >= cutoff,
        )
        .limit(500)
    )
    articles = [
        {
            "title": a.title,
            "summary": a.summary,
            "translated_title": a.translated_title,
            "translated_summary": a.translated_summary,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "url": a.url,
        }
        for a in result.scalars().all()
    ]

    active_types = await get_active_scenario_types(session)
    detector = NewsScenarioDetector()
    suggestions = detector.detect(articles, existing_active_types=active_types)

    if suggestions:
        await save_suggestions(suggestions, session)

    return [
        ScenarioSuggestionResponse(
            id=s["id"],
            scenario_type=s["scenario_type"],
            affected_nace_codes=s["affected_nace_codes"],
            trigger_article_count=s["trigger_article_count"],
            trigger_keywords_matched=s["trigger_keywords_matched"],
            sample_headlines=s["sample_headlines"],
            status=s["status"],
            created_at=s["created_at"].isoformat(),
        )
        for s in suggestions
    ]


@router.get(
    "/scenarios/suggestions",
    response_model=list[ScenarioSuggestionResponse],
    summary="List scenario suggestions",
)
async def list_scenario_suggestions_endpoint(
    status_filter: str | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_db),
) -> list[ScenarioSuggestionResponse]:
    from application.sector_intelligence.news_scenario_detector import list_scenario_suggestions
    from domain.enums import ScenarioSuggestionStatus

    status_enum = None
    if status_filter:
        try:
            status_enum = ScenarioSuggestionStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status: {status_filter}")

    models = await list_scenario_suggestions(status_enum, session)
    return [
        ScenarioSuggestionResponse(
            id=m.id,
            scenario_type=m.scenario_type,
            affected_nace_codes=m.affected_nace_codes or [],
            trigger_article_count=m.trigger_article_count,
            trigger_keywords_matched=m.trigger_keywords_matched or [],
            sample_headlines=m.sample_headlines or [],
            status=m.status,
            created_at=m.created_at.isoformat() if m.created_at else "",
            expires_at=m.expires_at.isoformat() if m.expires_at else None,
        )
        for m in models
    ]


@router.post(
    "/scenarios/suggestions/{suggestion_id}/activate",
    status_code=status.HTTP_200_OK,
    summary="Activate a scenario suggestion (Founder only)",
)
async def activate_scenario(
    suggestion_id: str,
    expires_in_days: int = Query(default=30, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from application.sector_intelligence.news_scenario_detector import activate_suggestion

    ok = await activate_suggestion(
        suggestion_id,
        activator_id="founder",
        session=session,
        expires_in_days=expires_in_days,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Suggestion not found or not pending")
    return {"activated": True, "suggestion_id": suggestion_id}


@router.post(
    "/scenarios/suggestions/{suggestion_id}/dismiss",
    status_code=status.HTTP_200_OK,
    summary="Dismiss a scenario suggestion",
)
async def dismiss_scenario(
    suggestion_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    from application.sector_intelligence.news_scenario_detector import dismiss_suggestion

    ok = await dismiss_suggestion(suggestion_id, session=session)
    if not ok:
        raise HTTPException(status_code=404, detail="Suggestion not found or not pending")
    return {"dismissed": True, "suggestion_id": suggestion_id}
