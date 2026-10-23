"""
Planner.

Decides the next action based on the LLM's latest response:
- If Gemini emitted a function_call → execute that tool.
- If Gemini emitted plain text → that's the final answer.
- If Gemini emitted both → prefer the tool call (continue the loop).

We also implement optional "evidence evaluation" between retrieval calls:
after each search_documents result, we ask Gemini (in a single extra call)
whether the evidence is SUFFICIENT or whether we should refine the query.
This keeps the agent from looping on a bad query.

For Phase 8 we keep the evaluator simple — it inspects the LLM response
shape, not its semantic content. A more sophisticated planner would feed
the evidence back into the planner prompt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from app.agent.state import RunState
from app.llm.gemini_client import LLMResponse


@dataclass
class NextAction:
    kind: Literal["call_tool", "answer", "stop"]
    tool_name: Optional[str] = None
    tool_arguments: Optional[dict] = None
    text: Optional[str] = None


def plan_next(state: RunState, response: LLMResponse) -> NextAction:
    """Return the next action to take given the LLM's latest response."""
    if response.tool_calls:
        # Take the first tool call. (Gemini may emit multiple; we handle one at a
        # time to keep the loop simple and traceable.)
        tc = response.tool_calls[0]
        return NextAction(
            kind="call_tool",
            tool_name=tc.tool_name,
            tool_arguments=tc.arguments,
        )

    if response.text:
        return NextAction(kind="answer", text=response.text)

    # No tool call and no text — typically a finish_reason like SAFETY.
    return NextAction(
        kind="stop",
        text="I cannot produce a response to that request.",
    )