"""The ORM mapping and its proofs, against the REAL dev PostgreSQL.

No HTTP here — these pin the adapter's own contract: the mapped classes
sit on topic 16's Core tables (the very same ``Table`` objects), the
version counter refuses stale writes with ``StaleDataError``, the
dirty-check rollback leaves the database untouched, and keyset
pagination agrees with offset windows over the same ordering. The
Testcontainers-marked clean-database round-trip lives separately (it
needs a Docker daemon the dev container does not have).
"""

import pytest
from pg_url import COMPOSE_PG_URL
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm.exc import StaleDataError

from guide.core.config import get_config
from guide.data.db.orm import Author, OrmProbeRepository, Post, create_session_factory
from guide.data.db.schema import posts as posts_table


@pytest.fixture
async def engine(monkeypatch: pytest.MonkeyPatch) -> AsyncEngine:
    """Engine over the dev compose PostgreSQL; config rail stays honest."""
    monkeypatch.setenv("FDG_DATABASE_URL", COMPOSE_PG_URL)
    get_config.cache_clear()
    engine = create_async_engine(COMPOSE_PG_URL, pool_pre_ping=True)
    try:
        yield engine
    finally:
        get_config.cache_clear()
        await engine.dispose()


@pytest.fixture
def sessions(engine: AsyncEngine) -> async_sessionmaker:
    return create_session_factory(engine)


@pytest.fixture
def probe(engine: AsyncEngine, sessions: async_sessionmaker) -> OrmProbeRepository:
    return OrmProbeRepository(engine, sessions)


def test_classes_map_onto_the_core_tables() -> None:
    """The ORM does not redeclare the schema — it claims topic 16's tables."""
    assert Post.__table__ is posts_table
    assert "version" in posts_table.c
    assert Post.__mapper__.version_id_col is posts_table.c.version


async def test_dirty_check_rollback_leaves_the_database_untouched(
    probe: OrmProbeRepository, sessions: async_sessionmaker
) -> None:
    before = await _anchor_status(sessions)
    proof = await probe.prove_dirty_check()
    assert proof.update_count == 1
    assert proof.committed is False
    assert proof.before == before
    assert await _anchor_status(sessions) == before


async def test_version_conflict_refuses_the_stale_write(probe: OrmProbeRepository) -> None:
    proof = await probe.run_version_conflict()
    assert proof.stale_version == 1
    assert proof.committed_version == 2
    assert proof.winner_status == "published"
    assert "StaleDataError" in proof.loser_error
    assert "0 were matched" in proof.loser_error


async def test_version_conflict_cleans_up_after_itself(
    probe: OrmProbeRepository, sessions: async_sessionmaker
) -> None:
    await probe.run_version_conflict()
    async with sessions() as session:
        remaining = (
            await session.execute(
                select(Post.id).where(Post.slug.like("orm-optimistic-versioning-probe-%"))
            )
        ).all()
    assert remaining == []


async def test_the_raw_stale_write_is_refused_at_the_session_level(
    sessions: async_sessionmaker,
) -> None:
    """The adapter is not special: any two sessions racing a versioned row
    get the same refusal — reproduced here with bare sessions."""
    async with sessions() as creator:
        grace = (
            await creator.scalars(
                select(Author).where(Author.email == "grace@guide.dev").limit(1)
            )
        ).one()
        post = Post(
            author_id=grace.id,
            slug="orm-stale-write-level-test",
            title="The engine-level stale write",
            body="Deleted by the test itself; no residue.",
            tags=["orm"],
            status="draft",
        )
        creator.add(post)
        await creator.commit()
        post_id = post.id
        try:
            async with sessions() as first, sessions() as second:
                stale = await first.get(Post, post_id)
                fresh = await second.get(Post, post_id)
                assert stale is not None and fresh is not None
                fresh.status = "published"
                await second.commit()
                stale.body = stale.body + " stale edit"
                with pytest.raises(StaleDataError):
                    await first.commit()
        finally:
            async with sessions() as cleaner:
                await cleaner.execute(
                    posts_table.delete().where(posts_table.c.id == post_id)
                )
                await cleaner.commit()


async def test_paginate_keyset_agrees_with_offset(probe: OrmProbeRepository) -> None:
    page = await probe.paginate(3)
    assert page.total >= 8
    assert page.agree is True
    assert len(page.offset_pages) == len(page.keyset_pages)
    assert "OFFSET" in page.offset_sql.upper()
    assert "OFFSET" not in page.keyset_sql.upper()
    assert "posts.id >" in page.keyset_sql


async def test_loading_probe_counts_are_deterministic(probe: OrmProbeRepository) -> None:
    loading = await probe.run_loading_probe(5)
    counts = {row.strategy: row.sql_count for row in loading.strategies}
    assert counts == {"lazy": 9, "joinedload": 1, "selectinload": 3}
    assert loading.results_match is True


async def _anchor_status(sessions: async_sessionmaker) -> str:
    async with sessions() as session:
        status = await session.scalar(
            select(Post.status).where(Post.slug == "designing-urls-people-can-read")
        )
    return str(status)
