
"""
Gemini client.

Uses the official `google-genai` SDK (the new unified SDK, not the legacy
google-generativeai package).

Key responsibilities:
1. Wrap the SDK behind our own LLMClient interface so the agent orchestrator
   has no Gemini imports.
2. Convert our tool definitions (from the MCP client) into the format Gemini
   expects.
3. Parse Gemini responses into structured outputs (text, tool_calls).

Error handling:
- Timeouts and rate limits raise UpstreamError so the agent loop can decide
  whether to retry or surface to the user.
- We never leak the API key into exception messages.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.core.exceptions import UpstreamError
from app.core.logging import get_logger
from app.llm.model_factory import get_chat_model

log = get_logger(__name__)


@dataclass
class ToolCallRequest:
    """A request from the LLM to invoke a tool."""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class LLMResponse:
    """Structured view of one Gemini chat completion."""
    text: Optional[str] = None
    tool_calls: List[ToolCallRequest] = field(default_factory=list)
    finish_reason: str = "STOP"
    usage: Dict[str, int] = field(default_factory=dict)
    raw: Any = None


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from a dictionary or a typed SDK object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class GeminiClient:
    """Thin wrapper over google-genai."""

    def __init__(self):
        settings = get_settings()
        api_key = settings.gemini_api_key.get_secret_value()

        if not api_key:
            raise UpstreamError("GEMINI_API_KEY is not set")

        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError as exc:
            raise UpstreamError("google-genai SDK not installed") from exc

        self._genai = genai
        self._genai_types = genai_types
        self._client = genai.Client(api_key=api_key)
        self._model = get_chat_model()
        self._timeout = settings.gemini_timeout_seconds
        self._temperature = settings.gemini_temperature
        self._max_output_tokens = settings.gemini_max_output_tokens

        log.info("gemini_client_ready", model=self._model)

    async def chat(
        self,
        *,
        system_instruction: str,
        contents: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """
        Run one chat turn.

        Supports dictionary-based conversation messages and typed Gemini
        Content/Part objects. Function-call and function-response parts are
        preserved when already represented as SDK objects.
        """
        try:
            types = self._genai_types

            afc = types.AutomaticFunctionCallingConfig(disable=True)

            gen_config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=self._temperature,
                max_output_tokens=self._max_output_tokens,
                tools=tools if tools else None,
                automatic_function_calling=afc if tools else None,
            )

            sdk_contents: list[Any] = []

            for content in contents:
                # Already a typed Gemini Content object.
                if isinstance(content, types.Content):
                    sdk_contents.append(content)
                    continue

                role = _get_value(content, "role", "user")
                # Gemini expects function/tool responses under the "user" role
                if role == "tool":
                    role = "user"

                raw_parts = _get_value(content, "parts", []) or []
                sdk_parts: list[Any] = []

                for part in raw_parts:
                    # Preserve existing SDK Part objects, including
                    # function_call and function_response parts.
                    if isinstance(part, types.Part):
                        sdk_parts.append(part)

                    elif isinstance(part, str):
                        sdk_parts.append(types.Part(text=part))

                    elif isinstance(part, dict) and "text" in part:
                        sdk_parts.append(types.Part(text=part["text"]))

                    elif isinstance(part, dict) and "function_response" in part:
                        fr = part["function_response"]
                        fn_name = fr.get("name", "")
                        fn_resp = fr.get("response", {})
                        if hasattr(types.Part, "from_function_response"):
                            sdk_parts.append(
                                types.Part.from_function_response(
                                    name=fn_name, response=fn_resp
                                )
                            )
                        else:
                            sdk_parts.append(
                                types.Part(
                                    function_response=types.FunctionResponse(
                                        name=fn_name, response=fn_resp
                                    )
                                )
                            )

                    elif isinstance(part, dict) and "function_call" in part:
                        fc = part["function_call"]
                        fn_name = fc.get("name", "")
                        fn_args = fc.get("args", {})
                        if hasattr(types.Part, "from_function_call"):
                            sdk_parts.append(
                                types.Part.from_function_call(
                                    name=fn_name, args=fn_args
                                )
                            )
                        else:
                            sdk_parts.append(
                                types.Part(
                                    function_call=types.FunctionCall(
                                        name=fn_name, args=fn_args
                                    )
                                )
                            )

                    elif _get_value(part, "text") is not None:
                        sdk_parts.append(
                            types.Part(text=_get_value(part, "text"))
                        )

                    else:
                        # Preserve other SDK-compatible part objects.
                        sdk_parts.append(part)

                sdk_contents.append(
                    types.Content(
                        role=role,
                        parts=sdk_parts,
                    )
                )

            import anyio

            def _call():
                return self._client.models.generate_content(
                    model=self._model,
                    contents=sdk_contents,
                    config=gen_config,
                )

            raw = None

            for attempt in range(3):
                try:
                    raw = await anyio.to_thread.run_sync(_call)
                    break

                except Exception as exc:
                    exc_str = str(exc)

                    is_temporary = (
                        "503" in exc_str
                        or "UNAVAILABLE" in exc_str
                        or "temporarily" in exc_str.lower()
                    )

                    if is_temporary and attempt < 2:
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue

                    raise

            from app.llm.tool_calling import _parse_response

            return _parse_response(raw)

        except Exception as exc:
            msg = str(exc)

            log.error(
                "gemini_call_failed",
                error=msg[:200],
            )

            if (
                "API_KEY" in msg.upper()
                or "permission" in msg.lower()
                or "unauthorized" in msg.lower()
            ):
                raise UpstreamError(
                    "Gemini auth failed — check GEMINI_API_KEY"
                ) from exc

            if (
                "RESOURCE_EXHAUSTED" in msg
                or "quota exceeded" in msg.lower()
            ):
                raise UpstreamError(
                    "Gemini rate limit / quota exceeded"
                ) from exc

            if "503" in msg or "UNAVAILABLE" in msg:
                raise UpstreamError(
                    "Gemini service temporarily unavailable "
                    "(high demand), please retry"
                ) from exc

            raise UpstreamError(
                f"Gemini call failed: {msg[:300]}"
            ) from exc
