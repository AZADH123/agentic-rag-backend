"""Re-export response_parser from tool_calling for naming consistency."""

from app.llm.tool_calling import _parse_response as parse_response  # noqa: F401