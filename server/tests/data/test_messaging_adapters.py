"""The PG outbox adapter against the REAL dev PostgreSQL.

The atomicity proof the pattern's whole claim rests on: with the crash
point tripped, the transaction that inserted the post AND the outbox row
rolls back TOGETHER — measured by counts before and after, never
claimed. Plus the poll's honest semantics: insertion order, the mark's
rowcount, and the partial-index-backed stats.
"""

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from pg_url import COMPOSE_PG_URL
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from guide.data.messaging.outbox_store import PgOutboxStore
from guide.domain.messaging.ports import OutboxPostDraft

TITLE = "adapter-level atomicity proof"


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(COMPOSE_PG_URL)
    # The demo's janitor, same as the endpoint tests: the posts the outbox
    # created (found via the rows' payloads) and the outbox rows themselves
    # leave together, so no live-smoke leftover can contaminate the counts.
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "DELETE FROM posts WHERE id IN "
                "(SELECT (payload->>'postId')::bigint FROM outbox)"
            )
        )
        await connection.execute(text("DELETE FROM outbox"))
    yield engine
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "DELETE FROM posts WHERE id IN "
                "(SELECT (payload->>'postId')::bigint FROM outbox)"
            )
        )
        await connection.execute(text("DELETE FROM outbox"))
    await engine.dispose()


async def _count_outbox(engine: AsyncEngine) -> int:
    async with engine.connect() as connection:
        return int(await connection.scalar(text("SELECT COUNT(*) FROM outbox")) or 0)


async def _posts_with_title(engine: AsyncEngine, title: str) -> int:
    async with engine.connect() as connection:
        return int(
            await connection.scalar(
                text("SELECT COUNT(*) FROM posts WHERE title = :title"), {"title": title}
            )
            or 0
        )


async def test_trip_crash_point_rolls_back_post_and_event_together(
    engine: AsyncEngine,
) -> None:
    store = PgOutboxStore(engine)
    before = await _count_outbox(engine)

    row = await store.create_post_with_event(
        OutboxPostDraft(title=TITLE), trip_crash_point=True
    )

    assert row.committed is False
    assert row.post is None and row.event is None
    assert "ck_posts_title_length" in row.failure  # PostgreSQL's own words
    assert await _count_outbox(engine) == before  # NO event row survived…
    assert await _posts_with_title(engine, TITLE) == 0  # …and NO post either


async def test_happy_write_leaves_both_halves_in_one_commit(engine: AsyncEngine) -> None:
    store = PgOutboxStore(engine)
    row = await store.create_post_with_event(OutboxPostDraft(title=TITLE))
    assert row.committed is True
    async with engine.connect() as connection:
        stored = await connection.scalar(
            text("SELECT payload->>'postId' FROM outbox WHERE event_id = :id"),
            {"id": UUID(row.event.event_id)},
        )
    assert stored == str(row.post.id)  # the event points at the post it rode with
    # cleanup: this proof's rows leave the way they arrived — together.
    async with engine.begin() as connection:
        await connection.execute(
            text("DELETE FROM posts WHERE id = :id"), {"id": row.post.id}
        )
        await connection.execute(
            text("DELETE FROM outbox WHERE event_id = :id"),
            {"id": UUID(row.event.event_id)},
        )


async def test_unpublished_is_ordered_and_mark_counts(engine: AsyncEngine) -> None:
    store = PgOutboxStore(engine)
    created = [
        await store.create_post_with_event(OutboxPostDraft(title=f"{TITLE} {n}"))
        for n in range(3)
    ]
    try:
        unpublished = await store.unpublished(limit=3)
        assert [row.event_id for row in unpublished] == [
            r.event.event_id for r in created
        ]  # insertion order — the poll is a stable cursor
        assert await store.mark_published(
            [created[0].event.event_id, "00000000-0000-7000-8000-00000000dead"]
        ) == 1  # only the real row stamped; re-marking stamps nothing
        assert await store.mark_published([created[0].event.event_id]) == 0
        stats = await store.stats()
        assert stats.total == 3 and stats.published == 1 and stats.unpublished == 2
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "DELETE FROM posts WHERE id IN "
                    "(SELECT (payload->>'postId')::bigint FROM outbox)"
                )
            )
            await connection.execute(text("DELETE FROM outbox"))
