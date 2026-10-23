"""
Optional reranker.

When the retriever returns more hits than top_k (controlled by
RERANK_CANDIDATE_COUNT), we can rerank them with a stronger model before
truncating. Phase 5 ships a simple "maximal marginal relevance"-ish
deduplicator that drops near-duplicates based on text overlap. A real
cross-encoder reranker (e.g., bge-reranker-base) can be dropped in here.
"""

from __future__ import annotations

from typing import List, Sequence

from app.rag.vector_store.base import SearchHit


def dedupe_hits(hits: Sequence[SearchHit], similarity_threshold: float = 0.85) -> List[SearchHit]:
    """Drop near-duplicate hits based on character overlap."""
    kept: List[SearchHit] = []
    for h in hits:
        if _is_near_duplicate(h, kept, similarity_threshold):
            continue
        kept.append(h)
    return kept


def _is_near_duplicate(
    candidate: SearchHit, kept: Sequence[SearchHit], threshold: float
) -> bool:
    """Naive Jaccard on word sets. Fast and good enough for short chunks."""
    cand_words = set(candidate.text.lower().split())
    if not cand_words:
        return False
    for k in kept:
        kept_words = set(k.text.lower().split())
        if not kept_words:
            continue
        intersection = cand_words & kept_words
        union = cand_words | kept_words
        score = len(intersection) / len(union)
        if score >= threshold:
            return True
    return False


def rerank(hits: Sequence[SearchHit], top_k: int) -> List[SearchHit]:
    """Apply reranking (currently dedup + truncate)."""
    deduped = dedupe_hits(hits)
    # Already sorted by score from the vector store.
    return deduped[:top_k]
