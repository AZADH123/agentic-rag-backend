"""
BGE embedding implementation.

Uses sentence-transformers under the hood. Wraps the synchronous encode()
call in anyio.to_thread.run_sync so the async event loop is never blocked
during CPU-heavy embedding work.

BGE models output L2-normalized vectors by default after encode() — we
explicitly re-normalize to be safe (norm_normalize=True).
"""

from __future__ import annotations

from typing import Sequence

import anyio

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.embeddings.base import EmbeddingModel
from app.rag.embeddings.model_loader import get_model

log = get_logger(__name__)


class BgeEmbeddings(EmbeddingModel):
    """Embedding model backed by BAAI/bge-small-en-v1.5 (configurable)."""

    def __init__(self):
        # Lazy: the model loads on first call to embed_texts.
        self._settings = get_settings()

    @property
    def name(self) -> str:
        return self._settings.embedding_model

    @property
    def dimensions(self) -> int:
        return self._settings.embedding_dimensions

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        model = get_model()
        batch_size = self._settings.embedding_batch_size

        # Offload the CPU-bound encode() to a worker thread.
        vectors = await anyio.to_thread.run_sync(
            lambda: model.encode(
                list(texts),
                batch_size=batch_size,
                normalize_embeddings=True,  # L2-normalize for cosine search
                show_progress_bar=False,
                convert_to_numpy=True,
            ).tolist(),
        )
        return vectors

    async def embed_query(self, query: str) -> list[float]:
        return (await self.embed_texts([query]))[0]


# Module-level singleton — embedding instances are stateless beyond config.
_embeddings: BgeEmbeddings | None = None


def get_embeddings() -> BgeEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = BgeEmbeddings()
    return _embeddings
