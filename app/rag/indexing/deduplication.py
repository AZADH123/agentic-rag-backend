"""
Deduplication helpers.

Two levels:
1. Document-level: same content hash → return existing doc (handled in
   DocumentService.upload_and_enqueue).
2. Chunk-level: within one ingestion run, we may produce near-duplicate
   chunks if the parser emits overlapping pages. This module provides a
   simple dedup pass on exact text equality.
"""

from __future__ import annotations

from typing import Iterable, List

from app.rag.ingestion.chunker import Chunk


def dedupe_chunks(chunks: Iterable[Chunk]) -> List[Chunk]:
    """Drop chunks with identical (normalized) text, keeping the first and resequencing."""
    seen: set[str] = set()
    out: List[Chunk] = []
    seq = 0
    for c in chunks:
        key = c.text.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        c.sequence = seq
        seq += 1
        out.append(c)
    return out
