"""
Agent memory — conversation context management.

Builds the `contents` list we send to Gemini each turn. The structure is:
    [{role: "user", parts: [{text: "earlier user msg"}]},
     {role: "model", parts: [{text: "earlier model reply"}]},
     ...,
     {role: "user", parts: [{text: "current question"}]}]

We cap memory to a configurable window of recent turns to avoid token
overflow. Older messages are dropped; the system prompt is always sent.
"""

from __future__ import annotations

from typing import List

from app.core.config import get_settings
from app.core.logging import get_logger
from app.modules.conversations.repository import ConversationRepository

log = get_logger(__name__)


class AgentMemory:
    """Loads + manages conversation context for the agent."""

    def __init__(self, conversation_id: str, owner_id: str, db_session):
        self._conversation_id = conversation_id
        self._owner_id = owner_id
        self._session = db_session

    async def build_initial_contents(self, current_user_message: str) -> List[dict]:
        """Return Gemini-format `contents` for the first turn of this chat call."""
        repo = ConversationRepository(self._session)
        messages = await repo.list_messages(self._conversation_id, limit=10)

        # Cap history to last N messages to manage context length.
        settings = get_settings()
        cap = max(4, settings.max_agent_steps * 2)
        if len(messages) > cap:
            messages = messages[-cap:]

        contents: List[dict] = []
        for m in messages:
            role = "user" if m.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})

        # Append the current user message.
        contents.append({"role": "user", "parts": [{"text": current_user_message}]})
        return contents

    def append_text(self, contents: List[dict], role: str, text: str) -> List[dict]:
        """Append a text turn to the in-flight contents list."""
        gemini_role = "user" if role == "user" else "model"
        contents.append({"role": gemini_role, "parts": [{"text": text}]})
        return contents

    def append_tool_response(self, contents: List[dict], tool_name: str, response: dict) -> List[dict]:
        """Append a function_response part back to Gemini."""
        contents.append({
            "role": "user",
            "parts": [{"function_response": {"name": tool_name, "response": response}}],
        })
        return contents