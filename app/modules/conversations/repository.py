"""
Conversations repository.
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conversations.models import Conversation, Message


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, conv: Conversation) -> Conversation:
        self._session.add(conv)
        await self._session.flush()
        return conv

    async def get(self, conversation_id: str) -> Optional[Conversation]:
        return await self._session.get(Conversation, conversation_id)

    async def list_by_owner(self, owner_id: str, limit: int = 50, offset: int = 0
                            ) -> tuple[Sequence[Conversation], int]:
        stmt = select(Conversation).where(
            Conversation.owner_id == owner_id
        ).order_by(Conversation.created_at.desc())
        items = (await self._session.execute(stmt.limit(limit).offset(offset))).scalars().all()
        total = (await self._session.execute(
            select(func.count()).select_from(Conversation).where(
                Conversation.owner_id == owner_id
            )
        )).scalar_one()
        return items, total

    async def delete(self, conversation_id: str) -> None:
        # Cascading FK on messages handles child rows.
        await self._session.execute(
            delete(Conversation).where(Conversation.conversation_id == conversation_id)
        )

    async def add_message(self, message: Message) -> Message:
        self._session.add(message)
        await self._session.flush()
        return message

    async def list_messages(self, conversation_id: str, limit: int = 50) -> Sequence[Message]:
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).limit(limit)
        return (await self._session.execute(stmt)).scalars().all()