"""
Weather MCP server.

Tool: get_weather(location: str) -> dict
Uses Open-Meteo's geocoding + forecast APIs. No API key required.

Flow:
1. Call https://geocoding-api.open-meteo.com/v1/search?name=<location>
   to resolve the location name to lat/long.
2. Call https://api.open-meteo.com/v1/forecast?lat=..&lon=..&current_weather=true
   to get the current weather.
3. Return a compact dict.

If the location is ambiguous (multiple matches), we use the first one but
also include alternatives so the agent can refine the query.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List

import httpx

from app.core.logging import configure_logging, get_logger

log = get_logger(__name__)


async def _get_weather(location: str) -> Dict[str, Any]:
    base = os.environ.get("WEATHER_API_BASE", "https://api.open-meteo.com/v1")
    timeout = float(os.environ.get("WEATHER_TIMEOUT_SECONDS", "10"))

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Geocode
        geo = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 5, "language": "en", "format": "json"},
        )
        geo.raise_for_status()
        geo_data = geo.json()
        results = geo_data.get("results") or []
        if not results:
            return {"error": f"Location not found: {location}"}
        top = results[0]

        # Forecast
        weather = await client.get(
            f"{base}/forecast",
            params={
                "latitude": top["latitude"],
                "longitude": top["longitude"],
                "current_weather": True,
            },
        )
        weather.raise_for_status()
        w = weather.json().get("current_weather") or {}

        return {
            "location": top["name"],
            "country": top.get("country"),
            "latitude": top["latitude"],
            "longitude": top["longitude"],
            "temperature_c": w.get("temperature"),
            "wind_speed_kmh": w.get("windspeed"),
            "weather_code": w.get("weathercode"),
            "time": w.get("time"),
            "alternatives": [
                {"name": r["name"], "country": r.get("country"),
                 "lat": r["latitude"], "lon": r["longitude"]}
                for r in results[1:3]
            ],
        }


def _build_tool_spec() -> Dict[str, Any]:
    return {
        "name": "get_weather",
        "description": (
            "Get the current weather for a named location (city, town, etc.). "
            "Returns temperature, wind speed, weather code, and alternative matches."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City or place name."},
            },
            "required": ["location"],
        },
    }


async def _serve() -> None:
    configure_logging()
    log.info("weather_mcp_server_starting")

    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

    server: Server = Server("weather")

    @server.list_tools()
    async def _list_tools() -> List[Tool]:
        spec = _build_tool_spec()
        return [Tool(name=spec["name"], description=spec["description"],
                     inputSchema=spec["inputSchema"])]

    @server.call_tool()
    async def _call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        if name != "get_weather":
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        try:
            result = await _get_weather(arguments["location"])
            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            log.exception("get_weather_failed")
            return [TextContent(type="text", text=f"ERROR: {e}")]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_serve())