"""
Async database engine and session factory.

We use SQLAlchemy 2.0 async style:
- `engine` is a single AsyncEngine per process.
- `AsyncSessionLocal` is a session factory used by FastAPI dependencies.
- `get_db_session` is the FastAPI dependency that yields a session and
  rolls back on exception.

The engine is created lazily so the app can boot without a live database
(needed for things like `alembic upgrade head` and tests).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

# Module-level singletons — created in init_db() (lifespan startup).
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db() -> None:
    """Create engine + session factory. Called once at app startup."""
    global _engine, _session_factory
    if _engine is not None:
        return

    settings = get_settings()
    log.info(
        "initializing_database",
        pool_size=settings.pg_pool_size,
        max_overflow=settings.pg_max_overflow,
    )
    _engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=settings.pg_pool_size,
        max_overflow=settings.pg_max_overflow,
        pool_timeout=settings.pg_pool_timeout,
        pool_pre_ping=True,  # recover from dropped connections
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def close_db() -> None:
    """Dispose engine — called on app shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        log.info("database_closed")
    _engine = None
    _session_factory = None


def get_engine() -> AsyncEngine:
    if _engine is None:
        init_db()
    assert _engine is not None
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        init_db()
    assert _session_factory is not None
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield a session, commit on success, rollback on error."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context-manager variant for use outside FastAPI deps (e.g., worker tasks)."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
