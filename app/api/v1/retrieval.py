"""
Retrieval endpoints.

POST  /retrieval/search                         — semantic search
GET   /retrieval/documents/{document_id}/chunks — inspect chunks for a doc
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DocumentNotFoundError
from app.dependencies import get_current_owner, get_session
from app.modules.documents.repository import DocumentRepository
from app.rag.retrieval.retriever import Retriever, to_chunk_hit
from app.schemas.retrieval import (
    ChunkListResponse,
    ChunkResponse,
    SearchRequest,
    SearchResponse,
)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(
    req: SearchRequest,
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    retriever = Retriever(session)
    hits = await retriever.search(
        req.query,
        owner_id=owner,
        document_ids=req.document_ids,
        top_k=req.top_k,
        filters=req.filters or None,
        use_reranker=req.rerank,
    )
    return SearchResponse(
        query=req.query,
        results=[to_chunk_hit(h) for h in hits],
        total=len(hits),
    )


@router.get("/documents/{document_id}/chunks", response_model=ChunkListResponse)
async def list_chunks(
    document_id: str,
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    # Verify document exists + is owned by caller.
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get(document_id)
    if doc is None or doc.owner_id != owner:
        raise DocumentNotFoundError(f"Document {document_id} not found")

    retriever = Retriever(session)
    hits = await retriever.list_chunks(document_id)
    return ChunkListResponse(
        document_id=document_id,
        chunks=[
            ChunkResponse(
                chunk_id=h.chunk_id,
                document_id=h.document_id,
                sequence=int(h.metadata.get("sequence", 0)) if h.metadata else 0,
                text=h.text,
                page=h.page,
                metadata=h.metadata,
            )
            for h in hits
        ],
        total=len(hits),
    )