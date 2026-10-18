"""The redis playground adapter, against the REAL dev Redis.

No HTTP here — these pin the adapter's own contract: every structure's
round-trip is real (the INCR counter is atomic, the hash comes back whole,
the list shows its push-order inversion, the set refuses duplicates, the
sorted set orders by score), the TTL proof is honest (the live TTL clock,
then the key's absence after the bounded wait), the pub/sub round-trip
collects the PUBLISHed message in a bounded task, runs are idempotent (the
stage is DEL'd first and left clean), and unreachable Redis degrades to
``service_unavailable`` (fast — the client's socket timeouts are the bound)
instead of hanging or crashing.
"""

import time

import pytest
from redis_url import COMPOSE_REDIS_URL

from guide.core.config import AppConfig
from guide.core.errors import AppError, FailureKind
from guide.data.redis import RedisPlaygroundRepository, create_redis_client
from guide.domain.db.ports import RedisPlaygroundRun


@pytest.fixture
async def repository() -> RedisPlaygroundRepository:
    """Adapter over the dev compose Redis; the run DELs its own stage."""
    client = create_redis_client(_config_with(COMPOSE_REDIS_URL))
    try:
        yield RedisPlaygroundRepository(client)
    finally:
        await client.aclose()


def _config_with(redis_url: str) -> AppConfig:
    """An AppConfig speaking only the redis rail (tests never read the host env)."""
    return AppConfig(redis_url=redis_url)


def _structure(run: RedisPlaygroundRun, kind: str):
    return next(s for s in run.structures if s.kind == kind)


async def test_every_structure_round_trips_with_real_results(
    repository: RedisPlaygroundRepository,
) -> None:
    run = await repository.run_playground("demo")
    assert [s.kind for s in run.structures] == ["string", "hash", "list", "set", "zset"]
    assert all(s.key.startswith("guide_demo:redis:demo:") for s in run.structures)

    string = _structure(run, "string")
    assert [v.value for v in string.values] == ["1", "3"]
    assert "(2, then 3)" in string.outcome

    hash_row = _structure(run, "hash")
    assert {v.label: v.value for v in hash_row.values} == {
        "name": "the redis playground",
        "tag": "demo",
        "visits": "1",
    }

    list_row = _structure(run, "list")
    assert [v.value for v in list_row.values] == ["first:demo", "second:demo", "third:demo"]
    assert "index 0" in list_row.outcome  # the push-order inversion, named

    set_row = _structure(run, "set")
    assert [v.value for v in set_row.values] == ["cache", "demo", "pubsub", "sessions"]
    assert "answer 0" in set_row.outcome  # duplicates refuse — by structure

    zset_row = _structure(run, "zset")
    assert [(v.label, v.value) for v in zset_row.values] == [
        ("grace", "score 100 · rank 1"),
        ("barbara", "score 180 · rank 2"),
        ("alan", "score 250 · rank 3"),
    ]


async def test_runs_are_idempotent_and_leave_no_keys_behind(
    repository: RedisPlaygroundRepository,
) -> None:
    """The stage is DEL'd first and cleaned after — repeats agree, nothing accumulates."""
    first = await repository.run_playground("demo")
    second = await repository.run_playground("demo")
    assert [v.value for v in _structure(first, "string").values] == [
        v.value for v in _structure(second, "string").values
    ]
    assert second.namespace == "guide_demo:redis:*"
    client = create_redis_client(_config_with(COMPOSE_REDIS_URL))
    try:
        leftovers = await client.keys("guide_demo:redis:demo:*")
    finally:
        await client.aclose()
    assert leftovers == []


async def test_the_ttl_proof_is_honest(repository: RedisPlaygroundRepository) -> None:
    """SET with an inline EX, the live TTL clock, then the ABSENCE after the wait."""
    run = await repository.run_playground("demo")
    ttl = run.ttl
    assert ttl.key == "guide_demo:redis:demo:flash"
    assert ttl.ttl_seconds == 2
    assert 1 <= ttl.ttl_first_read <= ttl.ttl_seconds  # the live clock, not a claim
    assert ttl.absent_after_expiry is True
    assert ttl.waited_ms >= 2100  # the wait really crossed the expiry
    assert "GET answered nil" in ttl.proof


async def test_the_pubsub_round_trip_is_real(repository: RedisPlaygroundRepository) -> None:
    """One bounded listener, one PUBLISH — both sides of the wire reported."""
    run = await repository.run_playground("demo")
    pubsub = run.pubsub
    assert pubsub.channel == "guide_demo:redis:demo:events"
    assert pubsub.receivers == 1  # PUBLISH answers the receiver count
    assert pubsub.matched is True
    assert pubsub.received_payload == pubsub.payload
    assert '"tag": "demo"' in pubsub.payload


async def test_a_fresh_tag_gets_a_fresh_key_family(
    repository: RedisPlaygroundRepository,
) -> None:
    """The caller value is woven into keys and values — repeat calls show fresh state."""
    run = await repository.run_playground("second-run")
    assert all(":second-run:" in s.key for s in run.structures)
    assert {v.label: v.value for v in _structure(run, "hash").values}["tag"] == "second-run"
    assert [v.value for v in _structure(run, "list").values] == [
        "first:second-run",
        "second:second-run",
        "third:second-run",
    ]


async def test_unreachable_redis_degrades_fast_to_service_unavailable() -> None:
    """The optional-service discipline: port 1 refuses instantly, the adapter maps it."""
    client = create_redis_client(_config_with("redis://127.0.0.1:1"))
    repository = RedisPlaygroundRepository(client)
    try:
        started = time.perf_counter()
        with pytest.raises(AppError) as raised:
            await repository.run_playground("demo")
        elapsed = time.perf_counter() - started
    finally:
        await client.aclose()
    assert raised.value.kind is FailureKind.SERVICE_UNAVAILABLE
    assert elapsed < 6, f"degradation must be fast, took {elapsed:.1f}s"
