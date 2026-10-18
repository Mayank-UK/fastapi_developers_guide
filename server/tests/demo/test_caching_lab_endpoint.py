"""The caching lab endpoints over the REAL dev Redis.

``GET /api/demo/caching/posts`` is a REAL conditional endpoint: it must
serve the cached page with validators and telemetry, honor
``If-None-Match`` with a bodyless 304, and degrade to the
``service_unavailable`` envelope when Redis is unreachable. The action
endpoints (``/lab``, ``/invalidate``, ``/stampede``) must report honest
state, force refetches, and prove single-flight determinism (ordered
awaits, no sleeps — the counts are pinned by the lock). Every test
flushes the one shared key first so a leftover entry from a previous
test can never contaminate a cold-start assertion.
"""

import asyncio
import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from redis.asyncio import Redis
from redis_url import COMPOSE_REDIS_URL

from guide.core.config import get_config
from guide.domain.caching.service import CACHE_KEY, TTL_EXPIRY_WAIT_S
from guide.main import create_app

POSTS_PATH = "/api/demo/caching/posts"
LAB_PATH = "/api/demo/caching/lab"
INVALIDATE_PATH = "/api/demo/caching/invalidate"
STAMPEDE_PATH = "/api/demo/caching/stampede"

UNREACHABLE_REDIS_URL = "redis://127.0.0.1:1"

ETAG_SHAPE = re.compile(r'^"[0-9a-f]{16}"$')


async def _flush_cache_key() -> None:
    """Delete the lab's one key directly — a deterministic cold start."""
    client = Redis.from_url(COMPOSE_REDIS_URL, decode_responses=True)
    try:
        await client.delete(CACHE_KEY)
    finally:
        await client.aclose()  # type: ignore[no-untyped-call]  # redis-py ships aclose unannotated


@pytest.fixture
def caching_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("FDG_REDIS_URL", COMPOSE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    asyncio.run(_flush_cache_key())
    with TestClient(app) as client:
        yield client
    asyncio.run(_flush_cache_key())


def test_first_fetch_misses_then_hits(caching_client: TestClient) -> None:
    first = caching_client.get(POSTS_PATH)
    assert first.status_code == 200
    assert first.headers["x-cache"] == "miss"
    assert int(first.headers["x-cache-elapsed-ms"]) >= 120  # the simulated origin cost
    assert ETAG_SHAPE.match(first.headers["etag"])
    assert first.headers["cache-control"] == "no-cache"
    page = first.json()
    assert page["items"] and page["total"] >= 1

    second = caching_client.get(POSTS_PATH)
    assert second.headers["x-cache"] == "hit"
    assert int(second.headers["x-cache-elapsed-ms"]) < 120  # warm: no origin
    assert "x-cache-age-ms" in second.headers
    assert second.json() == page  # the cached bytes, verbatim
    assert int(second.headers["x-cache-origin-fetches"]) == 1  # still one fill


def test_conditional_round_trip_answers_304(caching_client: TestClient) -> None:
    fresh = caching_client.get(POSTS_PATH)
    etag = fresh.headers["etag"]

    revalidated = caching_client.get(POSTS_PATH, headers={"If-None-Match": etag})
    assert revalidated.status_code == 304
    assert revalidated.content == b""  # no body, ever, on a 304
    assert "content-length" not in revalidated.headers
    assert revalidated.headers["etag"] == etag  # the validators ride along
    assert revalidated.headers["x-cache"] == "hit"
    assert revalidated.headers["cache-control"] == "no-cache"

    weak = caching_client.get(POSTS_PATH, headers={"If-None-Match": f"W/{etag}"})
    assert weak.status_code == 304

    star = caching_client.get(POSTS_PATH, headers={"If-None-Match": "*"})
    assert star.status_code == 304

    stale = caching_client.get(POSTS_PATH, headers={"If-None-Match": '"deadbeefdeadbeef"'})
    assert stale.status_code == 200
    assert stale.json()["items"]  # bodyless answers are only for current etags


def test_invalidate_forces_a_refetch(caching_client: TestClient) -> None:
    nothing = caching_client.post(INVALIDATE_PATH)
    assert nothing.status_code == 200
    assert nothing.json()["deletedEntries"] == 0  # nothing cached yet

    caching_client.get(POSTS_PATH)
    assert caching_client.get(POSTS_PATH).headers["x-cache"] == "hit"

    deleted = caching_client.post(INVALIDATE_PATH)
    assert deleted.json()["deletedEntries"] == 1
    assert "refills from the origin" in deleted.json()["detail"]
    assert caching_client.get(POSTS_PATH).headers["x-cache"] == "miss"


def test_ttl_expiry_refetches_after_the_deadline(caching_client: TestClient) -> None:
    caching_client.get(POSTS_PATH)  # miss, fills with the 2 s TTL
    warm = caching_client.get(LAB_PATH).json()["state"]
    assert warm["present"] is True
    assert 1 <= warm["ttlRemainingS"] <= 2

    asyncio.run(asyncio.sleep(TTL_EXPIRY_WAIT_S))  # deterministic: ≥ the deadline

    expired = caching_client.get(POSTS_PATH)
    assert expired.headers["x-cache"] == "miss"  # the safety net swept it
    assert int(expired.headers["x-cache-elapsed-ms"]) >= 120  # and paid the origin


def test_stampede_collapses_to_one_origin_fetch(caching_client: TestClient) -> None:
    body = caching_client.post(STAMPEDE_PATH, json={"requests": 8})
    assert body.status_code == 200
    row = body.json()
    assert row["requests"] == 8
    assert row["originFetches"] == 1  # the lock's guarantee, not timing luck
    assert row["servedWarm"] == 7
    outcomes = [r["outcome"] for r in row["rounds"]]
    assert outcomes.count("miss") == 1
    assert outcomes.count("coalesced") == 7
    assert row["wallMs"] >= 120  # at least one origin cost
    assert row["wallMs"] < 480  # but nowhere near 8 × 120 serialized


def test_stampede_bounds_are_enforced(caching_client: TestClient) -> None:
    assert caching_client.post(STAMPEDE_PATH, json={"requests": 1}).status_code == 422
    assert caching_client.post(STAMPEDE_PATH, json={"requests": 25}).status_code == 422
    default = caching_client.post(STAMPEDE_PATH, json={})  # empty body: defaults apply
    assert default.status_code == 200
    assert default.json()["requests"] == 8


def test_lab_payload_reports_honest_state(caching_client: TestClient) -> None:
    body = caching_client.get(LAB_PATH).json()
    assert body["key"] == CACHE_KEY
    assert body["namespace"] == "guide_demo:caching:*"
    assert body["ttlSeconds"] == 2
    assert body["originCostMs"] == 120
    assert "simulated" in body["originCostNote"]
    assert body["postsEndpoint"] == POSTS_PATH
    assert body["state"]["present"] is False  # nothing fetched yet
    assert set(body["state"]["telemetry"]) == {"hits", "misses", "coalesced", "invalidations"}


def test_unreachable_redis_maps_to_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FDG_REDIS_URL", UNREACHABLE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    client = TestClient(app)
    checks = (
        ("GET", POSTS_PATH, None),
        ("GET", LAB_PATH, None),
        ("POST", INVALIDATE_PATH, None),
        ("POST", STAMPEDE_PATH, {"requests": 8}),
    )
    for method, path, body in checks:
        response = client.post(path, json=body) if method == "POST" else client.get(path)
        assert response.status_code == 503, path
        assert response.json()["error"]["code"] == "service_unavailable", path


def test_the_app_boots_and_serves_with_redis_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The optional-service discipline, proven at the wiring level: an
    unreachable redis URL never stops the app from booting or serving —
    only the caching lab degrades."""
    monkeypatch.setenv("FDG_REDIS_URL", UNREACHABLE_REDIS_URL)
    get_config.cache_clear()
    app = create_app()
    get_config.cache_clear()
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        content = client.get("/api/content")
        assert content.status_code == 200
        assert len(content.json()["topics"]) >= 21
        degraded = client.get(POSTS_PATH)
        assert degraded.status_code == 503
        assert degraded.json()["error"]["code"] == "service_unavailable"
