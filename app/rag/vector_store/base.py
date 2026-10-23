"""
Abstract vector store interface.

Swappable so a future implementation could use Pinecone, Weaviate, or
Qdrant without touching the retriever.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence


@dataclass
class VectorRecord:
    """One row to insert into the vector store."""
    chunk_id: str
    document_id: str
    owner_id: str
    sequence: int
    text: str
    embedding: List[float]
    page: int | None
    metadata: Dict[str, Any]


@dataclass
class SearchHit:
    chunk_id: str
    document_id: str
    text: str
    score: float  # similarity in [0,1]
    page: int | None
    metadata: Dict[str, Any]


class VectorStore(ABC):
    """Vector store CRUD + similarity search."""

    @abstractmethod
    async def upsert(self, records: Sequence[VectorRecord]) -> int:
        """Insert or replace chunks. Returns count written."""

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        *,
        top_k: int,
        owner_id: str | None = None,
        document_ids: Sequence[str] | None = None,
        filters: Dict[str, Any] | None = None,
    ) -> List[SearchHit]:
        """Find the top_k nearest neighbors (cosine similarity)."""

    @abstractmethod
    async def delete_by_document(self, document_id: str) -> int:
        """Remove all chunks belonging to a document."""

    @abstractmethod
    async def list_by_document(self, document_id: str) -> List[SearchHit]:
        """Return all chunks for a document (for the inspection endpoint)."""