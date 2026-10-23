"""
Tool discovery endpoints.

GET   /tools            — list configured MCP tools
GET   /tools/{name}     — get a tool's description and input schema

These endpoints never invoke tools directly. Tool invocation goes through
the MCP client (which is the same path the agent uses), so the security
model is unified.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from app.core.exceptions import NotFoundError
from app.dependencies import get_current_owner
from app.mcp.client import get_mcp_client

router = APIRouter()


class ToolResponse(BaseModel):
    name: str
    description: str
    server: str
    input_schema: Dict[str, Any] = {}


class ToolListResponse(BaseModel):
    tools: List[ToolResponse]


@router.get("", response_model=ToolListResponse)
async def list_tools(owner: str = Depends(get_current_owner)):
    client = get_mcp_client()
    tools = client.list_tools()
    return ToolListResponse(
        tools=[
            ToolResponse(
                name=t.name,
                description=t.description,
                server=t.server_name,
                input_schema=t.input_schema,
            )
            for t in tools
        ]
    )


@router.get("/{tool_name}", response_model=ToolResponse)
async def get_tool(
    tool_name: str,
    owner: str = Depends(get_current_owner),
):
    client = get_mcp_client()
    try:
        td = client.get_tool(tool_name)
    except NotFoundError:
        raise
    return ToolResponse(
        name=td.name,
        description=td.description,
        server=td.server_name,
        input_schema=td.input_schema,
    )