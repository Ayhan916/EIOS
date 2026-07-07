"""RAG Ingestion Service — reads existing data, embeds, stores in rag_documents.

Sources:
  1. news_articles           → doc_type="news_article"
  2. intelligence_timeline_events → doc_type="intelligence_event"

Each source record becomes one document chunk.
Already-ingested records are skipped (uq_rag_source constraint).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.news_feed import NewsArticleModel
from infrastructure.persistence.models.rag_documents import RagDocumentModel
from infrastructure.persistence.models.supplier_digital_twin import (
    IntelligenceTimelineEventModel,
)

from .embedder import embed_passages_batch

logger = structlog.get_logger(__name__)


def _news_to_content(article: NewsArticleModel) -> str:
    """Build a rich text chunk from a news article."""
    title = article.translated_title or article.title or ""
    summary = article.translated_summary or article.summary or ""
    source = article.source_name or ""
    parts = [title]
    if source:
        parts.append(f"Quelle: {source}")
    if summary:
        parts.append(summary)
    return " | ".join(p for p in parts if p)


def _event_to_content(event: IntelligenceTimelineEventModel) -> str:
    """Build a rich text chunk from an intelligence timeline event."""
    parts = [
        event.title or "",
        event.summary or "",
        event.why_important or "",
        event.regulatory_impact or "",
        event.recommended_action or "",
    ]
    return " | ".join(p for p in parts if p)


async def ingest_news_articles(
    organization_id: str,
    session: AsyncSession,
    supplier_id: str | None = None,
) -> int:
    """Ingest news_articles into rag_documents. Returns count of newly added docs."""
    from infrastructure.persistence.models.news_feed import NewsSupplierAssignmentModel

    # Load articles not yet in rag_documents
    existing_ids_stmt = select(RagDocumentModel.source_id).where(
        RagDocumentModel.organization_id == organization_id,
        RagDocumentModel.doc_type == "news_article",
    )
    existing_ids = set((await session.execute(existing_ids_stmt)).scalars().all())

    stmt = select(NewsArticleModel).where(
        NewsArticleModel.organization_id == organization_id
    )
    articles = (await session.execute(stmt)).scalars().all()
    new_articles = [a for a in articles if a.id not in existing_ids]

    if not new_articles:
        return 0

    # Load supplier assignments for batch
    article_ids = [a.id for a in new_articles]
    assign_stmt = select(NewsSupplierAssignmentModel).where(
        NewsSupplierAssignmentModel.article_id.in_(article_ids),
        NewsSupplierAssignmentModel.organization_id == organization_id,
    )
    assignments = (await session.execute(assign_stmt)).scalars().all()
    article_to_supplier: dict[str, str] = {a.article_id: a.supplier_id for a in assignments}

    # Filter by supplier_id if requested
    if supplier_id:
        new_articles = [a for a in new_articles if article_to_supplier.get(a.id) == supplier_id]

    if not new_articles:
        return 0

    # Batch embed
    contents = [_news_to_content(a) for a in new_articles]
    embeddings = embed_passages_batch(contents)

    now = datetime.now(UTC)
    count = 0
    for article, content, embedding in zip(new_articles, contents, embeddings):
        sup_id = article_to_supplier.get(article.id)
        doc = RagDocumentModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            supplier_id=sup_id,
            doc_type="news_article",
            source_id=article.id,
            content=content,
            embedding=embedding,
            language=article.language or "en",
            source_name=article.source_name,
            published_at=article.published_at,
            created_at=now,
        )
        session.add(doc)
        count += 1

    logger.info("rag_ingestion.news_done", org=organization_id, count=count)
    return count


async def ingest_intelligence_events(
    organization_id: str,
    session: AsyncSession,
    supplier_id: str | None = None,
) -> int:
    """Ingest intelligence_timeline_events into rag_documents."""
    existing_ids_stmt = select(RagDocumentModel.source_id).where(
        RagDocumentModel.organization_id == organization_id,
        RagDocumentModel.doc_type == "intelligence_event",
    )
    existing_ids = set((await session.execute(existing_ids_stmt)).scalars().all())

    stmt = select(IntelligenceTimelineEventModel).where(
        IntelligenceTimelineEventModel.organization_id == organization_id,
        IntelligenceTimelineEventModel.is_active == True,  # noqa: E712
    )
    if supplier_id:
        stmt = stmt.where(IntelligenceTimelineEventModel.supplier_id == supplier_id)

    events = (await session.execute(stmt)).scalars().all()
    new_events = [e for e in events if e.id not in existing_ids]

    if not new_events:
        return 0

    contents = [_event_to_content(e) for e in new_events]
    embeddings = embed_passages_batch(contents)

    now = datetime.now(UTC)
    count = 0
    for event, content, embedding in zip(new_events, contents, embeddings):
        doc = RagDocumentModel(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            supplier_id=event.supplier_id,
            doc_type="intelligence_event",
            source_id=event.id,
            content=content,
            embedding=embedding,
            language="de",
            signal_type=event.event_type,
            severity=event.severity,
            source_name=event.source_name,
            published_at=event.occurred_at,
            created_at=now,
        )
        session.add(doc)
        count += 1

    logger.info("rag_ingestion.events_done", org=organization_id, count=count)
    return count


async def run_full_ingestion(
    organization_id: str,
    session: AsyncSession,
    supplier_id: str | None = None,
) -> dict[str, int]:
    """Ingest all available sources into the RAG knowledge base."""
    news_count = await ingest_news_articles(organization_id, session, supplier_id)
    event_count = await ingest_intelligence_events(organization_id, session, supplier_id)
    await session.commit()
    return {"news_articles": news_count, "intelligence_events": event_count}
