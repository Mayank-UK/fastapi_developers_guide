"""The async engine factory: one config rail, one engine.

Every database-touching adapter (the introspection reader, the audit
writer, topic 17's repositories) shares engines built here, so pooling
and pre-ping policy live in exactly one place. Engines are lazy —
construction opens nothing, which keeps ``create_app()`` cheap in tests
and lets the app boot with PostgreSQL down (the optional-service
discipline: connections are attempted per use, failures degrade).
"""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from guide.core.config import AppConfig


def create_db_engine(config: AppConfig) -> AsyncEngine:
    """Build the process's async engine from the app config's URL rail.

    ``pool_pre_ping`` so a PostgreSQL restart between requests surfaces as
    a clean reconnect instead of a stale-socket error; pool sizing stays
    at SQLAlchemy's defaults until topic 38 measures real load.
    """
    return create_async_engine(config.database_url, pool_pre_ping=True)
