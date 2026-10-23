"""
Shared FastAPI dependencies.

Centralizing dependencies here keeps route signatures clean and makes it
trivial to swap implementations (e.g., in tests).

Common pattern:
    @router.get("/foo")
    async def foo(session: AsyncSession = Depends(get_db_session),
                  owner: str = Depends(get_current_owner)):
        ...
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.database.session import get_db_session


async def get_current_owner(owner: str = Depends(require_api_key)) -> str:
    """Return the authenticated owner ID. See core/security.py."""
    return owner


async def get_session(session: AsyncSession = Depends(get_db_session)) -> AsyncSession:
    """Alias for get_db_session so routers have a clearer name."""
    return session