
"""
MCP client.

Lazily launches each configured MCP server using stdio transport,
discovers its tools, and exposes them through a uniform interface.

Lifecycle:
- get_mcp_client() returns the singleton client.
- start() launches configured MCP servers and discovers their tools.
- close_all() closes sessions and terminates subprocesses.

Tool invocation:
    result = await client.invoke_tool(
        "search_documents",
        {"query": "..."},
    )
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from contextlib import AsyncExitStack
from typing import Any, Dict, List

from app.core.exceptions import (
    NotFoundError,
    UpstreamError,
)
from app.core.logging import get_logger
from app.mcp.server_config import (
    McpServerSpec,
    get_server_specs,
)

log = get_logger(__name__)


@dataclass
class ToolDefinition:
    """Description of a tool discovered from an MCP server."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


class McpClient:
    """MCP client that manages server sessions and discovered tools."""

    def __init__(self) -> None:
        self._specs: List[McpServerSpec] = []
        self._sessions: Dict[str, Any] = {}
        self._tools: List[ToolDefinition] = []
        self._tools_by_name: Dict[str, ToolDefinition] = {}
        self._started = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start configured MCP servers and discover available tools."""
        async with self._lock:
            if self._started:
                return

            self._specs = get_server_specs()

            log.info(
                "mcp_starting",
                server_count=len(self._specs),
                python_executable=sys.executable,
            )

            for spec in self._specs:
                await self._launch_server(spec)

            self._started = True

            log.info(
                "mcp_client_ready",
                servers=list(self._sessions.keys()),
                tools=[tool.name for tool in self._tools],
                failed_servers=[
                    spec.name
                    for spec in self._specs
                    if spec.name not in self._sessions
                ],
            )

    async def _launch_server(self, spec: McpServerSpec) -> None:
        """Launch one MCP subprocess and discover its tools."""

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            log.exception("mcp_sdk_missing")
            raise UpstreamError("MCP SDK is not installed") from exc

        # Use this application's interpreter for Python MCP servers.
        # This ensures subprocesses use the active virtual environment.
        command = (
            sys.executable
            if spec.command.lower() in {"python", "python3"}
            else spec.command
        )

        # Inherit environment variables and apply server-specific overrides.
        env = {**os.environ, **spec.env}

        params = StdioServerParameters(
            command=command,
            args=spec.args,
            env=env,
        )

        log.info(
            "launching_mcp_server",
            name=spec.name,
            command=command,
            args=spec.args,
        )

        stack = AsyncExitStack()

        try:
            # Start the stdio subprocess and enter the MCP client session.
            read_stream, write_stream = await stack.enter_async_context(
                stdio_client(params)
            )
            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()

            # Discover the server's tools.
            tools_response = await session.list_tools()
            registered_count = 0

            for tool in tools_response.tools:
                # Respect the server's configured tool allowlist.
                if (
                    spec.tools_allowlist
                    and tool.name not in spec.tools_allowlist
                ):
                    log.info(
                        "tool_not_in_allowlist",
                        server=spec.name,
                        tool=tool.name,
                    )
                    continue

                definition = ToolDefinition(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=(
                        tool.inputSchema
                        or {
                            "type": "object",
                            "properties": {},
                        }
                    ),
                    server_name=spec.name,
                )

                # Avoid stale duplicate registrations.
                existing = self._tools_by_name.get(tool.name)
                if existing is not None:
                    log.warning(
                        "duplicate_mcp_tool_name",
                        tool=tool.name,
                        existing_server=existing.server_name,
                        new_server=spec.name,
                    )
                    continue

                self._tools.append(definition)
                self._tools_by_name[tool.name] = definition
                registered_count += 1

            # Retain session + stack so sessions remain alive.
            self._sessions[spec.name] = (session, stack)

            log.info(
                "mcp_server_ready",
                server=spec.name,
                tools_registered=registered_count,
            )

        except Exception as exc:
            log.exception(
                "mcp_launch_failed",
                server=spec.name,
                command=command,
                args=spec.args,
                error=str(exc),
            )
            try:
                await stack.aclose()
            except Exception:
                pass

    async def close_all(self) -> None:
        """Close MCP sessions and their subprocess contexts."""
        for name, (_, stack) in list(self._sessions.items()):
            try:
                await stack.aclose()
            except (Exception, asyncio.CancelledError):
                log.warning(
                    "mcp_session_close_failed",
                    server=name,
                )

        self._sessions.clear()
        self._tools.clear()
        self._tools_by_name.clear()
        self._started = False

        log.info("mcp_client_closed")

    def list_tools(self) -> List[ToolDefinition]:
        """Return all currently registered tools."""
        return list(self._tools)

    def get_tool(self, name: str) -> ToolDefinition:
        """Return a registered tool by name."""
        definition = self._tools_by_name.get(name)

        if definition is None:
            raise NotFoundError(
                f"Tool '{name}' is not available"
            )

        return definition

    def has_tool(self, name: str) -> bool:
        """Check whether a tool is registered."""
        return name in self._tools_by_name

    async def invoke_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Invoke a registered MCP tool and return its output."""
        definition = self.get_tool(name)

        session_info = self._sessions.get(definition.server_name)
        if session_info is None:
            raise UpstreamError(
                f"MCP server '{definition.server_name}' is not running"
            )

        session, _ = session_info

        try:
            log.info(
                "invoking_tool",
                name=name,
                args_keys=list(arguments.keys()),
            )

            result = await session.call_tool(
                name,
                arguments=arguments,
            )

            # Collect text output from MCP content items.
            texts: List[str] = []

            for content in result.content:
                text = getattr(content, "text", None)
                if text:
                    texts.append(text)

            raw = "\n".join(texts)

            # Return JSON objects when the tool returns JSON text.
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
                if isinstance(parsed, list):
                    return {"results": parsed}
            except json.JSONDecodeError:
                pass

            return {"text": raw}

        except Exception as exc:
            log.exception(
                "tool_invocation_failed",
                name=name,
                error=str(exc),
            )
            raise UpstreamError(
                f"Tool '{name}' invocation failed: {exc}"
            ) from exc


# Module-level singleton.
_client: McpClient | None = None


def get_mcp_client() -> McpClient:
    """Return the process-local MCP client singleton."""
    global _client

    if _client is None:
        _client = McpClient()

    return _client


async def ensure_mcp_started() -> None:
    """Start the MCP client during application startup."""
    client = get_mcp_client()
    await client.start()
