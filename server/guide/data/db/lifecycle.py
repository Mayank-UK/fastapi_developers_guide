"""Database lifecycle: apply migrations at startup, tolerantly.

Strategy (deliberate, documented): the app's lifespan runs
``alembic upgrade head`` ON STARTUP — idempotent (already-applied
revisions are a no-op that costs one version-table read), so every
environment converges on the schema without a deploy orchestration
step; the same command works from a terminal for humans
(``uv run alembic upgrade head``).

Alembic's ``command`` API is synchronous, and its async template runs
``asyncio.run`` internally — so the lifespan calls it through
``asyncio.to_thread``: a private event loop in a worker thread, never
the serving loop. Migrations are BEST-EFFORT at boot (the
optional-service discipline): with PostgreSQL down the app logs the
skip and serves everything that does not need the database; the
first DB-touching request then reports the outage through the
normal error taxonomy.
"""

import asyncio
from pathlib import Path
from typing import Final

import structlog
from alembic.config import Config

from alembic import command

logger = structlog.get_logger()

_SERVER_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
"""guide/data/db → guide → data → db … take three parents up: the server/
root of the REPO CHECKOUT, where the package runs editable and owns
alembic.ini + alembic/. Inside the production image the module lives in
the venv's site-packages — no alembic tree beside it — so the image
ships the same two assets at its working directory instead."""


def _alembic_root() -> Path:
    """The directory that owns alembic.ini + alembic/ for this deployment.

    The repo checkout wins (dev, CI, tests — resolution stays independent
    of the cwd); the production image falls back to its WORKDIR, where
    Dockerfile.prod copies the same single source of truth beside the
    app. When neither candidate carries the assets (a bare site-packages
    install), the checkout path is returned and the startup upgrade
    reports the miss through the normal best-effort skip.
    """
    for candidate in (_SERVER_ROOT, Path.cwd()):
        if (candidate / "alembic.ini").is_file():
            return candidate
    return _SERVER_ROOT


def build_alembic_config(database_url: str) -> Config:
    """Alembic config wired to this deployment: asset paths resolved per
    call (checkout first, image layout second), the URL injected from the
    app config (never stored in a file)."""
    root = _alembic_root()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def upgrade_database_to_head(database_url: str) -> None:
    """Synchronous ``alembic upgrade head`` (call via asyncio.to_thread)."""
    command.upgrade(build_alembic_config(database_url), "head")


async def upgrade_database_on_startup(database_url: str) -> None:
    """Best-effort startup migration: apply, or log the skip and continue."""
    try:
        await asyncio.to_thread(upgrade_database_to_head, database_url)
    except Exception as exc:
        logger.warning(
            "db_migrations_skipped",
            error=type(exc).__name__,
            detail=str(exc),
            hint="PostgreSQL may be down — the app stays up; DB-backed "
            "features will report service_unavailable until it returns.",
        )
    else:
        logger.info("db_migrations_applied", target="head")
