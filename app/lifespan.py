"""
Application lifespan: startup and shutdown of shared resources.

Anything that needs to be initialized exactly once per process lives here:
- structured logging
- database engine
- S3 bucket creation (dev convenience)
- MCP client connection pool (added in Phase 7)
- embedding model loader (added in Phase 4)

Startup failures should crash fast — we don't want a half-working API.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.database.session import close_db, init_db

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging()
    log.info("startup_begin", app=settings.app_name, env=settings.app_env)

    # Database engine (lazy init on first use, but we eagerly init so a
    # misconfigured DATABASE_URL fails the boot instead of the first request).
    init_db()
    log.info("database_ready")

    # Ensure S3 bucket exists (dev convenience; prod should pre-provision).
    try:
        from app.storage.s3_client import ensure_bucket_exists
        ensure_bucket_exists()
        log.info("storage_ready", backend=settings.storage_backend,
                 bucket=settings.s3_bucket_name)
    except Exception as e:
        # Non-fatal: uploads will simply fail later with a clear error.
        log.warning("storage_init_failed", error=str(e))

    # Start MCP client (Phase 7). Servers are launched as stdio subprocesses.
    # Non-fatal: the API can still serve document/retrieval endpoints without MCP.
    try:
        from app.mcp.client import ensure_mcp_started
        await ensure_mcp_started()
        log.info("mcp_ready")
    except Exception as e:
        log.warning("mcp_init_failed", error=str(e))

    log.info("startup_complete")
    try:
        yield
    finally:
        log.info("shutdown_begin")
        # Close MCP servers gracefully.
        try:
            from app.mcp.client import get_mcp_client
            await get_mcp_client().close_all()
        except Exception as e:
            log.warning("mcp_shutdown_failed", error=str(e))
        await close_db()
        log.info("shutdown_complete")