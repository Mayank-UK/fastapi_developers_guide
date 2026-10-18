"""Alembic environment: async engine on asyncpg, URL from the app config.

The URL never lives in alembic.ini — it is injected from the SAME
pydantic-settings rail the app uses (``guide.core.config``, the
``FDG_DATABASE_URL`` environment variable), so migrations and the app
can never disagree about which database they target. The target
metadata is the Core schema in ``guide.data.db.schema``; the async
template pattern is Alembic's cookbook recipe: build an async engine,
``run_sync`` the migration context over one connection, dispose.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from guide.core.config import get_config
from guide.data.db.schema import metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The URL comes from the app config rail UNLESS the caller already
# injected one into the Config (the lifespan and tests do — they may
# target a different database than the ambient FDG_ environment).
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", get_config().database_url)

target_metadata = metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a database (``alembic upgrade --sql``)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure the context over one live connection and run."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine from the config section, migrate, dispose."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Drive the async recipe with asyncio.run (sync alembic entrypoint)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
