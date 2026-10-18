"""The caching ports: a thin key-value store Protocol + the result rows.

``CacheStore`` is deliberately redis-shaped — get, set-with-TTL, delete,
TTL — because those four verbs ARE the cache-aside pattern's entire
contract with its store; the adapter (``guide.data.caching``) implements
them over redis-py under the optional-service discipline, and a second
implementation (in-process dict, another vendor's client) would change
nothing above this line. ``CachedPosts`` is the port the demo routers
see: the whole lab behind four calls.

Every row is a frozen snapshot of what one interaction really answered —
outcomes are ``"hit"`` (served from the store), ``"miss"`` (filled from
the origin), or ``"coalesced"`` (arrived during a fill, waited on the
single-flight lock, served warm the moment the fill landed).
"""

from typing import Literal, Protocol, runtime_checkable

from pydantic import Field

from guide.core.serialization import CamelModel

CacheOutcome = Literal["hit", "miss", "coalesced"]
"""What served one cache-aside read; ``coalesced`` only appears under load."""

STAMPEDE_REQUESTS_MIN: int = 2
STAMPEDE_REQUESTS_MAX: int = 24
"""The stampede round's bounds: enough to coalesce, few enough to stay polite."""


class CacheTelemetryRow(CamelModel):
    """The lab's in-process counters, snapshot at one interaction's end."""

    hits: int
    misses: int
    coalesced: int
    invalidations: int


class CacheFetchRow(CamelModel):
    """One cache-aside read: what served it, the payload, the telemetry.

    ``payload`` is the cached JSON string verbatim — the endpoint serves
    those exact bytes, so the ETag computed over them cannot drift from
    what a client receives. ``age_ms`` is derived from the store's TTL
    clock (second-granular); ``None`` when there was no entry to age.
    """

    outcome: CacheOutcome
    key: str
    payload: str
    etag: str
    elapsed_ms: int
    age_ms: int | None
    telemetry: CacheTelemetryRow


class CacheStateRow(CamelModel):
    """The state panel's facts: the key, its liveness, its size, counters."""

    key: str
    present: bool
    ttl_seconds: int
    ttl_remaining_s: int | None
    size_bytes: int | None
    etag: str | None
    last_outcome: CacheOutcome | None
    telemetry: CacheTelemetryRow


class InvalidationRow(CamelModel):
    """One explicit invalidation: what was deleted, what happens next."""

    key: str
    deleted_entries: int
    telemetry: CacheTelemetryRow
    detail: str


class StampedeRequestRow(CamelModel):
    """One request inside a stampede round, in launch order."""

    index: int
    outcome: CacheOutcome
    elapsed_ms: int


class StampedeRow(CamelModel):
    """One whole stampede round: the counts that prove single-flight."""

    requests: int
    origin_fetches: int
    served_warm: int
    wall_ms: int
    rounds: list[StampedeRequestRow]
    proof: str


class StampedeRequest(CamelModel):
    """The stampede button's body: how many concurrent requests to fire."""

    requests: int = Field(default=8, ge=STAMPEDE_REQUESTS_MIN, le=STAMPEDE_REQUESTS_MAX)


@runtime_checkable
class CacheStore(Protocol):
    """What every cache adapter must do; keys arrive fully formed."""

    async def get(self, key: str) -> str | None:
        """The value under ``key``, or None when absent (or expired)."""
        ...

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Store ``value`` under ``key`` with an expiry — the safety net."""
        ...

    async def delete(self, key: str) -> int:
        """Explicitly evict ``key``; answer how many entries died (0 or 1)."""
        ...

    async def ttl(self, key: str) -> int | None:
        """Seconds until expiry, or None when absent or immortal."""
        ...


@runtime_checkable
class CachedPosts(Protocol):
    """What every topic-21 caching service must provide.

    Four calls are the whole lab: the cache-aside read (with single-flight
    origin fills), the explicit invalidation, the state snapshot the panel
    renders, and the stampede round that proves coalescing under one
    process. Unreachable Redis is the adapter's problem to translate
    (service_unavailable), never the port's.
    """

    async def fetch_page(self) -> CacheFetchRow:
        """Serve the cached posts page — hit, miss, or coalesced."""
        ...

    async def invalidate(self) -> InvalidationRow:
        """Delete the cached entry; report what the next read will do."""
        ...

    async def state(self) -> CacheStateRow:
        """The key's liveness, size, and the telemetry counters."""
        ...

    async def stampede(self, requests: int) -> StampedeRow:
        """Cold-start, then N concurrent reads — single-flight, one origin fill."""
        ...
