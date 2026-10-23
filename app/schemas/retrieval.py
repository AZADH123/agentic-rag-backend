"""
Retrieval schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2048)
    top_k: int = Field(5, ge=1, le=50)
    document_ids: Optional[List[str]] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    # If true, run the optional reranker pass on rerank_candidate_count hits.
    rerank: bool = False


class ChunkHit(BaseModel):
    document_id: str
    chunk_id: str
    text: str
    score: float  # similarity in [0, 1] — higher is better
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    results: List[ChunkHit]
    total: int


class ChunkResponse(BaseModel):
    chunk_id: str
    document_id: str
    sequence: int
    text: str
    page: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChunkListResponse(BaseModel):
    document_id: str
    chunks: List[ChunkResponse]
    total: int
