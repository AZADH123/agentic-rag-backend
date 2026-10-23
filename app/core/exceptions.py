"""
Domain-specific exception hierarchy and a FastAPI exception handler.

Why custom exceptions instead of raising HTTPException everywhere?
- Services shouldn't know they're being called from an HTTP context.
- Mapping a domain error to an HTTP status code is the API layer's job.
- Tests and other callers can catch domain errors cleanly.

Flow:
    Service raises DocumentNotFoundError
      → FastAPI catches via the registered handler
        → Handler returns a JSON error envelope with a stable shape.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


# ───────── Domain error base ─────────

class AppError(Exception):
    """Base class for all expected application errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "validation_error"


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"


class UpstreamError(AppError):
    """An external dependency (Gemini, S3, weather API) failed."""
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "upstream_error"


# ───────── Convenience subclasses ─────────

class DocumentNotFoundError(NotFoundError):
    code = "document_not_found"


class JobNotFoundError(NotFoundError):
    code = "job_not_found"


class ConversationNotFoundError(NotFoundError):
    code = "conversation_not_found"


class InvalidFileError(ValidationError):
    code = "invalid_file"


class StorageError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "storage_error"


# ───────── Handler registration ─────────

async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    # Don't leak internal tracebacks to clients in non-dev envs.
    from app.core.config import get_settings
    settings = get_settings()
    message = str(exc) if settings.is_dev else "Internal server error"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": message,
                "details": {},
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)