"""
Thin agent-side MCP adapter.

The lower-level MCP client lives in app/mcp/client.py. This module wraps it
so the agent imports from app.agent.* (matches the plan's layout) without
introducing a second implementation.

Functionally identical to calling get_mcp_client() directly.
"""

from __future__ import annotations

from app.mcp.client import McpClient, get_mcp_client, ensure_mcp_started


async def get_agent_mcp_client() -> McpClient:
    await ensure_mcp_started()
    return get_mcp_client()