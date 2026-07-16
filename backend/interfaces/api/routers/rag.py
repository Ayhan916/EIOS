"""RAG Knowledge Base API.

Endpoints:
  POST /rag/ingest          — embed all new news + events into vector store
  POST /rag/ingest-history  — Phase 4: embed intelligence events + CAPs into historical_knowledge
  POST /rag/search          — semantic search (dev/debug)
  POST /rag/analyze         — RAG-gestützte Frage-Antwort (DE)
  POST /rag/simulate        — hybride Szenario-Simulation
  GET  /rag/stats           — knowledge base statistics
  GET  /rag/history         — Phase 4: historische Lerneinträge für einen Lieferanten
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from application.rag.analyzer import analyze
from application.rag.historical_ingestion import ingest_historical_knowledge
from application.rag.historical_retrieval import retrieve_history
from application.rag.ingestion import run_full_ingestion
from application.rag.retrieval import retrieve
from application.rag.simulator import simulate
from domain.user import User
from infrastructure.persistence.models.historical_knowledge import HistoricalKnowledgeModel
from infrastructure.persistence.models.rag_documents import RagDocumentModel
from interfaces.api.deps import get_current_user, get_db

router = APIRouter(tags=["RAG Knowledge Base"])


class IngestResponse(BaseModel):
    news_articles: int
    intelligence_events: int
    total_new: int
    message: str


class SearchRequest(BaseModel):
    query: str
    supplier_id: str | None = None
    doc_types: list[str] | None = None
    top_k: int = 8


class SearchResult(BaseModel):
    id: str
    supplier_id: str | None
    doc_type: str
    content: str
    signal_type: str | None
    severity: str | None
    source_name: str | None
    published_at: str | None
    similarity: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query: str


class SimulateRequest(BaseModel):
    scenario_type: str
    supplier_id: str
    supplier_name: str


class AffectedRight(BaseModel):
    right_id: str
    right_name: str
    baseline: int
    adjusted: int
    delta: int


class SimulateResponse(BaseModel):
    scenario_type: str
    scenario_name: str
    supplier_name: str
    narrative: str
    top_affected_rights: list[AffectedRight]
    deterministic_ok: bool
    sources: list[AnalyzeSource]
    chunks_found: int
    model: str


class AnalyzeRequest(BaseModel):
    query: str
    supplier_id: str | None = None
    supplier_name: str | None = None
    top_k: int | None = None


class AnalyzeSource(BaseModel):
    rank: int
    doc_type: str
    source_type: str  # "news" | "intelligence" | "document" | "historical"
    content_preview: str
    severity: str | None
    source_name: str | None
    published_at: str | None
    similarity: float


class AnalyzeResponse(BaseModel):
    answer: str
    sources: list[AnalyzeSource]
    sources_breakdown: dict[str, int]  # {"news": 2, "intelligence": 1, "document": 3, "historical": 1}
    chunks_found: int
    model: str
    query: str


class KnowledgeBaseStats(BaseModel):
    total_documents: int
    news_articles: int
    intelligence_events: int
    suppliers_covered: int
    historical_entries: int = 0


class HistoricalIngestResponse(BaseModel):
    timeline_events_new: int
    timeline_events_skipped: int
    cap_findings_new: int
    cap_findings_skipped: int
    total_new: int
    message: str


class HistoricalEntry(BaseModel):
    id: str
    supplier_id: str | None
    event_description: str
    event_type: str
    event_severity: str | None
    countermeasure_description: str
    countermeasure_type: str
    outcome_description: str
    outcome_category: str
    health_delta: float | None
    csddd_right: str | None
    twin_dimension: str | None
    reference_date: str | None
    similarity: float | None = None


class HistoricalResponse(BaseModel):
    entries: list[HistoricalEntry]
    total: int


@router.post("/rag/ingest", response_model=IngestResponse)
async def ingest_knowledge_base(
    supplier_id: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Embed all new news articles and intelligence events into the vector knowledge base.

    Pass supplier_id to ingest only for a specific supplier.
    Skips already-ingested records automatically.
    """
    counts = await run_full_ingestion(
        organization_id=current_user.organization_id,
        session=session,
        supplier_id=supplier_id,
    )
    total = counts["news_articles"] + counts["intelligence_events"]
    return IngestResponse(
        news_articles=counts["news_articles"],
        intelligence_events=counts["intelligence_events"],
        total_new=total,
        message=(
            f"{total} neue Dokumente eingebettet "
            f"({counts['news_articles']} Nachrichten, "
            f"{counts['intelligence_events']} Intelligence-Events)."
        ),
    )


@router.post("/rag/search", response_model=SearchResponse)
async def search_knowledge_base(
    body: SearchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Semantic search over the RAG knowledge base."""
    results = await retrieve(
        query=body.query,
        organization_id=current_user.organization_id,
        session=session,
        supplier_id=body.supplier_id,
        doc_types=body.doc_types,
        top_k=body.top_k,
    )
    return SearchResponse(
        results=[SearchResult(**r) for r in results],
        total=len(results),
        query=body.query,
    )


@router.post("/rag/simulate", response_model=SimulateResponse)
async def simulate_scenario(
    body: SimulateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SimulateResponse:
    """Hybride Szenario-Simulation: deterministischer CSDDD-Impact + RAG-Narrativ.

    Kombiniert die bestehende SimulationEngine (NACE × ScenarioType) mit
    supplier-spezifischem LLM-Narrativ auf Basis historischer RAG-Quellen.
    """
    result = await simulate(
        scenario_type=body.scenario_type,
        organization_id=current_user.organization_id,
        session=session,
        supplier_id=body.supplier_id,
        supplier_name=body.supplier_name,
    )
    return SimulateResponse(
        scenario_type=result["scenario_type"],
        scenario_name=result["scenario_name"],
        supplier_name=result["supplier_name"],
        narrative=result["narrative"],
        top_affected_rights=[AffectedRight(**r) for r in result["top_affected_rights"]],
        deterministic_ok=result["deterministic_ok"],
        sources=[AnalyzeSource(**s) for s in result["sources"]],
        chunks_found=result["chunks_found"],
        model=result["model"],
    )


@router.post("/rag/analyze", response_model=AnalyzeResponse)
async def analyze_with_rag(
    body: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """Beantwortet eine Frage zu einem Lieferanten auf Basis des RAG Knowledge Base.

    Sucht semantisch relevante Dokumente und generiert eine deutsche Antwort via LLM.
    """
    from infrastructure.llm.deps import get_org_pipeline_settings
    pipe = await get_org_pipeline_settings(current_user.organization_id, session)
    effective_top_k = body.top_k if body.top_k is not None else pipe["top_k"]
    result = await analyze(
        query=body.query,
        organization_id=current_user.organization_id,
        session=session,
        supplier_id=body.supplier_id,
        supplier_name=body.supplier_name,
        top_k=effective_top_k,
    )
    return AnalyzeResponse(
        answer=result["answer"],
        sources=[AnalyzeSource(**s) for s in result["sources"]],
        sources_breakdown=result["sources_breakdown"],
        chunks_found=result["chunks_found"],
        model=result["model"],
        query=result["query"],
    )


@router.get("/rag/stats", response_model=KnowledgeBaseStats)
async def get_knowledge_base_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> KnowledgeBaseStats:
    """Return statistics about the current knowledge base."""
    org_id = current_user.organization_id

    total = (await session.execute(
        select(func.count()).where(RagDocumentModel.organization_id == org_id)
    )).scalar_one() or 0

    news = (await session.execute(
        select(func.count()).where(
            RagDocumentModel.organization_id == org_id,
            RagDocumentModel.doc_type == "news_article",
        )
    )).scalar_one() or 0

    events = (await session.execute(
        select(func.count()).where(
            RagDocumentModel.organization_id == org_id,
            RagDocumentModel.doc_type == "intelligence_event",
        )
    )).scalar_one() or 0

    suppliers = (await session.execute(
        select(func.count(func.distinct(RagDocumentModel.supplier_id))).where(
            RagDocumentModel.organization_id == org_id,
            RagDocumentModel.supplier_id.isnot(None),
        )
    )).scalar_one() or 0

    historical = (await session.execute(
        select(func.count()).where(HistoricalKnowledgeModel.organization_id == org_id)
    )).scalar_one() or 0

    return KnowledgeBaseStats(
        total_documents=total,
        news_articles=news,
        intelligence_events=events,
        suppliers_covered=suppliers,
        historical_entries=historical,
    )


@router.post("/rag/ingest-history", response_model=HistoricalIngestResponse)
async def ingest_history(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> HistoricalIngestResponse:
    """Phase 4 — Historisches Lernen: ingests intelligence events + closed CAPs.

    Erstellt Lerneinträge in historical_knowledge mit Embeddings.
    Neue Einträge werden übersprungen wenn bereits vorhanden.
    """
    result = await ingest_historical_knowledge(
        organization_id=current_user.organization_id,
        session=session,
    )
    return HistoricalIngestResponse(**result)


@router.get("/rag/history", response_model=HistoricalResponse)
async def get_history(
    supplier_id: str | None = Query(default=None),
    csddd_right: str | None = Query(default=None),
    query: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> HistoricalResponse:
    """Phase 4 — Lernhistorie abrufen.

    Ohne query: chronologisch neueste Einträge.
    Mit query: semantische Suche (RAG) in historical_knowledge.
    """
    org_id = current_user.organization_id

    if query:
        entries = await retrieve_history(
            query=query,
            organization_id=org_id,
            session=session,
            supplier_id=supplier_id,
            csddd_right=csddd_right,
            top_k=limit,
        )
        return HistoricalResponse(
            entries=[HistoricalEntry(**e) for e in entries],
            total=len(entries),
        )

    # Chronologisch ohne semantische Suche
    filters = [HistoricalKnowledgeModel.organization_id == org_id]
    if supplier_id:
        from sqlalchemy import or_
        filters.append(
            or_(
                HistoricalKnowledgeModel.supplier_id == supplier_id,
                HistoricalKnowledgeModel.supplier_id.is_(None),
            )
        )
    if csddd_right:
        filters.append(HistoricalKnowledgeModel.csddd_right == csddd_right)

    result = await session.execute(
        select(HistoricalKnowledgeModel)
        .where(*filters)
        .order_by(HistoricalKnowledgeModel.reference_date.desc().nullslast())
        .limit(limit)
    )
    rows = result.scalars().all()

    total_count = (await session.execute(
        select(func.count(HistoricalKnowledgeModel.id)).where(*filters)
    )).scalar_one() or 0

    return HistoricalResponse(
        entries=[
            HistoricalEntry(
                id=r.id,
                supplier_id=r.supplier_id,
                event_description=r.event_description,
                event_type=r.event_type,
                event_severity=r.event_severity,
                countermeasure_description=r.countermeasure_description,
                countermeasure_type=r.countermeasure_type,
                outcome_description=r.outcome_description,
                outcome_category=r.outcome_category,
                health_delta=r.health_delta,
                csddd_right=r.csddd_right,
                twin_dimension=r.twin_dimension,
                reference_date=r.reference_date.isoformat() if r.reference_date else None,
            )
            for r in rows
        ],
        total=total_count,
    )
