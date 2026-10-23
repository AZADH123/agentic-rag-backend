"""Retrieval-related prompt fragments."""

from __future__ import annotations


RETRIEVAL_CONTEXT_PROMPT = """\
Use the following retrieved chunks to answer the user's question.

For each chunk, the format is:
[chunk_id: <id>] (document: <filename>, page: <page>)
<chunk text>

---
{chunks}
---
"""


def build_retrieval_context(chunks_text: str) -> str:
    return RETRIEVAL_CONTEXT_PROMPT.format(chunks=chunks_text)