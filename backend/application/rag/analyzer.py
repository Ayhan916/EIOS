"""RAG Analyse-Service — beantwortet Fragen mit Kontext aus dem Vector Store.

Ablauf:
  1. Semantische Suche (retrieve) → relevante Dokumente
  2. Kontext aufbauen aus den Top-k Chunks
  3. LLM-Prompt mit Kontext → strukturierte Antwort auf Deutsch
  4. Quellen zurückgeben (Transparenz / Audit Trail)
"""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .retrieval import retrieve

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """Du bist ein spezialisierter Lieferketten-Risikoanalyst für EIOS.
Du analysierst externe Intelligence-Daten (Nachrichten, Sanktionen, Risikoereignisse)
zu Lieferanten und beantwortest Fragen auf Basis der bereitgestellten Quellen.

Regeln:
- Antworte IMMER auf Deutsch
- Beziehe dich NUR auf die bereitgestellten Quelltexte — erfinde keine Fakten
- Wenn die Quellen keine Antwort liefern, sage das klar
- Sei konkret, präzise und handlungsorientiert
- Nenne relevante Regulierungen (LkSG, CSDDD, CSRD) wenn passend
- Formatiere die Antwort übersichtlich (Absätze, Aufzählungen)"""


def _build_context(chunks: list[dict]) -> str:
    """Formatiert die abgerufenen Chunks als lesbaren Kontext für den LLM-Prompt."""
    if not chunks:
        return "Keine relevanten Quellen gefunden."

    lines = []
    for i, chunk in enumerate(chunks, 1):
        meta_parts = []
        if chunk.get("doc_type") == "news_article":
            meta_parts.append("Nachricht")
        elif chunk.get("doc_type") == "intelligence_event":
            meta_parts.append("Intelligence-Event")
        if chunk.get("severity"):
            meta_parts.append(f"Schweregrad: {chunk['severity']}")
        if chunk.get("published_at"):
            meta_parts.append(chunk["published_at"][:10])
        if chunk.get("source_name"):
            meta_parts.append(chunk["source_name"])

        meta = " | ".join(meta_parts)
        lines.append(f"[Quelle {i}] {meta}")
        lines.append(chunk["content"])
        lines.append("")

    return "\n".join(lines)


async def analyze(
    query: str,
    organization_id: str,
    session: AsyncSession,
    supplier_id: str | None = None,
    supplier_name: str | None = None,
    top_k: int = 6,
) -> dict:
    """Beantwortet eine Frage zum Lieferanten via RAG + LLM.

    Gibt zurück:
      answer       — LLM-generierte Antwort auf Deutsch
      sources      — Liste der verwendeten Quellen (für Transparenz)
      chunks_found — Anzahl relevanter Chunks gefunden
      model        — verwendetes LLM-Modell
    """
    # 1. Relevante Dokumente abrufen
    chunks = await retrieve(
        query=query,
        organization_id=organization_id,
        session=session,
        supplier_id=supplier_id,
        top_k=top_k,
        min_similarity=0.25,
    )

    # 2. Kontext aufbauen
    context = _build_context(chunks)

    # 3. Prompt zusammenstellen
    supplier_ctx = f" zu Lieferant '{supplier_name}'" if supplier_name else ""
    user_prompt = (
        f"Frage{supplier_ctx}: {query}\n\n"
        f"Verfügbare Quellen:\n{context}\n\n"
        f"Bitte beantworte die Frage auf Basis der obigen Quellen."
    )

    # 4. LLM aufrufen
    answer = ""
    model_used = "unbekannt"
    try:
        from application.ports.llm import Message
        from infrastructure.llm.deps import get_llm_provider

        llm = get_llm_provider()
        model_used = llm.model_name()

        response = await llm.complete(
            messages=[Message(role="user", content=user_prompt)],
            system=_SYSTEM_PROMPT,
            max_tokens=1024,
            temperature=0.1,
        )
        answer = response.content.strip()

    except Exception as exc:
        logger.warning("rag_analyze.llm_failed", error=str(exc))
        if chunks:
            answer = (
                f"LLM nicht verfügbar. Gefundene Quellen ({len(chunks)}):\n\n"
                + "\n\n".join(f"• {c['content'][:200]}" for c in chunks)
            )
        else:
            answer = "Keine relevanten Informationen gefunden und LLM nicht verfügbar."

    # 5. Quellen aufbereiten
    sources = [
        {
            "rank": i + 1,
            "doc_type": c["doc_type"],
            "content_preview": c["content"][:120] + "…" if len(c["content"]) > 120 else c["content"],
            "severity": c.get("severity"),
            "source_name": c.get("source_name"),
            "published_at": c.get("published_at", "")[:10] if c.get("published_at") else None,
            "similarity": c["similarity"],
        }
        for i, c in enumerate(chunks)
    ]

    logger.info(
        "rag_analyze.done",
        org=organization_id,
        supplier_id=supplier_id,
        chunks=len(chunks),
        model=model_used,
    )

    return {
        "answer": answer,
        "sources": sources,
        "chunks_found": len(chunks),
        "model": model_used,
        "query": query,
    }
