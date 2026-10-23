"""
Citation construction.

Convert raw SearchHits (from the vector store) into Citation schema objects
suitable for the chat response. A citation ties a generated answer back to
the specific document + chunk that supported it.
"""

from __future__ import annotations

from typing import List, Sequence

from app.rag.vector_store.base import SearchHit
from app.schemas.citation import Citation


def build_citations(hits: Sequence[SearchHit], snippet_chars: int = 160) -> List[Citation]:
    """Build Citation schema objects from search hits."""
    out: List[Citation] = []
    for h in hits:
        snippet = h.text[:snippet_chars].strip()
        if len(h.text) > snippet_chars:
            snippet += "..."
        out.append(Citation(
            document_id=h.document_id,
            chunk_id=h.chunk_id,
            filename=h.metadata.get("filename"),
            page=h.page,
            snippet=snippet,
        ))
    return out