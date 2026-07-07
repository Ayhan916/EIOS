"""Singleton embedding service using intfloat/multilingual-e5-large.

The model is loaded once at first use and kept in memory.
Supports German + English text natively.

multilingual-e5-large requires instruction prefixes:
  - passages (stored docs): "passage: <text>"
  - queries  (search):      "query: <text>"
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

_MODEL_NAME = "intfloat/multilingual-e5-large"
_EMBEDDING_DIM = 1024

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        logger.info("rag_embedder.loading", model=_MODEL_NAME)
        _model = SentenceTransformer(_MODEL_NAME)
        logger.info("rag_embedder.ready", model=_MODEL_NAME)
    return _model


def embed_passage(text: str) -> list[float]:
    """Embed a document passage for storage."""
    model = _get_model()
    vec = model.encode(f"passage: {text}", normalize_embeddings=True)
    return vec.tolist()


def embed_query(text: str) -> list[float]:
    """Embed a search query for retrieval."""
    model = _get_model()
    vec = model.encode(f"query: {text}", normalize_embeddings=True)
    return vec.tolist()


def embed_passages_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed multiple passages efficiently."""
    model = _get_model()
    prefixed = [f"passage: {t}" for t in texts]
    vecs = model.encode(prefixed, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vecs]
