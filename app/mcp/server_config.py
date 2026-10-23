"""
MCP server configuration.

Each MCP server is launched as a stdio subprocess from the API process.
We keep the launch command in config so we can swap transports later
(HTTP/SSE) without changing call sites.

Why subprocess + stdio:
- Simplest to set up — no extra ports or processes to manage externally.
- The MCP Python SDK provides a StdioServerTransport that works out of the box.
- Matches the plan's directive to "keep MCP servers inside the backend
  initially" — they ship in the same repo, just run as separate processes
  spawned on demand.

Server spec format:
    {
        "name": "rag",
        "command": "python",
        "args": ["-m", "app.mcp.servers.rag_server"],
        "env": {},
        "tools_allowlist": ["search_documents"],
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from app.core.config import get_settings


@dataclass
class McpServerSpec:
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: dict = field(default_factory=dict)
    tools_allowlist: List[str] = field(default_factory=list)


def get_server_specs() -> List[McpServerSpec]:
    """Return the list of MCP servers to launch."""
    settings = get_settings()
    python = "python"

    return [
        McpServerSpec(
            name="rag",
            command=python,
            args=["-m", "app.mcp.servers.rag_server"],
            tools_allowlist=["search_documents"],
        ),
        McpServerSpec(
            name="calculator",
            command=python,
            args=["-m", "app.mcp.servers.calculator_server"],
            tools_allowlist=["calculate"],
        ),
        McpServerSpec(
            name="weather",
            command=python,
            args=["-m", "app.mcp.servers.weather_server"],
            env={
                "WEATHER_API_BASE": settings.weather_api_base,
                "WEATHER_TIMEOUT_SECONDS": str(settings.weather_timeout_seconds),
            },
            tools_allowlist=["get_weather"],
        ),
    ]