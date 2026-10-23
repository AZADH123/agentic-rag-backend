"""
Agent execution state.

A `RunState` is created at the start of one chat turn and mutated as the
orchestrator steps through its loop. It tracks:
- the conversation id this turn belongs to
- the messages exchanged with the LLM
- the tool calls attempted so far (with status)
- the citations accumulated from retrieval
- the step counter (bounded by MAX_AGENT_STEPS)

Keeping this state OUT of the orchestrator object lets us inspect / log /
persist it cleanly, and supports future features like checkpointing mid-run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class ToolAttempt:
    tool_name: str
    arguments: Dict[str, Any]
    status: str  # "success" | "error" | "skipped"
    result_summary: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class RunState:
    conversation_id: str
    user_message: str
    owner_id: str

    # LLM-side message history for this turn (Gemini `contents` list).
    messages: List[Dict[str, Any]] = field(default_factory=list)

    # Tool execution log for diagnostics + response.
    tool_calls: List[ToolAttempt] = field(default_factory=list)

    # Citations accumulated from retrieval tool calls.
    citations: List[Dict[str, Any]] = field(default_factory=list)

    # Bounded step counter.
    step_count: int = 0
    max_steps: int = 6

    # Set when the agent emits a final answer (text without tool_calls).
    final_answer: Optional[str] = None

    # Set if the agent could not produce an answer.
    error: Optional[str] = None

    @property
    def is_done(self) -> bool:
        return self.final_answer is not None or self.error is not None

    @property
    def steps_remaining(self) -> int:
        return max(0, self.max_steps - self.step_count)