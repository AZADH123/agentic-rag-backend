"""
Alembic env.py — async + uses our app Settings for the DB URL.

We import all model modules so Alembic's `target_metadata` knows about every
table. As new modules are added, register them in `IMPORTED_MODELS`.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.database.base import Base

# ── Register every module that defines ORM models ──
# (importing them registers their tables on Base.metadata)
# Models are imported here as they are added in later phases. To avoid
# import errors during Phase 1 (no models yet), each import is wrapped
# in a try/except. Once all phases are built, replace this block with
# direct imports.
for _module in (
    "app.modules.documents.models",
    "app.modules.ingestion_jobs.models",
    "app.modules.conversations.models",
    "app.rag.indexing.indexer",
):
    try:
        __import__(_module)
    except ImportError:
        pass

# Alembic config object (loaded from alembic.ini).
config = context.config

# Override sqlalchemy.url from our app settings so .env is honored.
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# Logging from alembic.ini [loggers] section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL script without a DB connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        # Render server_default for created/updated timestamps.
        render_as_batch=False,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against a live (async) DB connection."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())