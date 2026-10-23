"""
Embedding model interface.

Anything that can take a list of strings and return a list of float vectors
implements this contract. Swapping BGE for a different open-source model
(or even Gemini embeddings later) only requires writing a new class that
implements `embed_texts`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence


class EmbeddingModel(ABC):
    """Pluggable embedding model interface."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the vector dimensionality produced by this model."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the model identifier (e.g. 'BAAI/bge-small-en-v1.5')."""

    @abstractmethod
    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """
        Embed a batch of texts and return normalized vectors.

        Implementations MUST:
        - Return one vector per input text, in the same order.
        - L2-normalize vectors (so cosine similarity = dot product).
        - Batch internally to control memory.
        """

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query. Default implementation calls embed_texts."""
        return (await self.embed_texts([query]))[0]