"""Copilot Quality Filter — Intelligence Stufe 2.

Filters and re-ranks retrieval results before context assembly:
1. Remove near-duplicate chunks (same leading 120 chars)
2. Enforce per-document diversity (max 3 chunks per document_file_id)
3. Minimum content quality (too short → drop)
4. Re-rank by similarity + diversity score
"""

from __future__ import annotations

from .retrieval.base import RetrievalResult

_MIN_WORDS = 15
_MAX_CHUNKS_PER_DOC = 3
_DEDUP_PREFIX_LEN = 120


def filter_and_rank(results: list[RetrievalResult]) -> list[RetrievalResult]:
    """Apply quality filtering to each retrieval result in-place (returns new list)."""
    filtered = []
    for result in results:
        if result.retriever == "document_retriever":
            result = _filter_document_result(result)
        filtered.append(result)
    return filtered


def _filter_document_result(result: RetrievalResult) -> RetrievalResult:
    chunks = result.data

    # 1. Drop chunks that are too short to be useful
    chunks = [c for c in chunks if len(c.get("content", "").split()) >= _MIN_WORDS]

    # 2. Deduplicate: if two chunks share the same leading prefix, keep the higher-similarity one
    seen_prefixes: dict[str, dict] = {}
    for chunk in sorted(chunks, key=lambda c: c.get("similarity", 0), reverse=True):
        prefix = chunk.get("content", "")[:_DEDUP_PREFIX_LEN].strip().lower()
        if prefix not in seen_prefixes:
            seen_prefixes[prefix] = chunk
    chunks = list(seen_prefixes.values())

    # 3. Diversity cap: max N chunks per source document
    per_doc: dict[str, list[dict]] = {}
    for chunk in sorted(chunks, key=lambda c: c.get("similarity", 0), reverse=True):
        doc_id = str(chunk.get("source_id") or chunk.get("id") or "")
        # Use first 36 chars of id as document grouping key (UUID prefix)
        doc_key = doc_id[:36] if len(doc_id) >= 8 else doc_id
        if len(per_doc.get(doc_key, [])) < _MAX_CHUNKS_PER_DOC:
            per_doc.setdefault(doc_key, []).append(chunk)

    chunks = [c for group in per_doc.values() for c in group]

    # 4. Re-sort by similarity descending
    chunks.sort(key=lambda c: c.get("similarity", 0), reverse=True)

    if not chunks:
        return RetrievalResult(
            retriever=result.retriever,
            provenance=result.provenance,
            data=[],
            source_ids=[],
            citation_type=result.citation_type,
            freshness_metadata=[],
            context_text=None,
        )

    # Rebuild source_ids and context_text from filtered chunks
    source_ids = [c.get("id", "") for c in chunks]
    text_sections = []
    for d in chunks:
        header = f"[Document:{d['id']}] {d.get('company_name') or ''} {d.get('report_year') or ''} ({d.get('doc_type','')})"
        content = d.get("content", "")
        sim = d.get("similarity", 0)
        text_sections.append(f"{header} [sim={sim:.2f}]\n{content}")
    context_text = "\n\n".join(text_sections)

    removed = len(result.data) - len(chunks)
    provenance = result.provenance
    if removed > 0:
        provenance += f" (filtered: -{removed} low-quality/duplicate chunks)"

    return RetrievalResult(
        retriever=result.retriever,
        provenance=provenance,
        data=chunks,
        source_ids=source_ids,
        citation_type=result.citation_type,
        freshness_metadata=[
            fm for fm in result.freshness_metadata
            if fm.get("object_id") in set(source_ids)
        ],
        context_text=context_text,
    )
