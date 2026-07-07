"""
EvidenceLinkingService — M25

After findings are extracted from agent text, this service creates
FindingEvidenceLink records by matching each finding against the
knowledge chunks that were retrieved during the workflow run.

Matching algorithm (bag-of-words Jaccard + semantic score):
  1. Tokenize finding title + description + reasoning into a word set
  2. For each retrieved chunk, tokenize its text into a word set
  3. Jaccard = |A ∩ B| / |A ∪ B|
  4. final_score = jaccard * 0.6 + chunk.similarity_score * 0.4
  5. Take top MAX_LINKS_PER_FINDING chunks per finding where score > THRESHOLD

Evidence strength formula (per finding):
  - base_score = min(link_count, 5) / 5 * 0.4
  - conf_score = mean(confidence_scores) * 0.4
  - diversity   = min(distinct_evidence_docs, 3) / 3 * 0.2
  - total in [0, 1] → Weak / Moderate / Strong / Very Strong
"""

from __future__ import annotations

from domain.enums import EntityStatus, EvidenceStrength
from domain.finding import Finding
from domain.finding_evidence_link import FindingEvidenceLink

_MAX_LINKS_PER_FINDING = 5
_SCORE_THRESHOLD = 0.04  # minimum combined score to create a link

_STOP_WORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "in",
        "on",
        "at",
        "to",
        "of",
        "for",
        "with",
        "by",
        "and",
        "or",
        "but",
        "not",
        "this",
        "that",
        "it",
        "as",
        "its",
        "be",
        "been",
        "has",
        "have",
        "had",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "from",
    ]
)


def _tokenize(text: str) -> frozenset[str]:
    words = text.lower().split()
    return frozenset(
        w.strip(".,;:!?\"'()[]{}") for w in words if len(w) > 2 and w not in _STOP_WORDS
    )


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _excerpt(text: str, max_chars: int = 400) -> str:
    """Return a trimmed excerpt suitable for citation display."""
    cleaned = " ".join(text.split())
    return cleaned[:max_chars] + ("..." if len(cleaned) > max_chars else "")


def create_finding_evidence_links(
    findings: list[Finding],
    retrieved_chunks: list[dict],
    created_by: str | None = None,
) -> list[FindingEvidenceLink]:
    """Create FindingEvidenceLink domain objects for a set of findings.

    `retrieved_chunks` is the list of serialised RetrievedChunkMeta dicts
    stored in workflow_run.run_metadata["retrieved_chunks"].

    Returns a flat list of links. Callers persist them and then call
    `update_finding_evidence_strength()` to update Finding fields.
    """
    if not retrieved_chunks or not findings:
        return []

    # Pre-tokenize all chunks once
    chunk_tokens: list[frozenset[str]] = [_tokenize(c.get("text", "")) for c in retrieved_chunks]

    links: list[FindingEvidenceLink] = []

    for finding in findings:
        finding_text = f"{finding.title} {finding.description} {finding.reasoning or ''}"
        finding_tokens = _tokenize(finding_text)

        scored: list[tuple[float, int]] = []
        for i, chunk in enumerate(retrieved_chunks):
            jaccard = _jaccard(finding_tokens, chunk_tokens[i])
            semantic = float(chunk.get("similarity_score", 0.0))
            score = jaccard * 0.6 + semantic * 0.4
            if score >= _SCORE_THRESHOLD:
                scored.append((score, i))

        # Take top N by score
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:_MAX_LINKS_PER_FINDING]

        for score, idx in top:
            chunk = retrieved_chunks[idx]
            link = FindingEvidenceLink(
                finding_id=finding.id,
                evidence_id=chunk["evidence_id"],
                evidence_chunk_id=chunk.get("chunk_id"),
                page_number=chunk.get("page_number"),
                confidence_score=round(score, 4),
                supporting_excerpt=_excerpt(chunk.get("text", "")),
                link_method="auto",
                status=EntityStatus.ACTIVE,
                created_by=created_by,
            )
            links.append(link)

    return links


def compute_evidence_strength(links: list[FindingEvidenceLink]) -> EvidenceStrength | None:
    """Compute a strength label from the evidence links for one finding."""
    if not links:
        return None

    count = len(links)
    scores = [l.confidence_score for l in links if l.confidence_score is not None]
    avg_conf = sum(scores) / len(scores) if scores else 0.5
    distinct_docs = len({l.evidence_id for l in links})

    base_score = min(count, 5) / 5 * 0.4
    conf_score = avg_conf * 0.4
    diversity_score = min(distinct_docs, 3) / 3 * 0.2
    total = base_score + conf_score + diversity_score

    if total >= 0.75:
        return EvidenceStrength.VERY_STRONG
    if total >= 0.55:
        return EvidenceStrength.STRONG
    if total >= 0.30:
        return EvidenceStrength.MODERATE
    return EvidenceStrength.WEAK


def update_finding_evidence_strength(
    finding: Finding,
    links: list[FindingEvidenceLink],
) -> None:
    """Mutate finding in-place to set evidence_strength and evidence_source_count."""
    finding.evidence_strength = compute_evidence_strength(links)
    finding.evidence_source_count = len({l.evidence_id for l in links})
