"""
Tool executor.

Wraps ToolRegistry.invoke() with:
- structured logging per attempt
- converting tool results to a form the agent can ingest (Gemini
  function_response part)
- extracting citations from search_documents results
- error capture (tool failure doesn't crash the loop; we feed the error back
  to the LLM so it can recover)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.agent.state import RunState, ToolAttempt
from app.agent.tool_registry import ToolRegistry
from app.core.logging import get_logger

log = get_logger(__name__)


class ToolExecutor:
    def __init__(self, registry: ToolRegistry):
        self._registry = registry

    async def execute(
        self,
        state: RunState,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute one tool call. Records the attempt in state."""
        attempt = ToolAttempt(tool_name=tool_name, arguments=arguments, status="running")
        try:
            result = await self._registry.invoke(tool_name, arguments)

            # If this was a retrieval call, harvest citations.
            if tool_name == "search_documents":
                self._harvest_citations(state, result)

            attempt.status = "success"
            attempt.result_summary = _summarize(result)
            state.tool_calls.append(attempt)
            log.info("tool_executed", tool=tool_name, status="success")
            return result

        except Exception as e:
            attempt.status = "error"
            attempt.error = str(e)[:200]
            state.tool_calls.append(attempt)
            log.warning("tool_failed", tool=tool_name, error=attempt.error)
            # Return a structured error so the LLM can react.
            return {"error": str(e)[:500]}

    def _harvest_citations(self, state: RunState, result: Dict[str, Any]) -> None:
        """Pull citations out of a search_documents result."""
        hits = result.get("results", []) if isinstance(result, dict) else []
        for h in hits:
            # Avoid duplicate citations across multiple retrieval calls.
            existing_ids = {c.get("chunk_id") for c in state.citations}
            if h.get("chunk_id") in existing_ids:
                continue
            state.citations.append({
                "document_id": h.get("document_id"),
                "chunk_id": h.get("chunk_id"),
                "filename": h.get("filename"),
                "page": h.get("page"),
                "snippet": (h.get("text") or "")[:200],
            })


def _summarize(result: Any, max_chars: int = 100) -> str:
    s = str(result)
    return s if len(s) <= max_chars else s[:max_chars] + "..."