"""
EIOS Embedding Port Interface

Protocol definition for embedding providers.
The application layer depends only on this protocol.
Concrete implementations live in infrastructure/embeddings/.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents for storage."""
        ...

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string for similarity search."""
        ...

    def dim(self) -> int:
        """Return the embedding dimension for this provider."""
        ...
