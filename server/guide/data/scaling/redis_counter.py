"""The redis-backed ``SharedCounterStore`` — topic 40's only adapter.

Implements the domain port over the SHARED redis.asyncio client (the one
the composition root builds for every redis-touching adapter). INCR is
atomic — two increments from two callers can never interleave into a lost
update, which is exactly the property the statelessness demo leans on:
the value is one number, owned by the store, not a per-process copy.
Every command rides the optional-service context manager: unreachable
Redis degrades this demo to the ``service_unavailable`` envelope fast,
like every other optional store in the repo.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from guide.core.errors import AppError, FailureKind

logger = structlog.get_logger()

NAMESPACE: Final = "guide_demo:scaling:"
"""The demo's dedicated key namespace — the topic owns it exclusively."""


@contextmanager
def _map_scaling_failures(operation: str) -> Iterator[None]:
    """Optional-service discipline: Redis trouble becomes service_unavailable."""
    try:
        yield
    except AppError:
        raise
    except (RedisError, OSError) as exc:
        logger.warning(
            "shared_counter_unavailable",
            operation=operation,
            error=type(exc).__name__,
            detail=str(exc),
        )
        raise AppError(
            FailureKind.SERVICE_UNAVAILABLE,
            "Redis is unreachable — this demo's shared counter is the "
            "externalized-state half of the lesson, and it refuses to fake "
            "a number that never left the process.",
        ) from exc


class RedisSharedCounter:
    """The live-Redis adapter behind topic 40's statelessness demo."""

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def incr(self, key: str) -> int:
        """INCR — atomic; the answer is the value AFTER this caller's write."""
        with _map_scaling_failures("incr"):
            return int(await self._client.incr(key))

    async def delete(self, key: str) -> int:
        """DEL — the fresh stage before each demo round."""
        with _map_scaling_failures("delete"):
            return int(await self._client.delete(key))

    async def expire(self, key: str, seconds: int) -> bool:
        """EXPIRE — the demo key self-cleans after the round."""
        with _map_scaling_failures("expire"):
            return await self._client.expire(key, seconds)
