"""
Conversation history endpoints.

GET    /chat/conversations                 — list conversations
GET    /chat/conversations/{id}            — get a conversation + its messages
DELETE /chat/conversations/{id}            — delete a conversation
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_owner, get_session
from app.modules.conversations.service import ConversationService
from app.schemas.chat import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
)

router = APIRouter()


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    service = ConversationService(session)
    items, total = await service.list(owner, limit=limit, offset=offset)
    return ConversationListResponse(
        items=[ConversationResponse(
            conversation_id=c.conversation_id,
            title=c.title,
            owner_id=c.owner_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        ) for c in items],
        total=total,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    service = ConversationService(session)
    conv = await service.get(conversation_id, owner)
    messages = await service.list_messages(conversation_id)
    return ConversationDetailResponse(
        conversation_id=conv.conversation_id,
        title=conv.title,
        owner_id=conv.owner_id,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[
            MessageResponse(
                message_id=m.message_id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                citations=m.citations or [],
                tool_calls=m.tool_calls or [],
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    service = ConversationService(session)
    await service.delete(conversation_id, owner)
    return None