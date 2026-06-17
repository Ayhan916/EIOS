"""
EIOS Sentence-Transformer Embedding Provider

Implements EmbeddingProvider using the sentence-transformers library.
CPU inference by default; GPU is used automatically if available via PyTorch.

Model selection guide for ESG/compliance workloads:
  Development (fast, English):   BAAI/bge-small-en-v1.5   (384 dims, ~80MB)
  Production (multilingual ESG): intfloat/multilingual-e5-large (1024 dims, ~1.1GB)

E5 models require query/document prefixes; BGE and other models do not.
Prefix behaviour is detected automatically from the model name.
"""

import asyncio

import structlog
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger(__name__)


def _needs_e5_prefix(model_name: str) -> bool:
    return "e5" in model_name.lower()


class SentenceTransformerEmbeddingProvider:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._use_e5_prefix = _needs_e5_prefix(model_name)
        logger.info("embedding_provider_loading", model=model_name)
        self._model = SentenceTransformer(model_name)
        self._dim = self._model.get_sentence_embedding_dimension()
        logger.info("embedding_provider_ready", model=model_name, dim=self._dim)

    def dim(self) -> int:
        return int(self._dim)

    def _encode_sync(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [e.tolist() for e in embeddings]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        prefixed = [f"passage: {t}" if self._use_e5_prefix else t for t in texts]
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._encode_sync, prefixed)

    async def embed_query(self, text: str) -> list[float]:
        prefixed = f"query: {text}" if self._use_e5_prefix else text
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, self._encode_sync, [prefixed])
        return results[0]
