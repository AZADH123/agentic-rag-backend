"""
Structured logging configuration.

We use structlog for two reasons:
1. Every log line is a JSON object with stable fields (request_id, level,
   event, etc.) — easy to grep and ship to a log aggregator.
2. We can redact secret values up-front by configuring processors.

Usage:
    from app.core.logging import get_logger
    log = get_logger(__name__)
    log.info("document_uploaded", document_id=doc.id, filename=doc.filename)

The middleware in middleware.py adds request_id to every log line for the
duration of an HTTP request.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.config import get_settings


# Keys whose values should never appear in logs.
_REDACT_KEYS = {
    "password",
    "api_key",
    "apikey",
    "secret",
    "token",
    "authorization",
    "aws_secret_access_key",
    "gemini_api_key",
}


def _redact_processor(_logger: Any, _method: str, event_dict: EventDict) -> EventDict:
    """Replace secret-looking values with `[REDACTED]`."""
    for key in list(event_dict.keys()):
        low = key.lower()
        if any(s in low for s in _REDACT_KEYS):
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging() -> None:
    """Configure root + structlog logging. Call once at app startup."""
    settings = get_settings()

    # Standard library logging level
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stderr,
    )

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact_processor,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_json:
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=settings.is_dev)

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # Bridge stdlib logging into structlog so libraries (uvicorn, sqlalchemy,
    # boto3) produce the same structured output.
    logging.getLogger("uvicorn.access").handlers = []
    structlog.stdlib.ProcessorFormatter.wrap_for_formatter


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to `name` (usually __name__)."""
    return structlog.get_logger(name)  # type: ignore[return-value]