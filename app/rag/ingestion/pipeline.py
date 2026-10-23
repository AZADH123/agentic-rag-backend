"""
End-to-end ingestion pipeline.

Orchestrates the full flow:
  bytes (PDF/DOCX/TXT)
    → parse → list[ParsedPage]
    → chunk → list[Chunk]
    → dedupe
    → embed (batched, async)
    → upsert into pgvector
    → return summary

This is the function the worker calls. It is also callable directly for
testing without going through Taskiq.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.database.session import db_session
from app.rag.embeddings.bge_embeddings import get_embeddings
from app.rag.indexing.deduplication import dedupe_chunks
from app.rag.indexing.indexer import Indexer
from app.rag.ingestion.chunker import chunk_pages
from app.rag.ingestion.metadata import build_chunk_metadata
from app.rag.ingestion.parsers import parse
from app.rag.vector_store.base import VectorRecord
from app.utils.ids import new_id

log = get_logger(__name__)


class IngestionPipeline:
    """Stateless per-document ingestion."""

    def __init__(self):
        self._embeddings = get_embeddings()

    async def run(
        self,
        *,
        document_id: str,
        content_bytes: bytes,
        content_type: str,
        filename: str,
        owner_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the full ingestion for one document. Returns a summary."""
        # 1. Parse
        pages = parse(content_bytes, content_type)
        if not pages:
            raise RuntimeError(f"No text extracted from {filename}")
        total_text = sum(len(p.text) for p in pages)
        log.info("parsed", document_id=document_id,
                 pages=len(pages), text_chars=total_text)

        # 2. Chunk
        chunks = chunk_pages(pages)
        if not chunks:
            raise RuntimeError(f"Chunking produced zero chunks for {filename}")

        # 3. Dedupe
        chunks = dedupe_chunks(chunks)
        log.info("chunked", document_id=document_id, chunks=len(chunks))

        # 4. Embed (one batch, model internally batches)
        texts = [c.text for c in chunks]
        vectors = await self._embeddings.embed_texts(texts)
        if len(vectors) != len(chunks):
            raise RuntimeError(
                f"Embedding count mismatch: {len(vectors)} vs {len(chunks)}"
            )

        # 5. Persist to DB + pgvector
        async with db_session() as session:
            if owner_id is None:
                from app.modules.documents.repository import DocumentRepository
                doc = await DocumentRepository(session).get(document_id)
                if doc is None:
                    raise RuntimeError(f"Document {document_id} not found while indexing")
                owner_id = doc.owner_id

            records = [
                VectorRecord(
                    chunk_id=new_id("chunk"),
                    document_id=document_id,
                    owner_id=owner_id,
                    sequence=c.sequence,
                    text=c.text,
                    embedding=vec,
                    page=c.page,
                    metadata=build_chunk_metadata(
                        filename=filename,
                        page=c.page,
                        sequence=c.sequence,
                    ),
                )
                for c, vec in zip(chunks, vectors)
            ]

            indexer = Indexer(session)
            written = await indexer.index_chunks(records)
            log.info("indexed", document_id=document_id, written=written)

        return {
            "document_id": document_id,
            "pages": len(pages),
            "chunks": len(chunks),
            "vectors_written": written,
            "embedding_dim": self._embeddings.dimensions,
        }