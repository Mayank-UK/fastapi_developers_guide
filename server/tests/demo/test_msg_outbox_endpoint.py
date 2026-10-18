"""The outbox lab endpoints over the REAL dev PostgreSQL and Redis.

The one-transaction dual write (post + event commit together), the relay
cycle with its crash window, and the idempotent consumer's exactly-once
counts — all against the live stores the demo owns (the ``outbox`` table
from migration 0004 and the ``guide_demo:msg:*`` keys). Each test resets
the demo's state first: the outbox rows AND the posts they created leave
together (the payload's postId is the link), and the stream keys plus
the processed-set are deleted whole.
"""

import asyncio
from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pg_url import COMPOSE_PG_URL
from redis.asyncio import Redis
from redis_url import COMPOSE_REDIS_URL
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from guide.core.config import get_config
from guide.domain.messaging.outbox_service import OUTBOX_STREAM, PROCESSED_SET_KEY
from guide.domain.messaging.stream_service import STREAM_KEY
from guide.main import create_app

ROSTER_PATH = "/api/demo/msg/outbox"
POSTS_PATH = "/api/demo/msg/outbox/posts"
RELAY_PATH = "/api/demo/msg/outbox/relay"
CONSUME_PATH = "/api/demo/msg/outbox/consume"

UNREACHABLE_REDIS_URL = "redis://127.0.0.1:1"
UNREACHABLE_PG_URL = "postgresql+asyncpg://postgres:guide@127.0.0.1:1/guide"

TITLE = "The outbox, tested"


async def _flush_demo_state() -> None:
    """Reset the demo's whole world: its posts, its rows, its keys.

    The posts the outbox created are found through the rows' payloads
    (postId), so the business halves and the event halves leave together
    — the same atomicity the pattern teaches, used as a janitor.
    """
    engine = create_async_engine(COMPOSE_PG_URL)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "DELETE FROM posts WHERE id IN "
                    "(SELECT (payload->>'postId')::bigint FROM outbox)"
                )
            )
            await connection.execute(text("DELETE FROM outbox"))
    finally:
        await engine.dispose()
    client = Redis.from_url(COMPOSE_REDIS_URL, decode_responses=True)
    try:
        await client.delete(OUTBOX_STREAM, PROCESSED_SET_KEY, STREAM_KEY)
    finally:
        await client.aclose()  # type: ignore[no-untyped-call]  # redis-py ships aclose unannotated


@pytest.fixture
def outbox_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("FDG_DATABASE_URL", COMPOSE_PG_URL)
    monkeypatch.setenv("FDG_REDIS_URL", COMPOSE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    asyncio.run(_flush_demo_state())
    with TestClient(app) as client:
        yield client
    asyncio.run(_flush_demo_state())


def test_create_commits_post_and_event_in_one_round(outbox_client: TestClient) -> None:
    body = outbox_client.post(POSTS_PATH, json={"title": TITLE, "body": "both rows"}).json()
    assert body["committed"] is True
    post, event = body["post"], body["event"]
    assert post["title"] == TITLE and post["author"] == "Alan Kay"
    assert event["eventType"] == "post.created"
    assert event["aggregate"] == f"posts:{post['id']}"
    assert event["publishedAt"] is None  # waiting for the relay
    UUID(event["eventId"])  # the stable UUIDv7 consumers dedupe on
    roster = outbox_client.get(ROSTER_PATH).json()
    assert roster["stats"] == {"total": 1, "published": 0, "unpublished": 1}
    assert roster["outbox"][0]["eventId"] == event["eventId"]


def test_relay_drains_the_outbox_and_marks_rows(outbox_client: TestClient) -> None:
    outbox_client.post(POSTS_PATH, json={"title": TITLE})
    cycle = outbox_client.post(RELAY_PATH, json={}).json()
    assert cycle["discovered"] == 1 and cycle["marked"] == 1 and not cycle["crashed"]
    assert cycle["published"][0]["eventId"]  # landed on the stream
    stats = outbox_client.get(ROSTER_PATH).json()["stats"]
    assert stats == {"total": 1, "published": 1, "unpublished": 0}
    again = outbox_client.post(RELAY_PATH, json={}).json()
    assert again["discovered"] == 0  # drained


def test_the_crash_window_redelivers_and_dedupe_absorbs_it(
    outbox_client: TestClient,
) -> None:
    created = outbox_client.post(POSTS_PATH, json={"title": TITLE}).json()
    event_id = created["event"]["eventId"]

    crashed = outbox_client.post(RELAY_PATH, json={"crashBeforeMark": True}).json()
    assert crashed["crashed"] is True and crashed["marked"] == 0
    stats = outbox_client.get(ROSTER_PATH).json()["stats"]
    assert stats["unpublished"] == 1  # delivered-but-unmarked: still in the queue

    redelivered = outbox_client.post(RELAY_PATH, json={}).json()
    assert redelivered["discovered"] == 1 and redelivered["marked"] == 1

    proof = outbox_client.post(CONSUME_PATH).json()
    assert proof["entries"] == 2  # the SAME event id, twice on the stream
    assert proof["processed"] == 1
    assert proof["skippedDuplicates"] == 1  # the exactly-once EFFECT
    roster = outbox_client.get(ROSTER_PATH).json()
    assert roster["streamEntries"][0]["eventId"] == event_id
    assert roster["streamEntries"][1]["eventId"] == event_id
    assert roster["telemetry"]["duplicatesSkipped"] == 1


def test_second_consume_walk_skips_everything(outbox_client: TestClient) -> None:
    outbox_client.post(POSTS_PATH, json={"title": TITLE})
    outbox_client.post(RELAY_PATH, json={})
    first = outbox_client.post(CONSUME_PATH).json()
    assert first["processed"] == 1 and first["skippedDuplicates"] == 0
    second = outbox_client.post(CONSUME_PATH).json()
    assert second["processed"] == 0 and second["skippedDuplicates"] == 1


def test_draft_bounds_mirror_the_posts_checks(outbox_client: TestClient) -> None:
    assert outbox_client.post(POSTS_PATH, json={"title": ""}).status_code == 422
    assert outbox_client.post(POSTS_PATH, json={"title": "x" * 121}).status_code == 422
    body_only = outbox_client.post(POSTS_PATH, json={"title": "bare title"}).json()
    assert body_only["committed"] is True and body_only["post"]["slug"].startswith("bare-title")


def test_relay_bounds_are_enforced(outbox_client: TestClient) -> None:
    assert outbox_client.post(RELAY_PATH, json={"batch": 0}).status_code == 422
    assert outbox_client.post(RELAY_PATH, json={"batch": 11}).status_code == 422
    default = outbox_client.post(RELAY_PATH, json={}).json()  # defaults apply
    assert default["discovered"] == 0


def test_relay_with_redis_down_degrades_but_the_write_still_works(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redis publishes fail → the relay degrades to the 503 envelope; the
    ONE-transaction write (pure PostgreSQL) keeps working — the outbox's
    independence is the point."""
    monkeypatch.setenv("FDG_DATABASE_URL", COMPOSE_PG_URL)
    monkeypatch.setenv("FDG_REDIS_URL", UNREACHABLE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        created = client.post(POSTS_PATH, json={"title": TITLE}).json()
        assert created["committed"] is True
        relay = client.post(RELAY_PATH, json={})
        assert relay.status_code == 503
        assert relay.json()["error"]["code"] == "service_unavailable"
        consume = client.post(CONSUME_PATH)
        assert consume.status_code == 503
    asyncio.run(_delete_written_row(created["event"]["eventId"]))


async def _delete_written_row(event_id: str) -> None:
    """Janitor for tests outside the flushing fixture: remove the post AND
    its outbox row (the payload's postId is the link), so live substrates
    that pin the seed's shape never see this test's writes."""
    engine = create_async_engine(COMPOSE_PG_URL)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "DELETE FROM posts WHERE id IN "
                    "(SELECT (payload->>'postId')::bigint FROM outbox "
                    "WHERE event_id = :event_id)"
                ),
                {"event_id": UUID(event_id)},
            )
            await connection.execute(
                text("DELETE FROM outbox WHERE event_id = :event_id"),
                {"event_id": UUID(event_id)},
            )
    finally:
        await engine.dispose()


def test_create_with_postgres_down_degrades_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FDG_DATABASE_URL", UNREACHABLE_PG_URL)
    monkeypatch.setenv("FDG_REDIS_URL", COMPOSE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    client = TestClient(app)
    response = client.post(POSTS_PATH, json={"title": TITLE})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
