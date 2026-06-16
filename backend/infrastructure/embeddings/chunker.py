"""
Text chunking utility for the EIOS Knowledge Layer.

Splits text into overlapping chunks at sentence boundaries.
Used during evidence ingestion to prepare text for embedding.
"""

import re


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on .!? boundaries."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def chunk_text(text: str, max_chars: int = 512, overlap_chars: int = 50) -> list[str]:
    """
    Split text into overlapping chunks at sentence boundaries.

    Each chunk is at most max_chars characters. When a sentence would push the
    chunk over the limit, the current chunk is finalised and a new one begins
    with overlap_chars of context carried forward.
    """
    if not text or not text.strip():
        return []

    sentences = _split_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        if sentence_len > max_chars:
            # Long sentence: flush current chunk, then hard-split the sentence
            if current_parts:
                chunks.append(" ".join(current_parts))
                current_parts = []
                current_len = 0
            for i in range(0, sentence_len, max_chars - overlap_chars):
                chunks.append(sentence[i : i + max_chars])
            continue

        if current_len + sentence_len + (1 if current_parts else 0) > max_chars:
            chunks.append(" ".join(current_parts))
            # Carry overlap: take trailing sentences that fit within overlap_chars
            overlap_parts: list[str] = []
            overlap_len = 0
            for part in reversed(current_parts):
                if overlap_len + len(part) <= overlap_chars:
                    overlap_parts.insert(0, part)
                    overlap_len += len(part) + 1
                else:
                    break
            current_parts = overlap_parts
            current_len = overlap_len

        current_parts.append(sentence)
        current_len += sentence_len + (1 if len(current_parts) > 1 else 0)

    if current_parts:
        chunks.append(" ".join(current_parts))

    return [c for c in chunks if c.strip()]
