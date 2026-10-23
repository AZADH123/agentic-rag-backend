"""
Query transformation.

Two purposes:
1. Strip prompt-injection-style content from user queries ("ignore previous
   instructions and...") before embedding/search.
2. Produce optional query variants for multi-query retrieval. Phase 5 uses
   a simple "ask the LLM to reformulate" step; for now, we expose a
   deterministic transformer that just normalizes + trims.
"""

from __future__ import annotations

import re

from app.utils.text_normalizer import normalize_query

_INJECTION_PATTERNS = [
    re.compile(r"ignore (the )?previous instructions?.*", re.IGNORECASE),
    re.compile(r"disregard (the )?system prompt.*", re.IGNORECASE),
    re.compile(r"<\s*/?\s*(system|assistant|user)\s*>", re.IGNORECASE),
]


def transform_query(query: str) -> str:
    """Normalize + sanitize a user query."""
    q = normalize_query(query)
    for pat in _INJECTION_PATTERNS:
        q = pat.sub("", q).strip()
    return q or query.strip()