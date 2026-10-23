"""
Agent orchestrator.

Coordinates the agent loop:
1. Build conversation context (AgentMemory).
2. Load tools from the registry.
3. Loop:
   a. Call Gemini with current contents + tools.
   b. Planner decides: call_tool / answer / stop.
   c. If tool: executor runs it, append function_response to contents.
   d. If answer: persist user message + assistant message, return.
   e. Enforce step limit.
4. Persist conversation messages and return ChatResponse.

Why a synchronous loop (not async fan-out):
- Each LLM call depends on the previous tool result.
- Parallelism would complicate citation attribution.
- Latency is bounded by MAX_AGENT_STEPS (default 6).
"""

from __future__ import annotations

import json
from typing import List

from app.agent.executor import ToolExecutor
from app.agent.memory import AgentMemory
from app.agent.planner import NextAction, plan_next
from app.agent.policies import load_policies
from app.agent.state import RunState
from app.agent.tool_registry import ToolRegistry
from app.core.config import get_settings
from app.core.exceptions import UpstreamError
from app.core.logging import get_logger
from app.llm.gemini_client import GeminiClient
from app.llm.tool_calling import build_tool_response_part
from app.mcp.client import get_mcp_client
from app.prompts.system import SYSTEM_PROMPT
from app.schemas.chat import ChatResponse
from app.schemas.citation import Citation, ToolCallRecord
from app.utils.ids import new_id

log = get_logger(__name__)


class AgentOrchestrator:
    """Runs one chat turn end-to-end."""

    def __init__(self, session):
        self._session = session

    async def run(self, *, user_message: str, conversation_id: str | None,
                  owner_id: str, max_steps: int | None = None) -> ChatResponse:
        # 1. Resolve / create conversation.
        from app.modules.conversations.service import ConversationService
        conv_service = ConversationService(self._session)
        if conversation_id is None:
            conv = await conv_service.create(owner_id=owner_id,
                                              title=_derive_title(user_message))
            conversation_id = conv.conversation_id
        else:
            conv = await conv_service.get(conversation_id, owner_id)

        # 2. Build memory + state.
        memory = AgentMemory(conversation_id, owner_id, self._session)
        contents = await memory.build_initial_contents(user_message)

        policies = load_policies()
        state = RunState(
            conversation_id=conversation_id,
            user_message=user_message,
            owner_id=owner_id,
            max_steps=max_steps or policies.max_steps,
            messages=contents,
        )

        # 3. Set up LLM client + tool registry.
        gemini = GeminiClient()
        mcp = get_mcp_client()
        if not mcp._started:
            await mcp.start()
        registry = ToolRegistry(client=mcp)
        executor = ToolExecutor(registry)

        tools_spec = registry.list_for_gemini()
        system_prompt = SYSTEM_PROMPT.format(max_steps=state.max_steps)

        # 4. Persist the user's message first so history is consistent.
        await conv_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )

        # 5. The agent loop.
        while not state.is_done and state.step_count < state.max_steps:
            state.step_count += 1
            log.info("agent_step",
                     conversation_id=conversation_id,
                     step=state.step_count,
                     steps_remaining=state.steps_remaining)

            try:
                response = await gemini.chat(
                    system_instruction=system_prompt,
                    contents=state.messages,
                    tools=tools_spec if tools_spec else None,
                )
            except UpstreamError as e:
                state.error = str(e)
                break

            # Append the model's response to contents so the next turn has
            # full context (including any function_call parts).
            _append_model_response(state.messages, response)

            action = plan_next(state, response)

            if action.kind == "answer":
                state.final_answer = action.text
                break

            if action.kind == "stop":
                state.final_answer = action.text or "I cannot answer that."
                break

            if action.kind == "call_tool":
                # tool_name is Optional[str] per NextAction; guard against None.
                assert action.tool_name is not None, "call_tool action must have a tool_name"
                # Execute the tool.
                result = await executor.execute(
                    state, action.tool_name, action.tool_arguments or {}
                )
                # Feed the result back to the LLM as a function_response.
                # Append as a plain dict (matching messages: List[Dict[str, Any]])
                # so the GeminiClient's Content conversion picks it up correctly.
                resp_payload = result if isinstance(result, dict) else {"result": str(result)}
                state.messages.append({
                    "role": "tool",
                    "parts": [{"function_response": {"name": action.tool_name, "response": resp_payload}}],
                })

        if state.final_answer is None:
            if state.error:
                state.final_answer = (
                    f"I was unable to complete this request. Error: {state.error}"
                )
            else:
                state.final_answer = (
                    "I reached the maximum number of reasoning steps without "
                    "producing a final answer. Please refine your question."
                )

        # 6. Persist the assistant message.
        await conv_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=state.final_answer,
            citations=state.citations,
            tool_calls=[{
                "tool_name": t.tool_name,
                "status": t.status,
                "arguments_summary": json.dumps(t.arguments)[:200],
                "error": t.error,
            } for t in state.tool_calls],
        )

        # 7. Build response.
        return ChatResponse(
            conversation_id=conversation_id,
            answer=state.final_answer,
            citations=[Citation(**c) for c in state.citations],
            tool_calls=[
                ToolCallRecord(
                    tool_name=t.tool_name,
                    status=t.status,
                    arguments_summary=json.dumps(t.arguments)[:200],
                    error=t.error,
                )
                for t in state.tool_calls
            ],
            steps_taken=state.step_count,
        )


def _derive_title(message: str, max_len: int = 60) -> str:
    """Use the first line/sentence of the message as a conversation title."""
    t = message.strip().split("\n")[0]
    if len(t) > max_len:
        t = t[: max_len - 1] + "…"
    return t


def _append_model_response(contents: list, response) -> None:
    """Append Gemini's response as a 'model' turn, preserving thought_signature if present."""
    if response.raw and hasattr(response.raw, "candidates") and response.raw.candidates:
        candidate = response.raw.candidates[0]
        if hasattr(candidate, "content") and candidate.content:
            contents.append(candidate.content)
            return

    parts: list = []
    if response.text:
        parts.append({"text": response.text})
    for tc in response.tool_calls:
        fc_dict: dict = {
            "name": tc.tool_name,
            "args": tc.arguments,
        }
        if tc.call_id:
            fc_dict["id"] = tc.call_id
        parts.append({"function_call": fc_dict})
    if not parts:
        parts.append({"text": "(no response)"})
    contents.append({"role": "model", "parts": parts})