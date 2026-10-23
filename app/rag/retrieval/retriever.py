"""
High-level retriever: query → embed → search → rerank → citations.

This is the interface the agent will use via the MCP RAG server (Phase 7)
and the direct /retrieval/search REST endpoint.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.embeddings.bge_embeddings import get_embeddings
from app.rag.retrieval.citations import build_citations
from app.rag.retrieval.query_transformer import transform_query
from app.rag.retrieval.reranker import rerank
from app.rag.vector_store.base import SearchHit
from app.rag.vector_store.pgvector_store import PgvectorStore
from app.schemas.citation import Citation
from app.schemas.retrieval import ChunkHit

log = get_logger(__name__)


class Retriever:
    """Single entrypoint for semantic search over the knowledge base."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._embeddings = get_embeddings()
        self._store = PgvectorStore(session)

    async def search(
        self,
        query: str,
        *,
        owner_id: str | None = None,
        document_ids: Sequence[str] | None = None,
        top_k: int | None = None,
        filters: Dict[str, Any] | None = None,
        use_reranker: bool = False,
    ) -> List[SearchHit]:
        """Run an end-to-end retrieval. Returns SearchHit list (sorted by score)."""
        settings = get_settings()
        k = top_k or settings.retrieval_top_k

        transformed = transform_query(query)
        if transformed != query:
            log.info("query_transformed", original_len=len(query),
                     transformed_len=len(transformed))

        # Embed the query — returns a single 384-dim (configurable) vector.
        qvec = await self._embeddings.embed_query(transformed)

        # When reranker is on, over-fetch then trim.
        fetch_k = max(settings.rerank_candidate_count, k * 2) if use_reranker else k

        hits = await self._store.search(
            qvec,
            top_k=fetch_k,
            owner_id=owner_id,
            document_ids=document_ids,
            filters=filters,
        )

        if use_reranker:
            hits = rerank(hits, top_k=k)

        log.info("retrieval_done",
                 query_len=len(transformed),
                 fetched=len(hits), top_k=k,
                 use_reranker=use_reranker)
        return hits

    async def search_with_citations(self, query: str, **kwargs) -> tuple[List[SearchHit], List[Citation]]:
        """Convenience: returns hits + a Citation list ready for the chat response."""
        hits = await self.search(query, **kwargs)
        return hits, build_citations(hits)

    async def list_chunks(self, document_id: str) -> List[SearchHit]:
        """Return all chunks belonging to a document (for inspection endpoint)."""
        return await self._store.list_by_document(document_id)


def to_chunk_hit(h: SearchHit) -> ChunkHit:
    """Convert a SearchHit to the API schema."""
    return ChunkHit(
        document_id=h.document_id,
        chunk_id=h.chunk_id,
        text=h.text,
        score=h.score,
        metadata=h.metadata,
    )