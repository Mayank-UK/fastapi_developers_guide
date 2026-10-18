"""The jobs walk against the LIVE worker — honest-skip when it is absent.

The unit tests prove the policy and the service; the endpoint tests
prove the console contract. What only a real worker proves is the walk
itself: ``fail_once`` retried on the policy's curve to completion, and
``fail_always`` exhausting its budget into the dead-letter queue. This
test runs when the dev stack's redis AND the arq-worker container are
reachable — detected via the worker's OWN heartbeat key (it beats every
minute and once at boot) — and skips honestly, with the reason, when
either is down (the in-container suite has no worker by design; the
live smoke is the same walk by hand).
"""

import asyncio
from typing import Final

import pytest
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from redis.asyncio import Redis
from redis_url import COMPOSE_REDIS_URL

from guide.data.jobs import ArqJobs
from guide.domain.jobs.ports import HEARTBEAT_LAST_KEY
from guide.domain.jobs.service import JobsConsoleService

POLL_SECONDS: Final = 15.0


def _compose_store() -> ArqJobs:
    """A store over the dev-stack redis — the URL the whole suite uses."""

    async def factory() -> ArqRedis:
        return await create_pool(RedisSettings.from_dsn(COMPOSE_REDIS_URL))

    return ArqJobs(factory)


async def _live_worker() -> Redis | None:
    """The dev-stack redis client when a worker heartbeat exists, else None."""
    client = Redis.from_url(
        COMPOSE_REDIS_URL, decode_responses=True, socket_connect_timeout=0.5, socket_timeout=0.5
    )
    try:
        if await client.ping() and await client.get(HEARTBEAT_LAST_KEY) is not None:
            return client
        await client.aclose()
        return None
    except Exception:  # unreachable redis is the skip case, not a failure
        return None


@pytest.mark.asyncio
async def test_fail_once_retries_to_completion_with_a_live_worker() -> None:
    live = await _live_worker()
    if live is None:
        pytest.skip("no reachable redis with an arq worker heartbeat (compose arq-worker service)")
    await live.aclose()

    service = JobsConsoleService(_compose_store())
    ticket = await service.enqueue("fail_once")
    deadline = asyncio.get_running_loop().time() + POLL_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        snapshot = await service.snapshot(ticket.job_id)
        if snapshot.status in ("complete", "failed"):
            break
        await asyncio.sleep(0.25)
    assert snapshot.status == "complete", f"walk never finished: {snapshot.status}"
    outcomes = [step.outcome for step in snapshot.attempts]
    assert outcomes == ["retry_scheduled", "succeeded"], "the retry must be visible in the trail"
    assert snapshot.dead_lettered is False


@pytest.mark.asyncio
async def test_fail_always_exhausts_into_the_dead_letter_queue_with_a_live_worker() -> None:
    live = await _live_worker()
    if live is None:
        pytest.skip("no reachable redis with an arq worker heartbeat (compose arq-worker service)")
    await live.aclose()

    service = JobsConsoleService(_compose_store())
    ticket = await service.enqueue("fail_always")
    deadline = asyncio.get_running_loop().time() + POLL_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        snapshot = await service.snapshot(ticket.job_id)
        if snapshot.status in ("complete", "failed"):
            break
        await asyncio.sleep(0.25)
    assert snapshot.status == "failed"
    assert len(snapshot.attempts) == 3, "the full budget, no more"
    assert snapshot.dead_lettered is True
    parked = await service.dead_letters()
    assert any(entry.job_id == ticket.job_id for entry in parked), "the audit entry exists"
