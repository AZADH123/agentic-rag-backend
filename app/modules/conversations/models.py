"""
Conversation + Message ORM models.

A Conversation is a thread of Messages between one user and the assistant.
Messages track role (user/assistant) + content + optional citation metadata
+ optional tool_call trace.

We store citations/tool_calls as JSONB columns so we don't need to migrate
the schema every time we add a diagnostic field.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from app.database.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        server_default=func.now(), onupdate=func.now(),
    )


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    tool_calls: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )