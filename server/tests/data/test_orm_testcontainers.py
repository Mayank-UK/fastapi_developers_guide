"""The clean-database round-trip: a REAL throwaway PostgreSQL.

This is the testcontainers wiring the whole guide uses from topic 18
on: spin up a disposable PostgreSQL container, point Alembic's FULL
chain at it (``0001 → 0003``, nothing pre-applied), and prove the ORM
stack works on a database nobody seeded or migrated by hand — create,
eager load, commit a version bump, refuse a stale write. If this
passes, the migrations + models + sessions are self-sufficient; that
is the entire point of testing against a clean database.

Honest skipping: these tests need a REACHABLE Docker daemon. The
dev/verify container has no docker.sock, so the probe below fails
there and every test in this module SKIPS with the reason — the
in-container full suite stays green without pretending to have run
them. The host-run fallback command mounts docker.sock (+ TESTCONTAINERS_
HOST_OVERRIDE) and runs ``pytest -m testcontainers``, where the probe
passes and the tests run FOR REAL.
"""

import asyncio
import os
import socket
from collections.abc import Iterator
from typing import Final

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import StaleDataError
from testcontainers.community.postgres import PostgresContainer

from guide.data.db.lifecycle import build_alembic_config, upgrade_database_to_head
from guide.data.db.orm import Author, OrmProbeRepository, Post, create_session_factory

POSTGRES_IMAGE: Final = "postgres:17"
"""The same major version the dev and prod compose stacks run."""

DOCKER_PROBE_TIMEOUT: Final = 2.0


def _docker_reachable() -> tuple[bool, str]:
    """Probe for a usable Docker daemon endpoint — honestly.

    Supports the two transports that matter here: a unix socket (the
    default, and what the fallback run mounts) and tcp:// (a remote
    daemon). A socket FILE that exists but refuses connections counts
    as unreachable — the reason string says which and why.
    """
    raw = os.environ.get("DOCKER_HOST", "unix:///var/run/docker.sock")
    if raw.startswith("unix://"):
        path = raw.removeprefix("unix://")
        if not os.path.exists(path):
            return False, f"no Docker socket at {path} (dev/verify containers have none)"
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        probe.settimeout(DOCKER_PROBE_TIMEOUT)
        try:
            probe.connect(path)
        except OSError as exc:
            return False, f"Docker socket {path} unreachable: {exc}"
        finally:
            probe.close()
        return True, ""
    if raw.startswith("tcp://"):
        host, _, port = raw.removeprefix("tcp://").partition(":")
        try:
            probe = socket.create_connection(
                (host, int(port or 2375)), timeout=DOCKER_PROBE_TIMEOUT
            )
        except OSError as exc:
            return False, f"Docker endpoint {raw} unreachable: {exc}"
        probe.close()
        return True, ""
    return False, f"unsupported DOCKER_HOST transport: {raw}"


DOCKER_OK, DOCKER_SKIP_REASON = _docker_reachable()

pytestmark = [
    pytest.mark.testcontainers,
    pytest.mark.skipif(not DOCKER_OK, reason=DOCKER_SKIP_REASON),
]


@pytest.fixture
def container_url() -> Iterator[str]:
    """One throwaway PostgreSQL; its asyncpg URL is the whole fixture."""
    with PostgresContainer(POSTGRES_IMAGE) as postgres:
        # testcontainers hands out a psycopg2 URL; the guide speaks asyncpg.
        yield postgres.get_connection_url().replace("+psycopg2", "+asyncpg")


@pytest.fixture
async def engine(container_url: str) -> AsyncEngine:
    """Engine over the throwaway container, migrations applied to head."""
    await asyncio.to_thread(upgrade_database_to_head, container_url)
    engine = create_async_engine(container_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def sessions(engine: AsyncEngine) -> async_sessionmaker:
    return create_session_factory(engine)


async def test_migrations_apply_to_head_on_a_clean_database(engine: AsyncEngine) -> None:
    """The full chain 0001 → 0003 runs on an empty PostgreSQL."""
    async with engine.connect() as connection:
        current = (
            await connection.exec_driver_sql("SELECT version_num FROM alembic_version")
        ).scalar()
    assert current == "0003"


async def test_orm_round_trip_on_a_clean_database(
    sessions: async_sessionmaker,
) -> None:
    """Create → load (eager) → commit a version bump, on a clean database."""
    async with sessions() as session:
        author = Author(name="Clean Db", email="clean@guide.dev", bio="")
        post = Post(
            author=author,
            slug="clean-database-round-trip",
            title="The clean-database round trip",
            body="Created by the testcontainers test; dies with its container.",
            tags=["orm"],
            status="draft",
        )
        session.add(post)
        await session.commit()
        post_id, author_id = post.id, author.id
        assert post.version == 1  # migration 0003's server default

    async with sessions() as session:
        loaded = (
            await session.scalars(
                select(Post)
                .where(Post.id == post_id)
                .options(selectinload(Post.author), selectinload(Post.comments))
            )
        ).one()
        assert loaded.author.id == author_id  # eager: no lazy load needed
        assert loaded.comments == []
        assert loaded.version == 1
        loaded.status = "published"
        await session.commit()
        assert loaded.version == 2  # version_id_col bumped by the UPDATE

    async with sessions() as session:
        final = await session.get(Post, post_id)
        assert final is not None
        assert final.status == "published"
        assert final.version == 2


async def test_stale_write_is_refused_on_a_clean_database(
    sessions: async_sessionmaker,
) -> None:
    """The optimistic lock works from a clean database too — same refusal."""
    async with sessions() as session:
        author = Author(name="Stale Db", email="stale@guide.dev", bio="")
        post = Post(
            author=author,
            slug="clean-database-stale-write",
            title="The stale write on a clean database",
            body="Two sessions race; the loser must be refused.",
            tags=["orm"],
            status="draft",
        )
        session.add(post)
        await session.commit()
        post_id = post.id

    async with sessions() as winner, sessions() as loser:
        winning = await winner.get(Post, post_id)
        losing = await loser.get(Post, post_id)
        assert winning is not None and losing is not None
        winning.status = "published"
        await winner.commit()
        losing.body = losing.body + " (too late)"
        with pytest.raises(StaleDataError):
            await loser.commit()


async def test_the_probe_adapter_works_on_a_clean_database(
    engine: AsyncEngine, sessions: async_sessionmaker
) -> None:
    """The demo's own adapter runs against the throwaway database: it
    seeds nothing itself, so the proof covers the empty-collection edge
    (zero published posts) without raising."""
    probe = OrmProbeRepository(engine, sessions)
    loading = await probe.run_loading_probe(5)
    assert all(row.sql_count == 1 for row in loading.strategies)  # just the SELECT
    assert all(row.authors == [] for row in loading.strategies)
    assert loading.results_match is True  # all three agree on empty results
    assert loading.first_post_title == ""
    identity = await probe.prove_identity_map()
    # No such row: nothing enters the identity map, so BOTH gets SELECT.
    assert identity.same_object is False
    assert identity.select_count == 2
    page = await probe.paginate(3)
    assert page.total == 0
    assert page.offset_pages == [] and page.keyset_pages == []


def test_alembic_config_targets_the_given_url(container_url: str) -> None:
    """The chain the container ran is this repo's chain — 0001 → 0003."""
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(build_alembic_config(container_url))
    assert script.get_current_head() == "0003"
