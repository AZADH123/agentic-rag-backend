"""
API-key based auth and a tiny RBAC placeholder.

This is intentionally simple — production would use JWT/OAuth/OIDC.
Auth is OFF in development unless API_KEY is set in .env.

Usage in a route:
    from fastapi import Depends
    from app.dependencies import get_current_owner

    @router.get("/documents")
    async def list_documents(owner: str = Depends(get_current_owner)):
        ...
"""

from __future__ import annotations

from fastapi import Header, Request

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.logging import get_logger

log = get_logger(__name__)


async def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    """
    Return the owner identifier if the request is authorized.

    If `API_KEY` env is unset, auth is disabled (development mode) and
    we return the configured `DEFAULT_OWNER_ID`.

    If `API_KEY` is set, the client must send `X-API-Key: <same value>`.
    """
    settings = get_settings()
    expected = settings.api_key.get_secret_value()

    if not expected:
        # Auth disabled — assign a stable dev owner.
        owner = settings.default_owner_id
        request.state.owner = owner
        return owner

    if not x_api_key or x_api_key != expected:
        log.warning("unauthorized_request", path=request.url.path)
        raise UnauthorizedError("Missing or invalid API key")

    # In this minimal model, the API key IS the owner identity.
    owner = settings.default_owner_id
    request.state.owner = owner
    return owner