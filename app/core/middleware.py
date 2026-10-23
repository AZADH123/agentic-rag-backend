"""
FastAPI middleware:
- Request ID injection (every log line + response header gets a request_id)
- Structured access logging
- Lightweight in-memory rate limiting (token bucket per IP)
- CORS

We intentionally keep middleware minimal — auth is handled in dependencies.py
so endpoints can opt in via Depends().
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request_id, bind it to structlog contextvars, log start/end."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        # Bind for the duration of this request so any log line includes it.
        from structlog.contextvars import bind_contextvars, clear_contextvars
        bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        method, path = request.method, request.url.path
        log.info("request_started", method=method, path=path)

        try:
            response = await call_next(request)
        except Exception:
            log.exception("request_failed", method=method, path=path)
            raise
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            log.info("request_finished",
                     method=method, path=path,
                     status_code=getattr(response, "status_code", 500),
                     duration_ms=elapsed_ms)
            clear_contextvars()

        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Naive per-IP fixed-window rate limiter. Production should use Redis.
    Good enough for protecting the upload endpoint from a runaway client.
    """

    def __init__(self, app: ASGIApp, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip rate limiting for health checks (so probes don't get blocked).
        if request.url.path.startswith("/health"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window

        bucket = self._hits[client_ip]
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            return Response(
                content='{"error":{"code":"rate_limited","message":"Too many requests"}}',
                status_code=429,
                media_type="application/json",
            )

        bucket.append(now)
        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware, max_requests=200, window_seconds=60)
    app.add_middleware(RequestContextMiddleware)