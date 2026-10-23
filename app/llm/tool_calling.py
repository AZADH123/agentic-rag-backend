"""
Tool calling helpers.

Converts our internal ToolDefinition objects (produced by the MCP client
in Phase 7) into Gemini's function-declaration format, and parses Gemini's
function_call responses back into our ToolCallRequest objects.

Gemini's tool spec shape (high level):
    {
        "function_declarations": [
            {
                "name": "search_documents",
                "description": "...",
                "parameters": {  # JSON Schema
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        ]
    }

Gemini's function_call response shape:
    parts: [
        {"function_call": {"name": "search_documents", "args": {...}}}
    ]
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.llm.gemini_client import LLMResponse, ToolCallRequest


def _normalize_schema_for_gemini(schema: Any) -> Any:
    """Uppercase type strings ('object' -> 'OBJECT') as expected by google-genai SDK."""
    if isinstance(schema, dict):
        return {
            k: (v.upper() if k == "type" and isinstance(v, str) else _normalize_schema_for_gemini(v))
            for k, v in schema.items()
        }
    if isinstance(schema, list):
        return [_normalize_schema_for_gemini(x) for x in schema]
    return schema


def tools_to_gemini_spec(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert our normalized tool list into Gemini's `tools` argument shape.

    Each input tool is:
        {
            "name": str,
            "description": str,
            "input_schema": {json_schema_object}
        }
    """
    decls = []
    for t in tools:
        raw_schema = t.get("input_schema", {"type": "object", "properties": {}})
        norm_schema = _normalize_schema_for_gemini(raw_schema)
        decls.append({
            "name": t["name"],
            "description": t["description"],
            "parameters": norm_schema,
        })
    return [{"function_declarations": decls}] if decls else []


def build_tool_response_part(tool_name: str, response: Dict[str, Any]) -> Dict[str, Any]:
    """Build a function_response part to send back to Gemini after a tool runs."""
    return {
        "role": "user",  # Gemini expects function_response to come from "user" role
        "parts": [
            {"function_response": {"name": tool_name, "response": response}}
        ]
    }


def build_text_part(role: str, text: str) -> Dict[str, Any]:
    return {"role": role, "parts": [{"text": text}]}


def _parse_response(raw: Any) -> LLMResponse:
    """Parse a google-genai response into our LLMResponse."""
    text_parts: List[str] = []
    tool_calls: List[ToolCallRequest] = []
    usage = {}

    # The SDK returns an object with .candidates, .text, .usage_metadata.
    candidates = getattr(raw, "candidates", None) or []
    if candidates:
        c = candidates[0]
        content = getattr(c, "content", None)
        if content is not None:
            for part in getattr(content, "parts", []) or []:
                # Text part
                txt = getattr(part, "text", None)
                if txt:
                    text_parts.append(txt)
                # Function call part
                fc = getattr(part, "function_call", None)
                if fc is not None:
                    name = getattr(fc, "name", None) or (fc.get("name") if isinstance(fc, dict) else None)
                    args = getattr(fc, "args", None)
                    if args is None and isinstance(fc, dict):
                        args = fc.get("args", {})
                    args = dict(args) if args else {}
                    tool_calls.append(ToolCallRequest(
                        tool_name=name or "",
                        arguments=args,
                        call_id=getattr(fc, "id", None),
                    ))

    um = getattr(raw, "usage_metadata", None)
    if um is not None:
        usage = {
            "prompt_tokens": getattr(um, "prompt_token_count", 0) or 0,
            "output_tokens": getattr(um, "candidates_token_count", 0) or 0,
            "total_tokens": getattr(um, "total_token_count", 0) or 0,
        }

    return LLMResponse(
        text=" ".join(text_parts).strip() if text_parts else None,
        tool_calls=tool_calls,
        finish_reason=str(getattr(candidates[0], "finish_reason", "STOP")) if candidates else "STOP",
        usage=usage,
        raw=raw,
    )