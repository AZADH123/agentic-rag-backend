"""
FastAPI app factory + module wiring.

This is the single entrypoint Uvicorn loads (`uvicorn app.main:app`).

Responsibilities:
1. Create the FastAPI instance.
2. Register middleware (CORS, request_id, rate limit).
3. Register exception handlers (consistent JSON error envelope).
4. Mount the API router under the configured prefix.
5. Wire lifespan (startup/shutdown).
"""
from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.router import router as api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger
from app.core.middleware import register_middleware
from app.lifespan import lifespan

log = get_logger(__name__)
settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Modular Agentic RAG backend — FastAPI + Gemini + BGE + pgvector + MCP",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Middleware must be added before routes (FastAPI quirk).
    register_middleware(app)
    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    # Also expose /health at root (without /api/v1 prefix) for k8s probes.
    from app.api.v1.health import router as health_router
    app.include_router(health_router, prefix="/health", tags=["health"])

    return app


app = create_app()