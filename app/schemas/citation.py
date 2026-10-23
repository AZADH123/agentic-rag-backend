"""
Citation schema. A single citation ties a generated answer span back to a
specific chunk in a specific document.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Citation(BaseModel):
    document_id: str
    chunk_id: str
    filename: Optional[str] = None
    page: Optional[int] = None
    # Optional snippet from the chunk used to support the answer.
    snippet: Optional[str] = None


class ToolCallRecord(BaseModel):
    """Single tool execution record returned in the chat response."""
    tool_name: str
    status: str  # "success" | "error" | "skipped"
    arguments_summary: Optional[str] = None
    error: Optional[str] = None