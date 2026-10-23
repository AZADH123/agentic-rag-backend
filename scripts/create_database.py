"""
One-shot script: create the application database (and pgvector extension)
before running alembic migrations.

Usage:
    python scripts/create_database.py

This connects to the *maintenance* database (postgres) using the same
credentials as DATABASE_URL, then CREATE DATABASE if it doesn't exist,
then enables the vector extension.

It's safe to re-run.
"""

from __future__ import annotations

import asyncio
import re
import sys
from urllib.parse import urlparse

import asyncpg


def parse_db_url(url: str) -> tuple[str, str, str, str]:
    """Return (postgres_dsn, app_db_name, user, password)."""
    p = urlparse(url)
    return (
        f"postgresql://{p.username}:{p.password}@{p.hostname}:{p.port or 5432}/postgres",
        p.path.lstrip("/"),
        p.username or "",
        p.password or "",
    )


async def main() -> None:
    from app.core.config import get_settings
    settings = get_settings()

    admin_dsn, db_name, user, password = parse_db_url(settings.database_url)
    if not db_name:
        print("ERROR: could not parse database name from DATABASE_URL", file=sys.stderr)
        sys.exit(1)

    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )
        if exists:
            print(f"[skip] database '{db_name}' already exists")
        else:
            # CREATE DATABASE cannot be parameterized.
            safe_name = re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", db_name)
            if not safe_name:
                print(f"ERROR: invalid database name '{db_name}'", file=sys.stderr)
                sys.exit(1)
            await conn.execute(f'CREATE DATABASE "{db_name}" OWNER "{user}"')
            print(f"[ok] created database '{db_name}' owned by '{user}'")
    finally:
        await conn.close()

    # Connect to the new DB and enable pgvector.
    app_dsn = settings.database_url.replace("+asyncpg", "")
    conn = await asyncpg.connect(app_dsn)
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("[ok] enabled pgvector extension")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())