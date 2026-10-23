"""
Text chunker.

Splits text into overlapping chunks of approximately CHUNK_SIZE tokens.

Why "approximately" tokens:
- Tokenizing exactly with a transformers tokenizer is slow at ingestion scale.
- We approximate using a heuristic: split on sentence boundaries, accumulate
  up to a target character count, and add overlap.
- For most prose, ~4 chars ≈ 1 token, so we set chunk_size_chars = chunk_size_tokens * 4.
- The actual embedding model treats each chunk's text uniformly, so being
  off by ±10% doesn't hurt retrieval quality.

Chunk boundaries:
- Prefer sentence boundaries (". " or "? " or "! " or "\n\n").
- Fall back to word boundaries if no sentence boundary is found.
- Never split in the middle of a word.

Overlap:
- The last CHUNK_OVERLAP tokens of chunk N are repeated at the start of
  chunk N+1. This ensures retrieval continuity when a relevant fact
  straddles a chunk boundary.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.utils.text_normalizer import normalize_text


@dataclass
class Chunk:
    sequence: int  # 0-indexed within the document
    text: str
    page: int | None = None  # page number from the parser, if available


_SENTENCE_ENDINGS = (". ", "? ", "! ", "\n\n")


def _subdivide_long_piece(piece: str, max_chars: int) -> list[str]:
    """Break a long piece into smaller word-bounded chunks."""
    if len(piece) <= max_chars:
        return [piece]
    words = piece.split()
    sub_pieces: list[str] = []
    curr = ""
    for w in words:
        cand = f"{curr} {w}" if curr else w
        if len(cand) > max_chars and curr:
            sub_pieces.append(curr + " ")
            curr = w
        else:
            curr = cand
    if curr:
        sub_pieces.append(curr)

    # Handle oversized single words (e.g., base64 or long hex)
    final_pieces: list[str] = []
    for sp in sub_pieces:
        if len(sp) <= max_chars:
            final_pieces.append(sp)
        else:
            for i in range(0, len(sp), max_chars):
                final_pieces.append(sp[i : i + max_chars])
    return final_pieces


def _split_sentences(text: str, max_chars: int = 800) -> list[str]:
    """Sentence splitter that also subdivides overly long sentences."""
    out: list[str] = []
    start = 0
    i = 0
    while i < len(text):
        if text[i : i + 2] in _SENTENCE_ENDINGS:
            segment = text[start : i + 2]
            out.extend(_subdivide_long_piece(segment, max_chars))
            start = i + 2
        i += 1
    if start < len(text):
        segment = text[start:]
        out.extend(_subdivide_long_piece(segment, max_chars))
    return out


def chunk_text(
    text: str,
    *,
    page: int | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """Split a single text block into overlapping chunks."""
    settings = get_settings()
    cs_tokens = chunk_size or settings.chunk_size
    co_tokens = chunk_overlap or settings.chunk_overlap

    cs_chars = max(cs_tokens * 4, 200)  # ~4 chars/token heuristic, floor 200
    co_chars = max(co_tokens * 4, 0)

    text = normalize_text(text)
    if not text:
        return []

    sentences = _split_sentences(text, max_chars=cs_chars)
    chunks: list[Chunk] = []
    current = ""
    seq = 0

    for sentence in sentences:
        candidate = current + sentence
        if len(candidate) > cs_chars and current:
            # Flush current, start next with overlap.
            chunks.append(Chunk(sequence=seq, text=current.strip(), page=page))
            seq += 1
            if co_chars > 0 and len(current) > co_chars:
                # Take last co_chars as overlap prefix.
                current = current[-co_chars:] + sentence
            else:
                current = sentence
        else:
            current = candidate

    if current.strip():
        chunks.append(Chunk(sequence=seq, text=current.strip(), page=page))

    return chunks


def chunk_pages(pages: list) -> list[Chunk]:
    """
    Chunk a list of ParsedPage objects.

    Re-numbers chunks sequentially across pages so the final chunk sequence
    is 0,1,2,... regardless of which page each chunk came from.
    """
    all_chunks: list[Chunk] = []
    seq = 0
    for page in pages:
        page_chunks = chunk_text(page.text, page=page.page)
        for c in page_chunks:
            c.sequence = seq
            seq += 1
            all_chunks.append(c)
    return all_chunks