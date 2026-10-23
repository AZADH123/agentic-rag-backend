"""
Chat schemas (request/response for /chat endpoints).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.citation import Citation, ToolCallRecord


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8192)
    conversation_id: Optional[str] = None
    # Optional override of the maximum agent steps for this request.
    max_steps: Optional[int] = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    # Diagnostic info — useful during dev. Hide in production if desired.
    steps_taken: int = 0


class MessageResponse(BaseModel):
    message_id: str
    conversation_id: str
    role: str  # "user" | "assistant"
    content: str
    citations: List[Citation] = Field(default_factory=list)
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    created_at: datetime


class ConversationResponse(BaseModel):
    conversation_id: str
    title: Optional[str] = None
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ConversationListResponse(BaseModel):
    items: List[ConversationResponse]
    total: int


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = Field(default_factory=list)