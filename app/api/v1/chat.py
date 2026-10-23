"""
Chat endpoint.

POST /chat — send a question to the Agentic RAG system.

Request body:
    {"message": "...", "conversation_id": null}

Response:
    {"conversation_id": "...", "answer": "...", "citations": [...], "tool_calls": [...]}
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import AgentOrchestrator
from app.core.logging import get_logger
from app.dependencies import get_current_owner, get_session
from app.schemas.chat import ChatRequest, ChatResponse

log = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    req: ChatRequest,
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(get_current_owner),
):
    """Run one agentic chat turn."""
    log.info("chat_request",
             conversation_id=req.conversation_id,
             message_len=len(req.message))

    orchestrator = AgentOrchestrator(session)
    response = await orchestrator.run(
        user_message=req.message,
        conversation_id=req.conversation_id,
        owner_id=owner,
        max_steps=req.max_steps,
    )
    return response