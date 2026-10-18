"""The redis-backed ``CacheStore`` — topic 21's only adapter.

Implements the domain port over the SHARED redis.asyncio client built by
``guide.data.redis.client`` (same 2-second socket timeouts, same
``decode_responses=True`` str guarantee). Every method is one awaited
redis command wrapped in the optional-service context manager: when
Redis is unreachable, the failure degrades to the ``service_unavailable``
envelope fast — same discipline as the mongo and redis-playground
adapters, applied to a cache this time.

One translation is worth a comment: redis's TTL answers -2 for a missing
key and -1 for a key with NO deadline; the port promises plain seconds
or None, so both specials become None (this lab only writes keys WITH
deadlines, so -1 never appears — but the adapter still speaks the honest
contract rather than assuming it).
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final, cast

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from guide.core.errors import AppError, FailureKind

logger = structlog.get_logger()

TTL_ABSENT: Final[int] = -2
TTL_IMMORTAL: Final[int] = -1
"""redis-py's two special TTL answers — both map to the port's None."""


@contextmanager
def _map_cache_failures(operation: str) -> Iterator[None]:
    """Optional-service discipline: Redis trouble becomes service_unavailable."""
    try:
        yield
    except AppError:
        raise
    except (RedisError, OSError) as exc:
        logger.warning(
            "cache_store_unavailable",
            operation=operation,
            error=type(exc).__name__,
            detail=str(exc),
        )
        raise AppError(
            FailureKind.SERVICE_UNAVAILABLE,
            "Redis is unreachable — this lab's cache is the subject, so it refuses "
            "to pretend (production cache-aside would bypass the cache and serve "
            "the origin; topic 39's circuit breaker formalizes that fail-open).",
        ) from exc


class RedisCacheStore:
    """The live-Redis adapter behind the cache-aside service."""

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get(self, key: str) -> str | None:
        """GET — the store's own None is the honest 'absent or expired'."""
        with _map_cache_failures("get"):
            # decode_responses=True makes the runtime type str | None; the
            # cast carries that guarantee across redis-py's bytes-typed stubs.
            return cast("str | None", await self._client.get(key))

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """SET with the inline EX — the write and its deadline, one command."""
        with _map_cache_failures("set"):
            await self._client.set(key, value, ex=ttl_seconds)

    async def delete(self, key: str) -> int:
        """DEL — answers how many entries actually died."""
        with _map_cache_failures("delete"):
            return int(await self._client.delete(key))

    async def ttl(self, key: str) -> int | None:
        """TTL — seconds remaining, or None when absent or without deadline."""
        with _map_cache_failures("ttl"):
            raw = int(await self._client.ttl(key))
            return None if raw in (TTL_ABSENT, TTL_IMMORTAL) else raw
