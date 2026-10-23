"""
RAG MCP server.

Exposes one tool to the agent:
    search_documents(query: str, top_k: int = 5, filters: dict = {})

The server uses the SAME retriever that powers /api/v1/retrieval/search.
For the stdio transport (in-process), we instantiate the retriever per
call (cheap; the embedding model is cached at module level).

Run standalone (for debugging):
    python -m app.mcp.servers.rag_server
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List

from app.core.logging import configure_logging, get_logger
from app.core.security import require_api_key  # noqa: F401  (placeholder)
from app.database.session import init_db

log = get_logger(__name__)


async def _search_documents(
    query: str,
    top_k: int = 5,
    filters: Dict[str, Any] | None = None,
    owner_id: str | None = None,
) -> List[Dict[str, Any]]:
    """Implementation of the search_documents tool."""
    from app.database.session import db_session
    from app.rag.retrieval.retriever import Retriever

    async with db_session() as session:
        retriever = Retriever(session)
        hits = await retriever.search(
            query,
            owner_id=owner_id,
            top_k=top_k,
            filters=filters,
        )
        return [
            {
                "document_id": h.document_id,
                "chunk_id": h.chunk_id,
                "text": h.text,
                "score": round(h.score, 4),
                "page": h.page,
                "filename": h.metadata.get("filename"),
            }
            for h in hits
        ]


def _build_tool_spec() -> Dict[str, Any]:
    return {
        "name": "search_documents",
        "description": (
            "Search the indexed knowledge base for chunks relevant to a query. "
            "Returns up to top_k chunks with document_id, chunk_id, text, score, "
            "page, and filename metadata."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural-language search query."},
                "top_k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
                "filters": {
                    "type": "object",
                    "description": "Optional metadata filters (e.g. {filename: 'policy.pdf'}).",
                    "default": {},
                },
            },
            "required": ["query"],
        },
    }


async def _serve() -> None:
    """Run the MCP server over stdio using the official MCP Python SDK."""
    configure_logging()
    init_db()
    # Pre-warm embedding model so first tool invocation is fast
    from app.rag.embeddings.model_loader import get_model
    get_model()
    log.info("rag_mcp_server_starting")

    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Tool, TextContent
    except ImportError as e:
        log.error("mcp_sdk_missing", error=str(e))
        raise

    server: Server = Server("rag")

    @server.list_tools()
    async def _list_tools() -> List[Tool]:
        spec = _build_tool_spec()
        return [
            Tool(
                name=spec["name"],
                description=spec["description"],
                inputSchema=spec["inputSchema"],
            )
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        if name != "search_documents":
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        try:
            # Owner isolation: the MCP server doesn't have HTTP request context.
            # For local dev we use DEFAULT_OWNER_ID. In production you'd want
            # the agent to pass an owner_id argument.
            from app.core.config import get_settings
            owner = arguments.get("owner_id") or get_settings().default_owner_id

            results = await _search_documents(
                query=arguments["query"],
                top_k=arguments.get("top_k", 5),
                filters=arguments.get("filters", {}),
                owner_id=owner,
            )
            import json
            return [TextContent(type="text", text=json.dumps({"results": results}))]
        except Exception as e:
            log.exception("search_documents_failed")
            return [TextContent(type="text", text=f"ERROR: {e}")]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_serve())