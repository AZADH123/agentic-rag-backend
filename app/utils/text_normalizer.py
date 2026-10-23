"""
Text normalization utilities.

Used by both ingestion (cleaning extracted text) and retrieval (preparing
queries). The goal is consistency: the same normalization must be applied
to chunks at index time and to queries at search time.
"""

from __future__ import annotations

import re
import unicodedata


_WHITESPACE_RE = re.compile(r"\s+")
_BULLET_RE = re.compile(r"^[•\-\*●▪◦]\s*", re.MULTILINE)


def normalize_text(text: str) -> str:
    """Apply standard normalization: NFC unicode, collapse whitespace, strip."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    # Replace common bullet characters with a dash
    text = _BULLET_RE.sub("- ", text)
    # Collapse runs of whitespace (including newlines in the middle of paragraphs)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def normalize_query(text: str) -> str:
    """Lighter normalization for search queries — keeps question structure."""
    return normalize_text(text)