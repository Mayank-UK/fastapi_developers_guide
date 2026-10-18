"""The cache-aside service over the posts substrate — topic 21's core.

``CacheAsidePostsService`` is the teaching artifact itself: the read path
caches the posts list page as its CANONICAL JSON STRING (bytes, exactly
what a response would carry) under ONE versioned key in a ``CacheStore``
port, fills from the origin on a miss, and single-flights concurrent
fills with a per-key ``asyncio.Lock`` — the double-checked pattern: a
waiter re-checks the store INSIDE the lock, so exactly one request pays
the origin while the rest are served warm the moment the fill lands.

Two honest labels. First, the origin cost is SIMULATED — the in-memory
posts substrate answers in microseconds, so a flat 120 ms sleep stands in
for the database and I/O time a real origin pays, making hit-versus-miss
visible; the caching mechanics around it (keys, TTL, telemetry,
invalidation, single-flight) are 100% real. Second, telemetry counters
are process-local by design: one service instance per app, mutated only
on the serving event loop (no await between a counter's read and write),
so the numbers are coherent without locks.

In-process single-flight coalesces within ONE process; the distributed
form (``SET NX`` lock keys in Redis) is the topic's prose — this code
stays deterministic and testable instead.
"""

import asyncio
import time
from typing import Final, Literal

import structlog

from guide.core.result import Err
from guide.domain.caching.conditionals import compute_etag
from guide.domain.caching.ports import (
    CacheFetchRow,
    CacheOutcome,
    CacheStateRow,
    CacheStore,
    CacheTelemetryRow,
    InvalidationRow,
    StampedeRequestRow,
    StampedeRow,
)
from guide.domain.posts.entities import PostListQuery
from guide.domain.posts.use_cases import PostUseCases

logger = structlog.get_logger()

NAMESPACE: Final = "guide_demo:caching:"
"""The demo namespace every key lives under — the topic owns it exclusively."""

NAMESPACE_DISPLAY: Final = "guide_demo:caching:*"
"""The namespace as the lab payload displays it (the playground's convention)."""

CACHE_KEY: Final = f"{NAMESPACE}posts:v1"
"""The one key this lab caches: the posts list page, payload-version v1.

The version segment is the invalidation strategy taught in section four:
a new payload shape becomes ``posts:v2`` and the old entry is never read
again — it simply expires. Bump it when the cached projection changes."""

TTL_SECONDS: Final = 2
"""The safety-net expiry: short enough to demo, long enough to see hits."""

TTL_EXPIRY_WAIT_S: Final = 2.25
"""Sleep past the TTL so absence proofs are deterministic (asyncio sleeps
AT LEAST the requested time, so the entry is guaranteed gone)."""

ORIGIN_COST_MS: Final = 120
"""SIMULATED origin cost — a flat stand-in for real database/IO latency."""

ORIGIN_COST_NOTE: Final = (
    f"simulated — the real substrate answers in microseconds; the flat "
    f"{ORIGIN_COST_MS} ms stands in for database/IO time so hit-vs-miss is visible"
)

ORIGIN_QUERY: Final = PostListQuery(limit=6)
"""The page the lab caches: the newest six posts, the substrate's default view."""


class CacheAsidePostsService:
    """Cache-aside reads with single-flight fills and honest telemetry."""

    def __init__(self, posts: PostUseCases, store: CacheStore) -> None:
        self._posts = posts
        self._store = store
        self._origin_locks: dict[str, asyncio.Lock] = {}
        self._hits = 0
        self._misses = 0
        self._coalesced = 0
        self._invalidations = 0
        self._last_outcome: CacheOutcome | None = None

    async def fetch_page(self) -> CacheFetchRow:
        """Serve the cached page: hit, coalesced, or miss-then-fill.

        The read path is the pattern whole: one GET answers a hit; a miss
        takes the per-key lock, RE-CHECKS the store inside it (a fill may
        have landed while this request waited), and only a second miss
        pays the origin — then the fill is written with its TTL before
        the lock releases, so no waiter can observe a half-filled state.
        """
        started = time.monotonic()
        cached = await self._store.get(CACHE_KEY)
        if cached is not None:
            return await self._serve_from_store(cached, started, coalesced=False)
        async with self._lock_for(CACHE_KEY):
            cached = await self._store.get(CACHE_KEY)
            if cached is not None:
                # Single-flight did its job: another request filled the
                # entry while this one waited on the lock — serve it warm.
                return await self._serve_from_store(cached, started, coalesced=True)
            payload = await self._fetch_origin()
            await self._store.set(CACHE_KEY, payload, TTL_SECONDS)
            self._misses += 1
            self._last_outcome = "miss"
            return CacheFetchRow(
                outcome="miss",
                key=CACHE_KEY,
                payload=payload,
                etag=compute_etag(payload),
                elapsed_ms=self._elapsed_ms(started),
                age_ms=None,
                telemetry=self._telemetry(),
            )

    async def invalidate(self) -> InvalidationRow:
        """Explicitly delete the entry — the next read goes to the origin."""
        deleted = await self._store.delete(CACHE_KEY)
        if deleted > 0:
            self._invalidations += 1
            detail = (
                f"deleted {deleted} entry under {CACHE_KEY} — the next read is a "
                f"miss and refills from the origin"
            )
        else:
            detail = (
                f"no entry under {CACHE_KEY} — it had expired or was never filled; "
                f"the next read still refills from the origin"
            )
        logger.info("caching_invalidated", key=CACHE_KEY, deleted=deleted)
        return InvalidationRow(
            key=CACHE_KEY,
            deleted_entries=deleted,
            telemetry=self._telemetry(),
            detail=detail,
        )

    async def state(self) -> CacheStateRow:
        """The state panel's facts: liveness, size, ETag, and counters.

        The value's GET is the truth for presence: if the entry expires
        between the TTL read and the GET, the row reports absent — no
        countdown for a value that no longer exists.
        """
        ttl_remaining = await self._store.ttl(CACHE_KEY)
        value = None if ttl_remaining is None else await self._store.get(CACHE_KEY)
        present = value is not None
        return CacheStateRow(
            key=CACHE_KEY,
            present=present,
            ttl_seconds=TTL_SECONDS,
            ttl_remaining_s=ttl_remaining if present else None,
            size_bytes=None if value is None else len(value.encode("utf-8")),
            etag=None if value is None else compute_etag(value),
            last_outcome=self._last_outcome,
            telemetry=self._telemetry(),
        )

    async def stampede(self, requests: int) -> StampedeRow:
        """Cold-start, then N concurrent reads — exactly one origin fill.

        Determinism comes from the lock, not from sleeps: every request
        misses its first GET, queues on the per-key lock, and the first
        lock holder's fill lands before any waiter re-checks — so the
        counts are pinned (one origin fetch, the rest served warm) no
        matter how the event loop interleaves the waiters.
        """
        await self._store.delete(CACHE_KEY)
        started = time.monotonic()
        fetched = await asyncio.gather(*(self.fetch_page() for _ in range(requests)))
        wall_ms = self._elapsed_ms(started)
        rounds = [
            StampedeRequestRow(index=index, outcome=row.outcome, elapsed_ms=row.elapsed_ms)
            for index, row in enumerate(fetched)
        ]
        origin_fetches = sum(1 for row in fetched if row.outcome == "miss")
        served_warm = requests - origin_fetches
        proof = (
            f"{requests} concurrent requests against a cold cache produced exactly "
            f"{origin_fetches} origin fetch — the per-key lock let one request fill "
            f"while {served_warm} waited and were served warm, wall time {wall_ms} ms "
            f"instead of {requests} x {ORIGIN_COST_MS} ms serialized"
        )
        return StampedeRow(
            requests=requests,
            origin_fetches=origin_fetches,
            served_warm=served_warm,
            wall_ms=wall_ms,
            rounds=rounds,
            proof=proof,
        )

    async def _fetch_origin(self) -> str:
        """The expensive path, honestly labeled: simulated cost + the real use case.

        The sleep comes FIRST (it is the cost being simulated); the use
        case and its canonical serialization are the real substrate. The
        JSON string is what gets cached AND what the endpoint serves, so
        cache bytes and response bytes can never drift.
        """
        await asyncio.sleep(ORIGIN_COST_MS / 1000)
        result = self._posts.list_posts.execute(ORIGIN_QUERY)
        if isinstance(result, Err):
            raise result.failure
        return result.value.model_dump_json(by_alias=True)

    async def _serve_from_store(
        self, payload: str, started: float, coalesced: bool
    ) -> CacheFetchRow:
        """Account a store-served read; age comes from the TTL clock.

        The age is SECOND-granular TTL arithmetic (configured TTL minus
        the seconds remaining) — honest about its precision, and the race
        where the entry expires between the GET and the TTL read simply
        answers None (no age for a value that no longer exists).
        """
        outcome: Literal["hit", "coalesced"] = "coalesced" if coalesced else "hit"
        if coalesced:
            self._coalesced += 1
        else:
            self._hits += 1
        self._last_outcome = outcome
        ttl_remaining = await self._store.ttl(CACHE_KEY)
        age_ms = (
            None
            if ttl_remaining is None
            else max(0, TTL_SECONDS - ttl_remaining) * 1000
        )
        return CacheFetchRow(
            outcome=outcome,
            key=CACHE_KEY,
            payload=payload,
            etag=compute_etag(payload),
            elapsed_ms=self._elapsed_ms(started),
            age_ms=age_ms,
            telemetry=self._telemetry(),
        )

    def _lock_for(self, key: str) -> asyncio.Lock:
        """The per-key single-flight lock (this lab has exactly one key)."""
        lock = self._origin_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._origin_locks[key] = lock
        return lock

    def _telemetry(self) -> CacheTelemetryRow:
        return CacheTelemetryRow(
            hits=self._hits,
            misses=self._misses,
            coalesced=self._coalesced,
            invalidations=self._invalidations,
        )

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return round((time.monotonic() - started) * 1000)
