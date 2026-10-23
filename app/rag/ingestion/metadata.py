"""
Chunk metadata helpers.

Each chunk we index carries metadata useful for:
- filtering (filename, owner_id)
- citation display (page, source)
- debugging (created_at, sequence)

We attach metadata as a JSONB column on the document_chunks table.
"""

from __future__ import annotations

from typing import Any, Dict


def build_chunk_metadata(
    *,
    filename: str,
    page: int | None,
    sequence: int,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Construct the JSONB metadata blob stored alongside each chunk."""
    meta: Dict[str, Any] = {
        "filename": filename,
        "page": page,
        "sequence": sequence,
        "source": "upload",  # could be "api" / "webhook" / "migration" later
    }
    if extra:
        meta.update(extra)
    return meta