"""
Embedding provider singleton and FastAPI dependency.

The provider is initialised once at application startup (in the lifespan handler)
and reused across all requests. Model loading can take 5-30 seconds on first run
as weights are downloaded from HuggingFace; subsequent startups use the local cache.
"""

from shared.config import settings

from .sentence_transformer import SentenceTransformerEmbeddingProvider

_provider: SentenceTransformerEmbeddingProvider | None = None


def init_embedding_provider() -> SentenceTransformerEmbeddingProvider:
    """Load the model and initialise the singleton. Called once at startup."""
    global _provider
    if _provider is None:
        _provider = SentenceTransformerEmbeddingProvider(settings.embedding_model)
    return _provider


def get_embedding_provider() -> SentenceTransformerEmbeddingProvider:
    """FastAPI dependency — returns the pre-initialised singleton."""
    if _provider is None:
        raise RuntimeError(
            "Embedding provider not initialised. Call init_embedding_provider() at startup."
        )
    return _provider
