"""
pgvector-backed vector store.

Uses the cosine distance operator (`<=>`) which returns:
    1 - cosine_similarity

so we convert: score = 1 - distance, giving a similarity in [0, 1] where
higher is better — consistent with the SearchHit contract.

Index:
- We create an HNSW index on the embedding column for fast ANN search.
- HNSW is preferred over IVFFlat for our scale (~100k vectors) because it
  doesn't require a separate training step.

Filters:
- The `filters` dict supports equality on top-level JSONB metadata fields
  (e.g., {"filename": "policy.pdf"}). For nested/complex filters, extend
  this method.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence

from sqlalchemy import delete, insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.rag.vector_store.base import SearchHit, VectorRecord, VectorStore

log = get_logger(__name__)

# We use raw SQL for vector operations because pgvector's SQLAlchemy support
# is finicky across versions and we want predictable behavior.

_INSERT_CHUNK_SQL = text("""
    INSERT INTO document_chunks
        (chunk_id, document_id, owner_id, sequence, text, embedding, page, metadata, created_at)
    VALUES
        (:chunk_id, :document_id, :owner_id, :sequence, :text,
         CAST(:embedding AS vector), :page, CAST(:metadata AS JSONB), NOW())
""")

_DELETE_CHUNK_SQL = text("DELETE FROM document_chunks WHERE document_id = :document_id")

_SEARCH_SQL = text("""
    SELECT
        chunk_id,
        document_id,
        text,
        page,
        metadata,
        1 - (embedding <=> CAST(:q AS vector)) AS score
    FROM document_chunks
    WHERE 1=1
      AND (:owner_id IS NULL OR owner_id = :owner_id)
      AND (:document_ids IS NULL OR document_id = ANY(:document_ids))
    ORDER BY embedding <=> CAST(:q AS vector)
    LIMIT :top_k
""")


class PgvectorStore(VectorStore):
    """pgvector implementation."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(self, records: Sequence[VectorRecord]) -> int:
        if not records:
            return 0
        # Delete existing chunks for each document first (idempotent re-index).
        seen_docs = {r.document_id for r in records}
        for doc_id in seen_docs:
            await self._session.execute(_DELETE_CHUNK_SQL, {"document_id": doc_id})

        for r in records:
            await self._session.execute(_INSERT_CHUNK_SQL, {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "owner_id": r.owner_id,
                "sequence": r.sequence,
                "text": r.text,
                "embedding": _pg_vector_literal(r.embedding),
                "page": r.page,
                "metadata": json.dumps(r.metadata),
            })
        return len(records)

    async def search(
        self,
        query_embedding: List[float],
        *,
        top_k: int,
        owner_id: str | None = None,
        document_ids: Sequence[str] | None = None,
        filters: Dict[str, Any] | None = None,
    ) -> List[SearchHit]:
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {
            "q": _pg_vector_literal(query_embedding),
            "top_k": top_k,
        }

        if owner_id:
            where_clauses.append("owner_id = :owner_id")
            params["owner_id"] = owner_id

        if document_ids:
            where_clauses.append("document_id = ANY(CAST(:document_ids AS text[]))")
            params["document_ids"] = list(document_ids)

        if filters:
            where_clauses.append("CAST(metadata AS jsonb) @> CAST(:filters AS jsonb)")
            params["filters"] = json.dumps(filters)

        where_sql = " AND ".join(where_clauses)
        search_sql = text(f"""
            SELECT
                chunk_id,
                document_id,
                text,
                page,
                metadata,
                1 - (embedding <=> CAST(:q AS vector)) AS score
            FROM document_chunks
            WHERE {where_sql}
            ORDER BY embedding <=> CAST(:q AS vector)
            LIMIT :top_k
        """)

        rows = (await self._session.execute(search_sql, params)).mappings().all()

        return [
            SearchHit(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                text=r["text"],
                score=float(r["score"]),
                page=r.get("page"),
                metadata=r.get("metadata") or {},
            )
            for r in rows
        ]

    async def delete_by_document(self, document_id: str) -> int:
        result = await self._session.execute(
            _DELETE_CHUNK_SQL, {"document_id": document_id}
        )
        # SQLAlchemy 2.0 async: CursorResult exposes rowcount; use getattr
        # as a safe fallback in case the dialect wraps it differently.
        return getattr(result, "rowcount", None) or 0

    async def list_by_document(self, document_id: str) -> List[SearchHit]:
        stmt = text("""
            SELECT chunk_id, document_id, text, page, metadata
            FROM document_chunks
            WHERE document_id = :doc_id
            ORDER BY sequence ASC
        """)
        rows = (await self._session.execute(stmt, {"doc_id": document_id})).mappings().all()
        return [
            SearchHit(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                text=r["text"],
                score=0.0,  # not relevant for listing
                page=r.get("page"),
                metadata=r.get("metadata") or {},
            )
            for r in rows
        ]


def _pg_vector_literal(vec: List[float]) -> str:
    """Format a Python list as a pgvector literal: '[1.0,2.0,3.0]'."""
    return "[" + ",".join(str(float(v)) for v in vec) + "]"


def _matches_filters(metadata: Any, filters: Dict[str, Any]) -> bool:
    if not isinstance(metadata, dict):
        return False
    return all(metadata.get(k) == v for k, v in filters.items())