"""The stream lab endpoints over the REAL dev Redis.

Produce → group-read → ack, the poison persona's pending backlog, and
XAUTOCLAIM reclaim — every round runs against the live stream the demo
owns (``guide_demo:msg:stream``), and each test deletes the stream key
first so a leftover group or entry can never contaminate an assertion.
Unreachable Redis degrades every route to the service_unavailable
envelope while the app keeps serving the rest of the guide.
"""

import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from redis_url import COMPOSE_REDIS_URL

from guide.core.config import get_config
from guide.domain.messaging.stream_service import GROUP, STREAM_KEY
from guide.main import create_app

ROSTER_PATH = "/api/demo/msg/stream"
PRODUCE_PATH = "/api/demo/msg/stream/produce"
CONSUME_PATH = "/api/demo/msg/stream/consume"
PENDING_PATH = "/api/demo/msg/stream/pending"
RECLAIM_PATH = "/api/demo/msg/stream/reclaim"

UNREACHABLE_REDIS_URL = "redis://127.0.0.1:1"

ENTRY_ID_SHAPE = re.compile(r"^\d+-\d+$")


async def _flush_stream_key() -> None:
    """DEL the stream key — stream, entries, groups, and PELs all at once."""
    client = Redis.from_url(COMPOSE_REDIS_URL, decode_responses=True)
    try:
        await client.delete(STREAM_KEY)
    finally:
        await client.aclose()  # type: ignore[no-untyped-call]  # redis-py ships aclose unannotated


@pytest.fixture
def stream_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("FDG_REDIS_URL", COMPOSE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    import asyncio

    asyncio.run(_flush_stream_key())
    with TestClient(app) as client:
        yield client
    asyncio.run(_flush_stream_key())


def test_produce_appends_and_reports_the_ordered_log(stream_client: TestClient) -> None:
    first = stream_client.post(PRODUCE_PATH, json={"note": "one"}).json()
    second = stream_client.post(PRODUCE_PATH, json={"note": "two"}).json()
    assert ENTRY_ID_SHAPE.match(first["entryId"])
    assert second["entryId"] > first["entryId"]  # id order IS arrival order
    assert second["length"] == 2
    roster = stream_client.get(ROSTER_PATH).json()
    assert roster["length"] == 2
    assert roster["lastId"] == second["entryId"]
    assert [e["payload"] for e in roster["entries"]] == [
        '{"note": "one"}',
        '{"note": "two"}',
    ]
    assert roster["group"] == GROUP


def test_healthy_round_reads_and_acks(stream_client: TestClient) -> None:
    stream_client.post(PRODUCE_PATH, json={"note": "work"})
    row = stream_client.post(CONSUME_PATH, json={"mode": "healthy", "count": 5}).json()
    assert row["consumer"] == "healthy-worker"
    assert len(row["delivered"]) == 1
    assert row["acked"] == 1
    pending = stream_client.get(PENDING_PATH).json()
    assert pending["entries"] == []
    again = stream_client.post(CONSUME_PATH, json={"mode": "healthy", "count": 5}).json()
    assert again["delivered"] == []  # nothing new for the group


def test_poison_round_leaves_entries_pending_then_reclaim_finishes(
    stream_client: TestClient,
) -> None:
    stream_client.post(PRODUCE_PATH, json={"note": "stuck"})
    poison = stream_client.post(CONSUME_PATH, json={"mode": "poison", "count": 5}).json()
    assert poison["consumer"] == "poison-worker"
    assert len(poison["delivered"]) == 1 and poison["acked"] == 0

    pending = stream_client.get(PENDING_PATH).json()
    assert [(e["consumer"], e["deliveries"]) for e in pending["entries"]] == [
        ("poison-worker", 1)
    ]

    healthy = stream_client.post(CONSUME_PATH, json={"mode": "healthy", "count": 5}).json()
    assert healthy["delivered"] == []  # owned entries never re-delivered as new

    reclaim = stream_client.post(RECLAIM_PATH, json={"minIdleMs": 0}).json()
    assert len(reclaim["claimed"]) == 1
    assert reclaim["acked"] == 1
    assert stream_client.get(PENDING_PATH).json()["entries"] == []


def test_reclaim_below_the_threshold_claims_nothing(stream_client: TestClient) -> None:
    stream_client.post(PRODUCE_PATH, json={"note": "fresh work"})
    stream_client.post(CONSUME_PATH, json={"mode": "poison", "count": 5})
    reclaim = stream_client.post(RECLAIM_PATH, json={"minIdleMs": 60_000}).json()
    assert reclaim["claimed"] == [] and reclaim["acked"] == 0
    assert "nothing was idle" in reclaim["detail"]


def test_consume_bounds_are_enforced(stream_client: TestClient) -> None:
    assert stream_client.post(CONSUME_PATH, json={"mode": "healthy", "count": 0}).status_code == 422
    assert (
        stream_client.post(CONSUME_PATH, json={"mode": "healthy", "count": 11}).status_code == 422
    )
    assert stream_client.post(CONSUME_PATH, json={"mode": "nobody"}).status_code == 422
    default = stream_client.post(CONSUME_PATH, json={}).json()  # empty body: defaults apply
    assert default["mode"] == "healthy" and default["delivered"] == []


def test_roster_payload_reports_honest_state(stream_client: TestClient) -> None:
    body = stream_client.get(ROSTER_PATH).json()
    assert body["namespace"] == "guide_demo:msg:*"
    assert body["stream"] == STREAM_KEY
    assert body["healthyConsumer"] == "healthy-worker"
    assert body["poisonConsumer"] == "poison-worker"
    assert body["length"] == 0 and body["lastId"] is None
    assert body["produceEndpoint"] == PRODUCE_PATH
    assert "reasoning" in body


def test_unreachable_redis_maps_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FDG_REDIS_URL", UNREACHABLE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    client = TestClient(app)
    checks = (
        ("GET", ROSTER_PATH, None),
        ("POST", PRODUCE_PATH, {"note": "x"}),
        ("POST", CONSUME_PATH, {"mode": "healthy"}),
        ("GET", PENDING_PATH, None),
        ("POST", RECLAIM_PATH, {"minIdleMs": 0}),
    )
    for method, path, body in checks:
        response = (
            client.post(path, json=body) if method == "POST" else client.get(path)
        )
        assert response.status_code == 503, path
        assert response.json()["error"]["code"] == "service_unavailable", path


def test_the_app_boots_and_serves_with_redis_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The optional-service discipline at the wiring level: an unreachable
    redis URL never stops the app from booting or serving — only the
    messaging labs degrade."""
    monkeypatch.setenv("FDG_REDIS_URL", UNREACHABLE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        content = client.get("/api/content")
        assert content.status_code == 200
        assert len(content.json()["topics"]) >= 22
        degraded = client.get(ROSTER_PATH)
        assert degraded.status_code == 503
        assert degraded.json()["error"]["code"] == "service_unavailable"
