"""
Calculator MCP server.

Tool: calculate(a: float, b: float, operation: str) -> float
where operation ∈ {"add", "subtract", "multiply", "divide"}.

Security: we do NOT eval() or exec() arbitrary expressions. Only the four
fixed operations are allowed, dispatched explicitly. Division by zero is
returned as a structured error.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

from app.core.logging import configure_logging, get_logger

log = get_logger(__name__)


_OPERATIONS = {
    "add": lambda a, b: a + b,
    "subtract": lambda a, b: a - b,
    "multiply": lambda a, b: a * b,
    # divide handled separately for zero-check
}


def _calculate(a: float, b: float, operation: str) -> Dict[str, Any]:
    if operation not in _OPERATIONS and operation != "divide":
        return {"error": f"Unsupported operation: {operation}"}
    if operation == "divide":
        if b == 0:
            return {"error": "Division by zero"}
        return {"result": a / b}
    return {"result": _OPERATIONS[operation](a, b)}


def _build_tool_spec() -> Dict[str, Any]:
    return {
        "name": "calculate",
        "description": (
            "Perform a single arithmetic operation on two numeric operands. "
            "Supported operations: add, subtract, multiply, divide."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First operand."},
                "b": {"type": "number", "description": "Second operand."},
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                },
            },
            "required": ["a", "b", "operation"],
        },
    }


async def _serve() -> None:
    configure_logging()
    log.info("calculator_mcp_server_starting")

    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

    server: Server = Server("calculator")

    @server.list_tools()
    async def _list_tools() -> List[Tool]:
        spec = _build_tool_spec()
        return [Tool(name=spec["name"], description=spec["description"],
                     inputSchema=spec["inputSchema"])]

    @server.call_tool()
    async def _call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        if name != "calculate":
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        try:
            result = _calculate(
                float(arguments["a"]),
                float(arguments["b"]),
                arguments["operation"],
            )
            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            log.exception("calculate_failed")
            return [TextContent(type="text", text=f"ERROR: {e}")]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_serve())