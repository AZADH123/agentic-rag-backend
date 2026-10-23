"""
Tool registry + execution policies.

The registry is a thin wrapper over the MCP client's tool list, providing:
- a Gemini-format tool spec for the LLM (`tools_to_gemini_spec`)
- a single invoke() entrypoint
- policy enforcement (allowlist, max calls per run, per-tool arg validation)

Policies are intentionally simple — they're the bare minimum to prevent
runaway tool loops and prompt-injection-driven tool calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.exceptions import ForbiddenError, ValidationError
from app.core.logging import get_logger
from app.llm.tool_calling import tools_to_gemini_spec
from app.mcp.client import McpClient, get_mcp_client

log = get_logger(__name__)


@dataclass
class ToolPolicy:
    max_total_calls: int = 10
    max_calls_per_tool: int = 4
    allowlist: List[str] = field(default_factory=list)


class ToolRegistry:
    """Wraps the MCP client with policy enforcement."""

    def __init__(self, client: McpClient | None = None, policy: ToolPolicy | None = None):
        self._client = client or get_mcp_client()
        self._policy = policy or ToolPolicy()
        self._calls_per_tool: Dict[str, int] = {}

    def list_for_gemini(self) -> List[Dict[str, Any]]:
        """Return Gemini-formatted tool spec for the LLM."""
        tools = self._client.list_tools()
        if self._policy.allowlist:
            tools = [t for t in tools if t.name in self._policy.allowlist]
        normalized = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]
        return tools_to_gemini_spec(normalized)

    def total_calls(self) -> int:
        return sum(self._calls_per_tool.values())

    async def invoke(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Policy check 1: tool exists + is allowlisted
        if self._policy.allowlist and name not in self._policy.allowlist:
            raise ForbiddenError(f"Tool '{name}' is not allowed")
        if not self._client.has_tool(name):
            raise ForbiddenError(f"Tool '{name}' is not available")

        # Policy check 2: per-tool call limit
        if self._calls_per_tool.get(name, 0) >= self._policy.max_calls_per_tool:
            raise ForbiddenError(
                f"Tool '{name}' exceeded max calls ({self._policy.max_calls_per_tool})"
            )

        # Policy check 3: total call budget
        if self.total_calls() >= self._policy.max_total_calls:
            raise ForbiddenError("Total tool call budget exhausted")

        # Validate args (basic — non-empty for required fields)
        td = self._client.get_tool(name)
        schema = td.input_schema
        required = schema.get("required", []) if isinstance(schema, dict) else []
        for r in required:
            if r not in arguments:
                raise ValidationError(f"Missing required argument '{r}' for tool '{name}'")

        # Invoke
        self._calls_per_tool[name] = self._calls_per_tool.get(name, 0) + 1
        log.info("tool_invoke", tool=name, args_keys=list(arguments.keys()))
        return await self._client.invoke_tool(name, arguments)