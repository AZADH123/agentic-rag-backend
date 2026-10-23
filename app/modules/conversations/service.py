"""
Conversation service.

Provides the operations the agent + chat endpoints need:
- create a new conversation
- get an existing conversation (owner-scoped)
- list conversations
- delete a conversation (cascades to messages)
- add a message
- list messages
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConversationNotFoundError
from app.core.logging import get_logger
from app.modules.conversations.models import Conversation, Message
from app.modules.conversations.repository import ConversationRepository
from app.utils.ids import new_id

log = get_logger(__name__)


class ConversationService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = ConversationRepository(session)

    async def create(self, *, owner_id: str, title: Optional[str] = None) -> Conversation:
        conv = Conversation(
            conversation_id=new_id("conv"),
            owner_id=owner_id,
            title=title,
        )
        return await self._repo.create(conv)

    async def get(self, conversation_id: str, owner_id: str) -> Conversation:
        conv = await self._repo.get(conversation_id)
        if conv is None or conv.owner_id != owner_id:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
        return conv

    async def list(self, owner_id: str, limit: int = 50, offset: int = 0
                   ) -> tuple[Sequence[Conversation], int]:
        return await self._repo.list_by_owner(owner_id, limit, offset)

    async def delete(self, conversation_id: str, owner_id: str) -> None:
        # Verify ownership first (raises 404 if not owned).
        await self.get(conversation_id, owner_id)
        await self._repo.delete(conversation_id)

    async def add_message(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> Message:
        msg = Message(
            message_id=new_id("msg"),
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations,
            tool_calls=tool_calls,
        )
        return await self._repo.add_message(msg)

    async def list_messages(self, conversation_id: str, limit: int = 50) -> Sequence[Message]:
        return await self._repo.list_messages(conversation_id, limit)